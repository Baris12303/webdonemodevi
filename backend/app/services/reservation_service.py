from typing import List, Dict, Any
from fastapi import HTTPException, status
from app.dal.menu_dal import MenuDAL
from app.dal.reservation_dal import ReservationDAL
from app.redis_client import invalidate_menu_cache


class ReservationService:
    @staticmethod
    def create_reservation(kullanici_id: int, menu_id: int, porsiyon: str = "tam") -> Dict[str, Any]:
        try:
            result = ReservationDAL.make_reservation(kullanici_id, menu_id, porsiyon)
            coords = MenuDAL.get_menu_cache_coords(menu_id)
            if coords:
                tarih_str = coords["tarih"].isoformat() if hasattr(coords["tarih"], "isoformat") else str(coords["tarih"])
                invalidate_menu_cache(coords["yemekhane_id"], tarih_str, coords["ogun_id"])
            return {
                "message": "Rezervasyonunuz başarıyla oluşturuldu.",
                "rezervasyon_id": result["rezervasyon_id"],
                "guncel_bakiye": result["guncel_bakiye"],
            }
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    @staticmethod
    def cancel_reservation(kullanici_id: int, rezervasyon_id: int) -> Dict[str, Any]:
        try:
            guncel_bakiye = ReservationDAL.cancel_reservation(kullanici_id, rezervasyon_id)
            coords = ReservationDAL.get_reservation_menu_coords(rezervasyon_id)
            if coords:
                tarih_str = coords["tarih"].isoformat() if hasattr(coords["tarih"], "isoformat") else str(coords["tarih"])
                invalidate_menu_cache(coords["yemekhane_id"], tarih_str, coords["ogun_id"])
            return {
                "message": "Rezervasyon başarıyla iptal edildi ve ücret bakiyenize iade edildi.",
                "guncel_bakiye": guncel_bakiye,
            }
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    @staticmethod
    def get_reservations(kullanici_id: int) -> List[Dict[str, Any]]:
        return ReservationDAL.get_user_reservations(kullanici_id)
