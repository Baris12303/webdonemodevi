# Aşama 4: Değişiklik Talebi (Migration) ve Yeni Özellikler Raporu

## 1. Giriş ve Kapsam
Bu aşamada, canlı çalışan sistemi ve mevcut verileri bozmadan iki yeni iş gereksinimi sisteme entegre edilmiştir:
1. **Yarım Porsiyon Seçeneği:** Kullanıcılar kahvaltı hariç (öğle ve akşam) menüler için yarım porsiyon seçebilmelidir. Yarım porsiyon ücreti normal ücretin **%60'ı** olarak hesaplanır.
2. **Kullanıcı Alerjen Tercihleri ve Profil Uyarısı:** Kullanıcılar profillerinden hassas oldukları alerjenleri seçebilmeli; menüde bu alerjenleri içeren yemekler varsa sistem kullanıcıyı belirgin şekilde uyarmalıdır.

Tüm veritabanı değişiklikleri `db/04_degisiklik.sql` migration dosyası aracılığıyla canlı Primary veritabanında çalıştırılmış ve GTID replikasyonuyla Replica sunucusuna anında aktarılmıştır.

---

## 2. Veritabanı Değişiklikleri (`04_degisiklik.sql`)

### 2.1. İdempotent Şema Güncellemesi
MySQL 8.0 ortamında `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` doğrudan desteklenmediğinden, geçişin güvenli ve tekrar çalıştırılabilir (idempotent) olması için `information_schema.COLUMNS` kontrolü yapan bir prosedür kullanılmıştır:

```sql
-- rezervasyonlar tablosuna porsiyon sütunu ekleme (Varsayılan: 'tam')
DELIMITER $$
DROP PROCEDURE IF EXISTS _tmp_add_porsiyon$$
CREATE PROCEDURE _tmp_add_porsiyon()
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = 'yemekhane_db' 
          AND TABLE_NAME = 'rezervasyonlar' 
          AND COLUMN_NAME = 'porsiyon'
    ) THEN
        ALTER TABLE rezervasyonlar ADD COLUMN porsiyon ENUM('tam', 'yarim') NOT NULL DEFAULT 'tam' AFTER ucret;
    END IF;
END$$
DELIMITER ;
CALL _tmp_add_porsiyon();
DROP PROCEDURE IF EXISTS _tmp_add_porsiyon;
```

### 2.2. Kullanıcı Alerjen Tablosu
Kullanıcıların seçtiği alerjenler çoktan-çoğa (`N:M`) ilişki kurularak `kullanici_alerjenleri` tablosunda saklanır:

```sql
CREATE TABLE IF NOT EXISTS kullanici_alerjenleri (
    kullanici_id INT NOT NULL,
    alerjen_id INT NOT NULL,
    olusturulma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (kullanici_id, alerjen_id),
    FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(id) ON DELETE CASCADE,
    FOREIGN KEY (alerjen_id) REFERENCES alerjenler(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 2.3. Stored Procedure Güncellemesi (`sp_rezervasyon_yap`)
İş kuralları doğrudan Stored Procedure seviyesinde güvence altına alınmıştır:
- **Kahvaltı Kısıtı:** `IF p_porsiyon = 'yarim' AND v_ogun_adi = 'Kahvaltı' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Kahvaltıda yarım porsiyon seçeneği bulunmamaktadır.'; END IF;`
- **%60 Fiyat Hesabı:** `SET v_ucret = ROUND(v_tam_ucret * 0.60, 2);`
- **Bakiye Hareketi Açıklaması:** Harekete `(Yarım Porsiyon)` veya `(Tam Porsiyon)` etiketi eklenir.

---

## 3. GTID Replikasyon Doğrulaması (Primary $\rightarrow$ Replica)

Migration scripti Primary veritabanında çalıştırıldıktan sonra, Replica sunucusunun şemayı ve veriyi kayıpsız aldığı doğrulanmıştır.

