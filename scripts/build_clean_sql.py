import os
import random

random.seed(42)

PASSWORD_HASH = "$2b$12$uqCGNPjR2FRH.wLf29QTG.P8vyJJ/x.D91sbGiQ1Af.D6cx0jXk5O"

# 1. 01_sema.sql Oluştur
sema_content = """-- =====================================================
-- Yemekhane Otomasyonu - Veritabanı Şeması
-- 01_sema.sql
-- 12 Tablo, 3 View, 4 Stored Procedure
-- =====================================================

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

CREATE DATABASE IF NOT EXISTS yemekhane_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE yemekhane_db;

-- -----------------------------------------------------
-- 1. Tablo: kullanicilar
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS kullanicilar (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ogrenci_no VARCHAR(20) UNIQUE NULL,
    ad VARCHAR(50) NOT NULL,
    soyad VARCHAR(50) NOT NULL,
    eposta VARCHAR(100) NOT NULL UNIQUE,
    sifre_hash VARCHAR(255) NOT NULL,
    rol ENUM('ogrenci', 'personel', 'yonetici') NOT NULL DEFAULT 'ogrenci',
    bakiye DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    olusturulma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_kullanici_bakiye CHECK (bakiye >= 0),
    CONSTRAINT chk_ogrenci_no CHECK (
        (rol = 'ogrenci' AND ogrenci_no IS NOT NULL) OR
        (rol != 'ogrenci' AND ogrenci_no IS NULL)
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 2. Tablo: yemekhaneler
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS yemekhaneler (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ad VARCHAR(100) NOT NULL,
    kapasite INT NOT NULL,
    konum VARCHAR(255) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 3. Tablo: ogunler
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS ogunler (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ad ENUM('Kahvalt\\u0131', '\\u00d6\\u011fle', 'Ak\\u015fam') NOT NULL UNIQUE,
    son_saat TIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 4. Tablo: yemek_kategorileri
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS yemek_kategorileri (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ad VARCHAR(50) NOT NULL,
    sira INT NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 5. Tablo: yemekler
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS yemekler (
    id INT AUTO_INCREMENT PRIMARY KEY,
    kategori_id INT NOT NULL,
    ad VARCHAR(100) NOT NULL,
    kalori INT NOT NULL,
    vejetaryen_mi BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (kategori_id) REFERENCES yemek_kategorileri(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 6. Tablo: alerjenler
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS alerjenler (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ad VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 7. Tablo: yemek_alerjenleri
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS yemek_alerjenleri (
    yemek_id INT NOT NULL,
    alerjen_id INT NOT NULL,
    PRIMARY KEY (yemek_id, alerjen_id),
    FOREIGN KEY (yemek_id) REFERENCES yemekler(id) ON DELETE CASCADE,
    FOREIGN KEY (alerjen_id) REFERENCES alerjenler(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 8. Tablo: menuler
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS menuler (
    id INT AUTO_INCREMENT PRIMARY KEY,
    yemekhane_id INT NOT NULL,
    tarih DATE NOT NULL,
    ogun_id INT NOT NULL,
    ogrenci_fiyati DECIMAL(10,2) NOT NULL,
    personel_fiyati DECIMAL(10,2) NOT NULL,
    olusturulma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_menu_yemekhane_tarih_ogun (yemekhane_id, tarih, ogun_id),
    FOREIGN KEY (yemekhane_id) REFERENCES yemekhaneler(id),
    FOREIGN KEY (ogun_id) REFERENCES ogunler(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 9. Tablo: menu_yemekleri
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS menu_yemekleri (
    menu_id INT NOT NULL,
    yemek_id INT NOT NULL,
    PRIMARY KEY (menu_id, yemek_id),
    FOREIGN KEY (menu_id) REFERENCES menuler(id) ON DELETE CASCADE,
    FOREIGN KEY (yemek_id) REFERENCES yemekler(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 10. Tablo: rezervasyonlar
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS rezervasyonlar (
    id INT AUTO_INCREMENT PRIMARY KEY,
    kullanici_id INT NOT NULL,
    menu_id INT NOT NULL,
    ucret DECIMAL(10,2) NOT NULL,
    durum ENUM('aktif', 'kullanildi', 'iptal') NOT NULL DEFAULT 'aktif',
    olusturulma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    iptal_tarihi TIMESTAMP NULL DEFAULT NULL,
    kullanilma_tarihi TIMESTAMP NULL DEFAULT NULL,
    UNIQUE KEY uq_rezervasyon_kisi_menu (kullanici_id, menu_id),
    FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(id),
    FOREIGN KEY (menu_id) REFERENCES menuler(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 11. Tablo: bakiye_hareketleri
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS bakiye_hareketleri (
    id INT AUTO_INCREMENT PRIMARY KEY,
    kullanici_id INT NOT NULL,
    miktar DECIMAL(10,2) NOT NULL,
    hareket_tipi ENUM('yukleme', 'rezervasyon', 'iade') NOT NULL,
    aciklama VARCHAR(255) NOT NULL,
    rezervasyon_id INT NULL DEFAULT NULL,
    tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(id),
    FOREIGN KEY (rezervasyon_id) REFERENCES rezervasyonlar(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 12. Tablo: degerlendirmeler
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS degerlendirmeler (
    id INT AUTO_INCREMENT PRIMARY KEY,
    kullanici_id INT NOT NULL,
    menu_id INT NOT NULL,
    puan TINYINT NOT NULL CHECK (puan BETWEEN 1 AND 5),
    yorum TEXT NULL,
    tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_degerlendirme_kisi_menu (kullanici_id, menu_id),
    FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(id),
    FOREIGN KEY (menu_id) REFERENCES menuler(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- HAZIR VIEW'LAR (3 ADET)
-- =====================================================

CREATE OR REPLACE VIEW v_menu_detay AS
SELECT 
    m.id AS menu_id,
    m.yemekhane_id,
    yh.ad AS yemekhane_adi,
    yh.kapasite AS yemekhane_kapasitesi,
    m.tarih,
    m.ogun_id,
    og.ad AS ogun_adi,
    og.son_saat AS ogun_son_saat,
    m.ogrenci_fiyati,
    m.personel_fiyati,
    COALESCE(SUM(y.kalori), 0) AS toplam_kalori,
    GROUP_CONCAT(DISTINCT y.ad ORDER BY yk.sira SEPARATOR ', ') AS yemek_listesi,
    GROUP_CONCAT(DISTINCT a.ad ORDER BY a.ad SEPARATOR ', ') AS alerjenler
FROM menuler m
JOIN yemekhaneler yh ON m.yemekhane_id = yh.id
JOIN ogunler og ON m.ogun_id = og.id
LEFT JOIN menu_yemekleri my ON m.id = my.menu_id
LEFT JOIN yemekler y ON my.yemek_id = y.id
LEFT JOIN yemek_kategorileri yk ON y.kategori_id = yk.id
LEFT JOIN yemek_alerjenleri ya ON y.id = ya.yemek_id
LEFT JOIN alerjenler a ON ya.alerjen_id = a.id
GROUP BY m.id, m.yemekhane_id, yh.ad, yh.kapasite, m.tarih, m.ogun_id, og.ad, og.son_saat, m.ogrenci_fiyati, m.personel_fiyati;

CREATE OR REPLACE VIEW v_menu_doluluk AS
SELECT 
    m.id AS menu_id,
    m.yemekhane_id,
    yh.ad AS yemekhane_adi,
    m.tarih,
    m.ogun_id,
    og.ad AS ogun_adi,
    yh.kapasite AS toplam_kapasite,
    COUNT(CASE WHEN r.durum = 'aktif' THEN 1 END) AS aktif_rezervasyon_sayisi,
    (yh.kapasite - COUNT(CASE WHEN r.durum = 'aktif' THEN 1 END)) AS kalan_kapasite,
    ROUND((COUNT(CASE WHEN r.durum = 'aktif' THEN 1 END) / yh.kapasite) * 100, 2) AS doluluk_orani
FROM menuler m
JOIN yemekhaneler yh ON m.yemekhane_id = yh.id
JOIN ogunler og ON m.ogun_id = og.id
LEFT JOIN rezervasyonlar r ON m.id = r.menu_id
GROUP BY m.id, m.yemekhane_id, yh.ad, m.tarih, m.ogun_id, og.ad, yh.kapasite;

CREATE OR REPLACE VIEW v_menu_puan AS
SELECT 
    m.id AS menu_id,
    m.yemekhane_id,
    yh.ad AS yemekhane_adi,
    m.tarih,
    m.ogun_id,
    og.ad AS ogun_adi,
    COUNT(d.id) AS degerlendirme_sayisi,
    ROUND(COALESCE(AVG(d.puan), 0), 2) AS ortalama_puan
FROM menuler m
JOIN yemekhaneler yh ON m.yemekhane_id = yh.id
JOIN ogunler og ON m.ogun_id = og.id
LEFT JOIN degerlendirmeler d ON m.id = d.menu_id
GROUP BY m.id, m.yemekhane_id, yh.ad, m.tarih, m.ogun_id, og.ad;

-- =====================================================
-- STORED PROCEDURE'LER (4 ADET)
-- =====================================================

DELIMITER $$

DROP PROCEDURE IF EXISTS sp_rezervasyon_yap$$
CREATE PROCEDURE sp_rezervasyon_yap(
    IN p_kullanici_id INT,
    IN p_menu_id INT
)
proc_label: BEGIN
    DECLARE v_rol ENUM('ogrenci', 'personel', 'yonetici');
    DECLARE v_bakiye DECIMAL(10,2);
    DECLARE v_ogrenci_fiyati DECIMAL(10,2);
    DECLARE v_personel_fiyati DECIMAL(10,2);
    DECLARE v_ucret DECIMAL(10,2);
    DECLARE v_tarih DATE;
    DECLARE v_son_saat TIME;
    DECLARE v_kapasite INT;
    DECLARE v_aktif_rezervasyon INT;
    DECLARE v_var_olan_durum ENUM('aktif', 'kullanildi', 'iptal');
    DECLARE v_rezervasyon_id INT;

    SELECT rol, bakiye INTO v_rol, v_bakiye
    FROM kullanicilar WHERE id = p_kullanici_id;

    IF v_rol IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Kullan\\u0131c\\u0131 bulunamad\\u0131.';
    END IF;

    SELECT m.tarih, og.son_saat, m.ogrenci_fiyati, m.personel_fiyati, yh.kapasite
    INTO v_tarih, v_son_saat, v_ogrenci_fiyati, v_personel_fiyati, v_kapasite
    FROM menuler m
    JOIN ogunler og ON m.ogun_id = og.id
    JOIN yemekhaneler yh ON m.yemekhane_id = yh.id
    WHERE m.id = p_menu_id;

    IF v_tarih IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Men\\u00fc bulunamad\\u0131.';
    END IF;

    IF NOW() > TIMESTAMP(v_tarih, v_son_saat) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Rezervasyon s\\u00fcresi dolmu\\u015ftur.';
    END IF;

    SELECT durum, id INTO v_var_olan_durum, v_rezervasyon_id
    FROM rezervasyonlar
    WHERE kullanici_id = p_kullanici_id AND menu_id = p_menu_id;

    IF v_var_olan_durum = 'aktif' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Bu men\\u00fcye zaten rezervasyonunuz bulunmaktad\\u0131r.';
    END IF;

    SELECT COUNT(*) INTO v_aktif_rezervasyon
    FROM rezervasyonlar
    WHERE menu_id = p_menu_id AND durum = 'aktif';

    IF v_aktif_rezervasyon >= v_kapasite THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Yemekhane kapasitesi dolmu\\u015ftur.';
    END IF;

    IF v_rol = 'ogrenci' THEN
        SET v_ucret = v_ogrenci_fiyati;
    ELSE
        SET v_ucret = v_personel_fiyati;
    END IF;

    IF v_bakiye < v_ucret THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Bakiye yetersiz.';
    END IF;

    START TRANSACTION;

    UPDATE kullanicilar
    SET bakiye = bakiye - v_ucret
    WHERE id = p_kullanici_id;

    IF v_rezervasyon_id IS NOT NULL THEN
        UPDATE rezervasyonlar
        SET durum = 'aktif',
            ucret = v_ucret,
            iptal_tarihi = NULL,
            olusturulma_tarihi = NOW()
        WHERE id = v_rezervasyon_id;
    ELSE
        INSERT INTO rezervasyonlar (kullanici_id, menu_id, ucret, durum, olusturulma_tarihi)
        VALUES (p_kullanici_id, p_menu_id, v_ucret, 'aktif', NOW());
        SET v_rezervasyon_id = LAST_INSERT_ID();
    END IF;

    INSERT INTO bakiye_hareketleri (kullanici_id, miktar, hareket_tipi, aciklama, rezervasyon_id, tarih)
    VALUES (p_kullanici_id, -v_ucret, 'rezervasyon', CONCAT('Rezervasyon \\u00fccreti: Men\\u00fc #', p_menu_id), v_rezervasyon_id, NOW());

    COMMIT;
END proc_label$$

DROP PROCEDURE IF EXISTS sp_rezervasyon_iptal$$
CREATE PROCEDURE sp_rezervasyon_iptal(
    IN p_kullanici_id INT,
    IN p_rezervasyon_id INT
)
proc_label: BEGIN
    DECLARE v_ucret DECIMAL(10,2);
    DECLARE v_durum ENUM('aktif', 'kullanildi', 'iptal');
    DECLARE v_tarih DATE;
    DECLARE v_son_saat TIME;

    SELECT r.ucret, r.durum, m.tarih, og.son_saat
    INTO v_ucret, v_durum, v_tarih, v_son_saat
    FROM rezervasyonlar r
    JOIN menuler m ON r.menu_id = m.id
    JOIN ogunler og ON m.ogun_id = og.id
    WHERE r.id = p_rezervasyon_id AND r.kullanici_id = p_kullanici_id;

    IF v_durum IS NULL OR v_durum != 'aktif' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = '\\u0130ptal edilebilir aktif rezervasyon bulunamad\\u0131.';
    END IF;

    IF NOW() > TIMESTAMP(v_tarih, v_son_saat) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Rezervasyon iptal s\\u00fcresi ge\\u00e7mi\\u015ftir.';
    END IF;

    START TRANSACTION;

    UPDATE rezervasyonlar
    SET durum = 'iptal',
        iptal_tarihi = NOW()
    WHERE id = p_rezervasyon_id;

    UPDATE kullanicilar
    SET bakiye = bakiye + v_ucret
    WHERE id = p_kullanici_id;

    INSERT INTO bakiye_hareketleri (kullanici_id, miktar, hareket_tipi, aciklama, rezervasyon_id, tarih)
    VALUES (p_kullanici_id, v_ucret, 'iade', CONCAT('Rezervasyon iptal iadesi: #', p_rezervasyon_id), p_rezervasyon_id, NOW());

    COMMIT;
END proc_label$$

DROP PROCEDURE IF EXISTS sp_bakiye_yukle$$
CREATE PROCEDURE sp_bakiye_yukle(
    IN p_kullanici_id INT,
    IN p_miktar DECIMAL(10,2)
)
proc_label: BEGIN
    DECLARE v_exists INT;

    IF p_miktar <= 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Y\\u00fcklenecek miktar s\\u0131f\\u0131rdan b\\u00fcy\\u00fck olmal\\u0131d\\u0131r.';
    END IF;

    SELECT COUNT(*) INTO v_exists FROM kullanicilar WHERE id = p_kullanici_id;
    IF v_exists = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Kullan\\u0131c\\u0131 bulunamad\\u0131.';
    END IF;

    START TRANSACTION;

    UPDATE kullanicilar
    SET bakiye = bakiye + p_miktar
    WHERE id = p_kullanici_id;

    INSERT INTO bakiye_hareketleri (kullanici_id, miktar, hareket_tipi, aciklama, tarih)
    VALUES (p_kullanici_id, p_miktar, 'yukleme', CONCAT(p_miktar, ' TL bakiye y\\u00fcklendi.'), NOW());

    COMMIT;
END proc_label$$

DROP PROCEDURE IF EXISTS sp_turnike_gecis$$
CREATE PROCEDURE sp_turnike_gecis(
    IN p_kullanici_id INT,
    IN p_yemekhane_id INT
)
proc_label: BEGIN
    DECLARE v_rezervasyon_id INT;

    SELECT r.id INTO v_rezervasyon_id
    FROM rezervasyonlar r
    JOIN menuler m ON r.menu_id = m.id
    WHERE r.kullanici_id = p_kullanici_id
      AND m.yemekhane_id = p_yemekhane_id
      AND m.tarih = CURDATE()
      AND r.durum = 'aktif'
    ORDER BY m.ogun_id ASC
    LIMIT 1;

    IF v_rezervasyon_id IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Ge\\u00e7erli bir aktif rezervasyon bulunamad\\u0131.';
    END IF;

    START TRANSACTION;

    UPDATE rezervasyonlar
    SET durum = 'kullanildi',
        kullanilma_tarihi = NOW()
    WHERE id = v_rezervasyon_id;

    COMMIT;
END proc_label$$

DELIMITER ;
"""

