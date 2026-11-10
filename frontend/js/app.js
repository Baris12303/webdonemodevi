// Kampüs Yemekhane Otomasyonu - Frontend Script

const API_BASE = "/api";

// Uygulama Durumu (State)
let currentUser = null;
let currentToken = localStorage.getItem("auth_token") || null;
let userAllergenNames = []; // Kullanıcının seçtiği alerjenlerin adları
let userAllergenIds = [];   // Kullanıcının seçtiği alerjen ID'leri
let allSystemAllergens = []; // Sistemdeki tüm alerjenler
let adminStatsById = {};     // Yönetici istatistik satırları (menu_id -> satır)
let adminDishesCache = [];   // Yönetici yemek listesi önbelleği

// Güvenli HTML Kaçış Yardımcısı
function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Yerel Tarih Formatlayıcı (YYYY-MM-DD)
function getLocalDateString(d = new Date()) {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

// Yarım Porsiyon Kuralı (Yalnızca Öğle ve Akşam)
function isHalfPortionAllowed(menu) {
  if (!menu) return false;
  if (menu.ogun_adi === "Kahvaltı" || Number(menu.ogun_id) === 1) return false;
  return Number(menu.ogun_id) === 2 || Number(menu.ogun_id) === 3 || menu.ogun_adi === "Öğle" || menu.ogun_adi === "Akşam";
}

function calculateHalfPortionPrice(tamFiyat) {
  return Math.round((Number(tamFiyat) * 0.60) * 100 + Number.EPSILON) / 100;
}

function extractErrorMessage(data, fallback = "Bir hata oluştu.") {
  if (!data || !data.detail) return fallback;
  if (Array.isArray(data.detail)) {
    const msgs = data.detail.map(d => {
      if (d && d.msg) return d.msg;
      if (d && typeof d === "object") return JSON.stringify(d);
      return String(d);
    }).filter(Boolean);
    return msgs.length > 0 ? msgs.join(", ") : fallback;
  }
  if (typeof data.detail === "object") {
    return data.detail.message || data.detail.msg || JSON.stringify(data.detail);
  }
  return String(data.detail);
}

// Toast Bildirim Fonksiyonu
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Oturum Sıfırlama
function resetSession(message = null, type = "info") {
  setUserState(null, null);
  showScreen("screen-login");
  if (message) {
    showToast(message, type);
  }
}

// API İstek Yardımcısı (Token ile birlikte)
async function apiRequest(endpoint, method = "GET", body = null, { silent = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (currentToken) {
    headers["Authorization"] = `Bearer ${currentToken}`;
  }

  const options = { method, headers };
  if (body) {
    options.body = JSON.stringify(body);
  }

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, options);
    const contentType = res.headers.get("content-type");
    let data;
    if (contentType && contentType.includes("application/json")) {
      data = await res.json();
    } else {
      throw new Error(`Sunucu Hatası (${res.status}): Backend API servisine ulaşılamıyor.`);
    }
    if (!res.ok) {
      if (res.status === 401 && endpoint !== "/auth/login" && endpoint !== "/auth/logout") {
        const msg = extractErrorMessage(data, "Oturum süreniz doldu. Lütfen tekrar giriş yapın.");
        resetSession(silent ? null : msg, "error");
        const err = new Error(msg);
        err._handled401 = true;
        err.status = res.status;
        throw err;
      }
      const err = new Error(extractErrorMessage(data));
      err.status = res.status;
      throw err;
    }
    return data;
  } catch (err) {
    if (!silent && !err._handled401) {
      showToast(err.message, "error");
    }
    throw err;
  }
}

// Ekran Değiştirme
function showScreen(screenId) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));

  const targetScreen = document.getElementById(screenId);
  if (targetScreen) targetScreen.classList.add("active");

  const targetTab = document.querySelector(`[data-screen="${screenId}"]`);
  if (targetTab) targetTab.classList.add("active");

  // Ekran bazlı veri yükleme
  if (screenId === "screen-today") loadDailyMenu();
  if (screenId === "screen-weekly") loadWeeklyMenus();
  if (screenId === "screen-reservations") loadMyReservations();
  if (screenId === "screen-balance") loadBalanceAndHistory();
  if (screenId === "screen-allergens") loadAllergensScreen();
  if (screenId === "screen-admin") loadAdminDashboard();
}

// Kimlik Doğrulama İşlemleri
async function initAuth() {
  if (currentToken) {
    try {
      const user = await apiRequest("/auth/me", "GET", null, { silent: true });
      setUserState(user, currentToken);
      await loadUserAllergenNames();
      if (!currentUser || !currentToken) return;
      showScreen("screen-today");
    } catch {
      resetSession();
    }
  } else {
    showScreen("screen-login");
  }
}

