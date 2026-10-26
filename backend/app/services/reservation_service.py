from typing import List, Dict, Any
from fastapi import HTTPException, status
from app.dal.reservation_dal import ReservationDAL

class ReservationService:
    @staticmethod
    def create_reservation(kullanici_id: int, menu_id: int) -> Dict[str, Any]:
        try:
            result = ReservationDAL.make_reservation(kullanici_id, menu_id)
            return {
                "message": "Rezervasyonunuz başarıyla oluşturuldu.",
                "rezervasyon_id": result["rezervasyon_id"],
                "guncel_bakiye": result["guncel_bakiye"]
            }
        except ValueError as e:
            # Stored Procedure'den gelen SQLSTATE 45000 mesajı
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    @staticmethod
    def cancel_reservation(kullanici_id: int, rezervasyon_id: int) -> Dict[str, Any]:
        try:
            guncel_bakiye = ReservationDAL.cancel_reservation(kullanici_id, rezervasyon_id)
            return {
                "message": "Rezervasyon başarıyla iptal edildi ve ücret bakiyenize iade edildi.",
                "guncel_bakiye": guncel_bakiye
            }
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    @staticmethod
    def get_reservations(kullanici_id: int) -> List[Dict[str, Any]]:
        return ReservationDAL.get_user_reservations(kullanici_id)

