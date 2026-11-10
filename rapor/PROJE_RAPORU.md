# Kampüs Yemekhane Otomasyonu - Proje Raporu

- **Ders:** Web Teknolojileri
- **Öğretim Üyesi:** Burak Yılmaz
- **Mimari Seçimi:** Seçenek B - Web API + Arayüz (FastAPI + HTML5 / CSS3 / Vanilla JS)
- **Altyapı:** Docker Compose (6 container: `mysql-primary`, `mysql-replica`, `replica-setup`, `redis`, `uygulama`, `frontend`)

## 1. Mimari Seçimi ve İstek Akışı

Projede **Web API + Arayüz** yolu seçilmiştir. Sunucu tarafında Python FastAPI ile yalnızca JSON döndüren katmanlı bir REST API yazılmış; istemci tarafında ise React gibi bir çerçeve kullanılmadan HTML5, CSS3 ve Vanilla JS (`fetch`) ile masaüstü ve ~400 px mobil ekranlara uyumlu 7 ekranlık arayüz geliştirilmiştir. Apache 2.4 (`:8080`) statik dosyaları sunar ve `/api/` isteklerini iç ağdaki `uygulama:8000` servisine yönlendirir.

### Bir İsteğin Uygulama İçindeki Yolu (`POST /api/reservations`)

1. **Route (`backend/app/routers/reservations.py`):**
```python
@router.post("", response_model=ReservationCreateResponse, summary="Rezervasyon Yap")
def create_reservation(req: ReservationCreateRequest, user: dict = Depends(get_current_user)):
    return ReservationService.create_reservation(user["id"], req.menu_id, req.porsiyon)
```
2. **Service (`backend/app/services/reservation_service.py`):**
```python
result = ReservationDAL.make_reservation(kullanici_id, menu_id, porsiyon)
coords = MenuDAL.get_menu_cache_coords(menu_id)
if coords:
    invalidate_menu_cache(coords["yemekhane_id"], str(coords["tarih"]), coords["ogun_id"])
return {"message": "Rezervasyonunuz başarıyla oluşturuldu.", "rezervasyon_id": result["rezervasyon_id"], "guncel_bakiye": result["guncel_bakiye"]}
```
3. **Veri Katmanı / DAL (`backend/app/dal/reservation_dal.py`):**
```python
with get_primary_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute("CALL sp_rezervasyon_yap(%s, %s, %s);", (kullanici_id, menu_id, porsiyon))
        cursor.execute("SELECT bakiye FROM kullanicilar WHERE id = %s;", (kullanici_id,))
        user_row = cursor.fetchone()
    conn.commit()
    mark_primary_write(conn)
```
4. **Yanıt:** `sp_rezervasyon_yap` prosedürü kural hatasında `SQLSTATE '45000'` döndürür; `handle_mysql_error` bunu `ValueError` yapar, service HTTP `400` JSON yanıtı döner ve arayüz mesajı kullanıcıya gösterir.

### Replikasyon Gecikmesi (Replication Lag) Açıklaması

Listeleme ve menü sorguları `get_replica_connection()` üzerinden replika sunucusuna gönderilir. Ancak rezervasyon yapma, iptal ve bakiye yükleme sonrasında ekranda gösterilen güncel bakiye doğrudan primary sunucudan (`get_primary_connection()` / `use_primary=True`) okunur. MySQL replikasyonu asenkron çalıştığı için primary'de yapılan güncellemenin replikaya geçmesinde kısa bir gecikme yaşanabilir; doğrudan primary'den okuyarak kullanıcının eski bakiyeyi görmesi engellenir.

## 2. Aşama 1: Altyapı ve GTID Replikasyonu

- `docker compose ps` çıktısında `frontend`, `uygulama`, `mysql-primary`, `mysql-replica`, `redis` servisleri `healthy`, `replica-setup` ise `Exited (0)` durumundadır.
- `SHOW REPLICA STATUS\G` çıktısında `Replica_IO_Running: Yes`, `Replica_SQL_Running: Yes`, `Seconds_Behind_Source: 0`, `Auto_Position: 1` olarak doğrulandı.
- Primary üzerinde `CALL sp_bakiye_yukle(6, 100.00)` çağrıldıktan sonra replikada `SELECT id, ad, bakiye FROM kullanicilar WHERE id = 6;` ile `290.00` görüldü.
- Replikaya yazma denemesi (`UPDATE kullanicilar SET bakiye = 9999 WHERE id = 6;`) `--super-read-only` nedeniyle `ERROR 1290 (HY000)` ile reddedildi.
- `docker stop yemekhane-mysql-replica` ardından primary'de `CALL sp_bakiye_yukle(6, 50.00)` çalıştırılıp `docker start yemekhane-mysql-replica` yapıldığında replika GTID ile aradaki farkı otomatik yakaladı (`340.00`).

## 3. Aşama 3: Redis Önbellek ve Oturum Yönetimi

- **Menü önbelleği (`menu:{yemekhane_id}:{tarih}:{ogun_id}`):** Gün sonuna (`23:59:59`) kadar TTL ile saklanır. İlk istekte `[CACHE MISS]` / `[CACHE SET]`, sonraki isteklerde `[CACHE HIT]` logu oluşur (`redis-cli ttl "menu:1:2026-10-27:2"` -> `19148`). Menü güncellendiğinde (ve rezervasyon/değerlendirmede) anahtar silinir (`redis-cli exists ...` -> `0`).
- **Oturum (`oturum:{token}`):** 30 dakika TTL ile tutulur ve her istekte yenilenir. `docker restart yemekhane-uygulama` sonrasında `GET /api/auth/me` `200 OK` döner; `/api/auth/logout` ile anahtar silinir (`exists` -> `0`).

## 4. Aşama 4: Değişiklik Talebi (`04_degisiklik.sql`)

- `rezervasyonlar` tablosuna `porsiyon ENUM('tam', 'yarim') NOT NULL DEFAULT 'tam'` sütunu eklendi ve `kullanici_alerjenleri` tablosu oluşturuldu. Replikadan `SHOW CREATE TABLE rezervasyonlar\G` ve `SHOW CREATE TABLE kullanici_alerjenleri\G` çıktılarıyla geçiş doğrulandı.
- Kahvaltıda yarım porsiyon talebi `sp_rezervasyon_yap` tarafından reddedilir (`HTTP 400`, `Kahvaltıda yarım porsiyon seçeneği bulunmamaktadır.`). Öğle/akşam menülerinde ücret `%60` hesaplanır (`45.00 TL -> 27.00 TL`).
- Kullanıcı alerjenlerini profilinden seçer; menüde eşleşen yemekler kırmızı uyarı ile gösterilir.
- Eski menü önbellek kayıtları `docker exec yemekhane-redis redis-cli flushdb` ile temizlendi.

## 5. Ekran Görüntüleri

![Giriş Ekranı](ekran_goruntuleri/01_giris.png)
![Günün Menüsü](ekran_goruntuleri/02_gunun_menusu.png)
![Alerjen Tercihleri](ekran_goruntuleri/03_alerjenler.png)
![Bakiye Yönetimi](ekran_goruntuleri/04_bakiye.png)
![400px Mobil Görünüm](ekran_goruntuleri/05_mobil_400px.png)
