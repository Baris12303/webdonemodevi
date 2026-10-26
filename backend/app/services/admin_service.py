from typing import List, Dict, Any, Optional
from datetime import date
from fastapi import HTTPException, status
from app.dal.menu_dal import MenuDAL
from app.redis_client import invalidate_menu_cache
from app.db import get_replica_connection

class AdminService:
    @staticmethod
    def create_menu(data: dict) -> Dict[str, Any]:
        try:
            menu_id = MenuDAL.create_menu(
                yemekhane_id=data["yemekhane_id"],
                tarih=data["tarih"],
                ogun_id=data["ogun_id"],
                ogrenci_fiyati=data["ogrenci_fiyati"],
                personel_fiyati=data["personel_fiyati"],
                yemek_ids=data["yemek_ids"]
            )
            # Redis önbelleğini temizle (varsa eski cache gitsin)
            invalidate_menu_cache(data["yemekhane_id"], data["tarih"].isoformat(), data["ogun_id"])
            return {"message": "Menü başarıyla oluşturuldu.", "menu_id": menu_id}
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @staticmethod
    def update_menu(menu_id: int, data: dict) -> Dict[str, Any]:
        try:
            info = MenuDAL.update_menu(
                menu_id=menu_id,
                ogrenci_fiyati=data.get("ogrenci_fiyati"),
                personel_fiyati=data.get("personel_fiyati"),
                yemek_ids=data.get("yemek_ids")
            )
            # Menü güncellendiğinde Redis cache'ini temizle (Aşama 3 kuralı)
            invalidate_menu_cache(info["yemekhane_id"], info["tarih"].isoformat(), info["ogun_id"])
            return {"message": "Menü başarıyla güncellendi ve önbellek temizlendi."}
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @staticmethod
    def get_stats() -> List[Dict[str, Any]]:
        """Yönetici paneli için menü bazında doluluk ve ortalama puan istatistikleri (Okuma: Replica)"""
        with get_replica_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                SELECT 
                    dol.menu_id,
                    dol.yemekhane_adi,
                    dol.tarih,
                    dol.ogun_adi,
                    dol.toplam_kapasite,
                    dol.aktif_rezervasyon_sayisi,
                    dol.kalan_kapasite,
                    dol.doluluk_orani,
                    COALESCE(p.ortalama_puan, 0.0) as ortalama_puan,
                    COALESCE(p.degerlendirme_sayisi, 0) as degerlendirme_sayisi
                FROM v_menu_doluluk dol
                LEFT JOIN v_menu_puan p ON dol.menu_id = p.menu_id
                ORDER BY dol.tarih DESC, dol.ogun_id ASC;
                """
                cursor.execute(query)
                return cursor.fetchall()

