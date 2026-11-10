from typing import List, Dict, Any, Optional
from datetime import date
import pymysql
from app.db import get_replica_connection, get_primary_connection, handle_mysql_error


class MenuDAL:
    @staticmethod
    def get_menu_detail(yemekhane_id: int, tarih: date, ogun_id: int) -> Optional[Dict[str, Any]]:
        """Günün menü detayını view'lardan birleştirerek getirir (Okuma: Replica)"""
        with get_replica_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                SELECT 
                    d.menu_id,
                    d.yemekhane_id,
                    d.yemekhane_adi,
                    d.yemekhane_kapasitesi,
                    d.tarih,
                    d.ogun_id,
                    d.ogun_adi,
                    TIME_FORMAT(d.ogun_son_saat, '%%H:%%i') as ogun_son_saat,
                    d.ogrenci_fiyati,
                    d.personel_fiyati,
                    d.toplam_kalori,
                    COALESCE(dol.kalan_kapasite, d.yemekhane_kapasitesi) as kalan_kapasite,
                    COALESCE(dol.doluluk_orani, 0.0) as doluluk_orani,
                    COALESCE(p.ortalama_puan, 0.0) as ortalama_puan,
                    COALESCE(p.degerlendirme_sayisi, 0) as degerlendirme_sayisi
                FROM v_menu_detay d
                LEFT JOIN v_menu_doluluk dol ON d.menu_id = dol.menu_id
                LEFT JOIN v_menu_puan p ON d.menu_id = p.menu_id
                WHERE d.yemekhane_id = %s AND d.tarih = %s AND d.ogun_id = %s
                LIMIT 1;
                """
                cursor.execute(query, (yemekhane_id, tarih, ogun_id))
                menu = cursor.fetchone()
                if not menu:
                    return None

                menu["ogrenci_fiyati"] = float(menu["ogrenci_fiyati"])
                menu["personel_fiyati"] = float(menu["personel_fiyati"])
                menu["toplam_kalori"] = int(menu["toplam_kalori"])
                menu["kalan_kapasite"] = int(menu["kalan_kapasite"])
                menu["doluluk_orani"] = float(menu["doluluk_orani"])
                menu["ortalama_puan"] = float(menu["ortalama_puan"])
                menu["degerlendirme_sayisi"] = int(menu["degerlendirme_sayisi"])

                menu["yemekler"] = MenuDAL._get_menu_dishes(conn, menu["menu_id"])

                tum_alerjenler = set()
                vejetaryen = True
                for y in menu["yemekler"]:
                    for al in y["alerjenler"]:
                        tum_alerjenler.add(al)
                    if not y["vejetaryen_mi"]:
                        vejetaryen = False

                menu["tum_alerjenler"] = sorted(list(tum_alerjenler))
                menu["vejetaryen_mi"] = vejetaryen
                return menu

    @staticmethod
    def get_menu_cache_coords(menu_id: int) -> Optional[Dict[str, Any]]:
        """Önbellek geçersizleştirme için menünün (yemekhane_id, tarih, ogun_id) koordinatlarını döndürür"""
        with get_primary_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT yemekhane_id, tarih, ogun_id FROM menuler WHERE id = %s;",
                    (menu_id,),
                )
                return cursor.fetchone()

    @staticmethod
    def _get_menu_dishes(conn, menu_id: int) -> List[Dict[str, Any]]:
        with conn.cursor() as cursor:
            query = """
            SELECT 
                y.id,
                y.ad,
                y.kalori,
                y.vejetaryen_mi,
                yk.ad as kategori_adi,
                yk.sira as kategori_sira,
                GROUP_CONCAT(a.ad ORDER BY a.ad SEPARATOR ', ') as alerjen_str
            FROM menu_yemekleri my
            JOIN yemekler y ON my.yemek_id = y.id
            JOIN yemek_kategorileri yk ON y.kategori_id = yk.id
            LEFT JOIN yemek_alerjenleri ya ON y.id = ya.yemek_id
            LEFT JOIN alerjenler a ON ya.alerjen_id = a.id
            WHERE my.menu_id = %s
            GROUP BY y.id, y.ad, y.kalori, y.vejetaryen_mi, yk.ad, yk.sira
            ORDER BY yk.sira ASC;
            """
            cursor.execute(query, (menu_id,))
            rows = cursor.fetchall()
            for r in rows:
                r["vejetaryen_mi"] = bool(r["vejetaryen_mi"])
                r["alerjenler"] = r["alerjen_str"].split(", ") if r["alerjen_str"] else []
                del r["alerjen_str"]
            return rows

    @staticmethod
    def get_weekly_menus(yemekhane_id: int, baslangic_tarihi: date, bitis_tarihi: date) -> List[Dict[str, Any]]:
        """Haftalık menü listesi ve doluluk bilgileri (Okuma: Replica)"""
        with get_replica_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                SELECT 
                    d.menu_id,
                    d.yemekhane_id,
                    d.yemekhane_adi,
                    d.tarih,
                    d.ogun_id,
                    d.ogun_adi,
                    TIME_FORMAT(d.ogun_son_saat, '%%H:%%i') as ogun_son_saat,
                    d.ogrenci_fiyati,
                    d.personel_fiyati,
                    d.toplam_kalori,
                    d.yemek_listesi,
                    d.alerjenler,
                    COALESCE(dol.kalan_kapasite, d.yemekhane_kapasitesi) as kalan_kapasite,
                    COALESCE(dol.doluluk_orani, 0.0) as doluluk_orani,
                    (NOW() > TIMESTAMP(d.tarih, d.ogun_son_saat)) as sure_gecti_mi
                FROM v_menu_detay d
                LEFT JOIN v_menu_doluluk dol ON d.menu_id = dol.menu_id
                WHERE d.yemekhane_id = %s AND d.tarih BETWEEN %s AND %s
                ORDER BY d.tarih ASC, d.ogun_id ASC;
                """
                cursor.execute(query, (yemekhane_id, baslangic_tarihi, bitis_tarihi))
                menus = cursor.fetchall()
                for m in menus:
                    m["ogrenci_fiyati"] = float(m["ogrenci_fiyati"])
                    m["personel_fiyati"] = float(m["personel_fiyati"])
                    m["toplam_kalori"] = int(m["toplam_kalori"])
                    m["kalan_kapasite"] = int(m["kalan_kapasite"])
                    m["doluluk_orani"] = float(m["doluluk_orani"])
                    m["sure_gecti_mi"] = bool(m["sure_gecti_mi"])
                    m["tum_alerjenler"] = m["alerjenler"].split(", ") if m.get("alerjenler") else []
                    m.pop("alerjenler", None)
                return menus

    @staticmethod
    def get_menu_stats() -> List[Dict[str, Any]]:
        """Yönetici paneli için menü bazında doluluk ve ortalama puan istatistikleri (Okuma: Replica)"""
        with get_replica_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                SELECT 
                    dol.menu_id,
                    dol.yemekhane_id,
                    dol.yemekhane_adi,
                    dol.tarih,
                    dol.ogun_id,
                    dol.ogun_adi,
                    m.ogrenci_fiyati,
                    m.personel_fiyati,
                    dol.toplam_kapasite,
                    dol.aktif_rezervasyon_sayisi,
                    dol.kalan_kapasite,
                    dol.doluluk_orani,
                    COALESCE(p.ortalama_puan, 0.0) as ortalama_puan,
                    COALESCE(p.degerlendirme_sayisi, 0) as degerlendirme_sayisi
                FROM v_menu_doluluk dol
                JOIN menuler m ON dol.menu_id = m.id
                LEFT JOIN v_menu_puan p ON dol.menu_id = p.menu_id
                ORDER BY dol.tarih DESC, dol.ogun_id ASC;
                """
                cursor.execute(query)
                rows = cursor.fetchall()
                for r in rows:
                    r["ogrenci_fiyati"] = float(r["ogrenci_fiyati"])
                    r["personel_fiyati"] = float(r["personel_fiyati"])
                    r["toplam_kapasite"] = int(r["toplam_kapasite"])
                    r["aktif_rezervasyon_sayisi"] = int(r["aktif_rezervasyon_sayisi"])
                    r["kalan_kapasite"] = int(r["kalan_kapasite"])
                    r["doluluk_orani"] = float(r["doluluk_orani"])
                    r["ortalama_puan"] = float(r["ortalama_puan"])
                    r["degerlendirme_sayisi"] = int(r["degerlendirme_sayisi"])
                return rows

    @staticmethod
    def create_menu(yemekhane_id: int, tarih: date, ogun_id: int, ogrenci_fiyati: float, personel_fiyati: float, yemek_ids: List[int]) -> int:
        """Yeni menü oluşturur (Yazma: Primary)"""
        with get_primary_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO menuler (yemekhane_id, tarih, ogun_id, ogrenci_fiyati, personel_fiyati)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (yemekhane_id, tarih, ogun_id, ogrenci_fiyati, personel_fiyati),
                    )
                    menu_id = cursor.lastrowid
                    for y_id in yemek_ids:
                        cursor.execute(
                            "INSERT INTO menu_yemekleri (menu_id, yemek_id) VALUES (%s, %s)",
                            (menu_id, y_id),
                        )
                conn.commit()
                return menu_id
            except pymysql.MySQLError as e:
                conn.rollback()
                handle_mysql_error(e, "MenuDAL.create_menu")
            except Exception:
                conn.rollback()
                raise

    @staticmethod
    def update_menu(menu_id: int, ogrenci_fiyati: Optional[float], personel_fiyati: Optional[float], yemek_ids: Optional[List[int]]) -> Dict[str, Any]:
        """Menüyü ve yemeklerini günceller (Yazma: Primary)"""
        with get_primary_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT yemekhane_id, tarih, ogun_id FROM menuler WHERE id = %s FOR UPDATE", (menu_id,))
                    info = cursor.fetchone()
                    if not info:
                        raise ValueError("Menü bulunamadı.")

                    if ogrenci_fiyati is not None or personel_fiyati is not None:
                        cursor.execute(
                            """
                            UPDATE menuler 
                            SET ogrenci_fiyati = COALESCE(%s, ogrenci_fiyati),
                                personel_fiyati = COALESCE(%s, personel_fiyati)
                            WHERE id = %s
                            """,
                            (ogrenci_fiyati, personel_fiyati, menu_id),
                        )
                    if yemek_ids is not None:
                        cursor.execute("DELETE FROM menu_yemekleri WHERE menu_id = %s", (menu_id,))
                        for y_id in yemek_ids:
                            cursor.execute(
                                "INSERT INTO menu_yemekleri (menu_id, yemek_id) VALUES (%s, %s)",
                                (menu_id, y_id),
                            )
                conn.commit()
                return info
            except pymysql.MySQLError as e:
                conn.rollback()
                handle_mysql_error(e, "MenuDAL.update_menu")
            except Exception:
                conn.rollback()
                raise

    @staticmethod
    def get_all_dishes() -> List[Dict[str, Any]]:
        """Yönetici panelinde menü oluşturmak için tüm yemeklerin listesi (Okuma: Replica)"""
        with get_replica_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT y.id, y.ad, y.kalori, y.vejetaryen_mi, yk.ad as kategori_adi, yk.sira
                    FROM yemekler y
                    JOIN yemek_kategorileri yk ON y.kategori_id = yk.id
                    ORDER BY yk.sira ASC, y.ad ASC;
                """)
                rows = cursor.fetchall()
                for r in rows:
                    r["vejetaryen_mi"] = bool(r["vejetaryen_mi"])
                return rows
