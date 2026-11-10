import json
import logging
from datetime import datetime, time
import redis
from app.config import settings, now_tr, TURKEY_TZ

logger = logging.getLogger("redis")

# Redis Bağlantısı
r = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True,
    socket_connect_timeout=3,
    socket_timeout=3,
)


def get_seconds_until_end_of_day() -> int:
    """Günün sonuna (23:59:59 TRT) kadar kalan saniye sayısını hesaplar"""
    now = now_tr()
    end_of_day = datetime.combine(now.date(), time(23, 59, 59), tzinfo=TURKEY_TZ)
    seconds = int((end_of_day - now).total_seconds())
    return max(seconds, 60)


# -----------------------------------------------------
# Oturum (Session) Yönetimi
# Anahtar Formatı: oturum:{token}
# Süre: 30 Dakika (Her istekte yenilenir - Sliding Expiration)
# -----------------------------------------------------

def create_session(token: str, user_data: dict) -> bool:
    key = f"oturum:{token}"
    val = json.dumps(user_data, default=str)
    r.set(key, val, ex=settings.SESSION_EXPIRE_SECONDS)
    return True


def get_session(token: str) -> dict | None:
    if not token:
        return None
    key = f"oturum:{token}"
    data = r.get(key)
    if not data:
        return None

    try:
        parsed = json.loads(data)
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning(f"Corrupt session payload in Redis for {key}: {e}")
        try:
            r.delete(key)
        except redis.RedisError as del_err:
            logger.warning(f"Failed to delete corrupt session key {key}: {del_err}")
        return None

    if not isinstance(parsed, dict) or not parsed:
        logger.warning(f"Invalid session payload in Redis for {key}: {type(parsed).__name__}")
        try:
            r.delete(key)
        except redis.RedisError as del_err:
            logger.warning(f"Failed to delete invalid session key {key}: {del_err}")
        return None

    # Her istekte oturum süresini 30 dk yenile
    r.expire(key, settings.SESSION_EXPIRE_SECONDS)
    return parsed


def delete_session(token: str) -> bool:
    if not token:
        return False
    key = f"oturum:{token}"
    return bool(r.delete(key))


# -----------------------------------------------------
# Menü Önbelleği (Menu Caching)
# Anahtar Formatı: menu:{yemekhane_id}:{tarih}:{ogun_id}
# Süre: Gün sonuna kadar
# Silinme: Yönetici menüyü güncellediğinde veya doluluk/puan değiştiğinde
# -----------------------------------------------------

def get_cached_menu(yemekhane_id: int, tarih: str, ogun_id: int) -> dict | None:
    key = f"menu:{yemekhane_id}:{tarih}:{ogun_id}"
    try:
        data = r.get(key)
    except redis.RedisError as e:
        logger.warning(f"Redis get_cached_menu error for {key}: {e}")
        return None

    if not data:
        logger.info(f"[CACHE MISS] Menü Redis'te yok, DB'den okunacak: {key}")
        return None

    try:
        parsed = json.loads(data)
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning(f"Corrupt menu cache payload in Redis for {key}: {e}")
        try:
            r.delete(key)
        except redis.RedisError as del_err:
            logger.warning(f"Failed to delete corrupt menu cache key {key}: {del_err}")
        return None

    if not isinstance(parsed, dict) or not parsed:
        logger.warning(f"Invalid menu cache payload in Redis for {key}: {type(parsed).__name__}")
        try:
            r.delete(key)
        except redis.RedisError as del_err:
            logger.warning(f"Failed to delete invalid menu cache key {key}: {del_err}")
        return None

    logger.info(f"[CACHE HIT] Menü Redis'ten getirildi: {key}")
    return parsed


def set_cached_menu(yemekhane_id: int, tarih: str, ogun_id: int, menu_data: dict) -> bool:
    key = f"menu:{yemekhane_id}:{tarih}:{ogun_id}"
    ttl = get_seconds_until_end_of_day()
    try:
        val = json.dumps(menu_data, default=str)
        r.set(key, val, ex=ttl)
        logger.info(f"[CACHE SET] Menü Redis'e yazıldı: {key} (TTL: {ttl} sn)")
        return True
    except redis.RedisError as e:
        logger.warning(f"Redis set_cached_menu error for {key}: {e}")
        return False


def invalidate_menu_cache(yemekhane_id: int, tarih: str, ogun_id: int) -> bool:
    key = f"menu:{yemekhane_id}:{tarih}:{ogun_id}"
    try:
        res = r.delete(key)
        logger.info(f"[CACHE INVALIDATED] Menü önbellekten silindi: {key}")
        return bool(res)
    except redis.RedisError as e:
        logger.warning(f"Redis invalidate_menu_cache error for {key}: {e}")
        return False
