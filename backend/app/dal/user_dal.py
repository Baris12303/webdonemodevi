from typing import Optional, Dict, Any
from app.db import get_replica_connection, get_primary_connection

class UserDAL:
    @staticmethod
    def get_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Giriş doğrulaması için kullanıcıyı getirir (Okuma: Replica)"""
        with get_replica_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, ogrenci_no, ad, soyad, eposta, sifre_hash, rol, bakiye FROM kullanicilar WHERE eposta = %s",
                    (email,)
                )
                return cursor.fetchone()

    @staticmethod
    def get_by_id(user_id: int, use_primary: bool = False) -> Optional[Dict[str, Any]]:
        """Kullanıcı bilgilerini getirir. use_primary=True ise Replication Lag önlemek için Primary'den okur"""
        context_mgr = get_primary_connection if use_primary else get_replica_connection
        with context_mgr() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, ogrenci_no, ad, soyad, eposta, rol, bakiye FROM kullanicilar WHERE id = %s",
                    (user_id,)
                )
                return cursor.fetchone()

