// Kampüs Yemekhane Otomasyonu - Frontend Script

const API_BASE = "/api";

// Uygulama Durumu (State)
let currentUser = null;
let currentToken = localStorage.getItem("auth_token") || null;
let userAllergenNames = []; // Kullanıcının seçtiği alerjenlerin adları
let userAllergenIds = [];   // Kullanıcının seçtiği alerjen ID'leri
let allSystemAllergens = []; // Sistemdeki tüm alerjenler

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

// API İstek Yardımcısı (Token ile birlikte)
async function apiRequest(endpoint, method = "GET", body = null) {
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
      throw new Error(data.detail || "Bir hata oluştu.");
    }
    return data;
  } catch (err) {
    showToast(err.message, "error");
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
      const user = await apiRequest("/auth/me");
      setUserState(user, currentToken);
      await loadUserAllergenNames();
      showScreen("screen-today");
    } catch {
      logout();
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
    authNav.style.display = "flex";
    document.getElementById("user-name").textContent = `${user.ad} ${user.soyad}`;
    document.getElementById("user-role").textContent = user.rol;
    document.getElementById("user-balance").textContent = `${user.bakiye.toFixed(2)} TL`;
    
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
    showToast(`Hoş geldiniz, ${res.kullanici.ad}!`, "success");
    showScreen("screen-today");
  } catch (err) {
    // Hata mesajı showToast ile gösterildi
  }
}

function handleQuickFill(email) {
  document.getElementById("login-email").value = email;
  document.getElementById("login-password").value = "password123";
}

async function logout() {
  try {
    await apiRequest("/auth/logout", "POST");
  } catch {}
  setUserState(null, null);
  showToast("Oturum kapatıldı.", "info");
  showScreen("screen-login");
}

