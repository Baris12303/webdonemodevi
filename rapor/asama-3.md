# Aşama 3: Redis Önbellek ve Oturum Yönetimi Raporu

## 1. Giriş ve Kullanım Alanları
Sistemimizde Redis, performansı artırmak ve sunucuyu durumsuz (stateless) hale getirmek amacıyla iki temel görev için kullanılmıştır:
1. **Menü Önbelleği (Menu Caching):** Çoklu tablo birleşimleri (`JOIN`) ve View sorgularının getirdiği veritabanı yükünü azaltmak.
2. **Merkezi Oturum Deposu (Session Store):** Kullanıcı oturumlarını uygulama belleğinde değil, merkezi Redis'te tutarak sunucu kesintilerinde oturum kaybını önlemek.

---

## 2. Redis Yapılandırma Özeti

| Görev | Anahtar Şablonu (Key) | Geçerlilik Süresi (TTL) | Ne Zaman Silinir? (Invalidation) |
| :--- | :--- | :--- | :--- |
| **Menü Önbelleği** | `menu:{yemekhane_id}:{tarih}:{ogun_id}` | Günün sonuna kadar (`23:59:59`) | Yönetici o menüyü güncellediğinde |
| **Oturum Deposu** | `oturum:{token}` | 30 dakika (1800 sn) | Çıkış yapıldığında (`logout`) veya süre dolduğunda |

*Not: Oturum süresi `Sliding Expiration` mantığıyla çalışır. Kullanıcı her istek attığında 30 dakikalık sayaç baştan başlar.*

---

## 3. Doğrulama Testleri ve Çıktılar

### 3.1. Menü Önbellek Akışı (Cache Miss $\rightarrow$ Cache Set $\rightarrow$ Cache Hit)
Menü için ilk istek geldiğinde veritabanından okunmuş ve Redis'e yazılmıştır (`Cache Miss`). Aynı menüye gelen ikinci istek doğrudan Redis RAM'inden `0.2 ms` sürede getirilmiştir (`Cache Hit`).

**Uygulama Günlüğü (Container Log):**
```text
2026-10-27 18:40:27 [INFO] redis: [CACHE MISS] Menü Redis'te yok, DB'den okunacak: menu:1:2026-10-27:2
2026-10-27 18:40:27 [INFO] redis: [CACHE SET] Menü Redis'e yazıldı: menu:1:2026-10-27:2 (TTL: 19171 sn)
INFO: 172.18.0.3:48780 - "GET /api/menus/today?yemekhane_id=1&tarih=2026-10-27&ogun_id=2 HTTP/1.1" 200 OK
2026-10-27 18:40:36 [INFO] redis: [CACHE HIT] Menü Redis'ten getirildi: menu:1:2026-10-27:2
INFO: 172.18.0.3:52658 - "GET /api/menus/today?yemekhane_id=1&tarih=2026-10-27&ogun_id=2 HTTP/1.1" 200 OK
```

**JSON Yanıtlarındaki Kaynak Farkı:**
* 1. İstek Yanıtı: `"kaynak": "database"`
* 2. İstek Yanıtı: `"kaynak": "cache"`

**Redis-CLI TTL Kontrolü:**
```bash
docker exec yemekhane-redis redis-cli ttl "menu:1:2026-10-27:2"
# Çıktı: 19148 (Günün sonuna kadar kalan saniye)
```

---

### 3.2. Önbellek Geçersizleştirme (Cache Invalidation)
Yönetici menü fiyatını veya yemeklerini güncellediğinde, kullanıcıların eski menüyü görmesini engellemek için Redis'teki ilgili anahtar anında imha edilir.

**Komut (Yönetici Menü Güncelleme):**
```bash
PUT /api/admin/menus/44 {"ogrenci_fiyati": 50.0}
```

**Uygulama Günlüğü:**
```text
2026-10-27 18:41:18 [INFO] redis: [CACHE INVALIDATED] Menü önbellekten silindi: menu:1:2026-10-27:2
INFO: 172.18.0.3:52104 - "PUT /api/admin/menus/44 HTTP/1.1" 200 OK
```

**Redis-CLI Kontrolü:**
```bash
docker exec yemekhane-redis redis-cli exists "menu:1:2026-10-27:2"
# Çıktı: 0 (Anahtar başarıyla silindi)
```

---

### 3.3. Durumsuz (Stateless) Mimari: Konteyner Yeniden Başlatma Testi
Kullanıcı giriş yaptıktan sonra backend konteyneri durdurulup yeniden başlatılmış, oturum Redis'te tutulduğu için kullanıcının oturumunun düşmediği kanıtlanmıştır.

1. **Giriş yapıldı ve token alındı:** `f06f37822b904fc685c163cf9714b19e`
2. **Kullanıcı doğrulandı:**
   ```bash
   GET /api/auth/me (HTTP 200 OK - Kullanıcı: Barış Yılmaz)
   ```
3. **Uygulama konteyneri yeniden başlatıldı:**
   ```bash
   docker restart yemekhane-uygulama
   ```
4. **Yeniden başlatma sonrası aynı token ile istek atıldı:**
   ```bash
   GET /api/auth/me
   # Çıktı: {"id":1,"ad":"Barış","soyad":"Yılmaz","eposta":"admin@kampus.edu.tr","rol":"yonetici","bakiye":150.0}
   # HTTP 200 OK (Oturum kesintisiz devam ediyor)
   ```

5. **Çıkış (`logout`) yapıldığında Redis anahtarının silinmesi:**
   ```bash
   POST /api/auth/logout
   docker exec yemekhane-redis redis-cli exists "oturum:f06f37822b904fc685c163cf9714b19e"
   # Çıktı: 0 (Oturum anahtarı anında silindi)
   ```

