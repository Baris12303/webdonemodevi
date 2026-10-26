import uuid
import bcrypt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.dal.user_dal import UserDAL
from app.redis_client import create_session, get_session, delete_session

security = HTTPBearer(auto_error=False)

class AuthService:
    @staticmethod
    def login(eposta: str, sifre: str) -> dict:
        user = UserDAL.get_by_email(eposta)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz e-posta veya şifre."
            )

        # Bcrypt şifre kontrolü
        password_bytes = sifre.encode("utf-8")
        hash_bytes = user["sifre_hash"].encode("utf-8")
        
        if not bcrypt.checkpw(password_bytes, hash_bytes):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz e-posta veya şifre."
            )

        # 32 karakterlik güvenli rastgele token üret
        token = uuid.uuid4().hex
        user_session_data = {
            "id": user["id"],
            "ad": user["ad"],
            "soyad": user["soyad"],
            "eposta": user["eposta"],
            "rol": user["rol"],
            "ogrenci_no": user["ogrenci_no"],
            "bakiye": float(user["bakiye"])
        }

        # Redis'e 30 dakikalık sliding session kaydet
        create_session(token, user_session_data)

        return {
            "token": token,
            "kullanici": user_session_data
        }

    @staticmethod
    def logout(token: str) -> bool:
        return delete_session(token)

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """Oturum doğrulaması yapan FastAPI bağımlılığı (Dependency)"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Oturum açmanız gerekiyor."
        )
    token = credentials.credentials
    user_data = get_session(token)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Oturum süreniz dolmuş veya geçersiz token."
        )
    return user_data

def require_admin(user: dict = Security(get_current_user)) -> dict:
    if user.get("rol") != "yonetici":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için yönetici yetkisi gereklidir."
        )
    return user

