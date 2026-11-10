import logging
import pymysql
import redis
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.db import get_primary_connection, get_replica_connection
from app.redis_client import r
from app.routers import auth, menus, reservations, balance, reviews, admin

# Log yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app")

app = FastAPI(
    title="Kampüs Yemekhane Otomasyonu API",
    version="1.0.0",
    description="Mikroservis Mimarisine Sahip Kampüs Yemekhane Yönetim Sistemi REST API",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    logger.error("RuntimeError on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(pymysql.MySQLError)
async def mysql_error_handler(request: Request, exc: pymysql.MySQLError):
    logger.exception("Unhandled MySQLError on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Veritabanı servisine şu anda ulaşılamıyor."},
    )


@app.exception_handler(redis.RedisError)
async def redis_error_handler(request: Request, exc: redis.RedisError):
    logger.exception("RedisError on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Oturum/Önbellek servisine şu anda ulaşılamıyor."},
    )


# Router'ları ekle
app.include_router(auth.router)
app.include_router(menus.router)
app.include_router(reservations.router)
app.include_router(balance.router)
app.include_router(reviews.router)
app.include_router(admin.router)


@app.get("/api/health", tags=["Sağlık"])
def health_check():
    primary_status = "ok"
    replica_status = "ok"
    redis_status = "ok"

    try:
        with get_primary_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1;")
    except Exception as e:
        logger.warning("Healthcheck primary error: %s", e)
        primary_status = "error"

    try:
        with get_replica_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1;")
    except Exception as e:
        logger.warning("Healthcheck replica degraded: %s", e)
        replica_status = "degraded"

    try:
        if not r.ping():
            redis_status = "error"
    except Exception as e:
        logger.warning("Healthcheck redis error: %s", e)
        redis_status = "error"

    healthy = primary_status == "ok" and redis_status == "ok"
    payload = {
        "status": "ok" if healthy else "error",
        "service": "yemekhane-backend",
        "primary": primary_status,
        "replica": replica_status,
        "redis": redis_status,
    }
    if not healthy:
        return JSONResponse(status_code=503, content=payload)
    return payload
