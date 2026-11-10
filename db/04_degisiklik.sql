-- =====================================================
-- Yemekhane Otomasyonu - Değişiklik Talebi (Migration)
-- 04_degisiklik.sql
-- 1. Yarım porsiyon (%60 ücret, kahvaltı hariç)
-- 2. Kullanıcı alerjen tercihleri ve profil uyarısı
-- Mevcut veriyi bozmadan canlı sistemde çalışır.
-- =====================================================

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

USE yemekhane_db;

-- -----------------------------------------------------
-- 1. Değişiklik: rezervasyonlar tablosuna porsiyon sütunu
-- Geçmiş rezervasyonlar varsayılan olarak 'tam' sayılır.
-- -----------------------------------------------------
DELIMITER $$
DROP PROCEDURE IF EXISTS _tmp_add_porsiyon$$
CREATE PROCEDURE _tmp_add_porsiyon()
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = 'yemekhane_db' 
          AND TABLE_NAME = 'rezervasyonlar' 
          AND COLUMN_NAME = 'porsiyon'
    ) THEN
        ALTER TABLE rezervasyonlar ADD COLUMN porsiyon ENUM('tam', 'yarim') NOT NULL DEFAULT 'tam' AFTER ucret;
    END IF;
END$$
DELIMITER ;
CALL _tmp_add_porsiyon();
DROP PROCEDURE IF EXISTS _tmp_add_porsiyon;

