from typing import List, Dict, Any
import pymysql
from app.db import get_primary_connection, get_replica_connection, handle_mysql_error


class BalanceDAL:
    @staticmethod
    def top_up_balance(kullanici_id: int, miktar: float) -> float:
        """Kullanıcı bakiyesine yükleme yapar (sp_bakiye_yukle çağrılır)"""
        with get_primary_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("CALL sp_bakiye_yukle(%s, %s);", (kullanici_id, miktar))
                    cursor.execute("SELECT bakiye FROM kullanicilar WHERE id = %s;", (kullanici_id,))
                    row = cursor.fetchone()
                    guncel_bakiye = float(row["bakiye"]) if row else 0.0
                conn.commit()
                return guncel_bakiye
            except pymysql.MySQLError as e:
                conn.rollback()
                handle_mysql_error(e, "BalanceDAL.top_up_balance")
            except Exception:
                conn.rollback()
                raise

    @staticmethod
    def get_balance_movements(kullanici_id: int) -> List[Dict[str, Any]]:
        """Kullanıcının bakiye hareket geçmişini listeler (Okuma: Replica)"""
        with get_replica_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, miktar, hareket_tipi, aciklama, tarih, rezervasyon_id
                    FROM bakiye_hareketleri
                    WHERE kullanici_id = %s
                    ORDER BY tarih DESC;
                    """,
                    (kullanici_id,),
                )
                rows = cursor.fetchall()
                for r in rows:
                    r["miktar"] = float(r["miktar"])
                return rows
