from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from app.schemas.menu import MenuCreateRequest, MenuUpdateRequest
from app.services.admin_service import AdminService
from app.services.auth_service import require_admin
from app.dal.menu_dal import MenuDAL

router = APIRouter(prefix="/api/admin", tags=["Yönetici İşlemleri"])

@router.get("/stats", summary="Menü Doluluk ve Puan İstatistikleri")
def get_stats(admin: dict = Depends(require_admin)):
    return AdminService.get_stats()

@router.get("/dishes", summary="Tüm Yemekler Listesi")
def get_dishes(admin: dict = Depends(require_admin)):
    return MenuDAL.get_all_dishes()

@router.post("/menus", summary="Yeni Menü Oluştur")
def create_menu(req: MenuCreateRequest, admin: dict = Depends(require_admin)):
    return AdminService.create_menu(req.model_dump())

@router.put("/menus/{menu_id}", summary="Menü Düzenle")
def update_menu(menu_id: int, req: MenuUpdateRequest, admin: dict = Depends(require_admin)):
    return AdminService.update_menu(menu_id, req.model_dump(exclude_unset=True))