function setUserState(user, token) {
  currentUser = user;
  currentToken = token;
  if (token) localStorage.setItem("auth_token", token);
  else localStorage.removeItem("auth_token");

  // Header güncelle
  const userArea = document.getElementById("header-user-info");
  const authNav = document.getElementById("main-nav");
  const adminTab = document.getElementById("tab-admin");

  if (user) {
    userArea.style.display = "flex";
    authNav.style.display = "block";
    document.getElementById("user-name").textContent = `${user.ad} ${user.soyad}`;
    document.getElementById("user-role").textContent = user.rol;
    document.getElementById("user-balance").textContent = `${Number(user.bakiye).toFixed(2)} TL`;

    // Yönetici sekmesi kontrolü
    if (user.rol === "yonetici") {
      adminTab.style.display = "block";
    } else {
      adminTab.style.display = "none";
    }
  } else {
    userArea.style.display = "none";
    authNav.style.display = "none";
    adminTab.style.display = "none";
    userAllergenNames = [];
    userAllergenIds = [];
    allSystemAllergens = [];
    adminStatsById = {};
    if (typeof cancelEditMenu === "function") {
      cancelEditMenu();
    }
    const pwInput = document.getElementById("login-password");
    if (pwInput) pwInput.value = "";
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const eposta = document.getElementById("login-email").value;
  const sifre = document.getElementById("login-password").value;

  try {
    const res = await apiRequest("/auth/login", "POST", { eposta, sifre });
    setUserState(res.kullanici, res.token);
    await loadUserAllergenNames();
    if (!currentUser || !currentToken) return;
    showToast(`Hoş geldiniz, ${res.kullanici.ad}!`, "success");
    showScreen("screen-today");
  } catch (err) {
    // Hata mesajı apiRequest tarafından showToast ile gösterildi
  }
}

async function logout() {
  try {
    await apiRequest("/auth/logout", "POST", null, { silent: true });
  } catch {}
  resetSession("Oturum kapatıldı.", "info");
}

// Günün Menüsü
async function loadDailyMenu() {
  const container = document.getElementById("daily-menu-content");
  container.innerHTML = "<p>Menü yükleniyor...</p>";

  const yhId = document.getElementById("today-yh-select").value;
  const ogunId = document.getElementById("today-ogun-select").value;
  const tarih = document.getElementById("today-date-picker").value || getLocalDateString();

  try {
    const menu = await apiRequest(`/menus/today?yemekhane_id=${yhId}&tarih=${encodeURIComponent(tarih)}&ogun_id=${ogunId}`);

    // Kullanıcı fiyatını belirle
    const tamFiyat = Number(currentUser?.rol === "ogrenci" ? menu.ogrenci_fiyati : menu.personel_fiyati);
    const yarimFiyat = calculateHalfPortionPrice(tamFiyat);
    const allowHalf = isHalfPortionAllowed(menu);

    // Alerjen kontrolü
    const matchingAllergens = (menu.tum_alerjenler || []).filter(a => userAllergenNames.includes(a));
    let allergenAlertHtml = "";
    if (matchingAllergens.length > 0) {
      allergenAlertHtml = `
        <div style="background: #fef2f2; border: 1.5px solid #ef4444; border-radius: 8px; padding: 12px 16px; margin-bottom: 15px; color: #991b1b;">
          <div style="font-weight: 700; font-size: 0.95rem;">
            Alerjen Uyarısı
          </div>
          <p style="font-size: 0.85rem; margin-top: 5px; line-height: 1.4;">
            Bu menüdeki bazı yemekler seçtiğiniz alerjenleri içeriyor: <strong>${matchingAllergens.map(escapeHtml).join(', ')}</strong>.
          </p>
        </div>
      `;
    }

    let dishesHtml = "";
    (menu.yemekler || []).forEach(y => {
      const dishAllergens = Array.isArray(y.alerjenler) ? y.alerjenler : [];
      const matchingDishAllergens = dishAllergens.filter(a => userAllergenNames.includes(a));
      const hasDishWarning = matchingDishAllergens.length > 0;

      let dishAllergenHtml = "";
      if (dishAllergens.length > 0) {
        const pills = dishAllergens.map(a => {
          const isMatch = userAllergenNames.includes(a);
          return `<span class="badge ${isMatch ? 'badge-allergen-match' : 'badge-allergen'}">${escapeHtml(a)}</span>`;
        }).join("");
        dishAllergenHtml = `<div class="dish-allergens">${pills}</div>`;
      }

      dishesHtml += `
        <li class="dish-item ${hasDishWarning ? 'dish-item-warning' : ''}">
          <div class="dish-info">
            <span class="dish-name">${escapeHtml(y.ad)}${hasDishWarning ? ' (Alerjen Uyarısı)' : ''}</span>
            <span class="dish-category">${escapeHtml(y.kategori_adi)}</span>
            ${dishAllergenHtml}
          </div>
          <span class="dish-cal">${Number(y.kalori)} kcal</span>
        </li>
      `;
    });

    let allergenBadges = "";
    (menu.tum_alerjenler || []).forEach(a => {
      const isUserAllergen = userAllergenNames.includes(a);
      allergenBadges += `<span class="badge ${isUserAllergen ? 'badge-allergen-match' : 'badge-allergen'}">${escapeHtml(a)}</span>`;
    });

    const cacheBadge = menu.kaynak === "cache"
      ? '<span class="badge badge-info" title="Redis önbellekten yüklendi">Kaynak: Redis</span>'
      : '<span class="badge badge-veg" title="Veritabanından okundu">Kaynak: Veritabanı</span>';

    // Porsiyon seçimi (kahvaltıda sadece tam porsiyon)
    let portionSelectorHtml = "";
    if (!allowHalf) {
      portionSelectorHtml = `
        <div class="portion-box">
          <span style="font-size: 0.8rem; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 8px; text-transform: uppercase;">Porsiyon Seçimi</span>
          <label class="portion-option">
            <input type="radio" name="daily-portion" value="tam" checked onchange="updateDailyPriceDisplay(${tamFiyat})">
            <span><strong>Tam Porsiyon</strong> - ${tamFiyat.toFixed(2)} TL</span>
          </label>
          <p class="portion-note">Kahvaltıda yarım porsiyon seçeneği bulunmamaktadır.</p>
        </div>
      `;
    } else {
      portionSelectorHtml = `
        <div class="portion-box">
          <span style="font-size: 0.8rem; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 8px; text-transform: uppercase;">Porsiyon Seçimi</span>
          <div style="display: flex; gap: 20px; flex-wrap: wrap;">
            <label class="portion-option">
              <input type="radio" name="daily-portion" value="tam" checked onchange="updateDailyPriceDisplay(${tamFiyat})">
              <span><strong>Tam Porsiyon</strong> (${tamFiyat.toFixed(2)} TL)</span>
            </label>
            <label class="portion-option">
              <input type="radio" name="daily-portion" value="yarim" onchange="updateDailyPriceDisplay(${yarimFiyat})">
              <span><strong>Yarım Porsiyon (%60)</strong> (${yarimFiyat.toFixed(2)} TL)</span>
            </label>
          </div>
        </div>
      `;
    }

    container.innerHTML = `
      <div class="card">
        ${allergenAlertHtml}
        <div class="card-title">
          <span>${escapeHtml(menu.yemekhane_adi)} - ${escapeHtml(menu.ogun_adi)} Menüsü</span>
          ${cacheBadge}
        </div>
        <p style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 10px;">
          Tarih: ${escapeHtml(menu.tarih)} &nbsp;|&nbsp; Son Rezervasyon: ${escapeHtml(menu.ogun_son_saat)}
        </p>

        <ul class="dish-list">${dishesHtml}</ul>

        <div style="margin: 15px 0;">
          <strong>Toplam Kalori:</strong> ${Number(menu.toplam_kalori)} kcal
        </div>

        <div class="badge-group">
          ${menu.vejetaryen_mi ? '<span class="badge badge-veg">Vejetaryen Menü</span>' : ''}
          ${allergenBadges}
        </div>

        ${portionSelectorHtml}

        <div class="row-between" style="margin-top: 15px;">
          <div>
            <span style="font-size: 0.85rem; color: var(--text-muted);">Ödenecek Ücret (${escapeHtml(currentUser?.rol)}):</span>
            <div id="daily-price-display" style="font-size: 1.4rem; font-weight: 800; color: var(--primary);">${tamFiyat.toFixed(2)} TL</div>
          </div>
          <div style="text-align: right;">
            <span style="font-size: 0.85rem; color: var(--text-muted);">Kalan Kontenjan:</span>
            <div style="font-weight: 600;">${Number(menu.kalan_kapasite)} / ${Number(menu.yemekhane_kapasitesi)}</div>
          </div>
        </div>

        <button type="button" class="btn btn-primary" style="margin-top: 15px;" onclick="handleBookReservationFromDaily(${Number(menu.menu_id)}, ${allowHalf})">
          Bu Menüye Rezervasyon Yap
        </button>
      </div>
    `;
  } catch (err) {
    const msg = err && err.status === 404
      ? "Bu tarih ve öğün için menü kaydı bulunamadı."
      : `Menü yüklenemedi: ${escapeHtml(err?.message || "Bilinmeyen hata.")}`;
    container.innerHTML = `<div class="card"><p style="color: var(--danger);">${msg}</p></div>`;
  }
}

function updateDailyPriceDisplay(amount) {
  const el = document.getElementById("daily-price-display");
  if (el) el.textContent = `${parseFloat(amount).toFixed(2)} TL`;
}

async function handleBookReservationFromDaily(menuId, allowHalf = true) {
  const portionInput = document.querySelector('input[name="daily-portion"]:checked');
  const portion = allowHalf && portionInput ? portionInput.value : "tam";
  await handleBookReservation(menuId, portion, "daily");
}

// Haftalık Menü
async function loadWeeklyMenus() {
  const container = document.getElementById("weekly-menu-list");
  container.innerHTML = "<p>Haftalık menüler yükleniyor...</p>";

  const yhId = document.getElementById("weekly-yh-select").value;

  try {
    const menus = await apiRequest(`/menus/weekly?yemekhane_id=${yhId}`);
    if (menus.length === 0) {
      container.innerHTML = "<p>Haftalık menü bulunamadı.</p>";
      return;
    }

    let html = '<div class="grid-2">';
    menus.forEach(m => {
      const baseFiyat = Number(currentUser?.rol === "ogrenci" ? m.ogrenci_fiyati : m.personel_fiyati);
      const yarimFiyat = calculateHalfPortionPrice(baseFiyat);
      const isPast = Boolean(m.sure_gecti_mi);
      const isFull = Number(m.kalan_kapasite) <= 0;
      const allowHalf = isHalfPortionAllowed(m);

      // Haftalık yanıtta alerjen bilgisi varsa göster
      const weeklyAllergens = Array.isArray(m.tum_alerjenler)
        ? m.tum_alerjenler
        : (Array.isArray(m.alerjenler) ? m.alerjenler : []);
      let weeklyAllergenHtml = "";
      if (weeklyAllergens.length > 0) {
        const pills = weeklyAllergens.map(a => {
          const isMatch = userAllergenNames.includes(a);
          return `<span class="badge ${isMatch ? 'badge-allergen-match' : 'badge-allergen'}">${escapeHtml(a)}</span>`;
        }).join("");
        weeklyAllergenHtml = `<div class="badge-group">${pills}</div>`;
      }

      html += `
        <div class="schedule-card">
          <div>
            <div class="row-between" style="align-items: flex-start;">
              <strong>${escapeHtml(m.tarih)} - ${escapeHtml(m.ogun_adi)}</strong>
              <span class="badge ${isFull ? 'badge-allergen' : 'badge-veg'}">
                ${Number(m.kalan_kapasite)} Boş Yer
              </span>
            </div>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin: 6px 0;">
              Son Saat: ${escapeHtml(m.ogun_son_saat)}
            </p>
            <p style="font-size: 0.9rem; margin: 10px 0;">${escapeHtml(m.yemek_listesi) || 'Yemek bilgisi yok'}</p>
            ${weeklyAllergenHtml}
          </div>
          <div>
            <div style="margin-bottom: 8px;">
              <select id="weekly-portion-${Number(m.menu_id)}" style="width: 100%; padding: 6px 8px; font-size: 0.85rem;" onchange="updateWeeklyCardPrice(${Number(m.menu_id)}, ${baseFiyat}, ${yarimFiyat})">
                <option value="tam">Tam Porsiyon (${baseFiyat.toFixed(2)} TL)</option>
                ${allowHalf ? `<option value="yarim">Yarım Porsiyon (%60) (${yarimFiyat.toFixed(2)} TL)</option>` : ''}
              </select>
              ${!allowHalf ? '<div class="portion-note">Kahvaltıda yalnızca tam porsiyon sunulmaktadır.</div>' : ''}
            </div>
            <div id="weekly-price-${Number(m.menu_id)}" style="font-weight: 700; color: var(--primary); margin-bottom: 8px;">
              ${baseFiyat.toFixed(2)} TL
            </div>
            <button type="button" class="btn btn-primary btn-sm" style="width: 100%;"
              ${(isPast || isFull) ? 'disabled' : ''}
              onclick="handleBookReservationFromWeekly(${Number(m.menu_id)}, ${allowHalf})">
              ${isPast ? 'Süresi Doldu' : (isFull ? 'Kapasite Dolu' : 'Rezervasyon Yap')}
            </button>
          </div>
        </div>
      `;
    });
    html += '</div>';
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = "<p style='color: var(--danger);'>Haftalık menüler yüklenirken hata oluştu.</p>";
  }
}

function updateWeeklyCardPrice(menuId, baseFiyat, yarimFiyat) {
  const sel = document.getElementById(`weekly-portion-${menuId}`);
  const priceEl = document.getElementById(`weekly-price-${menuId}`);
  if (!sel || !priceEl) return;
  const price = sel.value === "yarim" ? yarimFiyat : baseFiyat;
  priceEl.textContent = `${price.toFixed(2)} TL`;
}

async function handleBookReservationFromWeekly(menuId, allowHalf = true) {
  const sel = document.getElementById(`weekly-portion-${menuId}`);
  const portion = allowHalf && sel ? sel.value : "tam";
  await handleBookReservation(menuId, portion, "weekly");
}

// Rezervasyon oluşturma
async function handleBookReservation(menuId, porsiyon = "tam", source = null) {
  try {
    const res = await apiRequest("/reservations", "POST", { menu_id: menuId, porsiyon: porsiyon });
    showToast(res.message, "success");
    // Rezervasyon sonrası güncel bakiyeyi header'a yaz
    document.getElementById("user-balance").textContent = `${Number(res.guncel_bakiye).toFixed(2)} TL`;
    if (currentUser) currentUser.bakiye = res.guncel_bakiye;

    const isWeeklyActive = source === "weekly" || document.getElementById("screen-weekly")?.classList.contains("active");
    const isTodayActive = source === "daily" || document.getElementById("screen-today")?.classList.contains("active");
    if (isWeeklyActive) {
      await loadWeeklyMenus();
    } else if (isTodayActive) {
      await loadDailyMenu();
    }
  } catch (err) {
    // Hata mesajı apiRequest içinde toast ile gösterildi
  }
}

// Rezervasyonlarım
async function loadMyReservations() {
  const container = document.getElementById("reservations-list");
  container.innerHTML = "<p>Rezervasyonlarınız yükleniyor...</p>";

  try {
    const rezs = await apiRequest("/reservations");
    if (rezs.length === 0) {
      container.innerHTML = "<p>Henüz bir rezervasyonunuz bulunmuyor.</p>";
      return;
    }

    let html = "";
    rezs.forEach(r => {
      let statusBadge = "";
      if (r.durum === "aktif") statusBadge = '<span class="badge badge-veg">Aktif</span>';
      else if (r.durum === "kullanildi") statusBadge = '<span class="badge badge-info">Kullanıldı</span>';
      else statusBadge = '<span class="badge badge-allergen">İptal Edildi</span>';

      const portionBadge = r.porsiyon === "yarim"
        ? '<span class="badge badge-info">Yarım Porsiyon (%60)</span>'
        : '<span class="badge" style="background: #e2e8f0; color: #334155;">Tam Porsiyon</span>';

      html += `
        <div class="card" style="margin-bottom: 12px; padding: 15px;">
          <div class="row-between" style="margin-bottom: 8px;">
            <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 6px; min-width: 0;">
              <strong>${escapeHtml(r.tarih)} - ${escapeHtml(r.yemekhane_adi)} (${escapeHtml(r.ogun_adi)})</strong>
              ${portionBadge}
            </div>
            ${statusBadge}
          </div>
          <p style="font-size: 0.85rem; color: var(--text-muted);">${escapeHtml(r.yemek_listesi) || ''}</p>
          <div class="row-between" style="margin-top: 10px;">
            <span style="font-weight: 700; color: var(--primary); white-space: nowrap;">${Number(r.ucret).toFixed(2)} TL</span>
            <div class="action-row" style="gap: 8px;">
              ${r.iptal_edilebilir_mi ? `
                <button type="button" class="btn btn-danger btn-sm" onclick="handleCancelReservation(${Number(r.id)})">
                  İptal Et
                </button>
              ` : ''}
              ${(r.durum === 'kullanildi' && !r.degerlendirildi_mi) ? `
                <button type="button" class="btn btn-primary btn-sm" onclick="openReviewModal(${Number(r.menu_id)})">
                  Değerlendir
                </button>
              ` : ''}
            </div>
          </div>
        </div>
      `;
    });
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = "<p style='color: var(--danger);'>Rezervasyonlar yüklenemedi.</p>";
  }
}

async function handleCancelReservation(rezId) {
  if (!confirm("Rezervasyonunuzu iptal etmek istediğinize emin misiniz? Ücret bakiyenize iade edilecektir.")) return;
  try {
    const res = await apiRequest(`/reservations/${rezId}/cancel`, "POST");
    showToast(res.message, "success");
    document.getElementById("user-balance").textContent = `${Number(res.guncel_bakiye).toFixed(2)} TL`;
    if (currentUser) currentUser.bakiye = res.guncel_bakiye;
    await loadMyReservations();
  } catch (err) {}
}

// Bakiye ve Hareket Geçmişi
async function loadBalanceAndHistory() {
  try {
    const data = await apiRequest("/balance");
    document.getElementById("balance-current-display").textContent = `${Number(data.guncel_bakiye).toFixed(2)} TL`;
    document.getElementById("user-balance").textContent = `${Number(data.guncel_bakiye).toFixed(2)} TL`;
    if (currentUser) currentUser.bakiye = data.guncel_bakiye;

    const list = document.getElementById("balance-history-list");
    if (data.hareketler.length === 0) {
      list.innerHTML = "<p>Henüz bakiye hareketi bulunmuyor.</p>";
      return;
    }

    let html = '<ul class="dish-list">';
    data.hareketler.forEach(h => {
      const isPositive = Number(h.miktar) > 0;
      const color = isPositive ? "var(--success)" : "var(--danger)";
      const sign = isPositive ? "+" : "";

      html += `
        <li class="dish-item">
          <div class="dish-info">
            <strong>${escapeHtml(h.aciklama)}</strong>
            <span class="dish-category">${escapeHtml(new Date(h.tarih).toLocaleString('tr-TR'))}</span>
          </div>
          <span class="balance-amount" style="font-weight: 700; color: ${color};">${sign}${Number(h.miktar).toFixed(2)} TL</span>
        </li>
      `;
    });
    html += '</ul>';
    list.innerHTML = html;
  } catch (err) {}
}

async function handleTopUp(amount) {
  try {
    const res = await apiRequest("/balance/topup", "POST", { miktar: amount });
    showToast(res.message, "success");
    await loadBalanceAndHistory();
  } catch (err) {}
}

// Değerlendirme İşlemleri
function openReviewModal(menuId) {
  document.getElementById("review-menu-id").value = menuId;
  showScreen("screen-review");
  loadMenuReviews(menuId);
}

async function loadMenuReviews(menuId) {
  const container = document.getElementById("menu-reviews-list");
  container.innerHTML = "<p>Değerlendirmeler yükleniyor...</p>";
  try {
    const revs = await apiRequest(`/reviews/${menuId}`);
    if (revs.length === 0) {
      container.innerHTML = "<p>Bu menüye henüz değerlendirme yapılmamış.</p>";
      return;
    }
    let html = "";
    revs.forEach(r => {
      const puan = Math.max(0, Math.min(5, parseInt(r.puan, 10) || 0));
      html += `
        <div class="card" style="margin-bottom: 10px; padding: 12px;">
          <div class="row-between" style="gap: 6px;">
            <strong>${escapeHtml(r.kullanici_ad_soyad)}</strong>
            <span style="color: #d97706; font-weight: 700; white-space: nowrap;">${puan} / 5</span>
          </div>
          <p style="margin-top: 6px; font-size: 0.9rem; word-break: break-word;">${escapeHtml(r.yorum) || ''}</p>
        </div>
      `;
    });
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = "<p>Değerlendirmeler alınamadı.</p>";
  }
}

async function handleSendReview(e) {
  e.preventDefault();
  const menuId = parseInt(document.getElementById("review-menu-id").value, 10);
  const puan = parseInt(document.getElementById("review-rating").value, 10);
  const yorum = document.getElementById("review-comment").value;

  try {
    const res = await apiRequest("/reviews", "POST", { menu_id: menuId, puan, yorum });
    showToast(res.message, "success");
    document.getElementById("review-comment").value = "";
    await loadMenuReviews(menuId);
  } catch (err) {}
}

// Alerjen Tercihleri
async function loadUserAllergenNames() {
  if (!currentToken) return;
  try {
    const data = await apiRequest("/auth/allergens");
    allSystemAllergens = data.tum_alerjenler || [];
    userAllergenIds = data.secili_alerjenler || [];
    userAllergenNames = allSystemAllergens
      .filter(a => userAllergenIds.includes(a.id))
      .map(a => a.ad);
  } catch (e) {
    if (e && e._handled401) throw e;
    console.error("Alerjenler yüklenemedi:", e);
  }
}

async function loadAllergensScreen() {
  const container = document.getElementById("allergens-checkbox-list");
  container.innerHTML = "<p>Alerjen listesi yükleniyor...</p>";

  try {
    const data = await apiRequest("/auth/allergens");
    allSystemAllergens = data.tum_alerjenler || [];
    userAllergenIds = data.secili_alerjenler || [];
    userAllergenNames = allSystemAllergens
      .filter(a => userAllergenIds.includes(a.id))
      .map(a => a.ad);

    if (allSystemAllergens.length === 0) {
      container.innerHTML = "<p>Sistemde tanımlı alerjen bulunmuyor.</p>";
      return;
    }

    let html = "";
    allSystemAllergens.forEach(a => {
      const isChecked = userAllergenIds.includes(a.id);
      html += `
        <label style="display: flex; align-items: center; gap: 10px; padding: 12px 14px; margin-bottom: 0; background: #ffffff; border: 1.5px solid ${isChecked ? 'var(--primary)' : 'var(--border)'}; border-radius: 8px; cursor: pointer; transition: all 0.15s ease;">
          <input type="checkbox" value="${Number(a.id)}" ${isChecked ? 'checked' : ''} class="allergen-chk" onchange="this.parentElement.style.borderColor = this.checked ? 'var(--primary)' : 'var(--border)'">
          <span style="font-weight: 600; font-size: 0.9rem; color: var(--text);">${escapeHtml(a.ad)}</span>
        </label>
      `;
    });
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = "<p style='color: var(--danger);'>Alerjenler yüklenirken bir hata oluştu.</p>";
  }
}

async function saveUserAllergens() {
  const checkboxes = document.querySelectorAll(".allergen-chk:checked");
  const selectedIds = Array.from(checkboxes).map(cb => parseInt(cb.value, 10));

  try {
    const res = await apiRequest("/auth/allergens", "POST", { alerjen_ids: selectedIds });
    showToast(res.message, "success");
    await loadUserAllergenNames();
  } catch (err) {}
}

// Yönetici Paneli
function resolveYemekhaneId(statRow) {
  if (statRow && statRow.yemekhane_id) return Number(statRow.yemekhane_id);
  const name = (statRow?.yemekhane_adi || "").trim();
  const select = document.getElementById("admin-yh-select");
  if (select) {
    const match = Array.from(select.options).find(opt => opt.textContent.trim() === name);
    if (match) return Number(match.value);
  }
  const fallbackMap = {
    "Merkez Yemekhanesi": 1,
    "Mühendislik Yemekhanesi": 2
  };
  return fallbackMap[name] || null;
}

function resolveOgunId(statRow) {
  if (statRow && statRow.ogun_id) return Number(statRow.ogun_id);
  const name = (statRow?.ogun_adi || "").trim();
  const fallbackMap = {
    "Kahvaltı": 1,
    "Öğle": 2,
    "Akşam": 3
  };
  return fallbackMap[name] || null;
}

async function loadAdminDashboard() {
  cancelEditMenu();
  await Promise.all([loadDishesForAdmin(), loadAdminStats()]);
}

async function loadAdminStats() {
  const container = document.getElementById("admin-stats-table");
  container.innerHTML = "<p>İstatistikler yükleniyor...</p>";

  try {
    const stats = await apiRequest("/admin/stats");
    adminStatsById = {};
    if (!Array.isArray(stats) || stats.length === 0) {
      container.innerHTML = "<p>Henüz menü istatistiği bulunmuyor.</p>";
      return;
    }

    let html = `
      <div class="table-responsive">
        <table class="admin-table">
          <thead>
            <tr style="background: var(--primary-light); text-align: left;">
              <th>Tarih/Öğün</th>
              <th>Yemekhane</th>
              <th>Doluluk</th>
              <th>Ort. Puan</th>
              <th>İşlem</th>
            </tr>
          </thead>
          <tbody>
    `;
    stats.forEach(s => {
      adminStatsById[s.menu_id] = s;
      html += `
        <tr style="border-bottom: 1px solid var(--border);">
          <td>${escapeHtml(s.tarih)} (${escapeHtml(s.ogun_adi)})</td>
          <td>${escapeHtml(s.yemekhane_adi)}</td>
          <td>%${Number(s.doluluk_orani)} (${Number(s.aktif_rezervasyon_sayisi)}/${Number(s.toplam_kapasite)})</td>
          <td style="font-weight: 700; color: #d97706;">${Number(s.ortalama_puan)} / 5 (${Number(s.degerlendirme_sayisi)})</td>
          <td>
            <button type="button" class="btn btn-primary btn-sm" style="white-space: nowrap;" onclick="openEditMenu(${Number(s.menu_id)})">
              Düzenle
            </button>
          </td>
        </tr>
      `;
    });
    html += "</tbody></table></div>";
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = "<p>İstatistikler alınamadı.</p>";
  }
}

async function loadDishesForAdmin() {
  const select = document.getElementById("admin-dishes-select");
  const editContainer = document.getElementById("admin-edit-dishes");
  try {
    const dishes = await apiRequest("/admin/dishes");
    adminDishesCache = Array.isArray(dishes) ? dishes : [];

    if (select) {
      select.innerHTML = "";
      adminDishesCache.forEach(d => {
        const opt = document.createElement("option");
        opt.value = d.id;
        opt.textContent = `[${d.kategori_adi}] ${d.ad} (${d.kalori} kcal)`;
        select.appendChild(opt);
      });
    }

    if (editContainer) {
      editContainer.innerHTML = "";
      adminDishesCache.forEach(d => {
        const lbl = document.createElement("label");
        lbl.className = "dish-checkbox-item";

        const chk = document.createElement("input");
        chk.type = "checkbox";
        chk.className = "admin-edit-dish-chk";
        chk.value = String(d.id);

        const span = document.createElement("span");
        span.textContent = `[${d.kategori_adi}] ${d.ad} (${d.kalori} kcal)`;

        lbl.appendChild(chk);
        lbl.appendChild(span);
        editContainer.appendChild(lbl);
      });
    }
  } catch (err) {}
}

async function openEditMenu(menuId) {
  const stat = adminStatsById[menuId];
  if (!stat) return;

  const yhId = resolveYemekhaneId(stat);
  const ogunId = resolveOgunId(stat);
  if (!yhId || !ogunId) {
    showToast("Menü bilgileri çözümlenemedi.", "error");
    return;
  }

  if (adminDishesCache.length === 0) {
    await loadDishesForAdmin();
  }

  try {
    const menu = await apiRequest(`/menus/today?yemekhane_id=${yhId}&tarih=${encodeURIComponent(stat.tarih)}&ogun_id=${ogunId}`);
    const resolvedId = Number(menu.menu_id || menuId);

    document.getElementById("admin-edit-menu-id").value = String(resolvedId);
    document.getElementById("admin-edit-title").textContent = `Menü Düzenle (#${resolvedId})`;
    document.getElementById("admin-edit-meta").textContent =
      `${menu.yemekhane_adi} • ${menu.tarih} • ${menu.ogun_adi} • Kapasite: ${menu.yemekhane_kapasitesi} kişi (salt okunur)`;
    document.getElementById("admin-edit-price-student").value = menu.ogrenci_fiyati;
    document.getElementById("admin-edit-price-staff").value = menu.personel_fiyati;

    const selectedDishIds = new Set((menu.yemekler || []).map(y => Number(y.id)));
    document.querySelectorAll(".admin-edit-dish-chk").forEach(chk => {
      chk.checked = selectedDishIds.has(Number(chk.value));
    });

    const editCard = document.getElementById("admin-edit-card");
    if (editCard) {
      editCard.style.display = "block";
      editCard.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  } catch (err) {}
}

function cancelEditMenu() {
  const editCard = document.getElementById("admin-edit-card");
  if (editCard) editCard.style.display = "none";

  const idEl = document.getElementById("admin-edit-menu-id");
  if (idEl) idEl.value = "";

  const metaEl = document.getElementById("admin-edit-meta");
  if (metaEl) metaEl.textContent = "";

  document.querySelectorAll(".admin-edit-dish-chk").forEach(chk => {
    chk.checked = false;
  });
}

async function handleUpdateMenu(e) {
  e.preventDefault();
  const menuId = parseInt(document.getElementById("admin-edit-menu-id").value, 10);
  const ogrenciFiyat = parseFloat(document.getElementById("admin-edit-price-student").value);
  const personelFiyat = parseFloat(document.getElementById("admin-edit-price-staff").value);
  const yemekIds = Array.from(document.querySelectorAll(".admin-edit-dish-chk:checked"))
    .map(cb => parseInt(cb.value, 10));

  if (!menuId) {
    showToast("Düzenlenecek menü seçilmedi.", "error");
    return;
  }
  if (Number.isNaN(ogrenciFiyat) || Number.isNaN(personelFiyat) || ogrenciFiyat <= 0 || personelFiyat <= 0) {
    showToast("Lütfen sıfırdan büyük geçerli fiyatlar girin.", "error");
    return;
  }
  if (yemekIds.length === 0) {
    showToast("En az 1 yemek seçmelisiniz.", "error");
    return;
  }

  try {
    const res = await apiRequest(`/admin/menus/${menuId}`, "PUT", {
      ogrenci_fiyati: ogrenciFiyat,
      personel_fiyati: personelFiyat,
      yemek_ids: yemekIds
    });
    showToast(res.message, "success");
    cancelEditMenu();
    await loadAdminStats();
  } catch (err) {}
}

async function handleCreateMenu(e) {
  e.preventDefault();
  const yemekhaneId = parseInt(document.getElementById("admin-yh-select").value, 10);
  const tarih = document.getElementById("admin-menu-date").value;
  const ogunId = parseInt(document.getElementById("admin-ogun-select").value, 10);
  const ogrenciFiyat = parseFloat(document.getElementById("admin-price-student").value);
  const personelFiyat = parseFloat(document.getElementById("admin-price-staff").value);

  const selectedOptions = Array.from(document.getElementById("admin-dishes-select").selectedOptions);
  const yemekIds = selectedOptions.map(o => parseInt(o.value, 10));

  if (!tarih) {
    showToast("Lütfen geçerli bir tarih seçiniz.", "error");
    return;
  }
  if (Number.isNaN(ogrenciFiyat) || Number.isNaN(personelFiyat) || ogrenciFiyat <= 0 || personelFiyat <= 0) {
    showToast("Lütfen sıfırdan büyük geçerli fiyatlar girin.", "error");
    return;
  }
  if (yemekIds.length === 0) {
    showToast("En az 1 yemek seçmelisiniz.", "error");
    return;
  }

  try {
    const res = await apiRequest("/admin/menus", "POST", {
      yemekhane_id: yemekhaneId,
      tarih: tarih,
      ogun_id: ogunId,
      ogrenci_fiyati: ogrenciFiyat,
      personel_fiyati: personelFiyat,
      yemek_ids: yemekIds
    });
    showToast(res.message, "success");
    Array.from(document.getElementById("admin-dishes-select").options).forEach(opt => {
      opt.selected = false;
    });
    await loadAdminStats();
  } catch (err) {}
}

// Sayfa Yüklendiğinde Başlat
document.addEventListener("DOMContentLoaded", () => {
  // Bugünün yerel tarihini varsayılan yap
  const todayStr = getLocalDateString();
  const datePicker = document.getElementById("today-date-picker");
  if (datePicker) datePicker.value = todayStr;
  const adminDatePicker = document.getElementById("admin-menu-date");
  if (adminDatePicker) adminDatePicker.value = todayStr;

  initAuth();
});

