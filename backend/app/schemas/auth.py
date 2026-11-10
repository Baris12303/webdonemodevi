from typing import List, Optional
from pydantic import AliasChoices, BaseModel, Field


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


class AllergenOut(BaseModel):
    id: int
    ad: str


class AllergensResponse(BaseModel):
    tum_alerjenler: List[AllergenOut]
    secili_alerjenler: List[int]


class AllergenUpdateRequest(BaseModel):
    alerjen_ids: List[int] = Field(
        default_factory=list,
        validation_alias=AliasChoices("alerjen_ids", "alerjen_idler"),
    )


class MessageResponse(BaseModel):
    message: str
