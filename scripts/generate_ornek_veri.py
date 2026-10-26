import random
from datetime import datetime, date, timedelta

# Sabit tohum (deterministic data)
random.seed(42)

# Bcrypt hash for 'password123'
PASSWORD_HASH = "$2b$12$uqCGNPjR2FRH.wLf29QTG.P8vyJJ/x.D91sbGiQ1Af.D6cx0jXk5O"

sql_lines = []
sql_lines.append("-- =====================================================")
sql_lines.append("-- Yemekhane Otomasyonu - Başlangıç Verileri")
sql_lines.append("-- 02_ornek_veri.sql")
sql_lines.append("-- 30 Kullanıcı, 52 Yemek, 84 Menü, ~365 Rezervasyon")
sql_lines.append("-- Tarihler kurulum anına göre dinamik üretilir")
sql_lines.append("-- =====================================================\n")
sql_lines.append("SET NAMES utf8mb4;\nSET CHARACTER SET utf8mb4;\nUSE yemekhane_db;\n")

# 1. Yemekhaneler (2 adet)
sql_lines.append("-- -----------------------------------------------------")
sql_lines.append("-- Yemekhaneler (2 Adet: Merkez 400, Mühendislik 60)")
sql_lines.append("-- -----------------------------------------------------")
sql_lines.append("INSERT INTO yemekhaneler (id, ad, kapasite, konum) VALUES")
sql_lines.append("  (1, 'Merkez Yemekhanesi', 400, 'Ana Kampüs Meydanı'),")
sql_lines.append("  (2, 'Mühendislik Yemekhanesi', 60, 'Mühendislik Fakültesi Zemin Kat');\n")

# 2. Öğünler (3 adet)
sql_lines.append("-- -----------------------------------------------------")
sql_lines.append("-- Öğünler (Kahvaltı 07:00, Öğle 10:00, Akşam 15:00)")
sql_lines.append("-- -----------------------------------------------------")
sql_lines.append("INSERT INTO ogunler (id, ad, son_saat) VALUES")
sql_lines.append("  (1, 'Kahvaltı', '07:00:00'),")
sql_lines.append("  (2, 'Öğle', '10:00:00'),")
sql_lines.append("  (3, 'Akşam', '15:00:00');\n")

# 3. Yemek Kategorileri (7 adet)
sql_lines.append("-- -----------------------------------------------------")
sql_lines.append("-- Yemek Kategorileri (7 Kategori)")
sql_lines.append("-- -----------------------------------------------------")
sql_lines.append("INSERT INTO yemek_kategorileri (id, ad, sira) VALUES")
sql_lines.append("  (1, 'Çorbalar', 1),")
sql_lines.append("  (2, 'Ana Yemekler', 2),")
sql_lines.append("  (3, 'Vejetaryen / Diyet', 3),")
sql_lines.append("  (4, 'Garnitür / Pilav / Makarna', 4),")
sql_lines.append("  (5, 'Salatalar', 5),")
sql_lines.append("  (6, 'Tatlılar & Meyveler', 6),")
sql_lines.append("  (7, 'İçecekler', 7);\n")

