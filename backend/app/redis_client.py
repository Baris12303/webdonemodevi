import json
import logging
from datetime import datetime, time
import redis
from app.config import settings

logger = logging.getLogger("redis")

# Redis Bağlantısı
r = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True
)

def get_seconds_until_end_of_day() -> int:
    """Günün sonuna (23:59:59) kadar kalan saniye sayısını hesaplar"""
    now = datetime.now()
    end_of_day = datetime.combine(now.date(), time(23, 59, 59))
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
    if data:
        # Sliding Expiration: Her başarılı istekte süreyi 30 dakika daha uzat
        r.expire(key, settings.SESSION_EXPIRE_SECONDS)
        return json.loads(data)
    return None

def delete_session(token: str) -> bool:
    if not token:
        return False
    key = f"oturum:{token}"
    return bool(r.delete(key))

# -----------------------------------------------------
# Menü Önbelleği (Menu Caching)
# Anahtar Formatı: menu:{yemekhane_id}:{tarih}:{ogun_id}
# Süre: Gün sonuna kadar
# Silinme: Yönetici menüyü güncellediğinde (Cache Invalidation)
# -----------------------------------------------------

def get_cached_menu(yemekhane_id: int, tarih: str, ogun_id: int) -> dict | None:
    key = f"menu:{yemekhane_id}:{tarih}:{ogun_id}"
    data = r.get(key)
    if data:
        logger.info(f"[CACHE HIT] Menü Redis'ten getirildi: {key}")
        return json.loads(data)
    logger.info(f"[CACHE MISS] Menü Redis'te yok, DB'den okunacak: {key}")
    return None

def set_cached_menu(yemekhane_id: int, tarih: str, ogun_id: int, menu_data: dict) -> bool:
    key = f"menu:{yemekhane_id}:{tarih}:{ogun_id}"
    ttl = get_seconds_until_end_of_day()
    val = json.dumps(menu_data, default=str)
    r.set(key, val, ex=ttl)
    logger.info(f"[CACHE SET] Menü Redis'e yazıldı: {key} (TTL: {ttl} sn)")
    return True

def invalidate_menu_cache(yemekhane_id: int, tarih: str, ogun_id: int) -> bool:
    key = f"menu:{yemekhane_id}:{tarih}:{ogun_id}"
    res = r.delete(key)
    logger.info(f"[CACHE INVALIDATED] Menü önbellekten silindi: {key}")
    return bool(res)