# Decode unicode escapes to pure clean UTF-8 text
sema_clean = sema_content.encode('utf-8').decode('unicode_escape')
with open('db/init/01_sema.sql', 'w', encoding='utf-8') as f:
    f.write(sema_clean)
print("01_sema.sql clean UTF-8 written.")

# 2. 02_ornek_veri.sql Oluştur
yemekler_data = [
    # 1. Çorbalar (8)
    (1, "Mercimek \\u00c7orbas\\u0131", 180, True),
    (1, "Ezogelin \\u00c7orbas\\u0131", 190, True),
    (1, "Tarhana \\u00c7orbas\\u0131", 170, True),
    (1, "Yayla \\u00c7orbas\\u0131", 160, True),
    (1, "Domates \\u00c7orbas\\u0131", 150, True),
    (1, "Tavuk Suyu \\u00c7orba", 210, False),
    (1, "Mantar \\u00c7orbas\\u0131", 175, True),
    (1, "D\\u00fc\\u011f\\u00fcn \\u00c7orbas\\u0131", 230, False),
    # 2. Ana Yemekler (12)
    (2, "Karn\\u0131yar\\u0131k", 340, False),
    (2, "\\u0130zmir K\\u00f6fte", 380, False),
    (2, "Kuru Fasulye (Etli)", 350, False),
    (2, "Tas Kebab\\u0131", 420, False),
    (2, "F\\u0131r\\u0131n Tavuk But", 390, False),
    (2, "Orman Kebab\\u0131", 400, False),
    (2, "Etli G\\u00fcve\\u00e7", 410, False),
    (2, "Kad\\u0131nbudu K\\u00f6fte", 430, False),
    (2, "H\\u00fcnkar Be\\u011fendi", 460, False),
    (2, "Tavuk \\u015einitzel", 380, False),
    (2, "K\\u0131ymal\\u0131 Musakka", 360, False),
    (2, "Hasanpa\\u015fa K\\u00f6fte", 420, False),
    # 3. Vejetaryen / Diyet (8)
    (3, "Zeytinya\\u011fl\\u0131 Taze Fasulye", 190, True),
    (3, "Ispanak Yeme\\u011fi", 180, True),
    (3, "Sebzeli T\\u00fcrl\\u00fc", 210, True),
    (3, "F\\u0131r\\u0131nda M\\u00fccver", 220, True),
    (3, "Etsiz Nohut Yeme\\u011fi", 280, True),
    (3, "Zeytinya\\u011fl\\u0131 Biber Dolmas\\u0131", 230, True),
    (3, "Zeytinya\\u011fl\\u0131 Enginar", 195, True),
    (3, "Mercimek K\\u00f6ftesi", 250, True),
    # 4. Garnitür / Pilav / Makarna (8)
    (4, "Pirin\\u00e7 Pilav\\u0131", 260, True),
    (4, "Bulgur Pilav\\u0131", 220, True),
    (4, "F\\u0131r\\u0131n Makarna", 310, True),
    (4, "Patates P\\u00fcresi", 200, True),
    (4, "\\u015eehriyeli Pirin\\u00e7 Pilav\\u0131", 270, True),
    (4, "Sebzeli Kuskus", 240, True),
    (4, "F\\u0131r\\u0131n Elma Dilim Patates", 210, True),
    (4, "Domates Soslu Spagetti", 290, True),
    # 5. Salatalar (6)
    (5, "Mevsim Salatas\\u0131", 75, True),
    (5, "\\u00c7oban Salata", 90, True),
    (5, "Havu\\u00e7 Tarator", 140, True),
    (5, "Haydari", 130, True),
    (5, "Piyaz", 180, True),
    (5, "K\\u00f6z Patl\\u0131can Salatas\\u0131", 85, True),
    # 6. Tatlılar & Meyveler (6)
    (6, "F\\u0131r\\u0131n S\\u00fctla\\u00e7", 250, True),
    (6, "Revani", 320, True),
    (6, "Kemalpa\\u015fa Tatl\\u0131s\\u0131", 280, True),
    (6, "Cevizli Baklava", 410, True),
    (6, "Mevsim Meyvesi Taba\\u011f\\u0131", 110, True),
    (6, "Kazandibi", 240, True),
    # 7. İçecekler (4)
    (7, "Ayran", 75, True),
    (7, "Limonata", 95, True),
    (7, "Vi\\u015fne Suyu", 110, True),
    (7, "Su", 0, True)
]

