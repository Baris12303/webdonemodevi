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

@router.get("/allergens", summary="Alerjenler ve Kullanıcı Seçimleri")
def get_user_allergens(user: dict = Depends(get_current_user)):
    all_allergens = UserDAL.get_all_allergens()
    user_allergens = UserDAL.get_user_allergens(user["id"])
    return {
        "tum_alerjenler": all_allergens,
        "secili_alerjenler": user_allergens
    }

@router.post("/allergens", summary="Kullanıcı Alerjen Tercihlerini Güncelle")
def update_user_allergens(req: dict, user: dict = Depends(get_current_user)):
    allergen_ids = req.get("alerjen_ids", [])
    UserDAL.update_user_allergens(user["id"], allergen_ids)
    return {"message": "Alerjen tercihleriniz başarıyla kaydedildi."}

