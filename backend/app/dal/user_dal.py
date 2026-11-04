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

    @staticmethod
    def get_all_allergens():
        """Tüm alerjenlerin listesi (Okuma: Replica)"""
        with get_replica_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, ad FROM alerjenler ORDER BY id ASC;")
                return cursor.fetchall()

    @staticmethod
    def get_user_allergens(user_id: int):
        """Kullanıcının seçtiği alerjen ID'leri (Okuma: Replica)"""
        with get_replica_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT alerjen_id FROM kullanici_alerjenleri WHERE kullanici_id = %s;",
                    (user_id,)
                )
                return [row["alerjen_id"] for row in cursor.fetchall()]

    @staticmethod
    def update_user_allergens(user_id: int, allergen_ids: list[int]):
        """Kullanıcının alerjen tercihlerini günceller (Yazma: Primary)"""
        with get_primary_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM kullanici_alerjenleri WHERE kullanici_id = %s;", (user_id,))
                    for a_id in allergen_ids:
                        cursor.execute(
                            "INSERT INTO kullanici_alerjenleri (kullanici_id, alerjen_id) VALUES (%s, %s);",
                            (user_id, a_id)
                        )
                conn.commit()
                return True
            except Exception:
                conn.rollback()
                raise

