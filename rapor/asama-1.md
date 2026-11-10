# Aşama 1: Altyapı ve Replikasyon Doğrulaması

Bu aşamada başlangıç paketi Docker Compose ile ayağa kaldırılarak servislerin sağlık durumları, MySQL GTID replikasyonu, replikanın salt-okunur (`--super-read-only`) koruması ve replika durdurulup başlatıldığında aradaki değişiklikleri yakalaması test edilmiştir.

## 1. Servislerin Durumu (`docker compose ps`)

Komut:
```bash
docker compose ps -a
```

Çıktı:
```text
NAME                      IMAGE                  COMMAND                  SERVICE         STATUS                    PORTS
yemekhane-frontend        httpd:2.4-alpine       "httpd-foreground"       frontend        Up (healthy)              0.0.0.0:8080->80/tcp
yemekhane-mysql-primary   mysql:8.0              "docker-entrypoint.s…"   mysql-primary   Up (healthy)              0.0.0.0:3307->3306/tcp
yemekhane-mysql-replica   mysql:8.0              "docker-entrypoint.s…"   mysql-replica   Up (healthy)              0.0.0.0:3308->3306/tcp
yemekhane-redis           redis:7-alpine         "docker-entrypoint.s…"   redis           Up (healthy)              0.0.0.0:6379->6379/tcp
yemekhane-replica-setup   mysql:8.0              "bash /replica-setup…"   replica-setup   Exited (0)                3306/tcp, 33060/tcp
```

Tüm servisler `healthy` durumundadır ve `replica-setup` kurulumu tamamlayıp `0` koduyla çıkmıştır.

## 2. Replikasyon Durumu (`SHOW REPLICA STATUS\G`)

Komut:
```bash
docker exec yemekhane-mysql-replica mysql -u root -prootpass -e "SHOW REPLICA STATUS\G"
```

İlgili satırlar:
```text
             Replica_IO_Running: Yes
            Replica_SQL_Running: Yes
          Seconds_Behind_Source: 0
                  Auto_Position: 1
```

## 3. Primary Üzerinde Bakiye Yükleme ve Replikada Okuma

Primary üzerinde `sp_bakiye_yukle` çağrıldı:
```bash
docker exec yemekhane-mysql-primary mysql -u root -prootpass yemekhane_db -e "CALL sp_bakiye_yukle(6, 100.00);"
```

Replica üzerinde okuma yapıldı:
```bash
docker exec yemekhane-mysql-replica mysql -u root -prootpass yemekhane_db -e "SELECT id, ad, soyad, bakiye FROM kullanicilar WHERE id = 6;"
```

Çıktı:
```text
id	ad	soyad	bakiye
6	Caner	Şahin	290.00
```

## 4. Replikaya Yazma Denemesi (Read-Only Kontrolü)

Komut:
```bash
docker exec yemekhane-mysql-replica mysql -u root -prootpass yemekhane_db -e "UPDATE kullanicilar SET bakiye = 9999 WHERE id = 6;"
```

Hata çıktısı:
```text
ERROR 1290 (HY000) at line 1: The MySQL server is running with the --super-read-only option so it cannot execute this statement
```

## 5. Replika Durdurma ve Yeniden Başlatma Testi

1. Replika durduruldu:
   ```bash
   docker stop yemekhane-mysql-replica
   ```
2. Replika kapalıyken primary üzerinde 50 TL daha yüklendi:
   ```bash
   docker exec yemekhane-mysql-primary mysql -u root -prootpass yemekhane_db -e "CALL sp_bakiye_yukle(6, 50.00);"
   ```
3. Replika tekrar başlatıldı:
   ```bash
   docker start yemekhane-mysql-replica
   ```
4. Replikadan güncel bakiye okundu:
   ```bash
   docker exec yemekhane-mysql-replica mysql -u root -prootpass yemekhane_db -e "SELECT id, ad, bakiye FROM kullanicilar WHERE id = 6;"
   ```

Çıktı:
```text
id	ad	bakiye
6	Caner	340.00
```

GTID `Auto_Position=1` sayesinde replika tekrar açıldığında eksik kalan transaction'ı primary üzerinden otomatik çekip veriyi eşitledi.
