import queue
import logging
import threading
import time
from contextlib import contextmanager
import pymysql
import pymysql.cursors
from app.config import settings

logger = logging.getLogger("db")

_gtid_lock = threading.Lock()
_last_write_gtid: str = ""
_last_write_ts: float = 0.0
_tls = threading.local()


def mark_primary_write(conn) -> None:
    """Son primary yazma işleminin GTID kümesini kaydeder."""
    global _last_write_gtid, _last_write_ts
    try:
        with _gtid_lock:
            with conn.cursor() as cursor:
                cursor.execute("SELECT @@GLOBAL.GTID_EXECUTED AS gtid;")
                row = cursor.fetchone()
            gtid = (row or {}).get("gtid") if isinstance(row, dict) else None
            if gtid:
                _last_write_gtid = str(gtid).strip()
                _last_write_ts = time.monotonic()
    except Exception as e:
        logger.warning("Failed to record primary GTID: %s", e)


def _sync_replica_to_last_write(conn) -> bool:
    """Replika bağlantısının son yazma GTID'sine yetişmesini bekler."""
    global _last_write_gtid
    with _gtid_lock:
        target_gtid = _last_write_gtid
        write_ts = _last_write_ts

    if not target_gtid or (time.monotonic() - write_ts) > 10.0:
        return True

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT WAIT_FOR_EXECUTED_GTID_SET(%s, 2) AS timed_out;", (target_gtid,))
            row = cursor.fetchone()
        conn.rollback()
        timed_out = int((row or {}).get("timed_out", 0)) if isinstance(row, dict) else 0
        if timed_out == 0:
            with _gtid_lock:
                if _last_write_gtid == target_gtid:
                    _last_write_gtid = ""
            return True
        logger.warning("Replica did not catch up to GTID %s within 2s", target_gtid)
        return False
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        logger.warning("Replica GTID sync check failed: %s", e)
        return False


def is_replica_synced() -> bool:
    return getattr(_tls, "last_replica_synced", True)


def handle_mysql_error(e: pymysql.MySQLError, context: str):
    """MySQL hatalarını iş kuralı (SQLSTATE 45000 / bütünlük) veya sistem hatasına ayırır."""
    errno = e.args[0] if e.args else None
    msg = str(e.args[1]) if len(e.args) > 1 else str(e)
    if errno == 1644:
        raise ValueError(msg)
    if errno == 1062:
        logger.warning("Duplicate key error in %s: %s", context, msg)
        raise ValueError("Bu kayıt zaten mevcut.")
    if errno == 1452:
        logger.warning("Foreign key error in %s: %s", context, msg)
        raise ValueError("Geçersiz referans kimliği.")
    logger.exception("Unexpected DB error in %s: %s", context, e)
    raise RuntimeError("Veritabanı işlemi sırasında beklenmeyen bir hata oluştu.")


class ConnectionPool:
    def __init__(self, host: str, port: int, user: str, password: str, db: str, pool_size: int = 10):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db = db
        self.pool_size = pool_size
        self._pool = queue.Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._created = 0

    def _create_connection(self):
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.db,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
            connect_timeout=5,
            read_timeout=15,
            write_timeout=15,
        )

    def get_connection(self):
        conn = None
        try:
            conn = self._pool.get_nowait()
        except queue.Empty:
            create_new = False
            with self._lock:
                if self._created < self.pool_size:
                    self._created += 1
                    create_new = True
            if create_new:
                try:
                    return self._create_connection()
                except Exception:
                    with self._lock:
                        self._created = max(0, self._created - 1)
                    raise
            try:
                conn = self._pool.get(timeout=5)
            except queue.Empty:
                raise RuntimeError("Veritabanı bağlantı havuzu dolu.")

        try:
            conn.ping(reconnect=True)
            return conn
        except (pymysql.err.OperationalError, pymysql.err.InterfaceError, OSError):
            try:
                conn.close()
            except Exception:
                pass
            try:
                return self._create_connection()
            except Exception:
                with self._lock:
                    self._created = max(0, self._created - 1)
                raise

    def release_connection(self, conn):
        if conn is None:
            return
        if conn.open:
            try:
                conn.rollback()
                self._pool.put_nowait(conn)
                return
            except queue.Full:
                pass
            except Exception:
                pass
        try:
            conn.close()
        except Exception:
            pass
        with self._lock:
            self._created = max(0, self._created - 1)


primary_pool = ConnectionPool(
    host=settings.DB_PRIMARY_HOST,
    port=settings.DB_PRIMARY_PORT,
    user=settings.DB_USER,
    password=settings.DB_PASSWORD,
    db=settings.DB_NAME,
    pool_size=10,
)

replica_pool = ConnectionPool(
    host=settings.DB_REPLICA_HOST,
    port=settings.DB_REPLICA_PORT,
    user=settings.DB_USER,
    password=settings.DB_PASSWORD,
    db=settings.DB_NAME,
    pool_size=15,
)


@contextmanager
def get_primary_connection():
    """Yazma işlemleri ve Stored Procedure çağrıları için Birincil Veritabanı"""
    conn = primary_pool.get_connection()
    try:
        yield conn
    finally:
        primary_pool.release_connection(conn)


@contextmanager
def get_replica_connection(wait_sync: bool = True):
    """Okuma işlemleri ve View sorguları için İkincil (Salt Okunur) Veritabanı"""
    conn = replica_pool.get_connection()
    try:
        _tls.last_replica_synced = _sync_replica_to_last_write(conn) if wait_sync else True
        yield conn
    finally:
        replica_pool.release_connection(conn)
