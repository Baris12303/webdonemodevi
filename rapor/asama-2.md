# Aşama 2: Uygulama Mimarisi ve Arayüz Raporu

## 1. Mimari Seçimi
Bu projede **Seçenek B: Web API + Arayüz** mimarisi tercih edilmiştir.
* **Backend:** Python / FastAPI katmanlı mimarisiyle REST API olarak geliştirilmiştir. Sadece JSON veri döndürür.
* **Frontend:** Apache 2.4 container'ında barındırılan HTML5, CSS3 ve Vanilla JavaScript (`fetch`) ile geliştirilmiştir. React veya harici bir SPA çatısı kullanılmamıştır.
* **Ters Proxy (Reverse Proxy):** Apache 2.4, statik dosyaları (HTML/CSS/JS) doğrudan sunmakta; gelen `/api/*` ve `/docs` isteklerini arka plandaki `uygulama:8000` FastAPI servisine iletmektedir.

---

## 2. Bir İsteğin Uygulama İçindeki Yolu (End-to-End Kod Akışı)
Aşağıda bir öğrencinin rezervasyon yapma isteğinin sistem içindeki akışı (`Route` $\rightarrow$ `Controller/Service` $\rightarrow$ `Veri Katmanı (DAL)` $\rightarrow$ `Stored Procedure` $\rightarrow$ `Yanıt`) kodlarımız üzerinden modellenmiştir:

```mermaid
sequenceDiagram
    autonumber
    actor Kullanıcı as Tarayıcı (Vanilla JS)
    participant Apache as Apache 2.4 (:8080)
    participant Route as app/routers/reservations.py
    participant Service as app/services/reservation_service.py
    participant DAL as app/dal/reservation_dal.py
    participant Primary as MySQL Primary (:3306)

    Kullanıcı->>Apache: POST /api/reservations { menu_id: 42 } + Bearer Token
    Apache->>Route: ProxyPass -> FastAPI Uygulaması
    Route->>Service: create_reservation(kullanici_id=6, menu_id=42)
    Service->>DAL: make_reservation(kullanici_id=6, menu_id=42)
    DAL->>Primary: CALL sp_rezervasyon_yap(6, 42);
    Note over Primary: Stored Procedure bakiye, tarih ve kapasiteyi kontrol eder.<br/>Bakiye düşer, rezervasyon ve bakiye hareketi ekler.
    Primary-->>DAL: Transaction Başarılı (veya SQLSTATE 45000 Hatası)
    DAL->>Primary: SELECT bakiye FROM kullanicilar WHERE id = 6; (Anlık Bakiye)
    DAL-->>Service: { rezervasyon_id: 105, guncel_bakiye: 245.00 }
    Service-->>Route: ReservationCreateResponse
    Route-->>Apache: HTTP 200 OK JSON
    Apache-->>Kullanıcı: JSON Yanıtı -> Ekranda Toast & Bakiye Güncellenir
```

### Kod Örneği Alıntıları:
1. **Route (`app/routers/reservations.py`):**
   ```python
   @router.post("", response_model=ReservationCreateResponse)
   def create_reservation(req: ReservationCreateRequest, user: dict = Depends(get_current_user)):
       return ReservationService.create_reservation(user["id"], req.menu_id)
   ```

2. **Controller / Service (`app/services/reservation_service.py`):**
   ```python
   class ReservationService:
       @staticmethod
       def create_reservation(kullanici_id: int, menu_id: int) -> Dict[str, Any]:
           try:
               result = ReservationDAL.make_reservation(kullanici_id, menu_id)
               return {
                   "message": "Rezervasyonunuz başarıyla oluşturuldu.",
                   "rezervasyon_id": result["rezervasyon_id"],
                   "guncel_bakiye": result["guncel_bakiye"]
               }
           except ValueError as e:
               # Stored Procedure'den dönen Türkçe hatayı yakala
               raise HTTPException(status_code=400, detail=str(e))
   ```

