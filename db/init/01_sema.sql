-- =====================================================
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
    ad ENUM('Kahvaltı', 'Öğle', 'Akşam') NOT NULL UNIQUE,
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
        SET MESSAGE_TEXT = 'Kullanıcı bulunamadı.';
    END IF;

    SELECT m.tarih, og.son_saat, m.ogrenci_fiyati, m.personel_fiyati, yh.kapasite
    INTO v_tarih, v_son_saat, v_ogrenci_fiyati, v_personel_fiyati, v_kapasite
    FROM menuler m
    JOIN ogunler og ON m.ogun_id = og.id
    JOIN yemekhaneler yh ON m.yemekhane_id = yh.id
    WHERE m.id = p_menu_id;

    IF v_tarih IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Menü bulunamadı.';
    END IF;

    IF NOW() > TIMESTAMP(v_tarih, v_son_saat) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Rezervasyon süresi dolmuştur.';
    END IF;

    SELECT durum, id INTO v_var_olan_durum, v_rezervasyon_id
    FROM rezervasyonlar
    WHERE kullanici_id = p_kullanici_id AND menu_id = p_menu_id;

    IF v_var_olan_durum = 'aktif' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Bu menüye zaten rezervasyonunuz bulunmaktadır.';
    END IF;

    SELECT COUNT(*) INTO v_aktif_rezervasyon
    FROM rezervasyonlar
    WHERE menu_id = p_menu_id AND durum = 'aktif';

    IF v_aktif_rezervasyon >= v_kapasite THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Yemekhane kapasitesi dolmuştur.';
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
    VALUES (p_kullanici_id, -v_ucret, 'rezervasyon', CONCAT('Rezervasyon ücreti: Menü #', p_menu_id), v_rezervasyon_id, NOW());

    COMMIT;
END proc_label$$

DROP PROCEDURE IF EXISTS sp_rezervasyon_iptal$$
CREATE PROCEDURE sp_rezervasyon_iptal(
    IN p_kullanici_id INT,
    IN p_rezervasyon_id INT
)
proc_label: BEGIN
    DECLARE v_kullanici_lock INT;
    DECLARE v_ucret DECIMAL(10,2);
    DECLARE v_durum ENUM('aktif', 'kullanildi', 'iptal');
    DECLARE v_menu_id INT;
    DECLARE v_tarih DATE;
    DECLARE v_son_saat TIME;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    SELECT id INTO v_kullanici_lock
    FROM kullanicilar
    WHERE id = p_kullanici_id
    FOR UPDATE;

    SELECT r.ucret, r.durum, r.menu_id
    INTO v_ucret, v_durum, v_menu_id
    FROM rezervasyonlar r
    WHERE r.id = p_rezervasyon_id AND r.kullanici_id = p_kullanici_id
    FOR UPDATE;

    IF v_durum IS NULL OR v_durum != 'aktif' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'İptal edilebilir aktif rezervasyon bulunamadı.';
    END IF;

    SELECT m.tarih, og.son_saat
    INTO v_tarih, v_son_saat
    FROM menuler m
    JOIN ogunler og ON m.ogun_id = og.id
    WHERE m.id = v_menu_id;

    IF NOW() > TIMESTAMP(v_tarih, v_son_saat) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Rezervasyon iptal süresi geçmiştir.';
    END IF;

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
    DECLARE v_kullanici_lock INT;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    IF p_miktar IS NULL OR p_miktar <= 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Yüklenecek miktar sıfırdan büyük olmalıdır.';
    END IF;

    START TRANSACTION;

    SELECT id INTO v_kullanici_lock
    FROM kullanicilar
    WHERE id = p_kullanici_id
    FOR UPDATE;

    IF v_kullanici_lock IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Kullanıcı bulunamadı.';
    END IF;

    UPDATE kullanicilar
    SET bakiye = bakiye + p_miktar
    WHERE id = p_kullanici_id;

    INSERT INTO bakiye_hareketleri (kullanici_id, miktar, hareket_tipi, aciklama, tarih)
    VALUES (p_kullanici_id, p_miktar, 'yukleme', CONCAT(p_miktar, ' TL bakiye yüklendi.'), NOW());

    COMMIT;
END proc_label$$

DROP PROCEDURE IF EXISTS sp_turnike_gecis$$
CREATE PROCEDURE sp_turnike_gecis(
    IN p_kullanici_id INT,
    IN p_yemekhane_id INT
)
proc_label: BEGIN
    DECLARE v_kullanici_lock INT;
    DECLARE v_rezervasyon_id INT;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    SELECT id INTO v_kullanici_lock
    FROM kullanicilar
    WHERE id = p_kullanici_id
    FOR UPDATE;

    SELECT r.id INTO v_rezervasyon_id
    FROM rezervasyonlar r
    JOIN menuler m ON r.menu_id = m.id
    WHERE r.kullanici_id = p_kullanici_id
      AND m.yemekhane_id = p_yemekhane_id
      AND m.tarih = CURDATE()
      AND r.durum = 'aktif'
    ORDER BY m.ogun_id ASC
    LIMIT 1
    FOR UPDATE OF r;

    IF v_rezervasyon_id IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Geçerli bir aktif rezervasyon bulunamadı.';
    END IF;

    UPDATE rezervasyonlar
    SET durum = 'kullanildi',
        kullanilma_tarihi = NOW()
    WHERE id = v_rezervasyon_id;

    COMMIT;
END proc_label$$

DELIMITER ;
