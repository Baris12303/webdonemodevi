from typing import Literal, Optional
from datetime import datetime, date
from pydantic import BaseModel, field_validator


class ReservationCreateRequest(BaseModel):
    menu_id: int
    porsiyon: Literal["tam", "yarim"] = "tam"

    @field_validator("porsiyon", mode="before")
    @classmethod
    def default_none_porsiyon(cls, v):
        if v is None:
            return "tam"
        return v


class ReservationOut(BaseModel):
    id: int
    kullanici_id: int
    menu_id: int
    tarih: date
    ogun_adi: str
    yemekhane_adi: str
    ucret: float
    porsiyon: str = "tam"
    durum: str  # 'aktif', 'kullanildi', 'iptal'
    iptal_edilebilir_mi: bool
    olusturulma_tarihi: datetime
    iptal_tarihi: Optional[datetime] = None
    kullanilma_tarihi: Optional[datetime] = None
    yemek_listesi: Optional[str] = None
    degerlendirildi_mi: bool = False


class ReservationCreateResponse(BaseModel):
    message: str
    rezervasyon_id: int
    guncel_bakiye: float  # Primary veritabanından okunan güncel bakiye