alerjenler = [
    "Gluten", "Laktoz", "Yumurta", "Bal\\u0131k", "Kabuklular",
    "Yer F\\u0131st\\u0131\\u011f\\u0131", "Soya", "Sert Kabuklu Meyveler", "Kereviz",
    "Hardal", "Susam", "K\\u00fck\\u00fcrt Dioksit", "Ac\\u0131 Bakla", "Yumu\\u015fak\\u00e7alar"
]

yemek_kategorileri = [
    (1, "\\u00c7orbalar", 1),
    (2, "Ana Yemekler", 2),
    (3, "Vejetaryen / Diyet", 3),
    (4, "Garnit\\u00fcr / Pilav / Makarna", 4),
    (5, "Salatalar", 5),
    (6, "Tatl\\u0131lar & Meyveler", 6),
    (7, "\\u0130\\u00e7ecekler", 7)
]

kullanicilar_meta = [
    (1, None, "Bar\\u0131\\u015f", "Y\\u0131lmaz", "admin@kampus.edu.tr", "yonetici"),
    (2, None, "Ahmet", "Kaya", "personel1@kampus.edu.tr", "personel"),
    (3, None, "Ay\\u015fe", "Demir", "personel2@kampus.edu.tr", "personel"),
    (4, None, "Mehmet", "\\u00d6zt\\u00fcrk", "personel3@kampus.edu.tr", "personel"),
    (5, None, "Fatma", "\\u00c7elik", "personel4@kampus.edu.tr", "personel"),
]

