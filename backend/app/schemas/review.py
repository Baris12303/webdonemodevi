from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ReviewCreateRequest(BaseModel):
    menu_id: int
    puan: int = Field(..., ge=1, le=5, description="1 ile 5 arasında bir puan")
    yorum: Optional[str] = None

class ReviewOut(BaseModel):
    id: int
    kullanici_ad_soyad: str
    menu_id: int
    puan: int
    yorum: Optional[str] = None
    tarih: datetime

