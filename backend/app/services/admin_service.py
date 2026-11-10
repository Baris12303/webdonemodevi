from typing import List, Dict, Any
from fastapi import HTTPException, status
from app.dal.menu_dal import MenuDAL
from app.redis_client import invalidate_menu_cache


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
                yemek_ids=data["yemek_ids"],
            )
            tarih_str = data["tarih"].isoformat() if hasattr(data["tarih"], "isoformat") else str(data["tarih"])
            invalidate_menu_cache(data["yemekhane_id"], tarih_str, data["ogun_id"])
            return {"message": "Menü başarıyla oluşturuldu.", "menu_id": menu_id}
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @staticmethod
    def update_menu(menu_id: int, data: dict) -> Dict[str, Any]:
        try:
            info = MenuDAL.update_menu(
                menu_id=menu_id,
                ogrenci_fiyati=data.get("ogrenci_fiyati"),
                personel_fiyati=data.get("personel_fiyati"),
                yemek_ids=data.get("yemek_ids"),
            )
            tarih_str = info["tarih"].isoformat() if hasattr(info["tarih"], "isoformat") else str(info["tarih"])
            invalidate_menu_cache(info["yemekhane_id"], tarih_str, info["ogun_id"])
            return {"message": "Menü güncellendi."}
        except ValueError as e:
            msg = str(e)
            code = status.HTTP_404_NOT_FOUND if msg == "Menü bulunamadı." else status.HTTP_400_BAD_REQUEST
            raise HTTPException(status_code=code, detail=msg)

    @staticmethod
    def get_stats() -> List[Dict[str, Any]]:
        """Yönetici paneli için menü bazında doluluk ve ortalama puan istatistikleri"""
        return MenuDAL.get_menu_stats()

    @staticmethod
    def get_dishes() -> List[Dict[str, Any]]:
        """Tüm yemeklerin listesi"""
        return MenuDAL.get_all_dishes()
