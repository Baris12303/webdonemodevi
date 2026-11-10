from typing import List, Dict, Any
import pymysql
from app.db import get_primary_connection, get_replica_connection, handle_mysql_error, mark_primary_write


class ReviewDAL:
    @staticmethod
    def add_review(kullanici_id: int, menu_id: int, puan: int, yorum: str | None) -> int:
        """Kullanılmış bir menüye değerlendirme ekler (Yazma: Primary)"""
        with get_primary_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM rezervasyonlar WHERE kullanici_id = %s AND menu_id = %s AND durum = 'kullanildi';",
                        (kullanici_id, menu_id),
                    )
                    used = cursor.fetchone()
                    if not used:
                        raise ValueError("Yalnızca kullanılmış (turnikeden geçilmiş) menülere değerlendirme yapabilirsiniz.")

                    cursor.execute(
                        "SELECT id FROM degerlendirmeler WHERE kullanici_id = %s AND menu_id = %s;",
                        (kullanici_id, menu_id),
                    )
                    if cursor.fetchone():
                        raise ValueError("Bu menüye zaten değerlendirme yaptınız.")

                    cursor.execute(
                        """
                        INSERT INTO degerlendirmeler (kullanici_id, menu_id, puan, yorum, tarih)
                        VALUES (%s, %s, %s, %s, NOW());
                        """,
                        (kullanici_id, menu_id, puan, yorum),
                    )
                    review_id = cursor.lastrowid
                conn.commit()
                mark_primary_write(conn)
                return review_id
            except pymysql.MySQLError as e:
                conn.rollback()
                handle_mysql_error(e, "ReviewDAL.add_review")
            except Exception:
                conn.rollback()
                raise

    @staticmethod
    def get_menu_reviews(menu_id: int) -> List[Dict[str, Any]]:
        """Menüye ait değerlendirmeleri listeler (Okuma: Replica)"""
        with get_replica_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT d.id, CONCAT(k.ad, ' ', SUBSTRING(k.soyad, 1, 1), '.') as kullanici_ad_soyad,
                           d.menu_id, d.puan, d.yorum, d.tarih
                    FROM degerlendirmeler d
                    JOIN kullanicilar k ON d.kullanici_id = k.id
                    WHERE d.menu_id = %s
                    ORDER BY d.tarih DESC, d.id DESC;
                    """,
                    (menu_id,),
                )
                return cursor.fetchall()
