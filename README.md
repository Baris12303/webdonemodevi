# Kampüs Yemekhane Otomasyonu

Mikroservis mimarisine sahip, Docker üzerinde koşan, MySQL Master-Slave GTID replikasyonu, Redis Caching/Session ve FastAPI katmanlı mimarisiyle geliştirilmiş kampüs yemekhane otomasyon sistemi.

---

## 🚀 Hızlı Başlangıç

Tüm sistemi tek komutla ayağa kaldırın:
```bash
docker compose up -d
```

Servislerin sağlık durumunu kontrol edin:
```bash
docker compose ps
```

Sistemi durdurmak için:
```bash
docker compose down
```

Tüm verileri sıfırlayarak baştan başlatmak için:
```bash
docker compose down -v
docker compose up -d
```

---

## 🌐 Servisler ve Port Bilgileri

| Servis Adı | Container Adı | Dahili Port | Host Portu | Açıklama |
| :--- | :--- | :--- | :--- | :--- |
| **frontend** | `yemekhane-frontend` | 80 | `8080` | Apache 2.4 (HTML/CSS & Ters Proxy) |
| **uygulama** | `yemekhane-uygulama` | 8000 | - | FastAPI Katmanlı REST API (Apache üzerinden erişilir) |
| **mysql-primary** | `yemekhane-mysql-primary` | 3306 | `3307` | Birincil Veritabanı (Yazma işlemleri & Şema) |
| **mysql-replica** | `yemekhane-mysql-replica` | 3306 | `3308` | İkincil Veritabanı (Salt okunur replika) |
| **redis** | `yemekhane-redis` | 6379 | `6379` | Menü Önbelleği & Oturum Deposu |
| **replica-setup** | `yemekhane-replica-setup` | - | - | Replikasyonu kurup çıkan tek seferlik servis |

---

## 🔑 Varsayılan Bağlantı ve Giriş Bilgileri

### Veritabanı Bilgileri
* **Primary (Yazma):** `localhost:3307` | Veritabanı: `yemekhane_db` | Kullanıcı: `yemekhane_user` | Şifre: `yemekhane_pass`
* **Replica (Okuma):** `localhost:3308` | Veritabanı: `yemekhane_db` | Kullanıcı: `root` / `rootpass`
* **Root Şifresi:** `rootpass`
* **Replikasyon Kullanıcısı:** `repl` / `replpass`

### Test Kullanıcıları (Varsayılan Şifre: `password123`)
* **Yönetici:** `admin@kampus.edu.tr`
* **Personel:** `personel1@kampus.edu.tr` ... `personel4@kampus.edu.tr`
* **Öğrenci:** `ogrenci1@kampus.edu.tr` ... `ogrenci25@kampus.edu.tr`

---

## 🧪 Aşama 1: Doğrulama Komutları

### 1. Servis Sağlık Kontrolü
```bash
docker compose ps
```
Beklenen: `mysql-primary`, `mysql-replica`, `redis`, `frontend` servisleri `healthy` durumunda; `replica-setup` ise `exited (0)` durumunda olmalıdır.

### 2. Replikasyon Sağlık Durumu
```bash
docker exec -it yemekhane-mysql-replica mysql -u root -prootpass -e "SHOW REPLICA STATUS\G"
```
Beklenen:
* `Replica_IO_Running: Yes`
* `Replica_SQL_Running: Yes`
* `Seconds_Behind_Source: 0`

### 3. Replikasyon Veri Akışı Testi (Bakiye Yükleme)
Kaynakta (Primary) bakiye yükleyip replikadan okuyun:
```bash
# Kaynakta bakiye yükle (Örnek: Kullanıcı 6'ya 100 TL yükle)
docker exec -it yemekhane-mysql-primary mysql -u root -prootpass yemekhane_db -e "CALL sp_bakiye_yukle(6, 100.00);"

# Replikada yansıdığını doğrula
docker exec -it yemekhane-mysql-replica mysql -u root -prootpass yemekhane_db -e "SELECT id, ad, bakiye FROM kullanicilar WHERE id = 6;"
```

### 4. Salt-Okunur (Read-Only) Güvenlik Doğrulaması
Replikaya doğrudan yazma denemesi yapılmalı ve hata alınmalıdır:
```bash
docker exec -it yemekhane-mysql-replica mysql -u root -prootpass yemekhane_db -e "UPDATE kullanicilar SET bakiye = 9999 WHERE id = 6;"
```
Beklenen Hata:
`ERROR 1290 (HY000): The MySQL server is running with the --super-read-only option so it cannot execute this statement`

### 5. Replika Kesinti ve Yeniden Senkronizasyon Testi
```bash
# Replikayı durdur
docker stop yemekhane-mysql-replica

# Primary üzerinde değişiklik yap
docker exec -it yemekhane-mysql-primary mysql -u root -prootpass yemekhane_db -e "CALL sp_bakiye_yukle(6, 50.00);"

# Replikayı yeniden başlat
docker start yemekhane-mysql-replica

# Replikadaki güncel bakiyeyi kontrol et (Replikasyon aradaki farkı yakalamalıdır)
docker exec -it yemekhane-mysql-replica mysql -u root -prootpass yemekhane_db -e "SELECT id, ad, bakiye FROM kullanicilar WHERE id = 6;"
```

---

## 🛠️ Sık Karşılaşılan Sorunlar ve Çözümleri

1. **`replica-setup` konteyneri hata veriyor / `Replica_IO_Running: Connecting` kalıyor:**
   - Birincil sunucunun hazır olması birkaç saniye sürebilir. `docker logs yemekhane-replica-setup` komutuyla logları kontrol edin. Gerekirse `docker compose restart replica-setup` çalıştırın.
2. **Bash betiğinde `\r: command not found` hatası:**
   - Windows ortamında satır sonları CRLF olabilir. Dosyanın LF formatında kaydedildiğinden emin olun.
3. **Port çakışması (3307, 3308, 6379, 8080):**
   - Host makinenizde yerel MySQL veya Redis servisleri çalışıyorsa portları meşgul edebilir. Görev yöneticisinden ilgili yerel servisleri durdurun ya da `docker-compose.yml` dosyasındaki host portlarını değiştirin.

