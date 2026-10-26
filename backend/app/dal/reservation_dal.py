from typing import List, Dict, Any, Optional
import pymysql
from app.db import get_primary_connection, get_replica_connection

class ReservationDAL:
    @staticmethod
    def make_reservation(kullanici_id: int, menu_id: int) -> Dict[str, Any]:
        """
        Rezervasyon yapma işlemi (Yazma: Primary).
        Doğrudan SQL yazılmaz; sp_rezervasyon_yap Stored Procedure'ü çağrılır!
        Hata durumunda SQLSTATE 45000 mesajı fırlatılır.
        İşlemden sonra kullanıcının bakiyesi REPLIKASYON GECİKMESİ OLMAMASI İÇİN
        doğrudan PRIMARY sunucudan okunur.
        """
        with get_primary_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    # Stored Procedure Çağrısı
                    cursor.execute("CALL sp_rezervasyon_yap(%s, %s);", (kullanici_id, menu_id))
                    
                    # Oluşturulan rezervasyon id'sini ve anlık güncel bakiyeyi PRIMARY'den oku
                    cursor.execute(
                        "SELECT id FROM rezervasyonlar WHERE kullanici_id = %s AND menu_id = %s AND durum = 'aktif';",
                        (kullanici_id, menu_id)
                    )
                    rez_row = cursor.fetchone()
                    rez_id = rez_row["id"] if rez_row else 0

                    cursor.execute("SELECT bakiye FROM kullanicilar WHERE id = %s;", (kullanici_id,))
                    user_row = cursor.fetchone()
                    guncel_bakiye = float(user_row["bakiye"]) if user_row else 0.0

                conn.commit()
                return {
                    "rezervasyon_id": rez_id,
                    "guncel_bakiye": guncel_bakiye
                }
            except pymysql.MySQLError as e:
                conn.rollback()
                # SQLSTATE 45000 ve diğer MySQL hata yakalama
                error_msg = str(e.args[1]) if len(e.args) > 1 else str(e)
                raise ValueError(error_msg)

    @staticmethod
    def cancel_reservation(kullanici_id: int, rezervasyon_id: int) -> float:
        """
        Rezervasyon iptal işlemi (Yazma: Primary).
        sp_rezervasyon_iptal Stored Procedure'ü çağrılır.
        İade sonrası güncel bakiye PRIMARY'den okunur.
        """
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
                error_msg = str(e.args[1]) if len(e.args) > 1 else str(e)
                raise ValueError(error_msg)

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
                    r["iptal_edilebilir_mi"] = bool(r["iptal_edilebilir_mi"])
                    r["degerlendirildi_mi"] = bool(r["degerlendirildi_mi"])
                return rows

