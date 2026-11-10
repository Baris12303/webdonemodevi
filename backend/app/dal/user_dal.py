from typing import Optional, Dict, Any
import pymysql
from app.db import get_replica_connection, get_primary_connection, handle_mysql_error, mark_primary_write


class UserDAL:
    @staticmethod
    def get_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Giriş doğrulaması için kullanıcıyı getirir (Okuma: Replica)"""
        with get_replica_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, ogrenci_no, ad, soyad, eposta, sifre_hash, rol, bakiye FROM kullanicilar WHERE eposta = %s",
                    (email,),
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
                    (user_id,),
                )
                user = cursor.fetchone()
                if user:
                    user["bakiye"] = float(user["bakiye"])
                return user

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
                    (user_id,),
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
                            (user_id, a_id),
                        )
                conn.commit()
                mark_primary_write(conn)
                return True
            except pymysql.MySQLError as e:
                conn.rollback()
                handle_mysql_error(e, "UserDAL.update_user_allergens")
            except Exception:
                conn.rollback()
                raise