// Günün Menüsü
async function loadDailyMenu() {
  const container = document.getElementById("daily-menu-content");
  container.innerHTML = "<p>Menü yükleniyor...</p>";

  const yhId = document.getElementById("today-yh-select").value;
  const ogunId = document.getElementById("today-ogun-select").value;
  const tarih = document.getElementById("today-date-picker").value || new Date().toISOString().split("T")[0];

  try {
    const menu = await apiRequest(`/menus/today?yemekhane_id=${yhId}&tarih=${tarih}&ogun_id=${ogunId}`);
    
    // Kullanıcı fiyatını belirle
    const tamFiyat = currentUser?.rol === "ogrenci" ? menu.ogrenci_fiyati : menu.personel_fiyati;
    const yarimFiyat = Math.round(tamFiyat * 0.60 * 100) / 100;
    const isKahvalti = menu.ogun_id === 1 || menu.ogun_adi === "Kahvaltı";

    // Alerjen kontrolü
    const matchingAllergens = (menu.tum_alerjenler || []).filter(a => userAllergenNames.includes(a));
    let allergenAlertHtml = "";
    if (matchingAllergens.length > 0) {
      allergenAlertHtml = `
        <div style="background: #fef2f2; border: 1.5px solid #ef4444; border-radius: 8px; padding: 12px 16px; margin-bottom: 15px; color: #991b1b;">
          <div style="font-weight: 700; display: flex; align-items: center; gap: 6px; font-size: 0.95rem;">
            <span>⚠️ DİKKAT: Alerjen Uyarısı!</span>
          </div>
          <p style="font-size: 0.85rem; margin-top: 5px; line-height: 1.4;">
            Bu menü profilinizde kayıtlı alerjenlerinizden <strong>${matchingAllergens.join(', ')}</strong> içermektedir. Sağlığınız için tüketmeden önce lütfen dikkat ediniz!
          </p>
        </div>
      `;
    }
    
    let dishesHtml = "";
    menu.yemekler.forEach(y => {
      dishesHtml += `
        <li class="dish-item">
          <div>
            <span class="dish-name">${y.ad}</span>
            <span class="dish-category">${y.kategori_adi}</span>
          </div>
          <span class="dish-cal">${y.kalori} kcal</span>
        </li>
      `;
    });

    let allergenBadges = "";
    menu.tum_alerjenler.forEach(a => {
      const isUserAllergen = userAllergenNames.includes(a);
      allergenBadges += `<span class="badge ${isUserAllergen ? 'badge-allergen' : 'badge-allergen'}" style="${isUserAllergen ? 'border: 1.5px solid #dc2626; font-weight: 700;' : ''}">⚠️ ${a}</span>`;
    });

    const cacheBadge = menu.kaynak === "cache" 
      ? '<span class="badge badge-info" title="Redis önbellekten yüklendi">⚡ Redis Önbellek</span>' 
      : '<span class="badge badge-veg" title="Veritabanından okundu">🗄️ MySQL Replica</span>';

    // Porsiyon seçimi
    let portionSelectorHtml = "";
    if (isKahvalti) {
      portionSelectorHtml = `
        <div style="margin: 15px 0; padding: 12px; background: #f8fafc; border: 1px solid var(--border); border-radius: 8px;">
          <span style="font-size: 0.8rem; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 8px; text-transform: uppercase;">Porsiyon Seçimi</span>
          <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; margin-bottom: 6px;">
            <input type="radio" name="daily-portion" value="tam" checked onchange="updateDailyPriceDisplay(${tamFiyat})">
            <span><strong>Tam Porsiyon</strong> - ${tamFiyat.toFixed(2)} TL</span>
          </label>
          <label style="display: flex; align-items: center; gap: 8px; color: var(--text-muted); cursor: not-allowed; font-size: 0.85rem;">
            <input type="radio" name="daily-portion" value="yarim" disabled>
            <span><strong>Yarım Porsiyon (%60)</strong> - <em>Kahvaltıda yarım porsiyon seçeneği bulunmamaktadır.</em></span>
          </label>
        </div>
      `;
    } else {
      portionSelectorHtml = `
        <div style="margin: 15px 0; padding: 12px; background: #f8fafc; border: 1px solid var(--border); border-radius: 8px;">
          <span style="font-size: 0.8rem; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 8px; text-transform: uppercase;">Porsiyon Seçimi</span>
          <div style="display: flex; gap: 20px; flex-wrap: wrap;">
            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
              <input type="radio" name="daily-portion" value="tam" checked onchange="updateDailyPriceDisplay(${tamFiyat})">
              <span><strong>Tam Porsiyon</strong> (${tamFiyat.toFixed(2)} TL)</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
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
          <span>${menu.yemekhane_adi} - ${menu.ogun_adi} Menüsü</span>
          ${cacheBadge}
        </div>
        <p style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 10px;">
          📅 ${menu.tarih} &nbsp;|&nbsp; ⏰ Son Rezervasyon: ${menu.ogun_son_saat}
        </p>

        <ul class="dish-list">${dishesHtml}</ul>

        <div style="margin: 15px 0;">
          <strong>Toplam Kalori:</strong> ${menu.toplam_kalori} kcal
        </div>

        <div class="badge-group">
          ${menu.vejetaryen_mi ? '<span class="badge badge-veg">🌱 Vejetaryen Menü</span>' : ''}
          ${allergenBadges}
        </div>

        ${portionSelectorHtml}

        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px;">
          <div>
            <span style="font-size: 0.85rem; color: var(--text-muted);">Ödenecek Ücret (${currentUser?.rol}):</span>
            <div id="daily-price-display" style="font-size: 1.4rem; font-weight: 800; color: var(--primary);">${tamFiyat.toFixed(2)} TL</div>
          </div>
          <div style="text-align: right;">
            <span style="font-size: 0.85rem; color: var(--text-muted);">Kalan Kontenjan:</span>
            <div style="font-weight: 600;">${menu.kalan_kapasite} / ${menu.yemekhane_kapasitesi}</div>
          </div>
        </div>

        <button class="btn btn-primary" style="margin-top: 15px;" onclick="handleBookReservationFromDaily(${menu.menu_id})">
          Bu Menüye Rezervasyon Yap
        </button>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="card"><p style="color: var(--danger);">Bu tarih ve öğün için menü kaydı bulunamadı.</p></div>`;
  }
}

function updateDailyPriceDisplay(amount) {
  const el = document.getElementById("daily-price-display");
  if (el) el.textContent = `${parseFloat(amount).toFixed(2)} TL`;
}

async function handleBookReservationFromDaily(menuId) {
  const portionInput = document.querySelector('input[name="daily-portion"]:checked');
  const portion = portionInput ? portionInput.value : "tam";
  await handleBookReservation(menuId, portion);
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
      const baseFiyat = currentUser?.rol === "ogrenci" ? m.ogrenci_fiyati : m.personel_fiyati;
      const yarimFiyat = Math.round(baseFiyat * 0.60 * 100) / 100;
      const isPast = m.sure_gecti_mi;
      const isFull = m.kalan_kapasite <= 0;
      const isKahvalti = m.ogun_adi === "Kahvaltı";

      html += `
        <div class="schedule-card">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
              <strong>${m.tarih} - ${m.ogun_adi}</strong>
              <span class="badge ${isFull ? 'badge-allergen' : 'badge-veg'}">
                ${m.kalan_kapasite} Boş Yer
              </span>
            </div>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin: 6px 0;">
              ⏰ Son Saat: ${m.ogun_son_saat}
            </p>
            <p style="font-size: 0.9rem; margin: 10px 0;">${m.yemek_listesi || 'Yemek bilgisi yok'}</p>
          </div>
          <div>
            <div style="margin-bottom: 8px;">
              <select id="weekly-portion-${m.menu_id}" style="width: 100%; padding: 5px 8px; font-size: 0.85rem;" onchange="updateWeeklyCardPrice(${m.menu_id}, ${baseFiyat}, ${yarimFiyat})">
                <option value="tam">Tam Porsiyon (${baseFiyat.toFixed(2)} TL)</option>
                ${!isKahvalti ? `<option value="yarim">Yarım Porsiyon (%60) (${yarimFiyat.toFixed(2)} TL)</option>` : ''}
              </select>
            </div>
            <div id="weekly-price-${m.menu_id}" style="font-weight: 700; color: var(--primary); margin-bottom: 8px;">
              ${baseFiyat.toFixed(2)} TL
            </div>
            <button class="btn btn-primary btn-sm" style="width: 100%;" 
              ${(isPast || isFull) ? 'disabled' : ''} 
              onclick="handleBookReservationFromWeekly(${m.menu_id})">
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

async function handleBookReservationFromWeekly(menuId) {
  const sel = document.getElementById(`weekly-portion-${menuId}`);
  const portion = sel ? sel.value : "tam";
  await handleBookReservation(menuId, portion);
}

// Rezervasyon Yapma (Stored Procedure Çağrısı - porsiyon parametresi ile)
async function handleBookReservation(menuId, porsiyon = "tam") {
  try {
    const res = await apiRequest("/reservations", "POST", { menu_id: menuId, porsiyon: porsiyon });
    showToast(res.message, "success");
    // Anlık güncel bakiyeyi header'a yansıt (Replication Lag yok!)
    document.getElementById("user-balance").textContent = `${res.guncel_bakiye.toFixed(2)} TL`;
    currentUser.bakiye = res.guncel_bakiye;
    loadDailyMenu();
  } catch (err) {
    // Hata mesajı (Örn: "Bakiye yetersiz." veya "Yemekhane kapasitesi dolmuştur.") gösterildi
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
        ? '<span class="badge badge-info" style="margin-left: 6px;">Yarım Porsiyon (%60)</span>'
        : '<span class="badge" style="background: #e2e8f0; color: #334155; margin-left: 6px;">Tam Porsiyon</span>';

      html += `
        <div class="card" style="margin-bottom: 12px; padding: 15px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 4px;">
              <strong>${r.tarih} - ${r.yemekhane_adi} (${r.ogun_adi})</strong>
              ${portionBadge}
            </div>
            ${statusBadge}
          </div>
          <p style="font-size: 0.85rem; color: var(--text-muted);">${r.yemek_listesi || ''}</p>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
            <span style="font-weight: 700; color: var(--primary);">${r.ucret.toFixed(2)} TL</span>
            <div>
              ${r.iptal_edilebilir_mi ? `
                <button class="btn btn-danger btn-sm" onclick="handleCancelReservation(${r.id})">
                  İptal Et
                </button>
              ` : ''}
              ${(r.durum === 'kullanildi' && !r.degerlendirildi_mi) ? `
                <button class="btn btn-primary btn-sm" onclick="openReviewModal(${r.menu_id})">
                  ⭐ Değerlendir
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
    document.getElementById("user-balance").textContent = `${res.guncel_bakiye.toFixed(2)} TL`;
    currentUser.bakiye = res.guncel_bakiye;
    loadMyReservations();
  } catch (err) {}
}

// Bakiye ve Hareket Geçmişi
async function loadBalanceAndHistory() {
  try {
    const data = await apiRequest("/balance");
    document.getElementById("balance-current-display").textContent = `${data.guncel_bakiye.toFixed(2)} TL`;
    document.getElementById("user-balance").textContent = `${data.guncel_bakiye.toFixed(2)} TL`;
    currentUser.bakiye = data.guncel_bakiye;

    const list = document.getElementById("balance-history-list");
    if (data.hareketler.length === 0) {
      list.innerHTML = "<p>Henüz bakiye hareketi bulunmuyor.</p>";
      return;
    }

    let html = '<ul class="dish-list">';
    data.hareketler.forEach(h => {
      const isPositive = h.miktar > 0;
      const color = isPositive ? "var(--success)" : "var(--danger)";
      const sign = isPositive ? "+" : "";

      html += `
        <li class="dish-item">
          <div>
            <strong>${h.aciklama}</strong>
            <span class="dish-category">${new Date(h.tarih).toLocaleString('tr-TR')}</span>
          </div>
          <span style="font-weight: 700; color: ${color};">${sign}${h.miktar.toFixed(2)} TL</span>
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
    loadBalanceAndHistory();
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
      html += `
        <div class="card" style="margin-bottom: 10px; padding: 12px;">
          <div style="display: flex; justify-content: space-between;">
            <strong>${r.kullanici_ad_soyad}</strong>
            <span style="color: #eab308; font-weight: 700;">${'⭐'.repeat(r.puan)} (${r.puan}/5)</span>
          </div>
          <p style="margin-top: 6px; font-size: 0.9rem;">${r.yorum || ''}</p>
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
  const menuId = parseInt(document.getElementById("review-menu-id").value);
  const puan = parseInt(document.getElementById("review-rating").value);
  const yorum = document.getElementById("review-comment").value;

  try {
    const res = await apiRequest("/reviews", "POST", { menu_id: menuId, puan, yorum });
    showToast(res.message, "success");
    document.getElementById("review-comment").value = "";
    loadMenuReviews(menuId);
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
        <label style="display: flex; align-items: center; gap: 10px; padding: 12px 14px; background: #ffffff; border: 1.5px solid ${isChecked ? 'var(--primary)' : 'var(--border)'}; border-radius: 8px; cursor: pointer; transition: all 0.15s ease;">
          <input type="checkbox" value="${a.id}" ${isChecked ? 'checked' : ''} class="allergen-chk" onchange="this.parentElement.style.borderColor = this.checked ? 'var(--primary)' : 'var(--border)'">
          <span style="font-weight: 600; font-size: 0.9rem;">⚠️ ${a.ad}</span>
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
  const selectedIds = Array.from(checkboxes).map(cb => parseInt(cb.value));

  try {
    const res = await apiRequest("/auth/allergens", "POST", { alerjen_ids: selectedIds });
    showToast(res.message, "success");
    await loadUserAllergenNames();
  } catch (err) {}
}

// Yönetici Paneli
async function loadAdminDashboard() {
  loadAdminStats();
  loadDishesForAdmin();
}

async function loadAdminStats() {
  const container = document.getElementById("admin-stats-table");
  container.innerHTML = "<p>İstatistikler yükleniyor...</p>";

  try {
    const stats = await apiRequest("/admin/stats");
    let html = `
      <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
          <thead>
            <tr style="background: var(--primary-light); text-align: left;">
              <th style="padding: 8px;">Tarih/Öğün</th>
              <th style="padding: 8px;">Yemekhane</th>
              <th style="padding: 8px;">Doluluk</th>
              <th style="padding: 8px;">Ort. Puan</th>
            </tr>
          </thead>
          <tbody>
    `;
    stats.slice(0, 15).forEach(s => {
      html += `
        <tr style="border-bottom: 1px solid var(--border);">
          <td style="padding: 8px;">${s.tarih} (${s.ogun_adi})</td>
          <td style="padding: 8px;">${s.yemekhane_adi}</td>
          <td style="padding: 8px;">%${s.doluluk_orani} (${s.aktif_rezervasyon_sayisi}/${s.toplam_kapasite})</td>
          <td style="padding: 8px; font-weight: 700; color: #d97706;">⭐ ${s.ortalama_puan} (${s.degerlendirme_sayisi})</td>
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
  try {
    const dishes = await apiRequest("/admin/dishes");
    select.innerHTML = "";
    dishes.forEach(d => {
      const opt = document.createElement("option");
      opt.value = d.id;
      opt.textContent = `[${d.kategori_adi}] ${d.ad} (${d.kalori} kcal)`;
      select.appendChild(opt);
    });
  } catch (err) {}
}

async function handleCreateMenu(e) {
  e.preventDefault();
  const yemekhaneId = parseInt(document.getElementById("admin-yh-select").value);
  const tarih = document.getElementById("admin-menu-date").value;
  const ogunId = parseInt(document.getElementById("admin-ogun-select").value);
  const ogrenciFiyat = parseFloat(document.getElementById("admin-price-student").value);
  const personelFiyat = parseFloat(document.getElementById("admin-price-staff").value);

  const selectedOptions = Array.from(document.getElementById("admin-dishes-select").selectedOptions);
  const yemekIds = selectedOptions.map(o => parseInt(o.value));

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
    loadAdminStats();
  } catch (err) {}
}

// Sayfa Yüklendiğinde Başlat
document.addEventListener("DOMContentLoaded", () => {
  // Bugünün tarihini varsayılan yap
  const todayStr = new Date().toISOString().split("T")[0];
  const datePicker = document.getElementById("today-date-picker");
  if (datePicker) datePicker.value = todayStr;
  const adminDatePicker = document.getElementById("admin-menu-date");
  if (adminDatePicker) adminDatePicker.value = todayStr;

  initAuth();
});

