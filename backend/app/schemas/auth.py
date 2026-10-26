from typing import Optional
from pydantic import BaseModel

class LoginRequest(BaseModel):
    eposta: str
    sifre: str

class UserOut(BaseModel):
    id: int
    ad: str
    soyad: str
    eposta: str
    rol: str
    ogrenci_no: Optional[str] = None
    bakiye: float

class LoginResponse(BaseModel):
    token: str
    kullanici: UserOut

