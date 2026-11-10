# Kampüs Yemekhane Otomasyonu

Mikroservis mimarisine sahip, Docker üzerinde koşan, MySQL Master-Slave GTID replikasyonu, Redis önbellek/oturum yönetimi ve FastAPI katmanlı mimarisiyle geliştirilmiş kampüs yemekhane otomasyon sistemi.

---

## 🚀 Hızlı Başlangıç

Tüm sistemi tek komutla (ek adım gerektirmeden, Aşama 4 `db/04_degisiklik.sql` migrasyonu otomatik uygulanacak şekilde) ayağa kaldırın:
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
| **frontend** | `yemekhane-frontend` | 80 | `8080` | Apache 2.4 (HTML5/CSS3/JS & `/api/` Ters Proxy) |
| **uygulama** | `yemekhane-uygulama` | 8000 | - | FastAPI Katmanlı REST API (Apache üzerinden erişilir) |
| **mysql-primary** | `yemekhane-mysql-primary` | 3306 | `3307` | Birincil Veritabanı (Yazma işlemleri & Şema) |
| **mysql-replica** | `yemekhane-mysql-replica` | 3306 | `3308` | İkincil Veritabanı (Salt okunur replika) |
| **redis** | `yemekhane-redis` | 6379 | `6379` | Menü Önbelleği & Oturum Deposu |
| **replica-setup** | `yemekhane-replica-setup` | - | - | Replikasyonu kurup çıkan tek seferlik servis |

---

## 🔑 Varsayılan Bağlantı ve Giriş Bilgileri

### Veritabanı Bilgileri
* **Primary (Yazma):** `localhost:3307` | Veritabanı: `yemekhane_db` | Uygulama Kullanıcısı: `root` / `rootpass` (ayrıca `yemekhane_user` / `yemekhane_pass` tanımlıdır)
* **Replica (Okuma):** `localhost:3308` | Veritabanı: `yemekhane_db` | Kullanıcı: `root` / `rootpass`
* **Root Şifresi:** `rootpass`
* **Replikasyon Kullanıcısı:** `repl` / `replpass`

### Test Kullanıcıları (Varsayılan Şifre: `password123`)
* **Yönetici:** `admin@kampus.edu.tr`
* **Personel:** `personel1@kampus.edu.tr` ... `personel4@kampus.edu.tr`
* **Öğrenci:** `ogrenci1@kampus.edu.tr` ... `ogrenci25@kampus.edu.tr`

---

## 🧪 Aşama 1–4 Doğrulama Komutları

### Aşama 1: Servis Sağlığı ve GTID Replikasyonu
1. **Servis Sağlık Kontrolü:**
   ```bash
   docker compose ps
   ```
   Beklenen: `frontend`, `uygulama`, `mysql-primary`, `mysql-replica`, `redis` servisleri `healthy` durumunda; `replica-setup` ise `exited (0)` durumunda olmalıdır.

2. **Replikasyon Sağlık Durumu:**
   ```bash
   docker exec -it yemekhane-mysql-replica mysql -u root -prootpass -e "SHOW REPLICA STATUS\G"
   ```
   Beklenen: `Replica_IO_Running: Yes`, `Replica_SQL_Running: Yes`, `Seconds_Behind_Source: 0`.

3. **Replikasyon Veri Akışı Testi (Bakiye Yükleme):**
   ```bash
   docker exec -it yemekhane-mysql-primary mysql -u root -prootpass yemekhane_db -e "CALL sp_bakiye_yukle(6, 100.00);"
   docker exec -it yemekhane-mysql-replica mysql -u root -prootpass yemekhane_db -e "SELECT id, ad, bakiye FROM kullanicilar WHERE id = 6;"
   ```

4. **Salt-Okunur (Read-Only) Güvenlik Doğrulaması:**
   ```bash
   docker exec -it yemekhane-mysql-replica mysql -u root -prootpass yemekhane_db -e "UPDATE kullanicilar SET bakiye = 9999 WHERE id = 6;"
   ```
   Beklenen Hata: `ERROR 1290 (HY000): The MySQL server is running with the --super-read-only option so it cannot execute this statement`

5. **Replika Kesinti ve Yeniden Senkronizasyon Testi:**
   ```bash
   docker stop yemekhane-mysql-replica
   docker exec -it yemekhane-mysql-primary mysql -u root -prootpass yemekhane_db -e "CALL sp_bakiye_yukle(6, 50.00);"
   docker start yemekhane-mysql-replica
   docker exec -it yemekhane-mysql-replica mysql -u root -prootpass yemekhane_db -e "SELECT id, ad, bakiye FROM kullanicilar WHERE id = 6;"
   ```

### Aşama 2: Web API ve Arayüz
* Tarayıcı üzerinden arayüz: `http://localhost:8080`
* API sağlık kontrolü (Apache ters proxy üzerinden): `curl -fsS http://localhost:8080/api/health`

### Aşama 3: Redis Menü Önbelleği ve Oturum Yönetimi
```bash
docker exec -it yemekhane-redis redis-cli KEYS "menu:*"
docker exec -it yemekhane-redis redis-cli KEYS "oturum:*"
docker compose logs uygulama
```
* İlk `GET /api/menus/today` isteği MySQL Replica'dan (`[CACHE MISS]` / `[CACHE SET]`), sonraki istekler Redis'ten (`[CACHE HIT]`) yanıtlanır.
* Menü güncellemesi, rezervasyon veya değerlendirme sonrası ilgili `menu:{yemekhane_id}:{tarih}:{ogun_id}` anahtarı temizlenir (`[CACHE INVALIDATED]`).
* `docker compose restart uygulama` sonrasında Redis'teki `oturum:{token}` anahtarı korunur; çıkış (`/api/auth/logout`) yapıldığında silinir.

### Aşama 4: Değişiklik Talebi (`db/04_degisiklik.sql`)
* `db/04_degisiklik.sql`, ilk `docker compose up -d` başlatımında `mysql-primary` üzerinde otomatik çalışır ve GTID replikasyonu ile `mysql-replica` sunucusuna aktarılır. Ayrıca idempotent olarak mevcut çalışan birincil veritabanında güvenle yeniden çalıştırılabilir.
* Replikada şema doğrulaması:
  ```bash
  docker exec -it yemekhane-mysql-replica mysql -u root -prootpass yemekhane_db -e "SHOW CREATE TABLE rezervasyonlar\G SHOW CREATE TABLE kullanici_alerjenleri\G"
  ```
* Yarım porsiyon (%60 ücret) yalnızca `Öğle` ve `Akşam` menülerinde geçerlidir; `Kahvaltı` için yarım porsiyon seçimi `SQLSTATE '45000'` hatası döndürür.

---

## 🛠️ Sık Karşılaşılan Sorunlar ve Çözümleri

1. **`replica-setup` konteyneri hata veriyor / `Replica_IO_Running: Connecting` kalıyor:**
   - Birincil sunucunun hazır olması birkaç saniye sürebilir. `docker logs yemekhane-replica-setup` komutuyla logları kontrol edin. Gerekirse `docker compose restart replica-setup` çalıştırın.
2. **Bash betiğinde `\r: command not found` hatası:**
   - Windows ortamında satır sonları CRLF olabilir. `db/replica-setup.sh` dosyasının LF formatında olduğundan emin olun.
3. **Port çakışması (3307, 3308, 6379, 8080):**
   - Host makinenizde yerel MySQL veya Redis servisleri çalışıyorsa portları meşgul edebilir. Görev yöneticisinden ilgili yerel servisleri durdurun ya da `docker-compose.yml` dosyasındaki host portlarını değiştirin.
