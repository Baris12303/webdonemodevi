from typing import List, Dict, Any, Optional
import pymysql
from app.db import get_primary_connection, get_replica_connection, handle_mysql_error


class ReservationDAL:
    @staticmethod
    def make_reservation(kullanici_id: int, menu_id: int, porsiyon: str = "tam") -> Dict[str, Any]:
        """Rezervasyon oluşturma ve bakiye düşümü (sp_rezervasyon_yap çağrılır)"""
        with get_primary_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("CALL sp_rezervasyon_yap(%s, %s, %s);", (kullanici_id, menu_id, porsiyon))

                    cursor.execute(
                        "SELECT id FROM rezervasyonlar WHERE kullanici_id = %s AND menu_id = %s AND durum = 'aktif';",
                        (kullanici_id, menu_id),
                    )
                    rez_row = cursor.fetchone()
                    rez_id = rez_row["id"] if rez_row else 0

                    cursor.execute("SELECT bakiye FROM kullanicilar WHERE id = %s;", (kullanici_id,))
                    user_row = cursor.fetchone()
                    guncel_bakiye = float(user_row["bakiye"]) if user_row else 0.0

                conn.commit()
                return {
                    "rezervasyon_id": rez_id,
                    "guncel_bakiye": guncel_bakiye,
                }
            except pymysql.MySQLError as e:
                conn.rollback()
                handle_mysql_error(e, "ReservationDAL.make_reservation")
            except Exception:
                conn.rollback()
                raise

    @staticmethod
    def get_reservation_menu_coords(rezervasyon_id: int) -> Optional[Dict[str, Any]]:
        """Önbellek geçersizleştirme için rezervasyonun menü koordinatlarını döndürür"""
        with get_primary_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT m.yemekhane_id, m.tarih, m.ogun_id
                    FROM rezervasyonlar r
                    JOIN menuler m ON r.menu_id = m.id
                    WHERE r.id = %s;
                    """,
                    (rezervasyon_id,),
                )
                return cursor.fetchone()

    @staticmethod
    def cancel_reservation(kullanici_id: int, rezervasyon_id: int) -> float:
        """Rezervasyon iptali ve ücret iadesi (sp_rezervasyon_iptal çağrılır)"""
        with get_primary_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("CALL sp_rezervasyon_iptal(%s, %s);", (kullanici_id, rezervasyon_id))
                    cursor.execute("SELECT bakiye FROM kullanicilar WHERE id = %s;", (kullanici_id,))
                    user_row = cursor.fetchone()
                    guncel_bakiye = float(user_row["bakiye"]) if user_row else 0.0
                conn.commit()
                return guncel_bakiye
            except pymysql.MySQLError as e:
                conn.rollback()
                handle_mysql_error(e, "ReservationDAL.cancel_reservation")
            except Exception:
                conn.rollback()
                raise

    @staticmethod
    def get_user_reservations(kullanici_id: int) -> List[Dict[str, Any]]:
        """Kullanıcının geçmiş ve aktif rezervasyonlarını listeler (Okuma: Replica)"""
        with get_replica_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                SELECT 
                    r.id,
                    r.kullanici_id,
                    r.menu_id,
                    m.tarih,
                    og.ad as ogun_adi,
                    yh.ad as yemekhane_adi,
                    r.ucret,
                    r.porsiyon,
                    r.durum,
                    (r.durum = 'aktif' AND NOW() <= TIMESTAMP(m.tarih, og.son_saat)) as iptal_edilebilir_mi,
                    r.olusturulma_tarihi,
                    r.iptal_tarihi,
                    r.kullanilma_tarihi,
                    d.yemek_listesi,
                    EXISTS(SELECT 1 FROM degerlendirmeler deg WHERE deg.kullanici_id = r.kullanici_id AND deg.menu_id = r.menu_id) as degerlendirildi_mi
                FROM rezervasyonlar r
                JOIN menuler m ON r.menu_id = m.id
                JOIN yemekhaneler yh ON m.yemekhane_id = yh.id
                JOIN ogunler og ON m.ogun_id = og.id
                LEFT JOIN v_menu_detay d ON m.id = d.menu_id
                WHERE r.kullanici_id = %s
                ORDER BY r.olusturulma_tarihi DESC;
                """
                cursor.execute(query, (kullanici_id,))
                rows = cursor.fetchall()
                for r in rows:
                    r["ucret"] = float(r["ucret"])
                    r["iptal_edilebilir_mi"] = bool(r["iptal_edilebilir_mi"])
                    r["degerlendirildi_mi"] = bool(r["degerlendirildi_mi"])
                return rows