# 4. Yemekler (52 adet)
yemekler_data = [
    # 1. Çorbalar (8)
    (1, "Mercimek Çorbası", 180, True),
    (1, "Ezogelin Çorbası", 190, True),
    (1, "Tarhana Çorbası", 170, True),
    (1, "Yayla Çorbası", 160, True),
    (1, "Domates Çorbası", 150, True),
    (1, "Tavuk Suyu Çorba", 210, False),
    (1, "Mantar Çorbası", 175, True),
    (1, "Düğün Çorbası", 230, False),
    # 2. Ana Yemekler (12)
    (2, "Karnıyarık", 340, False),
    (2, "İzmir Köfte", 380, False),
    (2, "Kuru Fasulye (Etli)", 350, False),
    (2, "Tas Kebabı", 420, False),
    (2, "Fırın Tavuk But", 390, False),
    (2, "Orman Kebabı", 400, False),
    (2, "Etli Güveç", 410, False),
    (2, "Kadınbudu Köfte", 430, False),
    (2, "Hünkar Beğendi", 460, False),
    (2, "Tavuk Şinitzel", 380, False),
    (2, "Kıymalı Musakka", 360, False),
    (2, "Hasanpaşa Köfte", 420, False),
    # 3. Vejetaryen / Diyet (8)
    (3, "Zeytinyağlı Taze Fasulye", 190, True),
    (3, "Ispanak Yemeği", 180, True),
    (3, "Sebzeli Türlü", 210, True),
    (3, "Fırında Mücver", 220, True),
    (3, "Etsiz Nohut Yemeği", 280, True),
    (3, "Zeytinyağlı Biber Dolması", 230, True),
    (3, "Zeytinyağlı Enginar", 195, True),
    (3, "Mercimek Köftesi", 250, True),
    # 4. Garnitür / Pilav / Makarna (8)
    (4, "Pirinç Pilavı", 260, True),
    (4, "Bulgur Pilavı", 220, True),
    (4, "Fırın Makarna", 310, True),
    (4, "Patates Püresi", 200, True),
    (4, "Şehriyeli Pirinç Pilavı", 270, True),
    (4, "Sebzeli Kuskus", 240, True),
    (4, "Fırın Elma Dilim Patates", 210, True),
    (4, "Domates Soslu Spagetti", 290, True),
    # 5. Salatalar (6)
    (5, "Mevsim Salatası", 75, True),
    (5, "Çoban Salata", 90, True),
    (5, "Havuç Tarator", 140, True),
    (5, "Haydari", 130, True),
    (5, "Piyaz", 180, True),
    (5, "Köz Patlıcan Salatası", 85, True),
    # 6. Tatlılar & Meyveler (6)
    (6, "Fırın Sütlaç", 250, True),
    (6, "Revani", 320, True),
    (6, "Kemalpaşa Tatlısı", 280, True),
    (6, "Cevizli Baklava", 410, True),
    (6, "Mevsim Meyvesi Tabağı", 110, True),
    (6, "Kazandibi", 240, True),
    # 7. İçecekler (4)
    (7, "Ayran", 75, True),
    (7, "Limonata", 95, True),
    (7, "Vişne Suyu", 110, True),
    (7, "Su", 0, True)
]

sql_lines.append("-- -----------------------------------------------------")
sql_lines.append("-- Yemekler (52 Yemek)")
sql_lines.append("-- -----------------------------------------------------")
sql_lines.append("INSERT INTO yemekler (id, kategori_id, ad, kalori, vejetaryen_mi) VALUES")
y_strs = []
for idx, (kat_id, ad, kalori, veg) in enumerate(yemekler_data, 1):
    veg_str = "TRUE" if veg else "FALSE"
    y_strs.append(f"  ({idx}, {kat_id}, '{ad}', {kalori}, {veg_str})")
sql_lines.append(",\n".join(y_strs) + ";\n")

# 5. Alerjenler (14 adet)
alerjenler = [
    "Gluten", "Laktoz", "Yumurta", "Balık", "Kabuklular",
    "Yer Fıstığı", "Soya", "Sert Kabuklu Meyveler", "Kereviz",
    "Hardal", "Susam", "Kükürt Dioksit", "Acı Bakla", "Yumuşakçalar"
]
sql_lines.append("-- -----------------------------------------------------")
sql_lines.append("-- Alerjenler (14 Alerjen)")
sql_lines.append("-- -----------------------------------------------------")
sql_lines.append("INSERT INTO alerjenler (id, ad) VALUES")
a_strs = [f"  ({idx}, '{ad}')" for idx, ad in enumerate(alerjenler, 1)]
sql_lines.append(",\n".join(a_strs) + ";\n")

