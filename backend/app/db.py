import queue
import logging
import threading
from contextlib import contextmanager
import pymysql
import pymysql.cursors
from app.config import settings

logger = logging.getLogger("db")


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
def get_replica_connection():
    """Okuma işlemleri ve View sorguları için İkincil (Salt Okunur) Veritabanı"""
    conn = replica_pool.get_connection()
    try:
        yield conn
    finally:
        replica_pool.release_connection(conn)
