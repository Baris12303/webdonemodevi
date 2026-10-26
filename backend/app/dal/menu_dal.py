from typing import List, Dict, Any, Optional
from datetime import date
from app.db import get_replica_connection, get_primary_connection

class MenuDAL:
    @staticmethod
    def get_menu_detail(yemekhane_id: int, tarih: date, ogun_id: int) -> Optional[Dict[str, Any]]:
        """Günün menü detayını view'lardan birleştirerek getirir (Okuma: Replica)"""
        with get_replica_connection() as conn:
            with conn.cursor() as cursor:
                # View 1 & View 2 & View 3 birleşimi
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

                # Menüdeki yemekleri ve alerjenlerini kategori sırasıyla al
                menu["yemekler"] = MenuDAL._get_menu_dishes(conn, menu["menu_id"])
                
                # Tüm alerjenleri ve vejetaryen durumunu derle
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
    def get_menu_by_id(menu_id: int) -> Optional[Dict[str, Any]]:
        """ID ile menü detayını getirir (Okuma: Replica)"""
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
                WHERE d.menu_id = %s
                LIMIT 1;
                """
                cursor.execute(query, (menu_id,))
                menu = cursor.fetchone()
                if not menu:
                    return None
                menu["yemekler"] = MenuDAL._get_menu_dishes(conn, menu_id)
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
                    m["sure_gecti_mi"] = bool(m["sure_gecti_mi"])
                return menus

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
                        (yemekhane_id, tarih, ogun_id, ogrenci_fiyati, personel_fiyati)
                    )
                    menu_id = cursor.lastrowid
                    for y_id in yemek_ids:
                        cursor.execute(
                            "INSERT INTO menu_yemekleri (menu_id, yemek_id) VALUES (%s, %s)",
                            (menu_id, y_id)
                        )
                conn.commit()
                return menu_id
            except Exception:
                conn.rollback()
                raise

    @staticmethod
    def update_menu(menu_id: int, ogrenci_fiyati: Optional[float], personel_fiyati: Optional[float], yemek_ids: Optional[List[int]]) -> Dict[str, Any]:
        """Menüyü ve yemeklerini günceller (Yazma: Primary)"""
        with get_primary_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT yemekhane_id, tarih, ogun_id FROM menuler WHERE id = %s", (menu_id,))
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
                            (ogrenci_fiyati, personel_fiyati, menu_id)
                        )
                    if yemek_ids is not None:
                        cursor.execute("DELETE FROM menu_yemekleri WHERE menu_id = %s", (menu_id,))
                        for y_id in yemek_ids:
                            cursor.execute("INSERT INTO menu_yemekleri (menu_id, yemek_id) VALUES (%s, %s)", (menu_id, y_id))
                conn.commit()
                return info
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