# 6. Yemek Alerjenleri (çoka çok ilişki)
yemek_alerjen_map = [
    # Çorbalar
    (1, [1]),        # Mercimek (Gluten)
    (2, [1]),        # Ezogelin (Gluten)
    (3, [1, 2]),     # Tarhana (Gluten, Laktoz)
    (4, [1, 2]),     # Yayla (Gluten, Laktoz)
    (5, [1, 2]),     # Domates (Gluten, Laktoz)
    (6, [1]),        # Tavuk suyu (Gluten)
    (7, [1, 2]),     # Mantar (Gluten, Laktoz)
    (8, [1, 2, 3]),  # Düğün (Gluten, Laktoz, Yumurta)
    # Ana Yemekler
    (10, [1, 3]),    # İzmir Köfte (Gluten, Yumurta)
    (16, [1, 3]),    # Kadınbudu Köfte (Gluten, Yumurta)
    (17, [1, 2]),    # Hünkar Beğendi (Gluten, Laktoz)
    (18, [1, 3]),    # Şinitzel (Gluten, Yumurta)
    (20, [1, 2, 3]), # Hasanpaşa Köfte (Gluten, Laktoz, Yumurta)
    # Vejetaryen
    (24, [1, 3]),    # Mücver (Gluten, Yumurta)
    (28, [1]),       # Mercimek köftesi (Gluten)
    # Garnitür
    (30, [1]),       # Bulgur pilavı (Gluten)
    (31, [1, 2, 3]), # Fırın makarna (Gluten, Laktoz, Yumurta)
    (32, [2]),       # Patates püresi (Laktoz)
    (33, [1]),       # Şehriyeli pirinç (Gluten)
    (34, [1]),       # Kuskus (Gluten)
    (36, [1]),       # Spagetti (Gluten)
    # Salatalar
    (39, [2, 8]),    # Havuç tarator (Laktoz, Ceviz)
    (40, [2]),       # Haydari (Laktoz)
    (41, [3]),       # Piyaz (Yumurta)
    # Tatlılar
    (43, [2]),       # Fırın sütlaç (Laktoz)
    (44, [1, 2, 3]), # Revani (Gluten, Laktoz, Yumurta)
    (45, [1, 2, 3]), # Kemalpaşa (Gluten, Laktoz, Yumurta)
    (46, [1, 2, 8]), # Baklava (Gluten, Laktoz, Ceviz)
    (48, [2]),       # Kazandibi (Laktoz)
    # İçecekler
    (49, [2])        # Ayran (Laktoz)
]

sql_lines.append("-- -----------------------------------------------------")
sql_lines.append("-- Yemek Alerjenleri")
sql_lines.append("-- -----------------------------------------------------")
sql_lines.append("INSERT INTO yemek_alerjenleri (yemek_id, alerjen_id) VALUES")
ya_strs = []
for y_id, a_ids in yemek_alerjen_map:
    for a_id in a_ids:
        ya_strs.append(f"  ({y_id}, {a_id})")
sql_lines.append(",\n".join(ya_strs) + ";\n")

# 7. Kullanıcılar (30 Kullanıcı: 1 Yönetici, 4 Personel, 25 Öğrenci)
kullanicilar = [
    # Yönetici (1)
    (1, None, "Barış", "Yılmaz", "admin@kampus.edu.tr", "yonetici"),
    # Personel (4)
    (2, None, "Ahmet", "Kaya", "personel1@kampus.edu.tr", "personel"),
    (3, None, "Ayşe", "Demir", "personel2@kampus.edu.tr", "personel"),
    (4, None, "Mehmet", "Öztürk", "personel3@kampus.edu.tr", "personel"),
    (5, None, "Fatma", "Çelik", "personel4@kampus.edu.tr", "personel"),
]

ogrenci_isimleri = [
    ("Caner", "Şahin"), ("Elif", "Yıldız"), ("Burak", "Koç"), ("Zeynep", "Aydın"),
    ("Emre", "Arslan"), ("Selin", "Doğan"), ("Berk", "Kılıç"), ("Gamze", "Aslan"),
    ("Onur", "Çetin"), ("Tuğba", "Kara"), ("Mert", "Polat"), ("Derya", "Kurt"),
    ("Tolga", "Yavuz"), ("Ezgi", "Şimşek"), ("Kaan", "Özdemir"), ("Melis", "Erdoğan"),
    ("Arda", "Tekin"), ("Ceren", "Aksoy"), ("Kerem", "Güneş"), ("İrem", "Yalçın"),
    ("Yasin", "Bozkurt"), ("Ece", "Korkmaz"), ("Sinan", "Avcı"), ("Büşra", "Taş"),
    ("Deniz", "Bulut")
]

