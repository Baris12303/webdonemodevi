# Aşama 4: Değişiklik Talebi (`04_degisiklik.sql`)

Yemekhane müdürlüğünden gelen değişiklik talebi kapsamında iki özellik eklenmiştir:
1. **Yarım porsiyon:** Öğle ve akşam menülerinde yarım porsiyon seçilebilir, ücreti tam fiyatın %60'ıdır. Kahvaltıda yarım porsiyon yoktur. Geçmiş rezervasyonlar tam porsiyon sayılır.
2. **Alerjen uyarısı:** Kullanıcı profilinden alerjenlerini seçer; menüde bu alerjenleri içeren yemekler uyarı ile gösterilir.

## 1. Migration Dosyası (`db/04_degisiklik.sql`)

Dosya mevcut veriyi bozmadan primary veritabanı üzerinde çalışacak ve tekrar çalıştırıldığında hata vermeyecek şekilde yazılmıştır:
- `rezervasyonlar` tablosuna `porsiyon ENUM('tam', 'yarim') NOT NULL DEFAULT 'tam'` sütunu eklendi.
- `kullanici_alerjenleri (kullanici_id, alerjen_id)` tablosu oluşturuldu.
- `sp_rezervasyon_yap` prosedürü `p_porsiyon` parametresi alacak, kahvaltıda yarım porsiyonu `SQLSTATE '45000'` ile reddedecek ve yarım porsiyonda `%60` ücret kesecek şekilde güncellendi.

## 2. Replikaya Geçiş Kanıtı (`SHOW CREATE TABLE`)

Migration primary üzerinde çalıştırıldıktan sonra replika üzerinden `SHOW CREATE TABLE` ile şemanın geçtiği kontrol edildi:

```bash
docker exec yemekhane-mysql-replica mysql -u root -prootpass yemekhane_db -e "SHOW CREATE TABLE rezervasyonlar\G SHOW CREATE TABLE kullanici_alerjenleri\G"
```

```sql
*************************** 1. row ***************************
       Table: rezervasyonlar
Create Table: CREATE TABLE `rezervasyonlar` (
  `id` int NOT NULL AUTO_INCREMENT,
  `kullanici_id` int NOT NULL,
  `menu_id` int NOT NULL,
  `ucret` decimal(10,2) NOT NULL,
  `porsiyon` enum('tam','yarim') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'tam',
  `durum` enum('aktif','kullanildi','iptal') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'aktif',
  ...
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci

*************************** 1. row ***************************
       Table: kullanici_alerjenleri
Create Table: CREATE TABLE `kullanici_alerjenleri` (
  `kullanici_id` int NOT NULL,
  `alerjen_id` int NOT NULL,
  `olusturulma_tarihi` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`kullanici_id`,`alerjen_id`),
  ...
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

## 3. Uygulama ve Redis Doğrulaması

### 3.1. Kahvaltıda Yarım Porsiyon Reddi
```json
POST /api/reservations {"menu_id": 49, "porsiyon": "yarim"}
-> HTTP 400 Bad Request
{"detail": "Kahvaltıda yarım porsiyon seçeneği bulunmamaktadır."}
```

### 3.2. Öğle Menüsünde Yarım Porsiyon (%60 Ücret) ve İptal
`45.00 TL` tam fiyatlı öğle menüsünde yarım porsiyon rezervasyonu yapıldığında `27.00 TL` kesildi (`190.00 TL -> 163.00 TL`):
```json
POST /api/reservations {"menu_id": 50, "porsiyon": "yarim"}
-> HTTP 200 OK
{"message": "Rezervasyonunuz başarıyla oluşturuldu.", "rezervasyon_id": 366, "guncel_bakiye": 163.0}
```

Rezervasyon iptal edildiğinde kesilen `27.00 TL` iade edildi:
```json
POST /api/reservations/366/cancel
-> HTTP 200 OK
{"message": "Rezervasyon başarıyla iptal edildi ve ücret bakiyenize iade edildi.", "guncel_bakiye": 190.0}
```

### 3.3. Alerjen Seçimi ve Menü Uyarısı
`POST /api/auth/allergens` ile `Gluten` (`1`) ve `Laktoz` (`2`) seçildiğinde, bu alerjenleri içeren yemeklerin bulunduğu menüde uyarı kutusu ve ilgili yemek satırlarında kırmızı alerjen etiketi gösterildi.

### 3.4. Redis Eski Önbellek Kayıtlarının Temizlenmesi
Şema değişikliği sonrası eski yapıdaki menü önbellek kayıtları temizlendi:
```bash
docker exec yemekhane-redis redis-cli flushdb
```