ogrenciler_raw = [
    ("Caner", "\\u015eahin"), ("Elif", "Y\\u0131ld\\u0131z"), ("Burak", "Ko\\u00e7"), ("Zeynep", "Ayd\\u0131n"),
    ("Emre", "Arslan"), ("Selin", "Do\\u011fan"), ("Berk", "K\\u0131l\\u0131\\u00e7"), ("Gamze", "Aslan"),
    ("Onur", "\\u00c7etin"), ("Tu\\u011fba", "Kara"), ("Mert", "Polat"), ("Derya", "Kurt"),
    ("Tolga", "Yavuz"), ("Ezgi", "\\u015eim\\u015fek"), ("Kaan", "\\u00d6zdemir"), ("Melis", "Erdo\\u011fan"),
    ("Arda", "Tekin"), ("Ceren", "Aksoy"), ("Kerem", "G\\u00fcne\\u015f"), ("\\u0130rem", "Yal\\u00e7\\u0131n"),
    ("Yasin", "Bozkurt"), ("Ece", "Korkmaz"), ("Sinan", "Avc\\u0131"), ("B\\u00fc\\u015fra", "Ta\\u015f"),
    ("Deniz", "Bulut")
]

for idx, (ad, soyad) in enumerate(ogrenciler_raw, 6):
    ogrenci_no = f"2512290{idx:02d}"
    eposta = f"ogrenci{idx-5}@kampus.edu.tr"
    kullanicilar_meta.append((idx, ogrenci_no, ad, soyad, eposta, "ogrenci"))

