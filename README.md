# Kampüs Yemekhane Otomasyonu

Docker Compose üzerinde çalışan, MySQL Primary-Replica (GTID) replikasyonu, Redis önbellek/oturum yönetimi ve FastAPI REST API + HTML5/CSS3/Vanilla JS arayüzünden oluşan kampüs yemekhane otomasyonu dönem ödevi projesi.

## Kurulum ve Çalıştırma

Tüm servisleri tek komutla ayağa kaldırmak için (ilk kurulumda `01_sema.sql`, `02_ornek_veri.sql` ve `04_degisiklik.sql` otomatik çalışır):

```bash
docker compose up -d
```

Servis durumlarını kontrol etmek için:

```bash
docker compose ps
```

Durdurmak için:

```bash
docker compose down
```

Veritabanı ve Redis volume'larını silip sıfırdan başlatmak için:

```bash
docker compose down -v
docker compose up -d
```

## Servisler ve Portlar

| Servis | Container Adı | İç Port | Host Portu | Açıklama |
| :--- | :--- | :--- | :--- | :--- |
| `frontend` | `yemekhane-frontend` | 80 | `8080` | Apache 2.4 (statik arayüz dosyaları ve `/api/` proxy) |
| `uygulama` | `yemekhane-uygulama` | 8000 | - | FastAPI REST API |
| `mysql-primary` | `yemekhane-mysql-primary` | 3306 | `3307` | Birincil MySQL sunucusu (yazma işlemleri) |
| `mysql-replica` | `yemekhane-mysql-replica` | 3306 | `3308` | İkincil MySQL sunucusu (salt okunur replika) |
| `redis` | `yemekhane-redis` | 6379 | `6379` | Menü önbelleği ve oturum deposu |
| `replica-setup` | `yemekhane-replica-setup` | - | - | Replikasyonu kuran tek seferlik kurulum container'ı |

## Bağlantı ve Test Hesapları

### Veritabanı
- **Primary:** `localhost:3307` (`yemekhane_db`, kullanıcı: `root` / `rootpass`, ayrıca `yemekhane_user` / `yemekhane_pass`)
- **Replica:** `localhost:3308` (`yemekhane_db`, kullanıcı: `root` / `rootpass`)
- **Replikasyon kullanıcısı:** `repl` / `replpass`

### Örnek Kullanıcılar (Şifre: `password123`)
- **Yönetici:** `admin@kampus.edu.tr`
- **Personel:** `personel1@kampus.edu.tr` .. `personel4@kampus.edu.tr`
- **Öğrenci:** `ogrenci1@kampus.edu.tr` .. `ogrenci25@kampus.edu.tr`

## Doğrulama Komutları

### Aşama 1: Altyapı ve GTID Replikasyon

```bash
docker compose ps
docker exec yemekhane-mysql-replica mysql -u root -prootpass -e "SHOW REPLICA STATUS\G"
```

Primary üzerinde bakiye yükleyip replikada görme:

```bash
docker exec yemekhane-mysql-primary mysql -u root -prootpass yemekhane_db -e "CALL sp_bakiye_yukle(6, 100.00);"
docker exec yemekhane-mysql-replica mysql -u root -prootpass yemekhane_db -e "SELECT id, ad, bakiye FROM kullanicilar WHERE id = 6;"
```

Replikaya yazma denemesi (`--super-read-only` hatası beklenir):

```bash
docker exec yemekhane-mysql-replica mysql -u root -prootpass yemekhane_db -e "UPDATE kullanicilar SET bakiye = 9999 WHERE id = 6;"
```

Replika durdurup tekrar başlatma (GTID yakalama testi):

```bash
docker stop yemekhane-mysql-replica
docker exec yemekhane-mysql-primary mysql -u root -prootpass yemekhane_db -e "CALL sp_bakiye_yukle(6, 50.00);"
docker start yemekhane-mysql-replica
docker exec yemekhane-mysql-replica mysql -u root -prootpass yemekhane_db -e "SELECT id, ad, bakiye FROM kullanicilar WHERE id = 6;"
```

### Aşama 2: Web API ve Arayüz

- Arayüz: `http://localhost:8080`
- Sağlık kontrolü: `curl -fsS http://localhost:8080/api/health`

### Aşama 3: Redis Önbellek ve Oturum

```bash
docker exec yemekhane-redis redis-cli KEYS "menu:*"
docker exec yemekhane-redis redis-cli KEYS "oturum:*"
docker compose logs uygulama
```

- İlk `GET /api/menus/today` isteği MySQL Replica'dan (`[CACHE MISS]` / `[CACHE SET]`), sonraki istekler Redis'ten (`[CACHE HIT]`) gelir.
- Menü güncellendiğinde, rezervasyon yapıldığında/iptal edildiğinde veya değerlendirme eklendiğinde ilgili `menu:{yemekhane_id}:{tarih}:{ogun_id}` anahtarı silinir.
- `docker compose restart uygulama` sonrasında Redis'teki `oturum:{token}` anahtarı korunduğu için kullanıcı oturumu düşmez; `/api/auth/logout` çağrıldığında anahtar silinir.

### Aşama 4: Değişiklik Talebi (`db/04_degisiklik.sql`)

- İlk kurulumda `docker-entrypoint-initdb.d` üzerinden primary sunucuda çalışır ve GTID ile replikaya aktarılır (idempotent yazıldığı için mevcut primary üzerinde tekrar çalıştırılabilir).
- Replikada şema kontrolü:

```bash
docker exec yemekhane-mysql-replica mysql -u root -prootpass yemekhane_db -e "SHOW CREATE TABLE rezervasyonlar\G SHOW CREATE TABLE kullanici_alerjenleri\G"
```

- Yarım porsiyon (%60 ücret) yalnızca `Öğle` ve `Akşam` menülerinde seçilebilir; `Kahvaltı` için yarım porsiyon denendiğinde `sp_rezervasyon_yap` tarafından `SQLSTATE '45000'` hatası döner.

## Sık Karşılaşılan Sorunlar

1. **`replica-setup` hata veriyor veya `Replica_IO_Running: Connecting` durumunda kalıyor:**
   Primary container'ın açılması biraz zaman alabilir. `docker logs yemekhane-replica-setup` ile loga bakıp gerekirse `docker compose restart replica-setup` çalıştırın.
2. **`replica-setup.sh` içinde `\r: command not found` hatası:**
   Windows üzerinde satır sonları CRLF olmuş olabilir. `db/replica-setup.sh` dosyasının LF olduğundan emin olun.
3. **Port çakışması (`3307`, `3308`, `6379`, `8080`):**
   Bilgisayarda yerel MySQL, Redis veya Apache çalışıyorsa bu portlar dolu olabilir; yerel servisleri durdurun veya `docker-compose.yml` port eşlemelerini güncelleyin.
