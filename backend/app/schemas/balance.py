from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class BalanceTopUpRequest(BaseModel):
    miktar: float = Field(..., gt=0, le=99999999.99, description="Yüklenecek miktar pozitif olmalıdır")

class BalanceMovementOut(BaseModel):
    id: int
    miktar: float
    hareket_tipi: str # 'yukleme', 'rezervasyon', 'iade'
    aciklama: str
    tarih: datetime
    rezervasyon_id: Optional[int] = None

class BalanceResponse(BaseModel):
    guncel_bakiye: float
    hareketler: list[BalanceMovementOut] = []

