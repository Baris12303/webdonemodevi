# Aşama 2: Uygulama Mimarisi ve Arayüz

## 1. Mimari Seçimi

Projede **Web API + Arayüz** yolu seçilmiştir:
- **Backend (`uygulama`):** Python / FastAPI ile yalnızca JSON dönen katmanlı REST API olarak yazıldı (`routers` -> `services` -> `dal` -> `MySQL`).
- **Frontend (`frontend`):** Apache 2.4 container'ı üzerinden sunulan HTML5, CSS3 ve Vanilla JS (`fetch`) ile geliştirildi. React gibi harici bir kütüphane kullanılmadı.
- **Yönlendirme:** Apache, statik dosyaları doğrudan sunarken `/api/` ile başlayan istekleri `uygulama:8000` servisine iletir.

## 2. Bir İsteğin Uygulama İçindeki Yolu (Rezervasyon Örneği)

Bir rezervasyon isteğinin `route -> service -> dal -> yanıt` akışı:

1. **Route (`backend/app/routers/reservations.py`):**
```python
@router.post("", response_model=ReservationCreateResponse, summary="Rezervasyon Yap")
def create_reservation(req: ReservationCreateRequest, user: dict = Depends(get_current_user)):
    return ReservationService.create_reservation(user["id"], req.menu_id)
```

2. **Service (`backend/app/services/reservation_service.py`):**
```python
class ReservationService:
    @staticmethod
    def create_reservation(kullanici_id: int, menu_id: int) -> Dict[str, Any]:
        try:
            result = ReservationDAL.make_reservation(kullanici_id, menu_id)
            return {
                "message": "Rezervasyonunuz başarıyla oluşturuldu.",
                "rezervasyon_id": result["rezervasyon_id"],
                "guncel_bakiye": result["guncel_bakiye"],
            }
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
```

3. **Veri Katmanı / DAL (`backend/app/dal/reservation_dal.py`):**
```python
class ReservationDAL:
    @staticmethod
    def make_reservation(kullanici_id: int, menu_id: int) -> Dict[str, Any]:
        with get_primary_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("CALL sp_rezervasyon_yap(%s, %s);", (kullanici_id, menu_id))
                cursor.execute(
                    "SELECT id FROM rezervasyonlar WHERE kullanici_id = %s AND menu_id = %s AND durum = 'aktif';",
                    (kullanici_id, menu_id),
                )
                rez_row = cursor.fetchone()
                cursor.execute("SELECT bakiye FROM kullanicilar WHERE id = %s;", (kullanici_id,))
                user_row = cursor.fetchone()
            conn.commit()
            return {"rezervasyon_id": rez_row["id"], "guncel_bakiye": float(user_row["bakiye"])}
```

4. **Yanıt:** Stored procedure (`sp_rezervasyon_yap`) hata fırlatırsa (`SQLSTATE 45000`), `handle_mysql_error` bunu `ValueError` olarak yükseltir; service HTTP 400 döner ve arayüz mesajı ekranda gösterir. Başarılı durumda HTTP 200 JSON yanıtı döner. *(Not: Aşama 4'te `sp_rezervasyon_yap` prosedürüne `p_porsiyon` parametresi eklenmiştir.)*

## 3. Replikasyon Gecikmesi (Replication Lag) Açıklaması

MySQL replikasyonu asenkron çalıştığı için primary sunucuda yapılan bir yazma işleminin binary log üzerinden replikaya geçmesi kısa bir gecikmeyle (replication lag) gerçekleşebilir. Eğer kullanıcı rezervasyon yaptıktan hemen sonra güncel bakiyesini replikadan okusaydı, replika henüz güncellenmediği durumda eski bakiyesini görebilirdi. Bu yüzden listeleme ve menü sorguları replikaya (`get_replica_connection`) gönderilirken, rezervasyon, iptal ve bakiye yükleme sonrasında gösterilen bakiye doğrudan primary sunucudan (`get_primary_connection` / `use_primary=True`) okunmaktadır.

## 4. Arayüz Ekranları

1. **Giriş ve Çıkış:** E-posta ve şifre ile giriş, bcrypt doğrulaması.
2. **Günün Menüsü:** Yemekhane, öğün ve tarih seçimi; yemekler, toplam kalori, vejetaryen ve alerjen bilgisi.
3. **Haftalık Menü ve Rezervasyon:** Boş yer sayısı, role göre ücret, son saat geçtiyse pasif düğme.
4. **Rezervasyonlarım:** Aktif, kullanıldı ve iptal durumları; süresi dolmamışsa iptal imkanı.
5. **Bakiye:** Güncel bakiye, hareket geçmişi ve bakiye yükleme.
6. **Değerlendirme:** Kullanılmış menüye 1-5 puan ve yorum.
7. **Yönetici Paneli:** Menü oluşturma, menü düzenleme, menü bazında doluluk ve ortalama puan listesi.