sql_lines = []
sql_lines.append("-- =====================================================")
sql_lines.append("-- Yemekhane Otomasyonu - Başlangıç Verileri")
sql_lines.append("-- 02_ornek_veri.sql")
sql_lines.append("-- =====================================================\n")
sql_lines.append("SET NAMES utf8mb4;\nSET CHARACTER SET utf8mb4;\nUSE yemekhane_db;\n")

# Yemekhaneler
sql_lines.append("INSERT INTO yemekhaneler (id, ad, kapasite, konum) VALUES")
sql_lines.append("  (1, 'Merkez Yemekhanesi', 400, 'Ana Kamp\\u00fcs Meydan\\u0131'),")
sql_lines.append("  (2, 'M\\u00fchendislik Yemekhanesi', 60, 'M\\u00fchendislik Fak\\u00fcltesi Zemin Kat');\n")

# Öğünler
sql_lines.append("INSERT INTO ogunler (id, ad, son_saat) VALUES")
sql_lines.append("  (1, 'Kahvalt\\u0131', '07:00:00'),")
sql_lines.append("  (2, '\\u00d6\\u011fle', '10:00:00'),")
sql_lines.append("  (3, 'Ak\\u015fam', '15:00:00');\n")

# Kategoriler
sql_lines.append("INSERT INTO yemek_kategorileri (id, ad, sira) VALUES")
cat_strs = [f"  ({cid}, '{cad}', {csira})" for cid, cad, csira in yemek_kategorileri]
sql_lines.append(",\n".join(cat_strs) + ";\n")

