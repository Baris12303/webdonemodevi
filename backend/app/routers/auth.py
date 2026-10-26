from fastapi import APIRouter, Depends, Security
from fastapi.security import HTTPAuthorizationCredentials
from app.schemas.auth import LoginRequest, LoginResponse, UserOut
from app.services.auth_service import AuthService, get_current_user, security
from app.dal.user_dal import UserDAL

router = APIRouter(prefix="/api/auth", tags=["Kimlik Doğrulama"])

@router.post("/login", response_model=LoginResponse, summary="Giriş Yap")
def login(req: LoginRequest):
    return AuthService.login(req.eposta, req.sifre)

@router.post("/logout", summary="Çıkış Yap")
def logout(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials:
        AuthService.logout(credentials.credentials)
    return {"message": "Başarıyla çıkış yapıldı."}

@router.get("/me", response_model=UserOut, summary="Giriş Yapan Kullanıcı Bilgisi")
def get_me(user: dict = Depends(get_current_user)):
    # Her zaman en güncel bakiyeyi okumak için
    latest_user = UserDAL.get_by_id(user["id"], use_primary=True)
    if latest_user:
        return latest_user
    return user