-- -----------------------------------------------------
-- 2. Değişiklik: kullanici_alerjenleri tablosu
-- Kullanıcının profilinde seçtiği alerjenleri tutar (çoka çok ilişki)
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS kullanici_alerjenleri (
    kullanici_id INT NOT NULL,
    alerjen_id INT NOT NULL,
    olusturulma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (kullanici_id, alerjen_id),
    FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(id) ON DELETE CASCADE,
    FOREIGN KEY (alerjen_id) REFERENCES alerjenler(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 3. Değişiklik: sp_rezervasyon_yap Stored Procedure Güncellemesi
-- Yarım porsiyon desteği (%60 ücret) ve kahvaltı kontrolü
-- -----------------------------------------------------
DELIMITER $$

DROP PROCEDURE IF EXISTS sp_rezervasyon_yap$$
CREATE PROCEDURE sp_rezervasyon_yap(
    IN p_kullanici_id INT,
    IN p_menu_id INT,
    IN p_porsiyon ENUM('tam', 'yarim')
)
proc_label: BEGIN
    DECLARE v_rol ENUM('ogrenci', 'personel', 'yonetici');
    DECLARE v_bakiye DECIMAL(10,2);
    DECLARE v_ogrenci_fiyati DECIMAL(10,2);
    DECLARE v_personel_fiyati DECIMAL(10,2);
    DECLARE v_tam_ucret DECIMAL(10,2);
    DECLARE v_ucret DECIMAL(10,2);
    DECLARE v_tarih DATE;
    DECLARE v_son_saat TIME;
    DECLARE v_ogun_adi VARCHAR(50);
    DECLARE v_kapasite INT;
    DECLARE v_aktif_rezervasyon INT;
    DECLARE v_var_olan_durum ENUM('aktif', 'kullanildi', 'iptal');
    DECLARE v_rezervasyon_id INT;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    IF p_porsiyon IS NULL THEN
        SET p_porsiyon = 'tam';
    END IF;

    -- Transaction Başlat (Satır kilitlemeden önce)
    START TRANSACTION;

    -- Kullanıcı kontrolü ve kilitleme
    SELECT rol, bakiye INTO v_rol, v_bakiye
    FROM kullanicilar WHERE id = p_kullanici_id
    FOR UPDATE;

    IF v_rol IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Kullanıcı bulunamadı.';
    END IF;

    -- Menü ve öğün kontrolü (menü satırını kilitle)
    SELECT m.tarih, og.son_saat, og.ad, m.ogrenci_fiyati, m.personel_fiyati, yh.kapasite
    INTO v_tarih, v_son_saat, v_ogun_adi, v_ogrenci_fiyati, v_personel_fiyati, v_kapasite
    FROM menuler m
    JOIN ogunler og ON m.ogun_id = og.id
    JOIN yemekhaneler yh ON m.yemekhane_id = yh.id
    WHERE m.id = p_menu_id
    FOR UPDATE OF m;

    IF v_tarih IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Menü bulunamadı.';
    END IF;

    -- Rezervasyon son saati kontrolü
    IF NOW() > TIMESTAMP(v_tarih, v_son_saat) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Rezervasyon süresi dolmuştur.';
    END IF;

    -- Kahvaltıda yarım porsiyon geçerli değildir
    IF p_porsiyon = 'yarim' AND v_ogun_adi = 'Kahvaltı' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Kahvaltıda yarım porsiyon seçeneği bulunmamaktadır.';
    END IF;

    -- Kullanıcının bu menüde aktif veya kullanılmış rezervasyonu var mı?
    SELECT durum, id INTO v_var_olan_durum, v_rezervasyon_id
    FROM rezervasyonlar
    WHERE kullanici_id = p_kullanici_id AND menu_id = p_menu_id
    FOR UPDATE;

    IF v_var_olan_durum IN ('aktif', 'kullanildi') THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Bu menüye zaten rezervasyonunuz bulunmaktadır.';
    END IF;

    -- Kapasite kontrolü
    SELECT COUNT(*) INTO v_aktif_rezervasyon
    FROM rezervasyonlar
    WHERE menu_id = p_menu_id AND durum = 'aktif'
    FOR UPDATE;

    IF v_aktif_rezervasyon >= v_kapasite THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Yemekhane kapasitesi dolmuştur.';
    END IF;

    -- Fiyat belirleme
    IF v_rol = 'ogrenci' THEN
        SET v_tam_ucret = v_ogrenci_fiyati;
    ELSE
        SET v_tam_ucret = v_personel_fiyati;
    END IF;

    -- Porsiyona göre ücret hesabı (%60 kuralı)
    IF p_porsiyon = 'yarim' THEN
        SET v_ucret = ROUND(v_tam_ucret * 0.60, 2);
    ELSE
        SET v_ucret = v_tam_ucret;
    END IF;

    -- Bakiye kontrolü
    IF v_bakiye < v_ucret THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Bakiye yetersiz.';
    END IF;

    -- Bakiyeden düş
    UPDATE kullanicilar
    SET bakiye = bakiye - v_ucret
    WHERE id = p_kullanici_id;

    -- Rezervasyonu kaydet / güncelle (iptal edilmiş kayıt varsa yeniden aktifleştir)
    IF v_rezervasyon_id IS NOT NULL THEN
        UPDATE rezervasyonlar
        SET durum = 'aktif',
            ucret = v_ucret,
            porsiyon = p_porsiyon,
            iptal_tarihi = NULL,
            kullanilma_tarihi = NULL,
            olusturulma_tarihi = NOW()
        WHERE id = v_rezervasyon_id;
    ELSE
        INSERT INTO rezervasyonlar (kullanici_id, menu_id, ucret, porsiyon, durum, olusturulma_tarihi)
        VALUES (p_kullanici_id, p_menu_id, v_ucret, p_porsiyon, 'aktif', NOW());
        SET v_rezervasyon_id = LAST_INSERT_ID();
    END IF;

    -- Bakiye hareketi ekle
    INSERT INTO bakiye_hareketleri (kullanici_id, miktar, hareket_tipi, aciklama, rezervasyon_id, tarih)
    VALUES (
        p_kullanici_id, 
        -v_ucret, 
        'rezervasyon', 
        CONCAT('Rezervasyon ücreti: Menü #', p_menu_id, ' (', IF(p_porsiyon = 'yarim', 'Yarım', 'Tam'), ' Porsiyon)'), 
        v_rezervasyon_id, 
        NOW()
    );

    COMMIT;
END proc_label$$

DELIMITER ;