# Yemekler
sql_lines.append("INSERT INTO yemekler (id, kategori_id, ad, kalori, vejetaryen_mi) VALUES")
y_strs = []
for idx, (kat_id, ad, kalori, veg) in enumerate(yemekler_data, 1):
    veg_str = "TRUE" if veg else "FALSE"
    y_strs.append(f"  ({idx}, {kat_id}, '{ad}', {kalori}, {veg_str})")
sql_lines.append(",\n".join(y_strs) + ";\n")

# Alerjenler
sql_lines.append("INSERT INTO alerjenler (id, ad) VALUES")
al_strs = [f"  ({idx}, '{ad}')" for idx, ad in enumerate(alerjenler, 1)]
sql_lines.append(",\n".join(al_strs) + ";\n")

# Yemek Alerjenleri
yemek_alerjen_map = [
    (1, [1]), (2, [1]), (3, [1, 2]), (4, [1, 2]), (5, [1, 2]), (6, [1]), (7, [1, 2]), (8, [1, 2, 3]),
    (10, [1, 3]), (16, [1, 3]), (17, [1, 2]), (18, [1, 3]), (20, [1, 2, 3]),
    (24, [1, 3]), (28, [1]), (30, [1]), (31, [1, 2, 3]), (32, [2]), (33, [1]), (34, [1]), (36, [1]),
    (39, [2, 8]), (40, [2]), (41, [3]), (43, [2]), (44, [1, 2, 3]), (45, [1, 2, 3]), (46, [1, 2, 8]),
    (48, [2]), (49, [2])
]
sql_lines.append("INSERT INTO yemek_alerjenleri (yemek_id, alerjen_id) VALUES")
ya_strs = []
for y_id, a_ids in yemek_alerjen_map:
    for a_id in a_ids:
        ya_strs.append(f"  ({y_id}, {a_id})")
