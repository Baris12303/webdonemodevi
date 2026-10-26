from typing import Optional
from datetime import datetime, date
from pydantic import BaseModel

class ReservationCreateRequest(BaseModel):
    menu_id: int
    porsiyon: Optional[str] = "tam" # Aşama 4 için uyumlu ("tam", "yarim")

class ReservationOut(BaseModel):
    id: int
    kullanici_id: int
    menu_id: int
    tarih: date
    ogun_adi: str
    yemekhane_adi: str
    ucret: float
    durum: str # 'aktif', 'kullanildi', 'iptal'
    iptal_edilebilir_mi: bool
    olusturulma_tarihi: datetime
    iptal_tarihi: Optional[datetime] = None
    kullanilma_tarihi: Optional[datetime] = None
    yemek_listesi: Optional[str] = None
    degerlendirildi_mi: bool = False

class ReservationCreateResponse(BaseModel):
    message: str
    rezervasyon_id: int
    guncel_bakiye: float # Doğrudan Primary'den okunan anlık bakiye!

