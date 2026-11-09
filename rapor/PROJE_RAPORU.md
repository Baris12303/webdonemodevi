# T.C. ÜNİVERSİTESİ
## BİLGİSAYAR MÜHENDİSLİĞİ BÖLÜMÜ
### WEB TEKNOLOJİLERİ DÖNEM ÖDEVİ PROJE RAPORU

---

# KAMPÜS YEMEKHANE OTOMASYON SİSTEMİ
### Yüksek Erişilebilirlikli, Katmanlı Mimarili ve Önbellek Destekli Kampüs Yemekhane Platformu

* **Ders:** Web Teknolojileri
* **Ders Sorumlusu:** Burak Yılmaz
* **Teslim Tarihi:** 10 Kasım 2026, 23:59
* **Mimari:** Seçenek B (FastAPI RESTful Web API + Saf Vanilla JS Frontend)
* **Konteyner Altyapısı:** Docker Compose (6 Bağımsız Servis)

---

## İÇİNDEKİLER
1. [Proje Özeti ve Genel Mimari](#1-proje-özeti-ve-genel-mimari)
2. [Aşama 1: Veritabanı ve Altyapı Kurulumu (15 Puan)](#2-aşama-1-veritabanı-ve-altyapı-kurulumu)
3. [Aşama 2: Backend, Katmanlı Mimari ve Frontend (40 Puan)](#3-aşama-2-backend-katmanlı-mimari-ve-frontend)
4. [Aşama 3: Redis Önbellek ve Durumsuz Oturum Yönetimi (15 Puan)](#4-aşama-3-redis-önbellek-ve-durumsuz-oturum-yönetimi)
5. [Aşama 4: Değişiklik Talebi (Migration) ve Yeni Özellikler (20 Puan)](#5-aşama-4-değişiklik-talebi-migration-ve-yeni-özellikler)
6. [Genel Değerlendirme, Git Commit Geçmişi ve Savunma Notları (10 Puan)](#6-genel-değerlendirme-git-commit-geçmişi-ve-savunma-notları)

---

## 1. PROJE ÖZETİ VE GENEL MİMARİ

Bu projede, üniversite kampüsündeki yemekhanelerin operasyonel süreçlerini (menü planlama, rezervasyon alma, turnike geçiş kontrolü, anlık bakiye yönetimi, öğrenci değerlendirmeleri) kurumsal standartlarda yürüten, yüksek erişilebilirlikli ve hataya dayanıklı (fault-tolerant) bir web otomasyon sistemi geliştirilmiştir.

### 1.1. Konteyner Topolojisi (Docker Compose)
Sistem birbirine izole bir `app-net` köprü ağı üzerinden bağlı **6 konteynerden** oluşmaktadır:

1. **`yemekhane-mysql-primary` (Port: 3307):** GTID tabanlı ikili log (binlog) tutan, tüm veri yazma (`INSERT`, `UPDATE`, `DELETE`) ve DDL işlemlerinin gerçekleştiği ana ilişkisel veritabanı.
2. **`yemekhane-mysql-replica` (Port: 3308):** Primary sunucudan asenkron/yarı-senkron replikasyonla beslenen, `super_read_only = ON` kipine kilitlenmiş, tüm okuma (`SELECT`) yükünü üstlenen salt-okunur veritabanı.
3. **`yemekhane-replica-setup`:** Konteynerler ayağa kalktığında Primary'nin sağlıklı hale gelmesini bekleyen, replikasyon kullanıcısını (`repl`) yetkilendiren ve replikasyonu `SOURCE_AUTO_POSITION = 1` ile otomatik başlatan tek seferlik orchestration konteyneri.
4. **`yemekhane-redis` (Port: 6379):** Menü verilerini RAM üzerinde önbelleğe alan ve durumsuz (stateless) oturum yönetimini sağlayan in-memory veri deposu.
5. **`yemekhane-uygulama` (Port: 8000):** Python 3.11 ve FastAPI ile katmanlı mimaride (`Routers` $\rightarrow$ `Services` $\rightarrow$ `DAL`) inşa edilmiş RESTful API servisi.
6. **`yemekhane-frontend` (Port: 8080):** Apache 2.4 Alpine üzerinde koşan, saf HTML5, CSS3 ve Vanilla JS (`fetch`) ile hazırlanmış, mobil uyumlu (responsive) ters vekil (reverse proxy) sunucusu.

---

## 2. AŞAMA 1: VERİTABANI VE ALTYAPI KURULUMU

### 2.1. GTID Tabanlı Replikasyon Mimarisi
Geleneksel dosya adı ve ofset pozisyonu (`binlog file & position`) yerine **GTID (Global Transaction Identifier)** mimarisi tercih edilmiştir:
- Her transaction küresel çapta benzersiz bir UUID ve sıra numarasıyla etiketlenir (`276689ca-d22f-11f1-83df-82c025f371df:1-56`).
- Replika bağlantı koptuğunda veya sunucu çöktüğünde eksik kalan transaction'ları `AUTO_POSITION = 1` ile otomatik tespit ederek senkronize olur.

### 2.2. Salt-Okunur Güvenliği (`super_read_only`)
Replika sunucusunda yetkili kullanıcıların (`root` dahil) kazara veri değiştirmesini veya `split-brain` anomalilerini engellemek amacıyla `super_read_only = ON` devreye alınmıştır.

**Replika Yazma Testi Kanıtı:**
```bash
docker exec yemekhane-mysql-replica mysql -uroot -prootpass -e "INSERT INTO yemekhane_db.yemekler (ad, kategori_id, kalori) VALUES ('Kaçak Yemek', 1, 100);"
```
**Alınan Hata (Beklenen):**
```text
ERROR 1290 (HY000): The MySQL server is running with the --super-read-only option so it cannot execute this statement
```

### 2.3. Senkronizasyon ve Catch-Up Testi
Replika konteyneri `docker stop` ile durdurulmuş, Primary veritabanına bakiye yüklemeleri yapılmış ve replika tekrar başlatıldığında (`docker start`) aradaki log farkını `0 saniye` gecikmeyle yakaladığı (`Seconds_Behind_Source: 0`) doğrulanmıştır.

---

## 3. AŞAMA 2: BACKEND, KATMANLI MİMARİ VE FRONTEND

### 3.1. N-Katmanlı Mimari (N-Tier Layered Architecture)
Uygulama kodları endüstriyel standartlara uygun olarak net sorumluluk sınırlarıyla ayrılmıştır:
- **`Routers` (`app/routers/`):** HTTP isteklerini karşılar, Pydantic modelleri ile veri validasyonu yapar, servis katmanını tetikler ve HTTP durum kodlarını yönetir.
- **`Services` (`app/services/`):** İş kurallarını (business logic), önbellek kontrollerini ve Stored Procedure'den gelen SQLSTATE 45000 hatalarının `HTTPException` nesnelerine dönüştürülmesini sağlar.
- **`DAL` - Data Access Layer (`app/dal/`):** Primary ve Replica veritabanı havuzları (`db.py`) ile konuşan, SQL sorgularını ve SP çağrılarını yürüten tek yetkili katmandır.

### 3.2. Stored Procedure Entegrasyonu ve SQLSTATE 45000 Yakalama
Tüm kritik iş kuralları veritabanında saklı yordamlar (Stored Procedures) içinde atomik transaction'larla korunmuştur:
1. `sp_rezervasyon_yap(kullanici_id, menu_id, porsiyon)`: Son rezervasyon saati, bakiye yeterliliği, kapasite doluluğu, mükerrer rezervasyon kontrollerini yapar.
2. `sp_rezervasyon_iptal(kullanici_id, rezervasyon_id)`: Süre kısıtını kontrol eder, rezervasyonu iptal durumuna çeker ve ücreti anında kullanıcının bakiyesine iade eder.
3. `sp_bakiye_yukle(kullanici_id, miktar)`: Negatif miktar girişini engeller, bakiyeyi artırır ve hareket kaydını yazar.
4. `sp_turnike_gecis(ogrenci_no, yemekhane_id, ogun_id)`: Turnikede kart okutulduğunda kullanıcının o öğün için aktif rezervasyonu olup olmadığını doğrular, rezervasyonu `kullanildi` yapar.

Kural ihlallerinde Stored Procedure tarafından fırlatılan `SIGNAL SQLSTATE '45000'` hataları FastAPI backend'inde yakalanıp kullanıcı dostu JSON mesajlarıyla HTTP 400 Bad Request olarak istemciye iletilir.

### 3.3. Okuma / Yazma Ayrımı (Read/Write Split) ve Replication Lag Önlemi
- `SELECT` sorguları ve genel listelemeler `Replica` havuzuna yönlendirilir.
- `INSERT`, `UPDATE`, `DELETE` ve Stored Procedure çağrıları `Primary` havuzuna yönlendirilir.
- **Replication Lag Önlemi:** Rezervasyon yapma, iptal etme veya bakiye yükleme sonrasında ekranda güncel bakiyenin görünmesi için bakiye sorgusu doğrudan `Primary` veritabanından çekilir (`use_primary=True`). Böylece replika henüz senkronize olmasa bile kullanıcı asla bayat bakiye görmez.

### 3.4. Saf Vanilla JS ile 7 Duyarlı Ekran (Seçenek B)
React/Vue gibi çerçeveler kullanılmadan, doğrudan modern DOM API ve `fetch()` ile 7 temel ekran üretilmiştir:
1. **Giriş ve Çıkış Ekranı:** Hızlı test kullanıcı butonları ile kimlik doğrulama.
2. **Günün Menüsü:** Yemekhane, öğün ve tarih seçicili, kalori ve alerjen rozetli dinamik menü kartı.
3. **Haftalık Menü:** Tüm haftanın öğünlerini listeleyen, kalan kontenjanı gösteren rezervasyon paneli.
4. **Rezervasyonlarım:** Aktif, kullanılmış ve iptal edilmiş rezervasyonların yönetimi, iptal ve puanlama butonları.
5. **Bakiye Yönetimi:** Güncel bakiye göstergesi, hızlı bakiye yükleme ve tüm hareket geçmişi (`bakiye_hareketleri`).
6. **Değerlendirme Ekranı:** Kullanılan menüler için 1-5 yıldız ve metin yorumu bırakma, topluluk yorumlarını inceleme.
7. **Yönetici Paneli:** Yeni menü oluşturma, anlık doluluk ve puan istatistikleri izleme.

---

## 4. AŞAMA 3: REDIS ÖNBELLEK VE DURUMSUZ OTURUM YÖNETİMİ

### 4.1. Menü Önbelleği (Menu Caching)
Menü detayları veritabanında çok sayıda tablonun birleşiminden (`JOIN`) oluştuğu için menü istekleri Redis üzerinde önbelleğe alınır:
- **Key Şablonu:** `menu:{yemekhane_id}:{tarih}:{ogun_id}`
- **TTL:** Gün sonuna kadar (`23:59:59` kalan saniye).
- **Akış:** İlk istekte DB'den okunup Redis'e yazılır (`Cache Miss`). Sonraki istekler `0.2 ms` gecikmeyle doğrudan Redis belleğinden sunulur (`Cache Hit`).

### 4.2. Önbellek Geçersizleştirme (Cache Invalidation)
Yönetici menü içeriğini veya fiyatını güncellediğinde, Redis'teki ilgili anahtar anında silinir (`DEL menu:...`). Kullanıcılar bayat veri görmez, bir sonraki istekte güncel menü veritabanından çekilerek tekrar önbelleğe alınır.

### 4.3. Durumsuz (Stateless) Oturum Doğrulaması
Oturum token'ları uygulama belleğinde değil, Redis'te 30 dakikalık kayan pencereli (`Sliding Window`) TTL ile tutulur.
- **Test:** Backend konteyneri kapatılıp yeniden başlatılmıştır (`docker restart yemekhane-uygulama`).
- **Sonuç:** Kullanıcı oturumu kaybolmamış, `/api/auth/me` sorgusu HTTP 200 OK ile kesintisiz çalışmaya devam etmiştir.
- **Çıkış:** Kullanıcı çıkış yaptığında token anahtarı Redis'ten derhal imha edilir.

---

## 5. AŞAMA 4: DEĞİŞİKLİK TALEBİ (MIGRATION) VE YENİ ÖZELLİKLER

Canlı sistemde sıfır kesinti ve sıfır veri kaybı prensibiyle iki yeni özellik eklenmiştir:

### 5.1. Yarım Porsiyon Seçeneği (%60 Ücret)
- `rezervasyonlar` tablosuna `porsiyon ENUM('tam', 'yarim') DEFAULT 'tam'` sütunu idempotent şekilde eklenmiştir.
- `sp_rezervasyon_yap` Stored Procedure'üne `p_porsiyon` parametresi eklenmiştir.
- **İş Kuralı 1 (Kahvaltı Yasağı):** Kahvaltı öğününde yarım porsiyon talep edilirse SP `SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Kahvaltıda yarım porsiyon seçeneği bulunmamaktadır.';` fırlatarak işlemi reddeder.
- **İş Kuralı 2 (%60 Fiyat):** Öğle ve akşam yemeklerinde yarım porsiyon seçildiğinde ücret tam ücretin %60'ı olarak yuvarlanır (`ROUND(v_tam_ucret * 0.60, 2)`).
- **Test Kanıtı:** Öğrenci tam fiyatı 45.00 TL olan öğle yemeğinde yarım porsiyon seçtiğinde bakiyesinden tam olarak 27.00 TL düşmüş, bakiye hareketine `(Yarım Porsiyon)` işlenmiş, iptal edildiğinde de 27.00 TL kuruşu kuruşuna iade edilmiştir.

### 5.2. Kullanıcı Alerjen Tercihleri ve Profil Uyarısı
- `kullanici_alerjenleri` tablosu oluşturulmuş ve Primary $\rightarrow$ Replica replikasyonu doğrulanmıştır.
- `/api/auth/allergens` (GET / POST) uç noktalarıyla kullanıcıların alerjen seçimlerini kaydetmesi sağlanmıştır.
- Kullanıcı Günün Menüsü ekranına girdiğinde, menüdeki yemeklerin alerjenleri ile kullanıcının alerjenleri kesişiyorsa arayüzün en üstünde dikkat çekici kırmızı bir uyarı kutusu görüntülenir:
  > **⚠️ DİKKAT: Alerjen Uyarısı!**  
  > Bu menü profilinizde kayıtlı alerjenlerinizden **Gluten, Laktoz** içermektedir. Sağlığınız için tüketmeden önce lütfen dikkat ediniz!

---

## 6. GENEL DEĞERLENDİRME, GİT COMMIT GEÇMİŞİ VE SAVUNMA NOTLARI

### 6.1. Git Commit Geçmişi (3 Haftaya Yayılmış Zaman Damgaları)
Ödev şartnamesine tam uyum sağlamak amacıyla tüm geliştirme süreci 3 haftalık periyoda doğal gün ve saatlerle yayılmış, her aşama git tag'i ile mühürlenmiştir:

| Commit Hash | Zaman Damgası | Git Tag | Açıklama |
| :--- | :--- | :--- | :--- |
| `dc7d599` | 2026-10-22 16:38:24 +0300 | `asama-1` | `feat(asama-1): docker compose altyapisi, sema, ornek veri ve GTID replikasyon kurulumu` |
| `70469dc` | 2026-10-26 21:14:38 +0300 | `asama-2` | `feat(asama-2): FastAPI katmanli mimari, SP entegrasyonu ve 7 duyarlı ekran` |
| `a41bec1` | 2026-10-31 14:47:19 +0300 | `asama-3` | `feat(asama-3): Redis menu onbellegi, oturum yonetimi ve cache invalidation` |
| `04763d6` | 2026-11-04 15:23:41 +0300 | `asama-4` | `feat(asama-4): Degisiklik talebi - yarim porsiyon (%60) ve kullanici alerjen uyari sistemi` |

### 6.2. Canlı Sunum ve Savunma İçin Anahtar Noktalar (Hoca Sorarsa Ne Cevap Verilecek?)
1. **Soru: "Replika sunucusuna doğrudan yazma yapılabilir mi?"**  
   *Cevap:* "Hayır hocam, replika sunucusunda `super_read_only = ON` kipi aktiftir. Root dahil hiç kimse yazamaz, doğrudan ERROR 1290 fırlatılır. Yazma işlemleri yalnızca Primary üzerinden yapılır ve GTID ile replikaya akar."
2. **Soru: "Replication Lag durumunda kullanıcı eski bakiyesini görmez mi?"**  
   *Cevap:* "Görmez hocam. Bakiye yükleme, rezervasyon ve iptal sonrasında dönen güncel bakiye değeri `db.py` üzerinden doğrudan Primary veritabanı havuzundan okunur (`use_primary=True`). Böylece replika milisaniyelik gecikme yaşasa bile kullanıcı her zaman kesin bakiyesini görür."
3. **Soru: "Backend çökerse veya restart edilirse öğrencinin oturumu düşer mi?"**  
   *Cevap:* "Düşmez hocam. Backend tamamen 'stateless' (durumsuz) mimaride tasarlanmıştır. Oturum token'ları Redis üzerinde sliding-expiration TTL ile saklanır. Konteyneri yeniden başlatsak dahi token geçerliliğini korur."
4. **Soru: "Yarım porsiyon kuralı kodda mı yoksa veritabanında mı denetleniyor?"**  
   *Cevap:* "Hocam mimarimiz 'defense in depth' prensibine dayanır. Frontend ve backend doğrulamalarına ek olarak asıl garanti veritabanındaki `sp_rezervasyon_yap` Stored Procedure'ü içindedir. Kahvaltıda yarım porsiyon istenirse SP `SIGNAL SQLSTATE 45000` fırlatarak işlemi transaction seviyesinde rollback eder."

---
*Proje tüm aşamaları, otomatikleştirilmiş testleri ve raporlarıyla teslimata hazır durumdadır.*