for idx, (ad, soyad) in enumerate(ogrenci_isimleri, 6):
    ogrenci_no = f"2512290{idx:02d}"
    eposta = f"ogrenci{idx-5}@kampus.edu.tr"
    kullanicilar.append((idx, ogrenci_no, ad, soyad, eposta, "ogrenci"))

# 8. Menüler (84 Menü: 14 Gün x 2 Yemekhane x 3 Öğün)
# Tarihler: CURDATE() - INTERVAL 7 DAY to CURDATE() + INTERVAL 6 DAY
# 14 gün offset: -7, -6, ..., +6
menuler = []
menu_id = 1
for day_offset in range(-7, 7):
    for yemekhane_id in [1, 2]:
        for ogun_id in [1, 2, 3]:
            if ogun_id == 1:
                ogr_fiyat = 30.00
                prs_fiyat = 60.00
            else:
                ogr_fiyat = 45.00
                prs_fiyat = 90.00
            menuler.append((menu_id, yemekhane_id, day_offset, ogun_id, ogr_fiyat, prs_fiyat))
            menu_id += 1

sql_lines.append("-- -----------------------------------------------------")
sql_lines.append("-- Menüler (84 Menü: 14 gün x 2 yemekhane x 3 öğün)")
sql_lines.append("-- Tarihler CURDATE() bazlıdır")
sql_lines.append("-- -----------------------------------------------------")
sql_lines.append("INSERT INTO menuler (id, yemekhane_id, tarih, ogun_id, ogrenci_fiyati, personel_fiyati) VALUES")
m_strs = []
for m in menuler:
    mid, yhid, doff, oid, ofiy, pfiy = m
    sign = "+" if doff >= 0 else "-"
    abs_doff = abs(doff)
    date_expr = f"DATE_ADD(CURDATE(), INTERVAL {doff} DAY)"
    m_strs.append(f"  ({mid}, {yhid}, {date_expr}, {oid}, {ofiy:.2f}, {pfiy:.2f})")
sql_lines.append(",\n".join(m_strs) + ";\n")

# 9. Menu Yemekleri (Her menüye 4 yemek)
sql_lines.append("-- -----------------------------------------------------")
sql_lines.append("-- Menü Yemekleri (Her Menüye 4 Çeşit)")
sql_lines.append("-- -----------------------------------------------------")
sql_lines.append("INSERT INTO menu_yemekleri (menu_id, yemek_id) VALUES")
my_strs = []
for m in menuler:
    mid = m[0]
    corba_id = ((mid * 3) % 8) + 1
    ana_id = ((mid * 5) % 12) + 9
    garnitur_id = ((mid * 7) % 8) + 29
    tatli_id = ((mid * 2) % 6) + 43
    my_strs.append(f"  ({mid}, {corba_id}), ({mid}, {ana_id}), ({mid}, {garnitur_id}), ({mid}, {tatli_id})")
sql_lines.append(",\n".join(my_strs) + ";\n")

# 10. Rezervasyonlar (~365 adet) ve Bakiye Hareketleri
# Her kullanıcının başlangıç yüklemesi, rezervasyon harcamaları ve iptalleri tam dengeli olmalı!
# kullanicilar.bakiye == SUM(bakiye_hareketleri.miktar)
user_balances = {u[0]: 0.0 for u in kullanicilar}
user_loadings = {u[0]: 0.0 for u in kullanicilar}

rezervasyonlar = []
bakiye_hareketleri = []
rez_id = 1
hareket_id = 1

# Önce her kullanıcıya bir başlangıç bakiyesi yükleyelim (250 - 600 TL arası)
for u in kullanicilar:
    uid = u[0]
    load_amount = float(random.choice([350, 400, 450, 500, 600]))
    user_balances[uid] += load_amount
    user_loadings[uid] += load_amount
    bakiye_hareketleri.append((
        hareket_id, uid, load_amount, 'yukleme',
        f"{load_amount:.2f} TL bakiye yüklendi.", "NULL",
        "DATE_SUB(NOW(), INTERVAL 10 DAY)"
    ))
    hareket_id += 1

# Rezervasyonları üret: 365 adet
# Menüler: mid 1..84
# Geçmiş menüler: day_offset < 0 (mid 1..42) -> 'kullanildi' (%85), 'iptal' (%15)
# Bugün menüler: day_offset == 0 (mid 43..48) -> 'kullanildi' (%40), 'aktif' (%60)
# Gelecek menüler: day_offset > 0 (mid 49..84) -> 'aktif' (%90), 'iptal' (%10)