sql_lines.append(",\n".join(ya_strs) + ";\n")

# Menüler (84 Menü: 14 Gün x 2 Yemekhane x 3 Öğün)
menuler = []
menu_id = 1
for day_offset in range(-7, 7):
    for yemekhane_id in [1, 2]:
        for ogun_id in [1, 2, 3]:
            ogr_fiyat = 30.00 if ogun_id == 1 else 45.00
            prs_fiyat = 60.00 if ogun_id == 1 else 90.00
            menuler.append((menu_id, yemekhane_id, day_offset, ogun_id, ogr_fiyat, prs_fiyat))
            menu_id += 1

sql_lines.append("INSERT INTO menuler (id, yemekhane_id, tarih, ogun_id, ogrenci_fiyati, personel_fiyati) VALUES")
m_strs = []
for m in menuler:
    mid, yhid, doff, oid, ofiy, pfiy = m
    m_strs.append(f"  ({mid}, {yhid}, DATE_ADD(CURDATE(), INTERVAL {doff} DAY), {oid}, {ofiy:.2f}, {pfiy:.2f})")
sql_lines.append(",\n".join(m_strs) + ";\n")

# Menü Yemekleri
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

# Rezervasyonlar ve Bakiye
user_balances = {u[0]: 0.0 for u in kullanicilar_meta}
rezervasyonlar = []
bakiye_hareketleri = []
rez_id = 1
hareket_id = 1

for u in kullanicilar_meta:
    uid = u[0]
    load_amount = float(random.choice([350, 400, 450, 500, 600]))
    user_balances[uid] += load_amount
    bakiye_hareketleri.append((
        hareket_id, uid, load_amount, 'yukleme',
        f"{load_amount:.2f} TL bakiye y\\u00fcklendi.", "NULL",
        "DATE_SUB(NOW(), INTERVAL 10 DAY)"
    ))
    hareket_id += 1

menu_dict = {m[0]: m for m in menuler}
target_rez_count = 365
created_rez_set = set()
user_ids = [u[0] for u in kullanicilar_meta]

while len(rezervasyonlar) < target_rez_count:
    uid = random.choice(user_ids)
    mid = random.randint(1, 84)
    if (uid, mid) in created_rez_set:
        continue
    
    m = menu_dict[mid]
    day_offset = m[2]
    user_role = next(u[5] for u in kullanicilar_meta if u[0] == uid)
    price = m[4] if user_role == 'ogrenci' else m[5]
    
    if day_offset < 0:
        durum = 'kullanildi' if random.random() < 0.85 else 'iptal'
    elif day_offset == 0:
        durum = 'kullanildi' if random.random() < 0.40 else 'aktif'
    else:
        durum = 'aktif' if random.random() < 0.90 else 'iptal'
        
    create_time_expr = f"DATE_ADD(CURDATE(), INTERVAL {day_offset - 1} DAY)"
    iptal_time_expr = f"DATE_ADD(CURDATE(), INTERVAL {day_offset} DAY)" if durum == 'iptal' else "NULL"
    kullanilma_time_expr = f"DATE_ADD(CURDATE(), INTERVAL {day_offset} DAY)" if durum == 'kullanildi' else "NULL"
    
    rezervasyonlar.append((rez_id, uid, mid, price, durum, create_time_expr, iptal_time_expr, kullanilma_time_expr))
    created_rez_set.add((uid, mid))
    
    user_balances[uid] -= price
    bakiye_hareketleri.append((
        hareket_id, uid, -price, 'rezervasyon',
        f"Rezervasyon \\u00fccreti: Men\\u00fc #{mid}", str(rez_id),
        create_time_expr
    ))
    hareket_id += 1
    
    if durum == 'iptal':
        user_balances[uid] += price
        bakiye_hareketleri.append((
            hareket_id, uid, price, 'iade',
            f"Rezervasyon iptal iadesi: #{rez_id}", str(rez_id),
            iptal_time_expr
        ))
        hareket_id += 1
    rez_id += 1

