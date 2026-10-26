# Aşama 1: Altyapı ve Replikasyon Doğrulama Raporu

## 1. Giriş ve Altyapı Özeti
Bu aşamada çoklu servis mimarisine sahip sistem Docker Compose ile ayağa kaldırılmış; birincil veritabanı (Primary), ikincil veritabanı (Replica), Redis önbellek/oturum sunucusu ve Apache 2.4 ters proxy servisi başarıyla yapılandırılmıştır.

---

## 2. Doğrulama Adımları ve Çıktılar

### 2.1. Servislerin Sağlık Durumu (`docker compose ps`)
Tüm servisler `healthy` durumundadır ve `replica-setup` konteyneri replikasyonu kurduktan sonra `exit 0` koduyla başarıyla sonlanmıştır.

**Komut:**
```bash
docker compose ps -a
```

**Çıktı:**
```text
NAME                      IMAGE              COMMAND                  SERVICE         STATUS                    PORTS
yemekhane-frontend        httpd:2.4-alpine   "httpd-foreground"       frontend        Up (healthy)              0.0.0.0:8080->80/tcp
yemekhane-mysql-primary   mysql:8.0          "docker-entrypoint.s…"   mysql-primary   Up (healthy)              0.0.0.0:3307->3306/tcp
yemekhane-mysql-replica   mysql:8.0          "docker-entrypoint.s…"   mysql-replica   Up (healthy)              0.0.0.0:3308->3306/tcp
yemekhane-redis           redis:7-alpine     "docker-entrypoint.s…"   redis           Up (healthy)              0.0.0.0:6379->6379/tcp
yemekhane-replica-setup   mysql:8.0          "bash /replica-setup…"   replica-setup   Exited (0)                3306/tcp, 33060/tcp
```

---

### 2.2. Replikasyon Durumu (`SHOW REPLICA STATUS\G`)
Replikasyon GTID (Global Transaction Identifier) tabanlı olarak `Auto_Position: 1` ile çalışmaktadır.

**Komut:**
```bash
docker exec yemekhane-mysql-replica mysql -u root -prootpass -e "SHOW REPLICA STATUS\G"
```

**Kritik Değerler:**
* `Replica_IO_Running: Yes` (Kaynak sunucudan binary log akışı aktif)
* `Replica_SQL_Running: Yes` (Alınan transaction'lar replica üzerinde hatasız işleniyor)
* `Seconds_Behind_Source: 0` (Gecikme 0 saniye)
* `Auto_Position: 1` (GTID otomatik pozisyonlama aktif)

---

### 2.3. Kaynakta Yapılan Değişikliğin Replikaya Yansıması (Bakiye Yükleme)
Birincil sunucuda `sp_bakiye_yukle` stored procedure'ü çağrılarak bakiye yüklenmiş ve replika sunucusunda okunduğunda verinin senkronize olduğu doğrulanmıştır.

**Komut 1 (Primary üzerinde 100 TL yükleme):**
```bash
docker exec yemekhane-mysql-primary mysql -u root -prootpass yemekhane_db -e "CALL sp_bakiye_yukle(6, 100.00);"
```

**Komut 2 (Replica üzerinde okuma):**
```bash
docker exec yemekhane-mysql-replica mysql -u root -prootpass yemekhane_db -e "SELECT id, ad, soyad, bakiye FROM kullanicilar WHERE id = 6;"
```

**Çıktı:**
```text
id   ad      soyad   bakiye
6    Caner   Şahin   290.00
```

---

### 2.4. Replikaya Yazma Denemesi (Salt-Okunur Güvenlik Kontrolü)
Replika sunucusunun salt-okunur (`--super-read-only=ON`) olduğu ve doğrudan gelen yazma isteklerini engellediği doğrulanmıştır.

**Komut:**
```bash
docker exec yemekhane-mysql-replica mysql -u root -prootpass yemekhane_db -e "UPDATE kullanicilar SET bakiye = 9999 WHERE id = 6;"
```

**Hata Çıktısı:**
```text
ERROR 1290 (HY000) at line 1: The MySQL server is running with the --super-read-only option so it cannot execute this statement
```

---

### 2.5. Replika Kesintisi ve Yeniden Senkronizasyon (Failover & Catch-up Testi)
Replika konteyneri geçici olarak durdurulmuş, bu esnada birincil sunucuda yeni bir işlem yapılmış, ardından replika tekrar başlatıldığında aradaki farkı otomatik olarak yakaladığı gözlemlenmiştir.

1. **Replika durduruldu:**
   ```bash
   docker stop yemekhane-mysql-replica
   ```
2. **Primary üzerinde 50 TL ilave yüklendi (Kullanıcı 6 bakiyesi 340.00 TL oldu):**
   ```bash
   docker exec yemekhane-mysql-primary mysql -u root -prootpass yemekhane_db -e "CALL sp_bakiye_yukle(6, 50.00);"
   ```
3. **Replika yeniden başlatıldı:**
   ```bash
   docker start yemekhane-mysql-replica
   ```
4. **Replikada güncel bakiye okundu:**
   ```bash
   docker exec yemekhane-mysql-replica mysql -u root -prootpass yemekhane_db -e "SELECT id, ad, bakiye FROM kullanicilar WHERE id = 6;"
   ```
   **Çıktı:**
   ```text
   id   ad      bakiye
   6    Caner   340.00
   ```
   *Sonuç: GTID sayesinde replika sunucu bağlantı koptuğu andaki transaction GTID'sinden itibaren eksik logları talep etmiş ve veritabanını tam tutarlılıkla güncellemiştir.*

