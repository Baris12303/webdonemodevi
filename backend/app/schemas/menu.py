from typing import List, Optional
from datetime import date, time
from pydantic import BaseModel

class YemekItem(BaseModel):
    id: int
    ad: str
    kalori: int
    vejetaryen_mi: bool
    kategori_adi: str
    kategori_sira: int
    alerjenler: List[str] = []

class MenuDetailOut(BaseModel):
    menu_id: int
    yemekhane_id: int
    yemekhane_adi: str
    yemekhane_kapasitesi: int
    tarih: date
    ogun_id: int
    ogun_adi: str
    ogun_son_saat: str
    ogrenci_fiyati: float
    personel_fiyati: float
    toplam_kalori: int
    yemekler: List[YemekItem] = []
    tum_alerjenler: List[str] = []
    vejetaryen_mi: bool = False
    kalan_kapasite: int = 0
    doluluk_orani: float = 0.0
    ortalama_puan: float = 0.0
    degerlendirme_sayisi: int = 0
    kaynak: str = "database" # "cache" veya "database"

class MenuCreateRequest(BaseModel):
    yemekhane_id: int
    tarih: date
    ogun_id: int
    ogrenci_fiyati: float
    personel_fiyati: float
    yemek_ids: List[int]

class MenuUpdateRequest(BaseModel):
    ogrenci_fiyati: Optional[float] = None
    personel_fiyati: Optional[float] = None
    yemek_ids: Optional[List[int]] = None