3. **Veri Katmanı / DAL (`app/dal/reservation_dal.py`):**
   ```python
   class ReservationDAL:
       @staticmethod
       def make_reservation(kullanici_id: int, menu_id: int) -> Dict[str, Any]:
           with get_primary_connection() as conn:
               with conn.cursor() as cursor:
                   # Para hareketi doğrudan SQL yazılmadan Stored Procedure ile yapılır
                   cursor.execute("CALL sp_rezervasyon_yap(%s, %s);", (kullanici_id, menu_id))
                   cursor.execute("SELECT id FROM rezervasyonlar WHERE ...")
                   cursor.execute("SELECT bakiye FROM kullanicilar WHERE id = %s;", (kullanici_id,))
                   user_row = cursor.fetchone()
               conn.commit()
               return {"rezervasyon_id": rez_id, "guncel_bakiye": float(user_row["bakiye"])}
   ```

---

## 3. Replikasyon Gecikmesi (Replication Lag) ve Çözümü

> **Teknik Açıklama:**
> Dağıtık MySQL replikasyon mimarilerinde birincil (Primary) sunucuya yazılan bir transaction'ın binary log üzerinden ikincil (Replica) sunucuya aktarılıp işlenmesi asenkron olarak gerçekleşir. Ağ yoğunluğu veya ağır sorgular sebebiyle mikrosaniyeler veya saniyeler mertebesinde bir gecikme (**Replication Lag**) oluşabilir.
> 
> Eğer bir öğrenci rezervasyon yapıp parası düştükten hemen sonra güncel bakiyesini görmek için okuma replikasına (`mysql-replica`) yönlendirilirse, henüz kopyalanmamış eski bakiyesini görebilir ve *"Bakiyem düşmedi"* yanılgısına düşebilir. Bu durumu engellemek amacıyla **"Read-Your-Own-Writes"** tasarım deseni uygulanmış; rezervasyon, iptal ve bakiye yükleme işlemlerinden hemen sonra gösterilen anlık bakiye bilgisi **doğrudan yazma yetkisine sahip birincil (`mysql-primary`) sunucudan** okunmuştur. Genel menü listeleme ve raporlama sorguları ise okuma replikasına (`mysql-replica`) yönlendirilerek kaynak sunucu üzerindeki yük dengelenmiştir.

---

## 4. Arayüzde Geliştirilen 7 Ekran
1. **Giriş ve Çıkış:** Kampüs e-postası ve bcrypt doğrulamalı şifre girişi, hızlı test hesapları butonları.
2. **Günün Menüsü:** Yemekhane, öğün ve tarih seçimi; yemeklerin listesi, toplam kalori, vejetaryen ve alerjen uyarı rozetleri; Redis cache göstergesi.
3. **Haftalık Menü ve Rezervasyon:** 7 günlük takvim görünümü, boş kontenjan göstergesi, role göre (öğrenci/personel) dinamik fiyat ve süresi geçmiş öğünlerde pasifleşen rezervasyon butonları.
4. **Rezervasyonlarım:** Aktif, kullanıldı ve iptal durumları. Süresi dolmamış rezervasyonlar için iptal butonu; kullanılmışlar için menüyü değerlendirme butonu.
5. **Bakiye:** Büyük göstergeli güncel bakiye kartı, hızlı bakiye yükleme (+50, +100, +200, +500 TL `sp_bakiye_yukle` çağrıları) ve tarihçeli bakiye hareket geçmişi tablosu.
6. **Değerlendirme:** 1-5 yıldız seçimi, opsiyonel yorum metni ve o menüye yapılan önceki yorumların listesi.
7. **Yönetici Paneli:** `v_menu_doluluk` ve `v_menu_puan` view'larından beslenen doluluk oranları ve ortalama puan tablosu, yemek seçimli yeni menü oluşturma formu.

