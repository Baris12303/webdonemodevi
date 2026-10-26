from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Query, HTTPException, status
from app.services.menu_service import MenuService
from app.schemas.menu import MenuDetailOut

router = APIRouter(prefix="/api/menus", tags=["Menüler"])

@router.get("/today", response_model=MenuDetailOut, summary="Günün Menüsü (Önbellek Destekli)")
def get_daily_menu(
    yemekhane_id: int = Query(1, description="1: Merkez, 2: Mühendislik"),
    tarih: Optional[date] = Query(default_factory=date.today),
    ogun_id: int = Query(2, description="1: Kahvaltı, 2: Öğle, 3: Akşam")
):
    menu = MenuService.get_daily_menu(yemekhane_id, tarih, ogun_id)
    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seçilen tarih ve öğün için menü bulunamadı."
        )
    return menu

@router.get("/weekly", summary="Haftalık Menü Listesi")
def get_weekly_menus(
    yemekhane_id: int = Query(1, description="1: Merkez, 2: Mühendislik"),
    baslangic_tarihi: Optional[date] = Query(default_factory=date.today)
):
    return MenuService.get_weekly_menus(yemekhane_id, baslangic_tarihi)