menu_dict = {m[0]: m for m in menuler}
target_rez_count = 365
created_rez_set = set() # (uid, mid) pair must be unique!

user_ids = [u[0] for u in kullanicilar]

# Belirli bir düzende 365 rezervasyon oluşturalım
while len(rezervasyonlar) < target_rez_count:
    uid = random.choice(user_ids)
    mid = random.randint(1, 84)
    
    if (uid, mid) in created_rez_set:
        continue
    
    m = menu_dict[mid]
    day_offset = m[2]
    user_role = next(u[5] for u in kullanicilar if u[0] == uid)
    price = m[4] if user_role == 'ogrenci' else m[5]
    
    # Durum belirleme
    if day_offset < 0:
        durum = 'kullanildi' if random.random() < 0.85 else 'iptal'
    elif day_offset == 0:
        durum = 'kullanildi' if random.random() < 0.40 else 'aktif'
    else:
        durum = 'aktif' if random.random() < 0.90 else 'iptal'
    
    # Tarih ifadeleri
    create_time_expr = f"DATE_ADD(CURDATE(), INTERVAL {day_offset - 1} DAY)"
    iptal_time_expr = f"DATE_ADD(CURDATE(), INTERVAL {day_offset} DAY)" if durum == 'iptal' else "NULL"
    kullanilma_time_expr = f"DATE_ADD(CURDATE(), INTERVAL {day_offset} DAY)" if durum == 'kullanildi' else "NULL"
    
    rezervasyonlar.append((
        rez_id, uid, mid, price, durum,
        create_time_expr, iptal_time_expr, kullanilma_time_expr
    ))
    created_rez_set.add((uid, mid))
    
    # Rezervasyon bakiye hareketi
    user_balances[uid] -= price
    bakiye_hareketleri.append((
        hareket_id, uid, -price, 'rezervasyon',
        f"Rezervasyon ücreti: Menü #{mid}", str(rez_id),
        create_time_expr
    ))
    hareket_id += 1
    
    # İptal ise iade hareketi
    if durum == 'iptal':
        user_balances[uid] += price
        bakiye_hareketleri.append((
            hareket_id, uid, price, 'iade',
            f"Rezervasyon iptal iadesi: #{rez_id}", str(rez_id),
            iptal_time_expr
        ))
        hareket_id += 1
        
    rez_id += 1

# Kullanıcıların bakiyesi negatif olamaz (chk_kullanici_bakiye)!
# Eğer negatif olan varsa ilave yükleme yapalım
for uid, bal in user_balances.items():
    if bal < 50.0:
        ek_yukleme = 150.0 - bal
        user_balances[uid] += ek_yukleme
        bakiye_hareketleri.append((
            hareket_id, uid, ek_yukleme, 'yukleme',
            f"{ek_yukleme:.2f} TL bakiye yüklendi.", "NULL",
            "DATE_SUB(NOW(), INTERVAL 5 DAY)"
        ))
        hareket_id += 1

# Şimdi Kullanıcılar tablosunu yazalım
sql_lines.append("-- -----------------------------------------------------")
sql_lines.append("-- Kullanıcılar (30 Kullanıcı: 1 Yönetici, 4 Personel, 25 Öğrenci)")
sql_lines.append("-- -----------------------------------------------------")
sql_lines.append("INSERT INTO kullanicilar (id, ogrenci_no, ad, soyad, eposta, sifre_hash, rol, bakiye) VALUES")
k_strs = []
for u in kullanicilar:
    uid, og_no, ad, soyad, eposta, rol = u
    og_no_str = f"'{og_no}'" if og_no else "NULL"
    bakiye = user_balances[uid]
    k_strs.append(f"  ({uid}, {og_no_str}, '{ad}', '{soyad}', '{eposta}', '{PASSWORD_HASH}', '{rol}', {bakiye:.2f})")
sql_lines.append(",\n".join(k_strs) + ";\n")

