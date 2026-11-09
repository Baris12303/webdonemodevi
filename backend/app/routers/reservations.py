from typing import List
from fastapi import APIRouter, Depends
from app.schemas.reservation import ReservationCreateRequest, ReservationCreateResponse, ReservationOut
from app.services.reservation_service import ReservationService
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/reservations", tags=["Rezervasyonlar"])

@router.get("", response_model=List[ReservationOut], summary="Kullanıcının Rezervasyonları")
def get_my_reservations(user: dict = Depends(get_current_user)):
    return ReservationService.get_reservations(user["id"])

@router.post("", response_model=ReservationCreateResponse, summary="Rezervasyon Yap")
def create_reservation(req: ReservationCreateRequest, user: dict = Depends(get_current_user)):
    return ReservationService.create_reservation(user["id"], req.menu_id, req.porsiyon)

@router.post("/{rezervasyon_id}/cancel", summary="Rezervasyon İptal Et")
def cancel_reservation(rezervasyon_id: int, user: dict = Depends(get_current_user)):
    return ReservationService.cancel_reservation(user["id"], rezervasyon_id)

