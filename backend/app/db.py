import queue
import logging
from contextlib import contextmanager
import pymysql
import pymysql.cursors
from app.config import settings

logger = logging.getLogger("db")

class ConnectionPool:
    def __init__(self, host: str, port: int, user: str, password: str, db: str, pool_size: int = 10):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db = db
        self.pool_size = pool_size
        self._pool = queue.Queue(maxsize=pool_size)
        
        # Havuzu doldur
        for _ in range(pool_size):
            conn = self._create_connection()
            self._pool.put(conn)

    def _create_connection(self):
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.db,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False
        )

    def get_connection(self):
        try:
            conn = self._pool.get(timeout=5)
            # Bağlantının canlı olup olmadığını test et
            conn.ping(reconnect=True)
            return conn
        except Exception:
            return self._create_connection()

    def release_connection(self, conn):
        try:
            if conn and conn.open:
                self._pool.put_nowait(conn)
            else:
                self._pool.put_nowait(self._create_connection())
        except queue.Full:
            try:
                conn.close()
            except Exception:
                pass

primary_pool = ConnectionPool(
    host=settings.DB_PRIMARY_HOST,
    port=settings.DB_PRIMARY_PORT,
    user=settings.DB_USER,
    password=settings.DB_PASSWORD,
    db=settings.DB_NAME,
    pool_size=10
)

replica_pool = ConnectionPool(
    host=settings.DB_REPLICA_HOST,
    port=settings.DB_REPLICA_PORT,
    user=settings.DB_USER,
    password=settings.DB_PASSWORD,
    db=settings.DB_NAME,
    pool_size=15
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