# Rezervasyonlar tablosunu yazalım
sql_lines.append("-- -----------------------------------------------------")
sql_lines.append(f"-- Rezervasyonlar ({len(rezervasyonlar)} Adet)")
sql_lines.append("-- -----------------------------------------------------")
sql_lines.append("INSERT INTO rezervasyonlar (id, kullanici_id, menu_id, ucret, durum, olusturulma_tarihi, iptal_tarihi, kullanilma_tarihi) VALUES")
r_strs = []
for r in rezervasyonlar:
    rid, ruid, rmid, rucret, rdurum, rcreate, riptal, rkullan = r
    r_strs.append(f"  ({rid}, {ruid}, {rmid}, {rucret:.2f}, '{rdurum}', {rcreate}, {riptal}, {rkullan})")
sql_lines.append(",\n".join(r_strs) + ";\n")

# Bakiye Hareketleri tablosunu yazalım
sql_lines.append("-- -----------------------------------------------------")
sql_lines.append(f"-- Bakiye Hareketleri ({len(bakiye_hareketleri)} Adet)")
sql_lines.append("-- Bakiye her zaman hareketlerin toplamına eşittir!")
sql_lines.append("-- -----------------------------------------------------")
sql_lines.append("INSERT INTO bakiye_hareketleri (id, kullanici_id, miktar, hareket_tipi, aciklama, rezervasyon_id, tarih) VALUES")
bh_strs = []
for bh in bakiye_hareketleri:
    bhid, bhuid, bhmiktar, bhtip, bhacik, bhrez, bhtarih = bh
    bh_strs.append(f"  ({bhid}, {bhuid}, {bhmiktar:.2f}, '{bhtip}', '{bhacik}', {bhrez}, {bhtarih})")
sql_lines.append(",\n".join(bh_strs) + ";\n")

# 11. Değerlendirmeler (Kullanılmış rezervasyonlardan üretilir)
sql_lines.append("-- -----------------------------------------------------")
sql_lines.append("-- Değerlendirmeler (Kullanılmış menülere ait değerlendirmeler)")
sql_lines.append("-- -----------------------------------------------------")
yorumlar = [
    (5, "Yemekler çok lezzetliydi, çorba sıcaktı."),
    (4, "Genel olarak gayet iyiydi, tatlı biraz fazla şekerliydi."),
    (5, "Porsiyonlar doyurucu, ellerinize sağlık."),
    (3, "Ana yemek güzeldi ama garnitür soğuktu."),
    (4, "Öğrenci menüsüne göre gayet başarılı."),
    (5, "Mükemmel menü, mercimek çorbası harikaydı."),
    (2, "Tavuk biraz kuruydu, geliştirilebilir."),
    (4, "Fiyat/performans olarak kampüsün en iyisi.")
]

degerlendirmeler = []
deg_id = 1
deg_set = set() # (uid, mid) unique!

for r in rezervasyonlar:
    if r[4] == 'kullanildi':
        uid = r[1]
        mid = r[2]
        if (uid, mid) not in deg_set and random.random() < 0.40:
            deg_set.add((uid, mid))
            puan, yorum = random.choice(yorumlar)
            degerlendirmeler.append((deg_id, uid, mid, puan, yorum, r[7]))
            deg_id += 1

sql_lines.append("INSERT INTO degerlendirmeler (id, kullanici_id, menu_id, puan, yorum, tarih) VALUES")
d_strs = []
for d in degerlendirmeler:
    did, duid, dmid, dpuan, dyorum, dtarih = d
    d_strs.append(f"  ({did}, {duid}, {dmid}, {dpuan}, '{dyorum}', {dtarih})")
sql_lines.append(",\n".join(d_strs) + ";\n")

# Dosyaya yaz
output_path = "db/init/02_ornek_veri.sql"
with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(sql_lines))

print(f"Başarıyla üretildi: {output_path}")
print(f"Kullanıcı sayısı: {len(kullanicilar)}")
print(f"Yemek sayısı: {len(yemekler_data)}")
print(f"Alerjen sayısı: {len(alerjenler)}")
print(f"Menü sayısı: {len(menuler)}")
print(f"Rezervasyon sayısı: {len(rezervasyonlar)}")
print(f"Bakiye hareketleri sayısı: {len(bakiye_hareketleri)}")
print(f"Değerlendirme sayısı: {len(degerlendirmeler)}")