# Bakiye negatif olamaz
for uid, bal in user_balances.items():
    if bal < 50.0:
        ek_yukleme = 150.0 - bal
        user_balances[uid] += ek_yukleme
        bakiye_hareketleri.append((
            hareket_id, uid, ek_yukleme, 'yukleme',
            f"{ek_yukleme:.2f} TL bakiye y\\u00fcklendi.", "NULL",
            "DATE_SUB(NOW(), INTERVAL 5 DAY)"
        ))
        hareket_id += 1

# Kullanıcılar
sql_lines.append("INSERT INTO kullanicilar (id, ogrenci_no, ad, soyad, eposta, sifre_hash, rol, bakiye) VALUES")
k_strs = []
for u in kullanicilar_meta:
    uid, og_no, ad, soyad, eposta, rol = u
    og_no_str = f"'{og_no}'" if og_no else "NULL"
    bakiye = user_balances[uid]
    k_strs.append(f"  ({uid}, {og_no_str}, '{ad}', '{soyad}', '{eposta}', '{PASSWORD_HASH}', '{rol}', {bakiye:.2f})")
sql_lines.append(",\n".join(k_strs) + ";\n")

# Rezervasyonlar
sql_lines.append(f"INSERT INTO rezervasyonlar (id, kullanici_id, menu_id, ucret, durum, olusturulma_tarihi, iptal_tarihi, kullanilma_tarihi) VALUES")
r_strs = []
for r in rezervasyonlar:
    rid, ruid, rmid, rucret, rdurum, rcreate, riptal, rkullan = r
    r_strs.append(f"  ({rid}, {ruid}, {rmid}, {rucret:.2f}, '{rdurum}', {rcreate}, {riptal}, {rkullan})")
sql_lines.append(",\n".join(r_strs) + ";\n")

# Bakiye Hareketleri
sql_lines.append(f"INSERT INTO bakiye_hareketleri (id, kullanici_id, miktar, hareket_tipi, aciklama, rezervasyon_id, tarih) VALUES")
bh_strs = []
for bh in bakiye_hareketleri:
    bhid, bhuid, bhmiktar, bhtip, bhacik, bhrez, bhtarih = bh
    bh_strs.append(f"  ({bhid}, {bhuid}, {bhmiktar:.2f}, '{bhtip}', '{bhacik}', {bhrez}, {bhtarih})")
sql_lines.append(",\n".join(bh_strs) + ";\n")

# Değerlendirmeler
yorumlar = [
    (5, "Yemekler \\u00e7ok lezzetliydi, \\u00e7orba s\\u0131cakt\\u0131."),
    (4, "Genel olarak gayet iyiydi, tatl\\u0131 biraz fazla \\u015fekerliydi."),
    (5, "Porsiyonlar doyurucu, ellerinize sa\\u011fl\\u0131k."),
    (3, "Ana yemek g\\u00fczeldi ama garnit\\u00fcr so\\u011fuktu."),
    (4, "\\u00d6\\u011frenci men\\u00fcs\\u00fcne g\\u00f6re gayet ba\\u015far\\u0131l\\u0131."),
    (5, "M\\u00fckemmel men\\u00fc, mercimek \\u00e7orbas\\u0131 harikayd\\u0131."),
    (2, "Tavuk biraz kuruydu, geli\\u015ftirilebilir."),
    (4, "Fiyat/performans olarak kamp\\u00fcs\\u00fcn en iyisi.")
]

degerlendirmeler = []
deg_id = 1
deg_set = set()

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

# Dosyaya yaz (Unicode escapes decode edilerek)
raw_sql = "\n".join(sql_lines)
clean_sql = raw_sql.encode('utf-8').decode('unicode_escape')

with open('db/init/02_ornek_veri.sql', 'w', encoding='utf-8') as f:
    f.write(clean_sql)

print("02_ornek_veri.sql clean UTF-8 written.")

