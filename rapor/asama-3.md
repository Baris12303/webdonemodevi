# Aşama 3: Redis Önbellek ve Oturum Yönetimi

## 1. Kullanım Alanları

Redis projede iki amaçla kullanılmıştır:
1. **Menü önbelleği:** Günün menüsü sorgularını veritabanına tekrar gitmeden döndürmek.
2. **Oturum deposu:** Kullanıcı oturumlarını uygulama belleği yerine Redis'te tutarak container yeniden başlasa bile oturumun korunmasını sağlamak.

| Görev | Anahtar | Süre (TTL) | Ne Zaman Silinir? |
| :--- | :--- | :--- | :--- |
| Menü önbelleği | `menu:{yemekhane_id}:{tarih}:{ogun_id}` | Günün sonuna kadar (`23:59:59`) | Yönetici menüyü güncellediğinde (ve rezervasyon/değerlendirmede) |
| Oturum | `oturum:{token}` | 30 dakika (her istekte yenilenir) | Çıkış yapıldığında (`/api/auth/logout`) |

## 2. Doğrulama Çıktıları

### 2.1. İlk İstek (DB) ve İkinci İstek (Redis)

Uygulama logları (`docker compose logs uygulama`):
```text
2026-10-27 18:40:27 [INFO] redis: [CACHE MISS] Menü Redis'te yok, DB'den okunacak: menu:1:2026-10-27:2
2026-10-27 18:40:27 [INFO] redis: [CACHE SET] Menü Redis'e yazıldı: menu:1:2026-10-27:2 (TTL: 19171 sn)
INFO: 172.18.0.3:48780 - "GET /api/menus/today?yemekhane_id=1&tarih=2026-10-27&ogun_id=2 HTTP/1.1" 200 OK
2026-10-27 18:40:36 [INFO] redis: [CACHE HIT] Menü Redis'ten getirildi: menu:1:2026-10-27:2
INFO: 172.18.0.3:52658 - "GET /api/menus/today?yemekhane_id=1&tarih=2026-10-27&ogun_id=2 HTTP/1.1" 200 OK
```

`redis-cli` ile TTL kontrolü:
```bash
docker exec yemekhane-redis redis-cli ttl "menu:1:2026-10-27:2"
# Çıktı: 19148
```

### 2.2. Menü Güncellenince Önbelleğin Silinmesi

Yönetici menü fiyatını güncellediğinde (`PUT /api/admin/menus/44`):
```text
2026-10-27 18:41:18 [INFO] redis: [CACHE INVALIDATED] Menü önbellekten silindi: menu:1:2026-10-27:2
INFO: 172.18.0.3:52104 - "PUT /api/admin/menus/44 HTTP/1.1" 200 OK
```

`redis-cli` kontrolü:
```bash
docker exec yemekhane-redis redis-cli exists "menu:1:2026-10-27:2"
# Çıktı: 0
```

### 2.3. Uygulama Container'ı Yeniden Başladığında Oturumun Korunması

1. Giriş yapılıp token alındı: `f06f37822b904fc685c163cf9714b19e`
2. Uygulama container'ı yeniden başlatıldı:
   ```bash
   docker restart yemekhane-uygulama
   ```
3. Aynı token ile `GET /api/auth/me` isteği atıldı ve `200 OK` döndü:
   ```json
   {"id":1,"ad":"Barış","soyad":"Yılmaz","eposta":"admin@kampus.edu.tr","rol":"yonetici","ogrenci_no":null,"bakiye":150.0}
   ```
4. Çıkış (`POST /api/auth/logout`) sonrası `redis-cli` kontrolü:
   ```bash
   docker exec yemekhane-redis redis-cli exists "oturum:f06f37822b904fc685c163cf9714b19e"
   # Çıktı: 0
   ```