### 3.1. Replica Üzerinde Tablo Yapısı Kontrolü
```bash
docker exec yemekhane-mysql-replica mysql -uroot -prootpass -e "SHOW CREATE TABLE yemekhane_db.rezervasyonlar\G"
```
**Çıktı Özeti:**
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
) ENGINE=InnoDB ...
```

### 3.2. Replica Replikasyon Durumu
```text
Replica_IO_Running: Yes
Replica_SQL_Running: Yes
Seconds_Behind_Source: 0
Retrieved_Gtid_Set: 276689ca-d22f-11f1-83df-82c025f371df:1-56
Executed_Gtid_Set: 276689ca-d22f-11f1-83df-82c025f371df:1-56
```

---

## 4. Fonksiyonel Doğrulama ve Test Çıktıları

### 4.1. Test 1: Kahvaltıda Yarım Porsiyon Reddi
Öğrenci kullanıcısı (`ogrenci1@kampus.edu.tr`), Kahvaltı menüsü için yarım porsiyon rezervasyonu yapmayı denemiştir.

**İstek:**
```json
POST /api/reservations
{
  "menu_id": 49,
  "porsiyon": "yarim"
}
```

**Yanıt (HTTP 400 Bad Request):**
```json
{
  "detail": "Kahvaltıda yarım porsiyon seçeneği bulunmamaktadır."
}
```
*Sonuç: Stored Procedure kuralı tetiklenmiş, SQLSTATE 45000 fırlatılmış ve işlem rollback edilmiştir.*

---

### 4.2. Test 2: Öğle Menüsünde Yarım Porsiyon Rezervasyonu ve %60 Fiyat Hesabı
Öğrenci normalde 45.00 TL olan Öğle menüsü (Menü #50) için yarım porsiyon seçerek rezervasyon yapmıştır.

- **Rezervasyon Öncesi Bakiye:** `190.00 TL`
- **Tam Porsiyon Fiyatı:** `45.00 TL`
- **Beklenen Yarım Porsiyon Ücreti (%60):** `45.00 * 0.60 = 27.00 TL`
- **Beklenen Rezervasyon Sonrası Bakiye:** `190.00 - 27.00 = 163.00 TL`

**API Yanıtı:**
```json
{
  "message": "Rezervasyonunuz başarıyla oluşturuldu.",
  "rezervasyon_id": 366,
  "guncel_bakiye": 163.0
}
```

**Veritabanı Kayıt Doğrulaması (`rezervasyonlar` Tablosu):**
```text
id: 366 | kullanici_id: 6 | menu_id: 50 | ucret: 27.00 | porsiyon: yarim | durum: aktif
```

**Bakiye Hareketi Kaydı (`bakiye_hareketleri` Tablosu):**
```text
id: 456 | miktar: -27.00 | tip: rezervasyon | aciklama: Rezervasyon ücreti: Menü #50 (Yarım Porsiyon)
```
*Sonuç: Kesinti tam %60 oranında yapılmış ve hareket geçmişine porsiyon türü yansıtılmıştır.*

---

### 4.3. Test 3: Yarım Porsiyon Rezervasyon İptali ve İade
Kullanıcı yarım porsiyon olarak oluşturduğu rezervasyonu iptal etmiştir.

**İstek:**
```bash
POST /api/reservations/366/cancel
```

**API Yanıtı:**
```json
{
  "message": "Rezervasyon başarıyla iptal edildi ve ücret bakiyenize iade edildi.",
  "guncel_bakiye": 190.0
}
```

**Bakiye Hareket Geçmişi:**
```text
id: 457 | miktar: +27.00 | tip: iade | aciklama: Rezervasyon iptal iadesi: #366
```
*Sonuç: İade işlemi tam olarak kesilen 27.00 TL üzerinden gerçekleştirilmiş, kullanıcının bakiyesi eksiksiz geri yüklenmiştir.*

---

### 4.4. Test 4: Kullanıcı Alerjen Tercihleri ve Arayüz Uyarısı
1. Öğrenci kullanıcısı profiline `Gluten (id: 1)` ve `Laktoz (id: 2)` alerjenlerini kaydetmiştir:
   ```bash
   POST /api/auth/allergens {"alerjen_ids": [1, 2]}
   ```
2. Günün Menüsü ekranında domates çorbası (Gluten ve Laktoz içerir) ve pirinç pilavı (Gluten içerir) bulunan menü açıldığında, arayüzün en üstünde kullanıcıyı uyaran kırmızı alert kutusu görüntülenmiştir:
   > ⚠️ **DİKKAT: Alerjen Uyarısı!**  
   > Bu menü profilinizde kayıtlı alerjenlerinizden **Gluten, Laktoz** içermektedir. Sağlığınız için tüketmeden önce lütfen dikkat ediniz!

---

## 5. Özet
Aşama 4 gereksinimleri canlı veritabanında hiçbir kesinti yaşanmadan, GTID replikasyonuyla senkronize şekilde ve arayüz/iş mantığı katmanlarıyla tam uyumlu olarak tamamlanmıştır.

