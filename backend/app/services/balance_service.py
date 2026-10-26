from typing import Dict, Any
from fastapi import HTTPException, status
from app.dal.balance_dal import BalanceDAL
from app.dal.user_dal import UserDAL

class BalanceService:
    @staticmethod
    def top_up(kullanici_id: int, miktar: float) -> Dict[str, Any]:
        if miktar <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Yüklenecek tutar 0'dan büyük olmalıdır."
            )
        try:
            guncel_bakiye = BalanceDAL.top_up_balance(kullanici_id, miktar)
            return {
                "message": f"{miktar:.2f} TL bakiye başarıyla yüklendi.",
                "guncel_bakiye": guncel_bakiye
            }
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    @staticmethod
    def get_balance_and_history(kullanici_id: int) -> Dict[str, Any]:
        # Anlık bakiyeyi doğrudan Primary DB'den oku
        user = UserDAL.get_by_id(kullanici_id, use_primary=True)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı.")
            
        movements = BalanceDAL.get_balance_movements(kullanici_id)
        return {
            "guncel_bakiye": float(user["bakiye"]),
            "hareketler": movements
        }

