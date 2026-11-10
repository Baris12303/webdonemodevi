from fastapi import APIRouter, Depends, Security
from fastapi.security import HTTPAuthorizationCredentials
from app.schemas.auth import (
    AllergensResponse,
    AllergenUpdateRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    UserOut,
)
from app.services.auth_service import AuthService, get_current_user, security

router = APIRouter(prefix="/api/auth", tags=["Kimlik Doğrulama"])


@router.post("/login", response_model=LoginResponse, summary="Giriş Yap")
def login(req: LoginRequest):
    return AuthService.login(req.eposta, req.sifre)


@router.post("/logout", response_model=MessageResponse, summary="Çıkış Yap")
def logout(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials:
        AuthService.logout(credentials.credentials)
    return {"message": "Başarıyla çıkış yapıldı."}


@router.get("/me", response_model=UserOut, summary="Giriş Yapan Kullanıcı Bilgisi")
def get_me(user: dict = Depends(get_current_user)):
    latest_user = AuthService.get_fresh_user(user["id"])
    if latest_user:
        return latest_user
    return user


@router.get("/allergens", response_model=AllergensResponse, summary="Alerjenler ve Kullanıcı Seçimleri")
def get_user_allergens(user: dict = Depends(get_current_user)):
    return AuthService.get_user_allergens(user["id"])


@router.post("/allergens", response_model=MessageResponse, summary="Kullanıcı Alerjen Tercihlerini Güncelle")
def update_user_allergens(req: AllergenUpdateRequest, user: dict = Depends(get_current_user)):
    return AuthService.update_user_allergens(user["id"], req.alerjen_ids)
