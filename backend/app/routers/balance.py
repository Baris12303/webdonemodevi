from fastapi import APIRouter, Depends
from app.schemas.balance import BalanceTopUpRequest, BalanceResponse
from app.services.balance_service import BalanceService
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/balance", tags=["Bakiye İşlemleri"])

@router.get("", response_model=BalanceResponse, summary="Güncel Bakiye ve Hareket Geçmişi")
def get_balance(user: dict = Depends(get_current_user)):
    return BalanceService.get_balance_and_history(user["id"])

@router.post("/topup", summary="Bakiye Yükle (Stored Procedure)")
def top_up(req: BalanceTopUpRequest, user: dict = Depends(get_current_user)):
    return BalanceService.top_up(user["id"], req.miktar)

