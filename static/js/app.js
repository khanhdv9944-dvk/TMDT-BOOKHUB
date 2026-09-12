// App State
let state = {
  currentUser: null,
  token: null,
  currentPortal: 'BUYER', // 'BUYER', 'SELLER', 'ADMIN'
  cart: [],
  categories: [],
  books: [],
  activeCategory: null,
  searchQuery: '',
  activeTab: 'home',
  productReviews: {},
  productReviewSummary: {}
};

let heroSlide = 0;
const heroSlides = [
  { tag: '✨ Sàn sách chính hãng', title: 'Khám phá tri thức,<br>đọc thử trước khi mua', desc: 'Sách giấy, Ebook và nội dung VIP được tuyển chọn từ các nhà xuất bản uy tín.' },
  { tag: '👑 Ưu đãi thành viên', title: 'Đọc Ebook không giới hạn<br>cùng BookHub VIP', desc: 'Mở khóa kho sách số và những ưu đãi riêng dành cho độc giả yêu sách.' },
  { tag: '🚚 Giao hàng tận nơi', title: 'Đặt sách hôm nay,<br>nhận sách thật nhanh', desc: 'Theo dõi đơn hàng minh bạch, hỗ trợ đổi trả và freeship từ 150.000đ.' }
];

if ('scrollRestoration' in history) {
  history.scrollRestoration = 'manual';
}

function resetPageScroll() {
  window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
  document.documentElement.scrollTop = 0;
  document.body.scrollTop = 0;
}

function navigateHome() {
  if (window.location.pathname !== '/') history.pushState({}, '', '/');
  showPublicMarketplace();
  resetPageScroll();
}

// Formatting helpers
function formatVND(amount) {
  if (!amount && amount !== 0) return '0 đ';
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
}

function showToast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = 'toast';
  
  let icon = 'ℹ️';
  if (type === 'success') icon = '✅';
  if (type === 'error') icon = '❌';
  if (type === 'warning') icon = '⚠️';

  toast.innerHTML = `<span>${icon}</span> <span>${msg}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// API Helper
async function apiCall(endpoint, options = {}) {
  const headers = options.headers || {};
  if (state.token) {
    headers['Authorization'] = `Bearer ${state.token}`;
  }
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  try {
    const res = await fetch(endpoint, {
      ...options,
      headers
    });
    
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Có lỗi xảy ra khi gọi máy chủ');
    }
    return data;
  } catch (err) {
    showToast(err.message, 'error');
    throw err;
  }
}

// Initialize App
document.addEventListener('DOMContentLoaded', async () => {
  loadCartFromStorage();
  renderMiniCart();
  initDarkMode();
  renderHeroSlide();
  initFlashSaleCountdown();
  window.addEventListener('popstate', handleBookHistoryNavigation);
  document.addEventListener('click', event => {
    const target = event.target;
    const clickedOnCatalogTrigger =
      target.closest('.catalog-menu-trigger') ||
      target.closest('.storefront-category-button') ||
      target.closest('.public-nav-link') ||
      target.closest('#catalog-mega-menu');

    if (!clickedOnCatalogTrigger) {
      closeCatalogMenu();
    }
  });

  const savedToken = localStorage.getItem('bookhub_token');
  const savedUser = localStorage.getItem('bookhub_user');

  if (savedToken && savedUser) {
    try {
      state.token = savedToken;
      state.currentUser = JSON.parse(savedUser);
      await enterMainApp();
    } catch (e) {
      localStorage.removeItem('bookhub_token');
      localStorage.removeItem('bookhub_user');
      state.currentUser = null;
      state.token = null;
      showPublicMarketplace();
    }
  } else {
    state.currentUser = null;
    state.token = null;
    showPublicMarketplace();
  }
  if (window.location.pathname.match(/^\/books\/\d+$/)) handleBookHistoryNavigation();
});

function handleBookHistoryNavigation() {
  const match = window.location.pathname.match(/^\/books\/(\d+)$/);
  if (match) openBookDetail(Number(match[1]), false);
  else if (document.getElementById('book-detail-root')?.style.display === 'block') showPublicMarketplace();
}

// Cart Management
function loadCartFromStorage() {
  const saved = localStorage.getItem('bookhub_cart');
  if (saved) {
    try {
      state.cart = JSON.parse(saved);
    } catch(e) { state.cart = []; }
  }
  updateCartBadge();
}

function saveCartToStorage() {
  localStorage.setItem('bookhub_cart', JSON.stringify(state.cart));
  updateCartBadge();
  renderMiniCart();
}

function requireLoginForAction(actionName, callback) {
  if (!state.currentUser) {
    const message = document.getElementById('login-required-message');
    if (message) {
      message.textContent = `Bạn cần đăng nhập để sử dụng chức năng này.${actionName ? `\n${actionName}` : ''}`;
    }
    const modal = document.getElementById('login-required-modal');
    if (modal) modal.classList.add('open');
    showToast('Bạn cần đăng nhập để sử dụng chức năng này.', 'warning');
    return;
  }

  if (callback) callback();
}

function addToCart(bookId) {
  requireLoginForAction('Thêm vào giỏ hàng', () => {
    const book = state.books.find(b => b.id === bookId) || state.books.find(b => b.id === Number(bookId));
    if (!book) return;

    const existing = state.cart.find(item => item.book_id === bookId);
    if (existing) {
      existing.quantity += 1;
    } else {
      state.cart.push({
        book_id: book.id,
        title: book.title,
        price: book.discount_price || book.price,
        cover_image: book.cover_image,
        seller_id: book.seller_id,
        quantity: 1
      });
    }
    saveCartToStorage();
    renderMiniCart();
    showToast(`Đã thêm "${book.title}" vào giỏ hàng!`, 'success');
  });
}

function renderMiniCart() {
  const dropdown = document.getElementById('mini-cart-dropdown');
  if (!dropdown) return;
  if (!state.cart.length) {
    dropdown.innerHTML = '<div class="mini-cart-empty">Giỏ hàng đang trống</div>';
    return;
  }
  dropdown.innerHTML = `<div class="mini-cart-title">Giỏ hàng nhanh <strong>${state.cart.reduce((sum, item) => sum + item.quantity, 0)} sản phẩm</strong></div>${state.cart.slice(0, 3).map(item => `<div class="mini-cart-item"><img src="${item.cover_image || ''}" alt=""><div><strong>${item.title}</strong><small>${item.quantity} x ${formatVND(item.price)}</small></div></div>`).join('')}${state.cart.length > 3 ? '<small class="mini-cart-more">Xem thêm sản phẩm trong giỏ hàng</small>' : ''}<button class="btn-primary mini-cart-checkout" onclick="openCartModal()">Thanh toán</button>`;
}

function toggleDarkMode() {
  document.body.classList.toggle('dark-mode');
  const enabled = document.body.classList.contains('dark-mode');
  localStorage.setItem('bookhub_dark_mode', enabled ? '1' : '0');
  const button = document.getElementById('theme-toggle');
  if (button) button.textContent = enabled ? '☀️' : '🌙';
}

function initDarkMode() {
  if (localStorage.getItem('bookhub_dark_mode') === '1') toggleDarkMode();
}

function renderHeroSlide() {
  const slide = heroSlides[heroSlide];
  const hero = document.querySelector('.hero-banner');
  if (!hero || !slide) return;
  hero.querySelector('.hero-tag').textContent = slide.tag;
  hero.querySelector('.hero-title').innerHTML = slide.title;
  hero.querySelector('.hero-desc').textContent = slide.desc;
  const dots = document.getElementById('hero-dots');
  if (dots) dots.innerHTML = heroSlides.map((_, index) => `<button class="hero-dot ${index === heroSlide ? 'active' : ''}" onclick="setHeroSlide(${index})" aria-label="Banner ${index + 1}"></button>`).join('');
}

function changeHeroSlide(delta) {
  heroSlide = (heroSlide + delta + heroSlides.length) % heroSlides.length;
  renderHeroSlide();
}

function setHeroSlide(index) {
  heroSlide = index;
  renderHeroSlide();
}

function buyNow(bookId, quantity = 1) {
  const book = state.books.find(b => b.id === bookId) || state.books.find(b => b.id === Number(bookId));
  if (!book) return;

  if (!state.currentUser) {
    const msg = document.getElementById('login-required-message');
    if (msg) msg.textContent = 'Bạn cần đăng nhập để mua hàng. Sau khi đăng nhập, hệ thống sẽ quay lại trang Checkout của sản phẩm này.';
    const modal = document.getElementById('login-required-modal');
    if (modal) {
      modal.classList.add('open');
      const loginAction = () => {
        closeModal('login-required-modal');
        showAuthPage();
        switchAuthTab('login');
        localStorage.setItem('bookhub_pending_buy_now', JSON.stringify({ bookId, quantity }));
      };
      const primaryBtn = document.querySelector('#login-required-modal .btn-primary');
      if (primaryBtn) primaryBtn.onclick = loginAction;
      const registerBtn = document.querySelector('#login-required-modal .btn-preview');
      if (registerBtn) registerBtn.onclick = () => {
        closeModal('login-required-modal');
        showAuthPage();
        switchAuthTab('register');
        localStorage.setItem('bookhub_pending_buy_now', JSON.stringify({ bookId, quantity }));
      };
    }
    showToast('Bạn cần đăng nhập để mua hàng.', 'warning');
    return;
  }

  localStorage.setItem('bookhub_pending_buy_now', JSON.stringify({ bookId, quantity }));
  showToast(`Đang mở Checkout cho "${book.title}"...`, 'info');
  openCheckoutForSingleProduct(bookId, quantity, false);
}

async function openCheckoutForSingleProduct(bookId, quantity = 1, fromLogin = false) {
  try {
    const payload = {
      book_id: Number(bookId),
      quantity: Number(quantity),
      shipping_name: state.currentUser?.full_name || '',
      shipping_phone: state.currentUser?.phone || '',
      shipping_address: state.currentUser?.address || '',
      payment_method: 'COD'
    };

    const checkout = await apiCall('/api/orders/checkout/instant', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    localStorage.setItem('bookhub_checkout_single', JSON.stringify(checkout));
    renderSingleCheckoutPage(checkout);
    if (fromLogin) {
      showToast('Đăng nhập thành công, bạn đang quay lại Checkout.', 'success');
    }
  } catch (e) {
    console.error(e);
  }
}

function renderSingleCheckoutPage(checkout) {
  const appWrapper = document.getElementById('main-app-wrapper');
  const authPage = document.getElementById('auth-page');
  if (appWrapper) appWrapper.style.display = 'block';
  if (authPage) authPage.style.display = 'none';

  document.querySelectorAll('.portal-container').forEach(portal => {
    portal.style.display = 'none';
  });
  const successRoot = document.getElementById('order-success-root');
  if (successRoot) successRoot.style.display = 'none';

  const checkoutRoot = document.getElementById('single-checkout-root');
  if (!checkoutRoot) return;

  const subtotal = Number(checkout.subtotal || 0);
  const shippingFee = Number(checkout.shipping_fee || 0);
  const total = Number(checkout.total_amount || 0);

  checkoutRoot.innerHTML = `
    <div class="checkout-page">
      <div class="checkout-header">
        <div>
          <span class="checkout-eyebrow">BOOKHUB CHECKOUT</span>
          <h2>Hoàn tất đơn hàng</h2>
          <p>Kiểm tra thông tin trước khi đặt mua sách.</p>
        </div>
        <button class="text-link-btn" onclick="showPublicMarketplace(); localStorage.removeItem('bookhub_checkout_single');">← Tiếp tục mua sắm</button>
      </div>

      <div class="checkout-layout">
        <section class="checkout-panel">
          <div class="checkout-step-heading"><span>1</span><div><h3>Sản phẩm đang mua</h3><p>Mua ngay, không qua giỏ hàng</p></div></div>
          <div class="checkout-product">
            <img src="${checkout.cover_image || 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&q=80&w=400'}" alt="${checkout.title}" class="checkout-product-image">
            <div class="checkout-product-info">
              <div class="checkout-product-label">SÁCH ĐANG CHỌN</div>
              <h3>${checkout.title}</h3>
              <p>Tác giả: <strong>${checkout.author || 'Đang cập nhật'}</strong></p>
              <div class="checkout-product-meta"><span>Đơn giá <strong>${formatVND(checkout.unit_price)}</strong></span><span>Số lượng <strong>${checkout.quantity}</strong></span></div>
            </div>
            <strong class="checkout-product-total">${formatVND(subtotal)}</strong>
          </div>

          <div class="checkout-step-heading"><span>2</span><div><h3>Thông tin nhận hàng</h3><p>Đơn hàng sẽ được giao đến địa chỉ này</p></div></div>
          <div class="checkout-form-grid">
            <div class="form-group"><label class="form-label">Họ tên người nhận</label><input id="checkout-name" class="form-control" value="${checkout.shipping_name || ''}" autocomplete="name"></div>
            <div class="form-group"><label class="form-label">Số điện thoại</label><input id="checkout-phone" class="form-control" value="${checkout.shipping_phone || ''}" autocomplete="tel"></div>
          </div>
          <div class="form-group"><label class="form-label">Địa chỉ giao hàng</label><input id="checkout-address" class="form-control" value="${checkout.shipping_address || ''}" autocomplete="street-address"></div>
          <div class="form-group"><label class="form-label">Ghi chú <span class="form-optional">(không bắt buộc)</span></label><textarea id="checkout-notes" class="form-control" rows="3" placeholder="Ví dụ: Giao trong giờ hành chính..."></textarea></div>

          <div class="checkout-step-heading"><span>3</span><div><h3>Phương thức thanh toán</h3><p>Chọn cách thanh toán phù hợp</p></div></div>
          <div class="form-group"><select id="checkout-payment-method" class="form-control checkout-payment-select"><option value="COD" ${checkout.payment_method === 'COD' ? 'selected' : ''}>Thanh toán khi nhận hàng (COD)</option><option value="VNPAY" ${checkout.payment_method === 'VNPAY' ? 'selected' : ''}>Chuyển khoản / VNPay QR</option><option value="MOMO" ${checkout.payment_method === 'MOMO' ? 'selected' : ''}>Thanh toán online qua MoMo</option></select></div>
        </section>

        <aside class="checkout-summary">
          <div class="checkout-summary-title"><span>4</span><h3>Chi phí đơn hàng</h3></div>
          <div class="checkout-summary-line"><span>Tiền sản phẩm</span><strong>${formatVND(subtotal)}</strong></div>
          <div class="checkout-summary-line"><span>Phí vận chuyển</span><strong>${formatVND(shippingFee)}</strong></div>
          <div class="checkout-summary-line checkout-discount"><span>Giảm giá / Voucher</span><strong>- ${formatVND(0)}</strong></div>
          <div class="checkout-total"><span>Tổng thanh toán</span><strong>${formatVND(total)}</strong></div>
          <button class="btn-primary checkout-submit-btn" onclick="submitSingleProductOrder()">Đặt hàng</button>
          <p class="checkout-secure-note">🔒 Thông tin của bạn được bảo mật trong quá trình đặt hàng.</p>
        </aside>
      </div>
    </div>
  `;

  checkoutRoot.style.display = 'block';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function submitSingleProductOrder() {
  const checkout = JSON.parse(localStorage.getItem('bookhub_checkout_single') || '{}');
  if (!checkout || !checkout.book_id) {
    showToast('Không có dữ liệu checkout cho sản phẩm này.', 'error');
    return;
  }

  const name = document.getElementById('checkout-name').value.trim();
  const phone = document.getElementById('checkout-phone').value.trim();
  const address = document.getElementById('checkout-address').value.trim();
  const notes = document.getElementById('checkout-notes').value.trim();
  const paymentMethod = document.getElementById('checkout-payment-method').value;

  if (!name || !phone || !address) {
    showToast('Vui lòng điền đầy đủ thông tin người nhận, địa chỉ và số điện thoại.', 'warning');
    return;
  }

  try {
    const payload = {
      items: [{ book_id: checkout.book_id, quantity: checkout.quantity || 1 }],
      shipping_name: name,
      shipping_phone: phone,
      shipping_address: address,
      payment_method: paymentMethod,
      notes
    };

    const newOrder = await apiCall('/api/orders', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    localStorage.removeItem('bookhub_checkout_single');
    localStorage.removeItem('bookhub_pending_buy_now');
    const checkoutRoot = document.getElementById('single-checkout-root');
    if (checkoutRoot) checkoutRoot.style.display = 'none';
    showOrderSuccess(newOrder);
  } catch (e) {
    console.error(e);
  }
}

function showOrderSuccess(order) {
  const appWrapper = document.getElementById('main-app-wrapper');
  if (appWrapper) appWrapper.style.display = 'block';
  document.querySelectorAll('.portal-container').forEach(portal => {
    portal.style.display = 'none';
  });

  const successRoot = document.getElementById('order-success-root');
  if (!successRoot) return;

  successRoot.innerHTML = `
    <div style="max-width:700px; margin:40px auto; background:#fff; border-radius:18px; border:1px solid #e2e8f0; box-shadow:0 10px 30px rgba(15,23,42,0.06); padding:32px; text-align:center;">
      <div style="font-size:52px;">✅</div>
      <h2 style="margin:16px 0 8px; font-size:32px;">Đặt hàng thành công</h2>
      <p style="color:#475569; margin-bottom:18px;">Cảm ơn bạn đã mua sắm tại BookHub.</p>
      <div style="display:inline-block; background:#eff6ff; color:#1d4ed8; border-radius:999px; padding:10px 16px; font-weight:800; margin-bottom:20px;">Mã đơn hàng: ${order.order_code}</div>
      <div style="display:flex; justify-content:center; gap:12px; flex-wrap:wrap; margin-top:14px;">
        <button class="btn-primary" onclick="openMyOrdersModal()">Xem chi tiết đơn hàng</button>
        <button class="btn-preview" onclick="showPublicMarketplace(); document.getElementById('order-success-root').innerHTML = '';">Tiếp tục mua sắm</button>
      </div>
    </div>
  `;
  successRoot.style.display = 'block';
}

function updateCartBadge() {
  const badge = document.getElementById('cart-badge-count');
  const totalItems = state.cart.reduce((sum, item) => sum + item.quantity, 0);
  if (badge) {
    badge.textContent = totalItems;
    badge.style.display = totalItems > 0 ? 'flex' : 'none';
  }
}

// Switch Demo User
async function switchDemoUser(username) {
  try {
    const data = await apiCall(`/api/auth/demo-switch-user?username=${username}`, { method: 'POST' });
    state.token = data.access_token;
    state.currentUser = data.user;

    // Save session
    localStorage.setItem('bookhub_token', data.access_token);
    localStorage.setItem('bookhub_user', JSON.stringify(data.user));

    // Update active demo button
    document.querySelectorAll('.role-btn').forEach(btn => {
      if (btn.dataset.username === username) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Update Header User Profile UI
    renderUserProfileWidget();

    // Determine default portal based on role
    if (state.currentUser.role === 'ADMIN') {
      switchPortal('ADMIN');
    } else if (state.currentUser.role === 'SELLER') {
      switchPortal('SELLER');
    } else {
      switchPortal('BUYER');
    }

    showToast(`Đang đóng vai: ${state.currentUser.full_name} (${state.currentUser.role})`, 'info');
  } catch (e) {
    console.error(e);
  }
}

function renderUserProfileWidget() {
  const widget = document.getElementById('user-profile-widget');
  const guestActions = document.getElementById('guest-auth-inline');
  const logoutBtn = document.getElementById('logout-btn');

  if (!widget) return;

  if (!state.currentUser) {
    widget.innerHTML = `
      <div style="display:flex; align-items:center; gap:8px; color:#1e293b; font-weight:700;">
        <span>👤</span>
        <span>Khách</span>
      </div>
    `;
    if (guestActions) guestActions.style.display = 'flex';
    if (logoutBtn) logoutBtn.style.display = 'none';
    return;
  }

  const isVipBadge = state.currentUser.is_vip ? `<span class="ad-label" style="background:#f59e0b; margin-left:4px;">👑 VIP</span>` : '';

  widget.innerHTML = `
    <img src="${state.currentUser.avatar || 'https://api.dicebear.com/7.x/bottts/svg?seed=' + state.currentUser.username}" class="user-avatar" alt="Avatar">
    <div>
      <div class="user-name-role">${state.currentUser.full_name || state.currentUser.username} ${isVipBadge}</div>
      <div class="user-role-label">${getRoleDisplayName(state.currentUser.role, state.currentUser.shop_name)}</div>
    </div>
  `;

  if (guestActions) guestActions.style.display = 'none';
  if (logoutBtn) logoutBtn.style.display = 'inline-flex';
}

function getRoleDisplayName(role, shopName) {
  if (role === 'ADMIN') return '👑 Chủ Sàn BookHub';
  if (role === 'SELLER') return `🏢 NXB / ${shopName || 'Nhà Sách'}`;
  return '👤 Độc Giả';
}

// Switch Portal (3 Cánh Cửa)
function switchPortal(portal) {
  state.currentPortal = portal;
  
  const buyerPortal = document.getElementById('buyer-portal');
  const sellerPortal = document.getElementById('seller-portal');
  const adminPortal = document.getElementById('admin-portal');

  buyerPortal.style.display = 'none';
  sellerPortal.style.display = 'none';
  adminPortal.style.display = 'none';
  document.querySelector('.demo-role-bar')?.classList.toggle('admin-chrome-hidden', portal === 'ADMIN');
  document.querySelector('.main-header')?.classList.toggle('admin-chrome-hidden', portal === 'ADMIN');
  document.querySelector('.storefront-nav')?.classList.toggle('admin-chrome-hidden', portal === 'ADMIN');
  document.querySelector('#catalog-mega-menu')?.classList.toggle('admin-chrome-hidden', portal === 'ADMIN');
  document.querySelector('.site-footer')?.classList.toggle('admin-chrome-hidden', portal === 'ADMIN');

  if (portal === 'BUYER') {
    buyerPortal.style.display = 'block';
    loadBooks();
    resetPageScroll();
  } else if (portal === 'SELLER') {
    sellerPortal.style.display = 'block';
    loadSellerDashboard();
  } else if (portal === 'ADMIN') {
    adminPortal.style.display = 'block';
    const adminRoute = window.location.pathname.match(/^\/admin(?:\/([A-Za-z0-9_-]+))?(?:\/([A-Za-z0-9_-]+))?$/);
    if (adminRoute?.[1] === 'settings' && adminRoute?.[2] === 'permissions') switchAdminView('permissions');
    else if (adminRoute?.[2] && ['disputes', 'payouts'].includes(adminRoute[1])) renderAdminDetail(adminRoute[1], adminRoute[2]);
    else if (adminRoute?.[2] && ['sellers', 'products', 'users', 'orders'].includes(adminRoute[1])) renderAdminEntityDetail(adminRoute[1], adminRoute[2]);
    else switchAdminView(adminRoute?.[1] || 'dashboard');
  }
}

// -------------------------------------------------------------
// CÁNH CỬA 1: ĐỘC GIẢ (BUYER PORTAL)
// -------------------------------------------------------------
async function loadCategories() {
  try {
    const cats = await apiCall('/api/books/categories');
    state.categories = cats;
    renderCategories();
  } catch (e) {}
}

function renderCategories() {
  const container = document.getElementById('category-pills');
  if (!container) return;

  let html = `<button class="pill-btn ${state.activeCategory === null ? 'active' : ''}" onclick="filterCategory(null)">📚 Tất cả thể loại</button>`;
  state.categories.forEach(c => {
    html += `<button class="pill-btn ${state.activeCategory === c.id ? 'active' : ''}" onclick="filterCategory(${c.id})">${c.name}</button>`;
  });
  container.innerHTML = html;
  renderCatalogMegaMenu();
}

function toggleCatalogMenu() {
  const menu = document.getElementById('catalog-mega-menu');
  const trigger = document.querySelector('.catalog-menu-trigger');
  if (!menu) return;
  const open = menu.classList.toggle('open');
  menu.setAttribute('aria-hidden', String(!open));
  if (trigger) trigger.setAttribute('aria-expanded', String(open));
}

function closeCatalogMenu() {
  const menu = document.getElementById('catalog-mega-menu');
  const trigger = document.querySelector('.catalog-menu-trigger');
  if (menu) { menu.classList.remove('open'); menu.setAttribute('aria-hidden', 'true'); }
  if (trigger) trigger.setAttribute('aria-expanded', 'false');
}

function renderCatalogMegaMenu() {
  const menu = document.getElementById('catalog-mega-menu');
  if (!menu) return;
  const categories = state.categories || [];
  const primary = categories;
  const groups = categories;
  menu.innerHTML = `<div class="catalog-menu-sidebar"><h3>Danh mục sản phẩm</h3>${primary.map((category, index) => `<button class="catalog-menu-side-item ${index === 0 ? 'active' : ''}" onclick="filterFromMegaMenu(${category.id})">${['▣','◈','✦','✿','◇','▤','○'][index] || '•'} ${category.name}<span>›</span></button>`).join('')}</div><div class="catalog-menu-content"><div class="catalog-menu-title">▣ <strong>Sách Trong Nước</strong></div><div class="catalog-menu-columns">${groups.map(category => `<div><h4>${category.name}</h4><button onclick="filterFromMegaMenu(${category.id})">${category.name}</button><button onclick="filterFromMegaMenu(${category.id})">Sách mới</button><button onclick="filterFromMegaMenu(${category.id})">Bán chạy</button><button class="catalog-menu-more" onclick="filterFromMegaMenu(${category.id})">Xem tất cả</button></div>`).join('')}</div><div class="catalog-menu-tags"><button onclick="navigateHome(); closeCatalogMenu();">Sách mới</button><button onclick="navigateHome(); closeCatalogMenu();">Sách bán chạy</button><button onclick="navigateHome(); closeCatalogMenu();">Ebook</button></div></div>`;
}

function filterFromMegaMenu(categoryId) {
  closeCatalogMenu();
  filterCategory(categoryId);
  document.getElementById('books-grid')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function filterCategory(catId) {
  state.activeCategory = catId;
  renderCategories();
  loadBooks();
}

function onSearchInput(e) {
  state.searchQuery = e.target.value.trim();
}

function submitBookSearch(event) {
  event.preventDefault();
  state.searchQuery = document.getElementById('global-search-input')?.value.trim() || '';
  loadBooks(true);
}

async function loadBooks(focusResults = false) {
  try {
    let url = '/api/books?';
    if (state.searchQuery) url += `q=${encodeURIComponent(state.searchQuery)}&`;
    if (state.activeCategory) url += `category_id=${state.activeCategory}&`;

    const books = await apiCall(url);
    state.books = books;
    populatePublisherFilter(books);
    renderRecentBooks();
    renderBooksGrid(books);
    renderPublicHomeSections(books);
    updateCatalogResultStatus(books.length, state.searchQuery ? ` cho “${state.searchQuery}”` : '');
    if (focusResults) document.getElementById('books-grid')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (e) {}
}

function populatePublisherFilter(books) {
  const select = document.getElementById('filter-publisher');
  if (!select) return;
  const current = select.value;
  const publishers = [...new Set(books.map(book => book.publisher).filter(Boolean))].sort();
  select.innerHTML = '<option value="">Nhà xuất bản</option>' + publishers.map(publisher => `<option value="${publisher}">${publisher}</option>`).join('');
  select.value = current;
}

function applyCatalogControls(focusResults = false) {
  const priceRange = document.getElementById('filter-price')?.value;
  const publisher = document.getElementById('filter-publisher')?.value;
  const cover = document.getElementById('filter-cover')?.value;
  const minRating = Number(document.getElementById('filter-rating')?.value || 0);
  const sort = document.getElementById('sort-books')?.value || 'newest';
  let books = state.books.filter(book => {
    const price = Number(book.discount_price || book.price || 0);
    const priceMatch = !priceRange || (priceRange === 'under_50' && price < 50000) || (priceRange === '50_150' && price >= 50000 && price <= 150000) || (priceRange === 'over_200' && price > 200000);
    return priceMatch && (!publisher || book.publisher === publisher) && (!cover || book.cover_type === cover) && Number(book.rating || 0) >= minRating;
  });
  books.sort((a, b) => sort === 'price_asc' ? (a.discount_price || a.price) - (b.discount_price || b.price) : sort === 'price_desc' ? (b.discount_price || b.price) - (a.discount_price || a.price) : sort === 'best_selling' ? (b.sold_count || 0) - (a.sold_count || 0) : new Date(b.created_at || 0) - new Date(a.created_at || 0));
  renderBooksGrid(books);
  updateCatalogResultStatus(books.length);
  if (focusResults) document.getElementById('books-grid')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function updateCatalogResultStatus(count, suffix = '') {
  const status = document.getElementById('catalog-result-status');
  if (status) status.textContent = `Đang hiển thị ${count} sách${suffix}.`;
}

function resetCatalogControls() {
  ['filter-price', 'filter-publisher', 'filter-cover', 'filter-rating'].forEach(id => { const element = document.getElementById(id); if (element) element.value = ''; });
  const sort = document.getElementById('sort-books');
  if (sort) sort.value = 'newest';
  renderBooksGrid(state.books);
  updateCatalogResultStatus(state.books.length);
}

function bookFormatLabel(book) {
  const format = book.book_format || 'PAPER';
  return format === 'EBOOK' ? 'Ebook' : format === 'AUDIOBOOK' ? 'Audiobook' : 'Sách giấy';
}

function bookBadges(book) {
  const vip = book.vip_eligible ? '<span class="book-badge badge-vip">👑 Đọc miễn phí với VIP</span>' : '';
  return `<div class="book-badges"><span class="book-badge badge-format">${bookFormatLabel(book)}</span>${vip}</div>`;
}

function rememberBook(book) {
  const recent = JSON.parse(localStorage.getItem('bookhub_recent_books') || '[]').filter(item => item.id !== book.id);
  recent.unshift(book);
  localStorage.setItem('bookhub_recent_books', JSON.stringify(recent.slice(0, 6)));
  renderRecentBooks();
}

function renderRecentBooks() {
  const section = document.getElementById('recent-books-section');
  const grid = document.getElementById('recent-books-grid');
  if (!section || !grid) return;
  const recent = JSON.parse(localStorage.getItem('bookhub_recent_books') || '[]');
  section.style.display = recent.length ? 'block' : 'none';
  grid.innerHTML = renderBookCards(recent.slice(0, 4), false);
}

function renderSmartRecommendations(book) {
  const section = document.getElementById('smart-recommendations-section');
  const grid = document.getElementById('smart-recommendations-grid');
  if (!section || !grid || !book) return;
  const recommendations = state.books.filter(item => item.id !== book.id && (item.author === book.author || item.category_id === book.category_id)).slice(0, 4);
  section.style.display = recommendations.length ? 'block' : 'none';
  grid.innerHTML = renderBookCards(recommendations, false);
}

function renderPublicHomeSections(books) {
  const promoGrid = document.getElementById('promo-grid');
  const categoryCards = document.getElementById('category-cards');
  const flashSaleGrid = document.getElementById('flash-sale-grid');
  const trendingGrid = document.getElementById('trending-books-grid');
  const bestSellerGrid = document.getElementById('bestseller-books-grid');
  const newBooksGrid = document.getElementById('new-books-grid');
  const vipBanner = document.getElementById('vip-cta-banner');
  const heroBooks = document.getElementById('hero-books');
  const homeCategorySidebar = document.getElementById('home-category-sidebar');
  const homePromoRail = document.getElementById('home-promo-rail');
  const footerYear = document.getElementById('footer-year');

  if (footerYear) footerYear.textContent = new Date().getFullYear();

  if (heroBooks) {
    heroBooks.innerHTML = [...books].sort((a, b) => (b.sold_count || 0) - (a.sold_count || 0)).slice(0, 3).map((book, index) => `<button class="hero-book hero-book-${index + 1}" onclick="openBookDetail(${book.id})" aria-label="Xem ${book.title}"><img src="${book.cover_image || ''}" alt="${book.title}"></button>`).join('');
  }

  if (homeCategorySidebar) {
    homeCategorySidebar.innerHTML = state.categories.map((category, index) => `<button onclick="filterFromMegaMenu(${category.id})"><span>${['▧','♧','▤','♢','♧','▱','◈','✧','◎','◇','◌','✥','▦'][index] || '•'}</span>${category.name}</button>`).join('');
  }

  if (homePromoRail) {
    const promoBooks = [...books].sort((a, b) => (b.sold_count || 0) - (a.sold_count || 0)).slice(0, 3);
    homePromoRail.innerHTML = promoBooks.map((book, index) => `<button class="home-promo-card promo-card-${index + 1}" onclick="openBookDetail(${book.id})"><img src="${book.cover_image || ''}" alt="${book.title}"><span>${index === 0 ? 'NỔI BẬT' : index === 1 ? 'SÁCH MỚI' : 'BÁN CHẠY'}</span></button>`).join('');
  }

  if (promoGrid) {
    promoGrid.innerHTML = [
      { icon: '📚', title: 'Sách mới', text: 'Khám phá bản mới' },
      { icon: '⚡', title: 'Flash sale', text: 'Giảm sâu đến 50%' },
      { icon: '📖', title: 'Ebook', text: 'Đọc mọi lúc' },
      { icon: '👑', title: 'VIP', text: 'Ưu đãi độc quyền' }
    ].map(p => `
      <div class="promo-card">
        <div class="promo-card-icon">${p.icon}</div>
        <div>
          <h3>${p.title}</h3>
          <p>${p.text}</p>
        </div>
      </div>
    `).join('');
  }

  if (categoryCards) {
    const categoryItems = (state.categories.length ? state.categories : [
      { id: 1, name: 'Văn học', slug: 'van-hoc' },
      { id: 2, name: 'Kinh tế', slug: 'kinh-te' },
      { id: 3, name: 'Kỹ năng', slug: 'ky-nang' },
      { id: 4, name: 'Thiếu nhi', slug: 'thieu-nhi' },
      { id: 5, name: 'Ngoại ngữ', slug: 'ngoai-ngu' },
      { id: 6, name: 'Công nghệ', slug: 'cong-nghe' }
    ]).slice(0, 6);

    categoryCards.innerHTML = categoryItems.map((category, index) => {
      const icons = ['📖', '💼', '🧠', '🌟', '🌍', '💻'];
      return `
        <div class="category-card" onclick="filterCategory(${category.id || index + 1})">
          <div class="category-card-icon">${icons[index % icons.length]}</div>
          <div>
            <h4>${category.name}</h4>
            <small>${category.slug || 'Danh mục'}</small>
          </div>
        </div>
      `;
    }).join('');
  }

  if (flashSaleGrid) {
    const flashBooks = [...books].sort((a, b) => ((b.discount_price || b.price) - (a.discount_price || a.price))).slice(0, 4);
    flashSaleGrid.innerHTML = flashBooks.map(book => {
      const original = Number(book.price || 0);
      const final = Number(book.discount_price || book.price || 0);
      const discounted = original > final ? Math.round(((original - final) / original) * 100) : 0;
      return `
        <div class="book-card featured-ad" onclick="openBookDetail(${book.id})">
          <div class="ad-ribbon">-${discounted}%</div>
          <div class="book-cover-wrap">
            <img src="${book.cover_image || 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&q=80&w=400'}" class="book-cover" alt="${book.title}">
            ${bookBadges(book)}
          </div>
          <div class="book-body">
            <div class="book-shop-tag">${book.seller_shop_name || 'NXB chính hãng'}</div>
            <div class="book-title" title="${book.title}">${book.title}</div>
            <div class="book-author">⭐ ${book.rating || 4.8}</div>
            <div class="book-price-row">
              <span class="price-current">${formatVND(final)}</span>
              <span class="price-original">${formatVND(original)}</span>
            </div>
            <div class="flash-progress"><span>Đã bán ${Math.min(99, Math.max(12, Math.round((book.sold_count || 0) / Math.max((book.sold_count || 0) + (book.stock || 1), 1) * 100)))}%</span><i><b style="width:${Math.min(99, Math.max(12, Math.round((book.sold_count || 0) / Math.max((book.sold_count || 0) + (book.stock || 1), 1) * 100)))}%"></b></i></div><div class="book-actions-row">
              <button class="btn-preview" onclick="event.stopPropagation(); openBookDetail(${book.id})">📖 Xem</button>
              <button class="btn-buy" onclick="event.stopPropagation(); buyNow(${book.id})">⚡ Mua ngay</button>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  if (trendingGrid) {
    const trending = [...books].sort((a, b) => (b.sold_count || 0) - (a.sold_count || 0)).slice(0, 5);
    trendingGrid.innerHTML = renderBookCards(trending, false);
  }

  if (bestSellerGrid) {
    const best = [...books].sort((a, b) => (b.sold_count || 0) - (a.sold_count || 0)).slice(0, 5);
    bestSellerGrid.innerHTML = renderBookCards(best, false);
  }

  if (newBooksGrid) {
    const newest = [...books].sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0)).slice(0, 5);
    newBooksGrid.innerHTML = renderBookCards(newest, false);
  }

  if (vipBanner) {
    vipBanner.innerHTML = `
      <div>
        <h3>👑 BookHub VIP</h3>
        <p>Đọc Ebook & Sách nói không giới hạn, ưu đãi độc quyền cho thành viên VIP.</p>
      </div>
      <button class="btn-vip-gold" onclick="${state.currentUser ? 'openVipModal()' : 'requireLoginForAction(\'Khám phá gói VIP\')'}">Khám phá VIP</button>
    `;
  }
}

function renderBookCards(books, showFeaturedFlag = true) {
  return books.map(b => {
    const isAd = showFeaturedFlag && b.is_featured_ad;
    const priceCurrent = b.discount_price ? formatVND(b.discount_price) : formatVND(b.price);
    const priceOriginal = b.discount_price ? `<span class="price-original">${formatVND(b.price)}</span>` : '';

    const discount = b.price > (b.discount_price || b.price) ? Math.round((1 - (b.discount_price || b.price) / b.price) * 100) : 0;
    return `
      <div class="book-card ${isAd ? 'featured-ad' : ''}" onclick="openBookDetail(${b.id})">
        ${isAd ? '<div class="ad-ribbon">⭐ TÀI TRỢ</div>' : ''}
        ${discount ? `<div class="discount-badge">-${discount}%</div>` : ''}
        <div class="book-cover-wrap">
          <img src="${b.cover_image || 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&q=80&w=400'}" class="book-cover" alt="${b.title}">
          ${bookBadges(b)}
        </div>
        <div class="book-body">
          <div class="book-shop-tag">${b.seller_shop_name || 'NXB Chính Hãng'}</div>
          <div class="book-title" title="${b.title}">${b.title}</div>
          <div class="book-author">Tác giả: ${b.author}</div>
          <div class="book-price-row">
            <span class="price-current">${priceCurrent}</span>
            ${priceOriginal}
          </div>
          <div class="book-actions-row">
            <button class="btn-preview" onclick="event.stopPropagation(); openBookDetail(${b.id})">📖 Xem chi tiết</button>
            <button class="btn-buy" onclick="event.stopPropagation(); buyNow(${b.id})">⚡ Mua ngay</button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function renderBooksGrid(books) {
  const grid = document.getElementById('books-grid');
  if (!grid) return;

  if (books.length === 0) {
    grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:40px; color:#94a3b8;">Không tìm thấy cuốn sách nào phù hợp</div>`;
    return;
  }

  let html = '';
  books.forEach(b => {
    const isAd = b.is_featured_ad;
    const discount = b.price > (b.discount_price || b.price) ? Math.round((1 - (b.discount_price || b.price) / b.price) * 100) : 0;
    const priceCurrent = b.discount_price ? formatVND(b.discount_price) : formatVND(b.price);
    const priceOriginal = b.discount_price ? `<span class="price-original">${formatVND(b.price)}</span>` : '';

    html += `
      <div class="book-card ${isAd ? 'featured-ad' : ''}" onclick="openBookDetail(${b.id})">
        ${isAd ? '<div class="ad-ribbon">⭐ TÀI TRỢ / NỔI BẬT</div>' : ''}
        ${discount ? `<div class="discount-badge">-${discount}%</div>` : ''}
        <div class="book-cover-wrap">
          <img src="${b.cover_image || 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&q=80&w=400'}" class="book-cover" alt="${b.title}">
          ${bookBadges(b)}
        </div>
        <div class="book-body">
          <div class="book-shop-tag">${b.seller_shop_name || 'NXB Chính Hãng'}</div>
          <div class="book-title" title="${b.title}">${b.title}</div>
          <div class="book-author">Tác giả: ${b.author}</div>
          <div class="book-price-row">
            <span class="price-current">${priceCurrent}</span>
            ${priceOriginal}
          </div>
          <div class="book-actions-row">
            <button class="btn-preview" onclick="event.stopPropagation(); openBookDetail(${b.id})">📖 Xem sách</button>
            <button class="btn-buy" onclick="event.stopPropagation(); buyNow(${b.id})">⚡ Mua ngay</button>
          </div>
        </div>
      </div>
    `;
  });
  grid.innerHTML = html;
}

const detailReviews = [
  { userName: 'Minh Anh', rating: 5, comment: 'Sách đóng gói kỹ, nội dung rất đáng đọc.', date: '12/08/2026', helpful: 18 },
  { userName: 'Hoàng Nam', rating: 4, comment: 'Giao hàng nhanh, chất lượng sách tốt.', date: '05/08/2026', helpful: 9 },
  { userName: 'Thu Hà', rating: 5, comment: 'Hình ảnh và mô tả đúng với sản phẩm.', date: '28/07/2026', helpful: 12 }
];

async function openBookDetail(bookId, pushHistory = true) {
  try {
    const book = await apiCall(`/api/books/${bookId}`);
    if (pushHistory) history.pushState({ bookId }, '', `/books/${bookId}`);
    rememberBook(book);
    renderSmartRecommendations(book);
    await renderBookDetail(book);
  } catch (error) {
    renderBookNotFound();
  }
}

function renderBookNotFound() {
  const root = document.getElementById('book-detail-root');
  if (!root) return;
  document.querySelectorAll('.portal-container').forEach(portal => { portal.style.display = 'none'; });
  root.innerHTML = '<div class="book-detail-page"><div class="detail-empty"><h2>Không tìm thấy sản phẩm</h2><p>Cuốn sách này không tồn tại hoặc đã được gỡ khỏi sàn.</p><button class="btn-primary" onclick="navigateHome()">Về trang chủ</button></div></div>';
  root.style.display = 'block';
  resetPageScroll();
}

function detailPrice(book) {
  const current = Number(book.discount_price || book.price || 0);
  const original = Number(book.price || current);
  const discount = original > current ? Math.round((1 - current / original) * 100) : 0;
  return { current, original, discount };
}

async function renderBookDetail(book) {
  const root = document.getElementById('book-detail-root');
  if (!root) return;
  const prices = detailPrice(book);
  const related = state.books.filter(item => item.id !== book.id && (item.category_id === book.category?.id || item.author === book.author)).slice(0, 8);
  const reviewSummary = state.productReviewSummary[book.id] || { total_reviews: 0, average_rating: 0, rating_distribution: { '5': 0, '4': 0, '3': 0, '2': 0, '1': 0 }, reviews: [] };
  const reviews = reviewSummary.reviews || [];
  document.querySelectorAll('.portal-container').forEach(portal => { portal.style.display = 'none'; });
  document.getElementById('single-checkout-root').style.display = 'none';
  root.innerHTML = `
    <main class="book-detail-page">
      <div class="detail-breadcrumb"><button onclick="navigateHome()">Trang chủ</button><span>›</span><span>${book.category?.name || book.category_name || 'Sách'}</span><span>›</span><strong>${book.title}</strong></div>
      <section class="detail-product-card">
        <div class="detail-gallery"><div class="detail-main-image"><img id="detail-main-image" src="${book.cover_image || ''}" alt="${book.title}"></div><div class="detail-thumbnails"><button class="detail-thumb active" onclick="changeDetailImage(this, '${book.cover_image || ''}')"><img src="${book.cover_image || ''}" alt=""></button><button class="detail-thumb" onclick="changeDetailImage(this, '${book.cover_image || ''}')"><img src="${book.cover_image || ''}" alt=""></button></div></div>
        <div class="detail-info"><span class="detail-format-label">${bookFormatLabel(book)}${book.vip_eligible ? ' · 👑 VIP' : ''}</span><h1>${book.title}</h1><div class="detail-rating"><span>★★★★★</span> <strong>${Number(reviewSummary.average_rating || book.rating || 0).toFixed(1)}/5</strong> <a href="#reviews">(${reviewSummary.total_reviews || reviews.length} đánh giá)</a></div><div class="detail-meta-list"><div><span>Tác giả</span><strong>${book.author || 'Đang cập nhật'}</strong></div><div><span>Nhà xuất bản</span><strong>${book.publisher || 'Đang cập nhật'}</strong></div><div><span>Tình trạng</span><strong class="${book.stock > 0 ? 'stock-in' : 'stock-out'}">${book.stock > 0 ? `Còn hàng (${book.stock})` : 'Hết hàng'}</strong></div></div><div class="detail-price"><strong>${formatVND(prices.current)}</strong>${prices.discount ? `<del>${formatVND(prices.original)}</del><span>-${prices.discount}%</span>` : ''}</div><div class="detail-buy-row"><span>Số lượng</span><div class="detail-quantity"><button onclick="changeDetailQuantity(-1)">−</button><strong id="detail-quantity">1</strong><button onclick="changeDetailQuantity(1)">+</button></div></div><div class="detail-actions"><button class="btn-preview detail-cart-button" onclick="addDetailToCart(${book.id})">🛒 Thêm vào giỏ hàng</button><button class="btn-buy detail-buy-button" onclick="buyNow(${book.id}, Number(document.getElementById('detail-quantity').textContent))">⚡ Mua ngay</button></div><div class="detail-promise"><span>✓</span> Đọc thử miễn phí · Đổi trả trong 7 ngày · Giao hàng toàn quốc</div></div>
      </section>
      <section class="detail-section"><h2>Thông tin chi tiết</h2><div class="spec-grid"><div><span>Mã sản phẩm</span><strong>BH-${book.id}</strong></div><div><span>ISBN</span><strong>${book.isbn || 'Đang cập nhật'}</strong></div><div><span>Tác giả</span><strong>${book.author || 'Đang cập nhật'}</strong></div><div><span>Nhà xuất bản</span><strong>${book.publisher || 'Đang cập nhật'}</strong></div><div><span>Năm xuất bản</span><strong>${book.publication_year || new Date(book.created_at || Date.now()).getFullYear()}</strong></div><div><span>Ngôn ngữ</span><strong>${book.language || 'Tiếng Việt'}</strong></div><div><span>Số trang</span><strong>${book.page_count || 'Đang cập nhật'}</strong></div><div><span>Kích thước</span><strong>${book.size || '13 x 20 cm'}</strong></div><div><span>Loại bìa</span><strong>${book.cover_type === 'HARD' ? 'Bìa cứng' : 'Bìa mềm'}</strong></div><div><span>Thể loại</span><strong>${book.category?.name || book.category_name || 'Tổng hợp'}</strong></div></div></section>
      <section class="detail-section"><h2>Mô tả sản phẩm</h2><div id="detail-description" class="detail-description collapsed">${book.description || 'Mô tả sản phẩm đang được cập nhật.'}</div><button class="detail-more-button" onclick="toggleDetailDescription(this)">Xem thêm</button></section>
      <section id="reviews" class="detail-section review-section"><div class="review-heading"><div><h2>Đánh giá sản phẩm</h2><div class="review-score"><span>★★★★★</span><strong>${Number(reviewSummary.average_rating || book.rating || 0).toFixed(1)} / 5</strong><small>${reviewSummary.total_reviews || reviews.length} đánh giá</small></div></div><button class="btn-preview" onclick="${state.currentUser ? `openMyOrdersModal()` : `showAuthPage(); switchAuthTab('login')`} ">${state.currentUser ? 'Viết đánh giá' : 'Đăng nhập để đánh giá'}</button></div>${renderReviewDistribution(reviewSummary.rating_distribution || { '5': 0, '4': 0, '3': 0, '2': 0, '1': 0 })}<div class="review-filters"><button class="active" onclick="filterDetailReviews(0, this)">Tất cả</button>${[5,4,3,2,1].map(star => `<button onclick="filterDetailReviews(${star}, this)">${star} sao</button>`).join('')}</div><div id="detail-reviews-list">${renderDetailReviews(reviews)}</div></section>
      <section class="detail-section related-section"><div class="section-title-wrap"><h2>Có thể bạn cũng thích</h2><div><button class="related-arrow" onclick="scrollRelatedBooks(-1)">←</button><button class="related-arrow" onclick="scrollRelatedBooks(1)">→</button></div></div><div id="related-books-grid" class="related-books-grid">${renderBookCards(related, false)}</div></section>
    </main>`;
  root.style.display = 'block';
  root.dataset.detailBookId = book.id;
  await loadBookReviews(book.id);
  resetPageScroll();
}

function changeDetailImage(button, source) {
  document.getElementById('detail-main-image').src = source;
  document.querySelectorAll('.detail-thumb').forEach(item => item.classList.remove('active'));
  button.classList.add('active');
}

function changeDetailQuantity(delta) {
  const current = Number(document.getElementById('detail-quantity').textContent);
  const book = state.books.find(item => item.id === Number(document.getElementById('book-detail-root').dataset.detailBookId));
  document.getElementById('detail-quantity').textContent = Math.max(1, Math.min(book?.stock || 1, current + delta));
}

function addDetailToCart(bookId) {
  addToCart(bookId);
  showToast('Đã thêm sách vào giỏ hàng.', 'success');
}

function toggleDetailDescription(button) {
  const description = document.getElementById('detail-description');
  description.classList.toggle('collapsed');
  button.textContent = description.classList.contains('collapsed') ? 'Xem thêm' : 'Thu gọn';
}

function renderReviewDistribution(distribution = { '5': 0, '4': 0, '3': 0, '2': 0, '1': 0 }) {
  const total = Object.values(distribution).reduce((sum, val) => sum + Number(val || 0), 0) || 1;
  return `<div class="review-distribution">${[5,4,3,2,1].map(star => {
    const value = Number(distribution[String(star)] || 0);
    const width = Math.round((value / total) * 100);
    return `<span>${star} sao <i style="width:${width}%"></i> ${width}%</span>`;
  }).join('')}</div>`;
}

function renderDetailReviews(reviews = []) {
  if (!Array.isArray(reviews) || !reviews.length) return '<p class="detail-muted">Chưa có đánh giá phù hợp.</p>';
  return reviews.map(review => {
    const buyer = review.buyer_name || 'Người mua';
    const date = review.created_at ? new Date(review.created_at).toLocaleDateString('vi-VN') : 'Gần đây';
    const replyHtml = review.reply ? `<div class="review-reply"><strong>Phản hồi shop:</strong> ${review.reply.content}</div>` : '';
    const avatar = (buyer.charAt(0) || 'U').toUpperCase();
    return `<article class="review-item"><div class="review-avatar">${avatar}</div><div><div class="review-item-head"><strong>${buyer}</strong><small>${date}</small></div><div class="review-stars">${'★'.repeat(Number(review.rating || 0))}${'☆'.repeat(5 - Number(review.rating || 0))}</div><p>${(review.content || '').replace(/</g, '&lt;')}</p>${replyHtml}</div></article>`;
  }).join('');
}

function filterDetailReviews(star, button) {
  const root = document.getElementById('book-detail-root');
  const bookId = Number(root?.dataset.detailBookId || 0);
  const allReviews = state.productReviews[bookId] || [];
  document.querySelectorAll('.review-filters button').forEach(item => item.classList.remove('active'));
  button.classList.add('active');
  const visible = star ? allReviews.filter(review => Number(review.rating) === Number(star)) : allReviews;
  document.getElementById('detail-reviews-list').innerHTML = renderDetailReviews(visible);
}

async function loadBookReviews(bookId) {
  if (!bookId) return;
  try {
    const summary = await apiCall(`/api/reviews/product/${bookId}`);
    state.productReviews[bookId] = summary.reviews || [];
    state.productReviewSummary[bookId] = summary;
    const detailRoot = document.getElementById('book-detail-root');
    if (!detailRoot || Number(detailRoot.dataset.detailBookId) !== Number(bookId)) return;
    const reviewList = document.getElementById('detail-reviews-list');
    if (reviewList) reviewList.innerHTML = renderDetailReviews(summary.reviews || []);
  } catch (error) {
    state.productReviews[bookId] = [];
    state.productReviewSummary[bookId] = { total_reviews: 0, average_rating: 0, rating_distribution: { '5': 0, '4': 0, '3': 0, '2': 0, '1': 0 }, reviews: [] };
  }
}

function scrollRelatedBooks(direction) {
  document.getElementById('related-books-grid')?.scrollBy({ left: direction * 360, behavior: 'smooth' });
}

// Book Reader Modal
async function openBookReaderModal(bookId) {
  try {
    const book = await apiCall(`/api/books/${bookId}`);
    rememberBook(book);
    renderSmartRecommendations(book);
    const modal = document.getElementById('reader-modal');
    
    document.getElementById('reader-modal-title').textContent = `📖 Đọc Thử: ${book.title}`;
    document.getElementById('reader-book-meta').innerHTML = `
      <div style="display:flex; gap:16px; margin-bottom:16px; align-items:center;">
        <img src="${book.cover_image}" style="width:60px; height:80px; object-fit:cover; border-radius:6px;">
        <div>
          <h4 style="margin-bottom:4px;">${book.title}</h4>
          <p style="font-size:13px; color:#64748b;">Tác giả: <b>${book.author}</b> | NXB: ${book.publisher || 'Nhã Nam / Kim Đồng'}</p>
          <span class="ad-label" style="background:#4f46e5; margin-top:4px;">Giá bán: ${formatVND(book.discount_price || book.price)}</span>
        </div>
      </div>
    `;

    const readerBody = document.getElementById('reader-content-box');
    
    if (book.can_read_full && book.full_ebook_content) {
      readerBody.innerHTML = `
        <span class="reader-badge-preview" style="background:#ecfdf5; color:#10b981;">👑 BẠN ĐANG LÀ VIP: ĐƯỢC ĐỌC TOÀN BỘ EBOOK KHÔNG GIỚI HẠN</span>
        <div>${book.sample_content}\n\n${book.full_ebook_content}</div>
      `;
    } else {
      readerBody.innerHTML = `
        <span class="reader-badge-preview">✨ NỘI DUNG ĐỌC THỬ MIỄN PHÍ (3 TRANG ĐẦU)</span>
        <div>${book.sample_content || 'Nội dung đang được cập nhật...'}</div>
        <div style="margin-top:24px; padding:16px; background:#f1f5f9; border-radius:8px; text-align:center;">
          <p style="font-size:13px; font-weight:700; margin-bottom:10px;">Bạn muốn đọc trọn vẹn cuốn sách này?</p>
          <div style="display:flex; justify-content:center; gap:12px; flex-wrap:wrap;">
            <button class="btn-vip-gold" onclick="closeModal('reader-modal'); openVipModal();">👑 Mở khóa Gói VIP Ebook</button>
            <button class="btn-primary" onclick="closeModal('reader-modal'); buyNow(${book.id});">⚡ Mua ngay</button>
            <button class="btn-preview" onclick="closeModal('reader-modal'); addToCart(${book.id}); openCartModal();">🛒 Thêm vào giỏ hàng</button>
          </div>
        </div>
      `;
    }

    modal.classList.add('open');
  } catch (e) {}
}

// VIP Subscription Modal
async function openVipModal() {
  if (!state.currentUser) {
    requireLoginForAction('Mở gói VIP');
    return;
  }

  try {
    const plans = await apiCall('/api/vip/plans');
    const container = document.getElementById('vip-plans-container');
    
    let html = '';
    plans.forEach(p => {
      html += `
        <div class="vip-card ${p.popular ? 'popular' : ''}">
          ${p.popular ? '<div class="vip-badge-pop">GÓI PHỔ BIẾN NHẤT</div>' : ''}
          <h3 style="font-size:17px; font-weight:800;">${p.name}</h3>
          <div class="vip-price">${formatVND(p.price)}</div>
          <p style="font-size:12px; color:#64748b;">Thời hạn: ${p.duration_days} ngày đọc thả ga</p>
          <ul class="vip-features">
            ${p.features.map(f => `<li>${f}</li>`).join('')}
          </ul>
          <button class="btn-vip-gold" style="width:100%; justify-content:center;" onclick="subscribeVip('${p.name}', ${p.price}, ${p.duration_days})">
            Kích Hoạt Ngay
          </button>
        </div>
      `;
    });
    container.innerHTML = html;

    document.getElementById('vip-modal').classList.add('open');
  } catch (e) {}
}

async function subscribeVip(planName, price, durationDays) {
  try {
    const res = await apiCall('/api/vip/subscribe', {
      method: 'POST',
      body: JSON.stringify({
        plan_name: planName,
        price: price,
        duration_days: durationDays
      })
    });
    showToast(res.message, 'success');
    state.currentUser.is_vip = true;
    renderUserProfileWidget();
    closeModal('vip-modal');
  } catch (e) {}
}

// Cart & Checkout Modal
function openCartModal() {
  if (!state.currentUser) {
    requireLoginForAction('Xem giỏ hàng và thanh toán');
    return;
  }

  const modal = document.getElementById('cart-modal');
  renderCartModalContent();
  modal.classList.add('open');
}

function renderCartModalContent() {
  const container = document.getElementById('cart-items-wrap');
  const summary = document.getElementById('cart-summary-wrap');
  
  if (state.cart.length === 0) {
    container.innerHTML = `<div style="text-align:center; padding:30px; color:#94a3b8;">Giỏ hàng của bạn đang trống!</div>`;
    summary.innerHTML = '';
    return;
  }

  let html = '';
  let subtotal = 0;

  state.cart.forEach((item, idx) => {
    const itemTotal = item.price * item.quantity;
    subtotal += itemTotal;
    html += `
      <div style="display:flex; align-items:center; justify-content:space-between; padding:12px 0; border-bottom:1px solid #f1f5f9;">
        <div style="display:flex; align-items:center; gap:12px;">
          <img src="${item.cover_image}" style="width:45px; height:60px; object-fit:cover; border-radius:4px;">
          <div>
            <div style="font-weight:700; font-size:14px;">${item.title}</div>
            <div style="font-size:12px; color:#64748b;">${formatVND(item.price)} x ${item.quantity} cuốn</div>
          </div>
        </div>
        <div style="display:flex; align-items:center; gap:12px;">
          <span style="font-weight:800; color:#ef4444;">${formatVND(itemTotal)}</span>
          <button style="background:none; border:none; color:#94a3b8; cursor:pointer;" onclick="removeCartItem(${idx})">🗑️</button>
        </div>
      </div>
    `;
  });
  container.innerHTML = html;

  // Tự động phân tách phí hoa hồng sàn 10% minh bạch
  const platformFee = subtotal * 0.10;
  const sellerReceives = subtotal - platformFee;

  summary.innerHTML = `
    <div style="background:#f8fafc; padding:16px; border-radius:8px; margin-top:16px;">
      <div style="display:flex; justify-content:space-between; margin-bottom:8px; font-size:14px;">
        <span>Tổng giá trị đơn hàng:</span>
        <span style="font-weight:800; font-size:16px; color:#ef4444;">${formatVND(subtotal)}</span>
      </div>
      <div style="font-size:11px; color:#64748b; margin-bottom:12px; border-top:1px dashed #cbd5e1; padding-top:8px;">
        ℹ️ <i>Cơ chế ăn chia: Sàn thu 10% phí dịch vụ (${formatVND(platformFee)}), NXB thực nhận 90% (${formatVND(sellerReceives)}) khi giao thành công.</i>
      </div>
      
      <div class="form-group">
        <label class="form-label">Tên người nhận:</label>
        <input type="text" id="order-shipping-name" class="form-control" value="${state.currentUser ? state.currentUser.full_name : 'Nguyễn Văn Độc Giả'}">
      </div>
      <div class="form-group">
        <label class="form-label">Số điện thoại giao hàng:</label>
        <input type="text" id="order-shipping-phone" class="form-control" value="${state.currentUser ? (state.currentUser.phone || '0901234567') : '0901234567'}">
      </div>
      <div class="form-group">
        <label class="form-label">Tỉnh/Thành phố:</label>
        <select id="order-province" class="form-control" onchange="loadCartDistricts()"><option value="">Chọn Tỉnh/Thành phố</option></select>
      </div>
      <div class="form-group">
        <label class="form-label">Quận/Huyện:</label>
        <select id="order-district" class="form-control" onchange="loadCartWards()" disabled><option value="">Chọn Quận/Huyện</option></select>
      </div>
      <div class="form-group">
        <label class="form-label">Phường/Xã:</label>
        <select id="order-ward" class="form-control" disabled><option value="">Chọn Phường/Xã</option></select>
      </div>
      <div class="form-group">
        <label class="form-label">Số nhà, tên đường:</label>
        <input type="text" id="order-shipping-address" class="form-control" placeholder="Ví dụ: 12 Nguyễn Trãi">
      </div>
      <div class="form-group">
        <label class="form-label">Phương thức thanh toán:</label>
        <select id="order-payment-method" class="form-control">
          <option value="COD">Thanh toán khi nhận hàng (COD)</option>
          <option value="VIETQR">VietQR / Chuyển khoản</option>
          <option value="MOMO">Ví MoMo</option>
          <option value="ZALOPAY">Ví ZaloPay</option>
          <option value="SHOPEEPAY">Ví ShopeePay</option>
          <option value="CARD">ATM / Visa / Mastercard</option>
        </select>
      </div>

      <div class="form-group">
        <label class="form-label">🚚 Phương thức vận chuyển:</label>
        <select id="order-shipping-method" class="form-control">
          <option value="STANDARD">Giao tiết kiệm - 25.000đ</option>
          <option value="EXPRESS">Giao nhanh - 40.000đ</option>
          <option value="SAME_DAY">Giao hỏa tốc - 60.000đ</option>
        </select>
      </div>
      <div class="voucher-entry"><input id="order-voucher-code" class="form-control" placeholder="Mã voucher"><button type="button" class="btn-preview" onclick="applyCartVoucher()">Áp dụng</button></div>
      <label class="terms-check"><input id="order-terms" type="checkbox"> Tôi đồng ý với Điều khoản dịch vụ và Chính sách mua hàng của BookHub.</label>

      <button class="btn-primary" style="width:100%; justify-content:center; padding:12px; font-size:15px;" onclick="submitOrder()">
        ✅ Xác Nhận Đặt Mua & Theo Dõi Lộ Trình
      </button>
    </div>
  `;
  loadCartLocations();
}

async function loadCartLocations() {
  try {
    const data = await apiCall('/api/orders/locations');
    window.cartLocations = data.locations;
    const province = document.getElementById('order-province');
    if (province) province.innerHTML = '<option value="">Chọn Tỉnh/Thành phố</option>' + data.locations.map(item => `<option value="${item.code}">${item.name}</option>`).join('');
  } catch (error) { console.error(error); }
}

function loadCartDistricts() {
  const province = document.getElementById('order-province');
  const district = document.getElementById('order-district');
  const ward = document.getElementById('order-ward');
  const item = (window.cartLocations || []).find(location => String(location.code) === String(province?.value));
  district.innerHTML = '<option value="">Chọn Quận/Huyện</option>' + (item?.districts || []).map(value => `<option value="${value.code}">${value.name}</option>`).join('');
  district.disabled = !item;
  ward.innerHTML = '<option value="">Chọn Phường/Xã</option>';
  ward.disabled = true;
}

function loadCartWards() {
  const province = document.getElementById('order-province');
  const district = document.getElementById('order-district');
  const ward = document.getElementById('order-ward');
  const provinceItem = (window.cartLocations || []).find(location => String(location.code) === String(province?.value));
  const districtItem = provinceItem?.districts.find(item => String(item.code) === String(district?.value));
  ward.innerHTML = '<option value="">Chọn Phường/Xã</option>' + (districtItem?.wards || []).map(value => `<option value="${value.code}">${value.name}</option>`).join('');
  ward.disabled = !districtItem;
}

function removeCartItem(index) {
  state.cart.splice(index, 1);
  saveCartToStorage();
  renderMiniCart();
  renderCartModalContent();
}

async function submitOrder() {
  if (!state.currentUser) {
    requireLoginForAction('Đặt hàng và thanh toán');
    return;
  }

  if (state.cart.length === 0) return;

  const name = document.getElementById('order-shipping-name').value;
  const phone = document.getElementById('order-shipping-phone').value;
  const address = document.getElementById('order-shipping-address').value;
  const payment = document.getElementById('order-payment-method').value;
  const shippingMethod = document.getElementById('order-shipping-method').value;
  const voucherCode = document.getElementById('order-voucher-code').value.trim() || null;
  const provinceSelect = document.getElementById('order-province');
  const districtSelect = document.getElementById('order-district');
  const wardSelect = document.getElementById('order-ward');
  const province = provinceSelect?.selectedOptions[0];
  const district = districtSelect?.selectedOptions[0];
  const ward = wardSelect?.selectedOptions[0];

  if (!name || !phone || !address || !province?.value || !district?.value || !ward?.value) {
    showToast('Vui lòng chọn đầy đủ Tỉnh/Thành phố, Quận/Huyện, Phường/Xã và nhập số nhà, tên đường.', 'warning');
    return;
  }
  if (!document.getElementById('order-terms').checked) {
    showToast('Vui lòng đồng ý với Điều khoản dịch vụ và Chính sách mua hàng.', 'warning');
    return;
  }

  const payload = {
    items: state.cart.map(c => ({ book_id: c.book_id, quantity: c.quantity })),
    shipping_name: name,
    shipping_phone: phone,
    shipping_address: `${address}, ${ward.textContent}, ${district.textContent}, ${province.textContent}`,
    shipping_province: province.textContent,
    shipping_province_code: province.value,
    shipping_district: district.textContent,
    shipping_district_code: district.value,
    shipping_ward: ward.textContent,
    shipping_ward_code: ward.value,
    shipping_street: address,
    payment_method: payment,
    shipping_method: shippingMethod,
    voucher_code: voucherCode,
    terms_accepted: true
  };

  try {
    const newOrder = await apiCall('/api/orders', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    state.cart = [];
    saveCartToStorage();
    closeModal('cart-modal');
    showToast(`Đặt hàng thành công! Mã đơn: ${newOrder.order_code}`, 'success');

    // Mở ngay modal theo dõi lộ trình đơn hàng
    openOrderTrackerModal(newOrder.id);
  } catch (e) {}
}

async function applyCartVoucher() {
  const code = document.getElementById('order-voucher-code').value.trim();
  const subtotal = state.cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
  if (!code) { showToast('Vui lòng nhập mã voucher.', 'warning'); return; }
  try {
    const result = await apiCall('/api/orders/vouchers/apply', { method: 'POST', body: JSON.stringify({ code, subtotal }) });
    document.getElementById('order-voucher-code').dataset.validatedCode = result.code;
    showToast(`${result.name}: giảm ${formatVND(result.discount_amount)}`, 'success');
  } catch (error) {}
}

// Order Tracker Modal (Live Tracking)
async function openOrderTrackerModal(orderId) {
  try {
    const order = await apiCall(`/api/orders/${orderId}`);
    const modal = document.getElementById('tracker-modal');

    document.getElementById('tracker-order-code').textContent = order.order_code;
    document.getElementById('tracker-order-amount').textContent = formatVND(order.total_amount);
    document.getElementById('tracker-shipping-dest').textContent = `${order.shipping_name} - ${order.shipping_phone} (${order.shipping_address})`;

    // Update 4-step progress
    const step = order.tracking_step || 1;
    const steps = [
      { num: 1, label: 'Đã Đặt Hàng', desc: 'Đơn hàng đã được tiếp nhận' },
      { num: 2, label: 'Đóng Gói', desc: 'NXB đang đóng gói sách cẩn thận' },
      { num: 3, label: 'Đang Giao', desc: 'Đã bàn giao cho shipper vận chuyển' },
      { num: 4, label: 'Hoàn Tất', desc: 'Giao hàng thành công' }
    ];

    let stepsHtml = '';
    steps.forEach(s => {
      let stepClass = '';
      if (s.num < step) stepClass = 'done';
      else if (s.num === step) stepClass = 'active';

      stepsHtml += `
        <div class="tracking-step-item ${stepClass}">
          <div class="step-circle">${s.num < step ? '✓' : s.num}</div>
          <div class="step-label">${s.label}</div>
        </div>
      `;
    });
    document.getElementById('tracker-steps-bar').innerHTML = stepsHtml;

    // Hiển thị danh sách cuốn sách trong đơn
    let itemsHtml = '';
    order.items.forEach(it => {
      itemsHtml += `
        <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #f1f5f9; font-size:13px;">
          <div style="display:flex; align-items:center; gap:8px;">
            <img src="${it.book_cover || 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&q=80&w=100'}" style="width:30px; height:40px; object-fit:cover; border-radius:3px;">
            <span>${it.book_title} (x${it.quantity})</span>
          </div>
          <span style="font-weight:700;">${formatVND(it.price * it.quantity)}</span>
        </div>
      `;
    });
    document.getElementById('tracker-items-list').innerHTML = itemsHtml;

    modal.classList.add('open');
  } catch (e) {}
}

async function openMyOrdersModal() {
  if (!state.currentUser) {
    requireLoginForAction('Xem lịch sử đơn hàng');
    return;
  }

  try {
    const orders = await apiCall('/api/orders/my-orders');
    const modal = document.getElementById('my-orders-modal');
    const container = document.getElementById('my-orders-list');

    if (orders.length === 0) {
      container.innerHTML = `<div style="text-align:center; padding:30px; color:#94a3b8;">Bạn chưa có đơn hàng nào</div>`;
    } else {
      let html = '';
      orders.forEach(o => {
        let statusBadge = '<span class="badge badge-warning">Chờ đóng gói</span>';
        if (o.status === 'PACKING') statusBadge = '<span class="badge badge-info">Đang đóng gói</span>';
        if (o.status === 'SHIPPING') statusBadge = '<span class="badge badge-info">Đang giao hàng</span>';
        if (o.status === 'DELIVERED') statusBadge = '<span class="badge badge-success">Đã giao thành công</span>';

        const returnButton = o.status === 'DELIVERED'
          ? `<button class="btn-secondary" style="padding:4px 10px; font-size:12px; margin-left:8px;" onclick="closeModal('my-orders-modal'); openReturnRequestModal(${o.id})">↩️ Yêu cầu trả hàng</button>`
          : '';
        const reviewButton = o.status === 'DELIVERED'
          ? `<button class="btn-preview" style="padding:4px 10px; font-size:12px;" onclick="closeModal('my-orders-modal'); openOrderReviewModal(${o.id})">⭐ Đánh giá sản phẩm</button>`
          : '';

        html += `
          <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:16px; margin-bottom:12px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
              <span style="font-weight:800;">Mã đơn: ${o.order_code}</span>
              ${statusBadge}
            </div>
            <div style="font-size:13px; color:#64748b; margin-bottom:8px;">
              Tổng tiền: <b style="color:#ef4444;">${formatVND(o.total_amount)}</b> | ${new Date(o.created_at).toLocaleDateString('vi-VN')}
            </div>
            <div style="display:flex; gap:8px; flex-wrap:wrap;">
              <button class="btn-primary" style="padding:4px 10px; font-size:12px;" onclick="closeModal('my-orders-modal'); openOrderTrackerModal(${o.id})">
                🚚 Xem lộ trình vận chuyển
              </button>
              ${reviewButton}
              ${returnButton}
            </div>
          </div>
        `;
      });
      container.innerHTML = html;
    }

    modal.classList.add('open');
  } catch (e) {}
}

async function openOrderReviewModal(orderId) {
  if (!state.currentUser) {
    requireLoginForAction('Đánh giá sản phẩm');
    return;
  }

  try {
    const order = await apiCall(`/api/orders/${orderId}`);
    const formRoot = document.getElementById('review-form-root');
    if (!formRoot) return;
    formRoot.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:16px;">
        <div>
          <h4 style="margin:0 0 6px; font-size:16px;">Đơn hàng: ${order.order_code}</h4>
          <p style="margin:0; color:#64748b; font-size:13px;">Mỗi sản phẩm chỉ được đánh giá một lần. Bạn có thể thêm ảnh minh họa nếu muốn.</p>
        </div>
        ${order.items.map(item => `
          <div data-review-item="${item.id}" style="padding:12px; border:1px solid #e2e8f0; border-radius:10px; background:#f8fafc; display:flex; gap:12px; align-items:flex-start;">
            <img src="${item.book_cover || 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&q=80&w=80'}" style="width:56px; height:72px; object-fit:cover; border-radius:8px;">
            <div style="flex:1; min-width:0;">
              <div style="font-weight:700; margin-bottom:8px;">${item.book_title}</div>
              <div class="review-stars" style="margin-bottom:8px;">
                ${[5,4,3,2,1].map(star => `<label style="cursor:pointer; color:#fbbf24; font-size:18px; margin-right:4px;"><input type="radio" name="rating-${item.id}" value="${star}" style="display:none;">★</label>`).join('')}
              </div>
              <textarea rows="3" placeholder="Viết nhận xét của bạn về sản phẩm..." style="width:100%; resize:vertical; border:1px solid #cbd5e1; border-radius:8px; padding:10px 12px; font-size:13px;" data-review-content="${item.id}"></textarea>
              <input type="text" placeholder="URL ảnh minh họa (tuỳ chọn)" style="width:100%; margin-top:8px; border:1px solid #cbd5e1; border-radius:8px; padding:8px 10px; font-size:13px;" data-review-image="${item.id}">
              <div style="display:flex; justify-content:flex-end; margin-top:10px;">
                <button class="btn-primary" style="padding:6px 12px; font-size:12px;" onclick="submitReviewItem(${order.id}, ${item.id}, ${item.book_id})">Gửi đánh giá</button>
              </div>
            </div>
          </div>
        `).join('')}
      </div>
    `;
    document.getElementById('review-modal').classList.add('open');
  } catch (error) {
    showToast(error.message || 'Không thể mở form đánh giá.', 'error');
  }
}

async function submitReviewItem(orderId, orderItemId, productId) {
  const itemRoot = document.querySelector(`[data-review-item="${orderItemId}"]`);
  if (!itemRoot) return;
  const checked = itemRoot.querySelector('input[name="rating-' + orderItemId + '"]:checked');
  const content = itemRoot.querySelector('[data-review-content="' + orderItemId + '"]').value.trim();
  const imageInput = itemRoot.querySelector('[data-review-image="' + orderItemId + '"]');
  const rating = Number(checked?.value || 0);
  if (!rating) {
    showToast('Vui lòng chọn số sao trước khi gửi đánh giá.', 'warning');
    return;
  }
  if (!content) {
    showToast('Vui lòng nhập nhận xét cho sản phẩm.', 'warning');
    return;
  }
  try {
    const body = {
      order_id: Number(orderId),
      order_item_id: Number(orderItemId),
      product_id: Number(productId),
      rating,
      content,
      images: imageInput && imageInput.value.trim() ? [imageInput.value.trim()] : []
    };
    await apiCall('/api/reviews', { method: 'POST', body: JSON.stringify(body) });
    showToast('Đánh giá của bạn đã được gửi thành công.', 'success');
    closeModal('review-modal');
    await openMyOrdersModal();
    if (state.currentUser && state.currentPortal !== 'SELLER') {
      const book = state.books.find(item => item.id === Number(productId));
      if (book) await loadBookReviews(book.id);
    }
  } catch (error) {
    // keep the modal open so user can retry on validation errors
  }
}

async function openReturnRequestModal(orderId) {
  if (!state.currentUser) {
    requireLoginForAction('Yêu cầu trả hàng');
    return;
  }

  try {
    const order = await apiCall(`/api/orders/${orderId}`);
    const formRoot = document.getElementById('return-request-form');
    if (!formRoot) return;

    const itemOptions = order.items.map(item => `
      <label style="display:flex; align-items:center; justify-content:space-between; gap:12px; padding:10px 12px; border:1px solid #e2e8f0; border-radius:8px; margin-bottom:8px; background:#fff;">
        <span style="display:flex; align-items:center; gap:10px; min-width:0;">
          <input type="checkbox" name="return-item" value="${item.id}" data-book-id="${item.book_id}" data-quantity="${item.quantity}" checked>
          <img src="${item.book_cover || 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&q=80&w=60'}" style="width:36px; height:48px; object-fit:cover; border-radius:5px;">
          <span style="font-size:13px; color:#1e293b;">${item.book_title}<br><small>x${item.quantity}</small></span>
        </span>
        <span style="font-size:12px; font-weight:700; color:#ef4444;">${formatVND(item.price * item.quantity)}</span>
      </label>
    `).join('');

    formRoot.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:16px;">
        <div>
          <h4 style="margin:0 0 6px; font-size:16px;">Đơn hàng: ${order.order_code}</h4>
          <p style="margin:0; color:#64748b; font-size:13px;">Chọn tối thiểu một mặt hàng và nhập lý do trả.</p>
        </div>
        <div>
          <label style="display:block; font-weight:700; font-size:13px; margin-bottom:8px;">Sản phẩm cần trả</label>
          <div>${itemOptions || '<p class="text-muted">Không có mặt hàng nào trong đơn.</p>'}</div>
        </div>
        <div>
          <label style="display:block; font-weight:700; font-size:13px; margin-bottom:8px;">Lý do trả</label>
          <select id="return-reason" style="width:100%; border:1px solid #cbd5e1; border-radius:8px; padding:10px 12px;">
            <option value="PRODUCT_DEFECT">Sản phẩm bị lỗi/hư hỏng</option>
            <option value="WRONG_PRODUCT">Giao sai sản phẩm</option>
            <option value="DESCRIPTION_MISMATCH">Không đúng mô tả</option>
            <option value="MISSING_ITEM">Thiếu phụ kiện / thiếu hàng</option>
            <option value="CHANGE_OF_MIND">Đổi ý</option>
            <option value="OTHER">Lý do khác</option>
          </select>
        </div>
        <div>
          <label style="display:block; font-weight:700; font-size:13px; margin-bottom:8px;">Mô tả chi tiết</label>
          <textarea id="return-description" rows="3" placeholder="Mô tả tình trạng sản phẩm" style="width:100%; resize:vertical; border:1px solid #cbd5e1; border-radius:8px; padding:10px 12px;"></textarea>
        </div>
        <div>
          <label style="display:block; font-weight:700; font-size:13px; margin-bottom:8px;">Phương thức hoàn tiền</label>
          <select id="return-method" style="width:100%; border:1px solid #cbd5e1; border-radius:8px; padding:10px 12px;">
            <option value="BANK_TRANSFER">Chuyển khoản ngân hàng</option>
            <option value="WALLET">Ví điện tử</option>
            <option value="CASH">Tiền mặt</option>
          </select>
        </div>
        <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:8px;">
          <button class="btn-secondary" type="button" onclick="closeModal('return-request-modal')">Hủy</button>
          <button class="btn-primary" type="button" onclick="submitReturnRequestForm(${order.id})">Gửi yêu cầu</button>
        </div>
      </div>
    `;

    document.getElementById('return-request-modal').classList.add('open');
  } catch (error) {
    showToast(error.message || 'Không thể mở form trả hàng', 'error');
  }
}

async function submitReturnRequestForm(orderId) {
  const selected = [...document.querySelectorAll('input[name="return-item"]:checked')];
  if (!selected.length) {
    showToast('Vui lòng chọn ít nhất 1 sản phẩm để trả.', 'warning');
    return;
  }

  const body = {
    order_id: orderId,
    reason: document.getElementById('return-reason')?.value || 'OTHER',
    description: document.getElementById('return-description')?.value || '',
    refund_method: document.getElementById('return-method')?.value || 'BANK_TRANSFER',
    items: selected.map(item => ({
      order_item_id: Number(item.value),
      product_id: Number(item.dataset.bookId),
      quantity: Number(item.dataset.quantity || 1)
    }))
  };

  try {
    const result = await apiCall('/api/returns', {
      method: 'POST',
      body: JSON.stringify(body)
    });
    showToast('Đã gửi yêu cầu trả hàng thành công.', 'success');
    closeModal('return-request-modal');
    openMyOrdersModal();
    if (state.currentPortal === 'ADMIN') {
      await renderAdminReturnsLive();
    }
    return result;
  } catch (error) {
    return null;
  }
}

// -------------------------------------------------------------
// CÁNH CỬA 2: DOANH NGHIỆP / NXB (SELLER PORTAL - MERCHANT CENTER)
// -------------------------------------------------------------
let sellerState = {
  currentTab: 'dashboard',
  stats: null,
  books: [],
  orders: [],
  vouchers: [],
  withdrawals: [],
  staff: [],
  profile: null,
  bookFilter: 'ALL',
  bookSearch: '',
  orderStatusFilter: 'ALL',
  selectedBookIds: new Set()
};

// Chuyển đổi giữa 5 Tab của Merchant Portal
function switchSellerTab(tabName) {
  sellerState.currentTab = tabName;

  // Cập nhật active tab button
  document.querySelectorAll('.seller-nav-tab').forEach(btn => btn.classList.remove('active'));
  const activeBtn = document.getElementById(`seller-tab-btn-${tabName}`);
  if (activeBtn) activeBtn.classList.add('active');

  // Cập nhật active tab pane
  document.querySelectorAll('.seller-tab-pane').forEach(pane => pane.classList.remove('active'));
  const activePane = document.getElementById(`seller-pane-${tabName}`);
  if (activePane) activePane.classList.add('active');

  // Tải dữ liệu tương ứng cho từng tab
  if (tabName === 'dashboard') {
    loadSellerDashboard();
  } else if (tabName === 'products') {
    loadSellerBooks();
  } else if (tabName === 'orders') {
    loadSellerOrders();
  } else if (tabName === 'marketing') {
    loadSellerMarketing();
  } else if (tabName === 'settings') {
    loadSellerSettings();
  }
}

// =============================================================
// TAB 1: 📊 TỔNG QUAN & BÁO CÁO (DASHBOARD & ANALYTICS)
// =============================================================
async function loadSellerDashboard() {
  try {
    const stats = await apiCall('/api/seller/dashboard');
    sellerState.stats = stats;

    // Header Profile & Balance
    const shopTitle = document.getElementById('seller-shop-name-title');
    if (shopTitle) shopTitle.textContent = stats.shop_name;
    const balanceHeader = document.getElementById('seller-header-balance');
    if (balanceHeader) balanceHeader.textContent = formatVND(stats.seller_balance);
    const avatarImg = document.getElementById('seller-avatar-img');
    if (avatarImg && stats.shop_logo) avatarImg.src = stats.shop_logo;

    // 6 Thẻ Metric Tổng Quan
    const grossRev = document.getElementById('seller-gross-rev');
    if (grossRev) grossRev.textContent = formatVND(stats.total_revenue_gross);
    const feePaid = document.getElementById('seller-fee-paid');
    if (feePaid) feePaid.textContent = formatVND(stats.platform_commission_paid);
    const netRev = document.getElementById('seller-net-rev');
    if (netRev) netRev.textContent = formatVND(stats.net_earnings);
    const ordersCount = document.getElementById('seller-orders-count');
    if (ordersCount) ordersCount.textContent = stats.total_orders;
    const pendingOrdersSub = document.getElementById('seller-orders-pending-sub');
    if (pendingOrdersSub) pendingOrdersSub.textContent = stats.pending_orders_count;
    const booksCount = document.getElementById('seller-books-count');
    if (booksCount) booksCount.textContent = stats.total_books;
    const pendingBooksSub = document.getElementById('seller-books-pending-sub');
    if (pendingBooksSub) pendingBooksSub.textContent = stats.pending_books;
    const lowstockCount = document.getElementById('seller-lowstock-count');
    if (lowstockCount) lowstockCount.textContent = stats.low_stock_books;

    // Cập nhật Quick Actions Bar
    const qaPending = document.getElementById('qa-pending-orders');
    if (qaPending) qaPending.textContent = `${stats.pending_orders_count} đơn cần giao`;
    const qaLowStock = document.getElementById('qa-lowstock-books');
    if (qaLowStock) qaLowStock.textContent = `${stats.low_stock_books} cuốn tồn kho ≤ 5`;

    // Badge thông báo ở thanh Tabs
    const lowStockBadge = document.getElementById('seller-lowstock-badge');
    if (lowStockBadge) {
      lowStockBadge.textContent = stats.low_stock_books;
      lowStockBadge.style.display = stats.low_stock_books > 0 ? 'inline-flex' : 'none';
    }
    const pendingOrdersBadge = document.getElementById('seller-pending-orders-badge');
    if (pendingOrdersBadge) {
      pendingOrdersBadge.textContent = stats.pending_orders_count;
      pendingOrdersBadge.style.display = stats.pending_orders_count > 0 ? 'inline-flex' : 'none';
    }

    // Render Biểu đồ Doanh thu 7 ngày
    renderSellerRevenueChart(stats.chart_data || []);

    // Render Top 5 Sách Bán Chạy Nhất
    renderSellerTopBooks(stats.top_books || []);

    // Tải danh sách lịch sử rút tiền
    await loadSellerWithdrawals();

    // Tải thông tin hồ sơ cho header (địa chỉ kho, logo preview)
    loadSellerProfileMini();
  } catch (e) {
    console.error('Lỗi khi tải Dashboard Seller:', e);
  }
}

async function loadSellerProfileMini() {
  try {
    const profile = await apiCall('/api/seller/profile');
    sellerState.profile = profile;
    const whElem = document.getElementById('seller-header-warehouse');
    if (whElem && profile.warehouse_address) {
      whElem.textContent = `Kho: ${profile.warehouse_address}`;
    }
    const descElem = document.getElementById('seller-shop-desc-text');
    if (descElem && profile.shop_description) {
      descElem.textContent = profile.shop_description;
    }
    const bannerBg = document.getElementById('seller-header-banner-bg');
    if (bannerBg && profile.shop_banner) {
      bannerBg.style.backgroundImage = `url('${profile.shop_banner}')`;
    }
  } catch (e) {}
}

// Vẽ biểu đồ SVG 7 ngày trực quan
function renderSellerRevenueChart(chartData) {
  const container = document.getElementById('seller-revenue-chart-container');
  if (!container) return;

  if (!chartData || chartData.length === 0) {
    container.innerHTML = `<div style="text-align:center; padding:40px; color:#94a3b8;">Chưa có dữ liệu giao dịch 7 ngày qua</div>`;
    return;
  }

  const maxRevenue = Math.max(...chartData.map(d => d.revenue), 100000);

  let barsHtml = '';
  chartData.forEach(item => {
    const heightPercent = Math.max((item.revenue / maxRevenue) * 100, 4);
    barsHtml += `
      <div class="seller-chart-col" title="${item.date}: ${formatVND(item.revenue)} (${item.orders} đơn)">
        <div class="chart-val-popup">${formatVND(item.revenue)}</div>
        <div class="chart-bar-wrap">
          <div class="chart-bar-fill" style="height:${heightPercent}%;"></div>
        </div>
        <div class="chart-col-date">${item.date}</div>
        <div class="chart-col-orders">${item.orders} đơn</div>
      </div>
    `;
  });

  container.innerHTML = `
    <div class="seller-chart-bars-wrap">
      ${barsHtml}
    </div>
  `;
}

// Xuất CSV Doanh Thu 7 Ngày
function exportSellerRevenueCSV() {
  const stats = sellerState.stats;
  if (!stats || !stats.chart_data || stats.chart_data.length === 0) {
    showToast('Chưa có dữ liệu biểu đồ để xuất CSV', 'warning');
    return;
  }

  const rows = [
    ['Ngay', 'Doanh_Thu_Thuc_Nhan_VND', 'So_Luong_Don_Hang']
  ];

  stats.chart_data.forEach(item => {
    rows.push([item.date, item.revenue, item.orders]);
  });

  const csvContent = '\uFEFF' + rows.map(r => r.join(',')).join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `Bao_Cao_Doanh_Thu_7_Ngay_${new Date().toISOString().slice(0,10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToast('Đã xuất file CSV doanh thu thành công!', 'success');
}

// Render Top 5 Sách Bán Chạy Nhất
function renderSellerTopBooks(topBooks) {
  const container = document.getElementById('seller-top-books-list');
  if (!container) return;

  if (topBooks.length === 0) {
    container.innerHTML = `<div style="text-align:center; padding:30px; color:#94a3b8;">Chưa có dữ liệu sách bán ra</div>`;
    return;
  }

  let html = '';
  topBooks.forEach((book, index) => {
    html += `
      <div class="seller-top-book-item">
        <div class="top-rank-badge rank-${index + 1}">#${index + 1}</div>
        <img src="${book.cover_image || 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&q=80&w=100'}" class="top-book-thumb" alt="${book.title}">
        <div class="top-book-info">
          <div class="top-book-title">${book.title}</div>
          <div class="top-book-meta">
            <span class="top-book-price">${formatVND(book.price)}</span>
            <span class="top-book-sold">🔥 Đã bán: <b>${book.sold_count}</b> cuốn</span>
            <span class="top-book-stock">📦 Còn: <b>${book.stock}</b></span>
          </div>
        </div>
      </div>
    `;
  });
  container.innerHTML = html;
}

// Lịch sử rút tiền
async function loadSellerWithdrawals() {
  try {
    const list = await apiCall('/api/seller/withdrawals');
    sellerState.withdrawals = list;
    const container = document.getElementById('seller-withdrawals-table-body');
    if (!container) return;

    if (list.length === 0) {
      container.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:20px; color:#94a3b8;">Chưa có yêu cầu rút tiền nào</td></tr>`;
      return;
    }

    let html = '';
    list.forEach(w => {
      let statusBadge = '<span class="badge badge-warning">⏳ Đang xử lý</span>';
      if (w.status === 'APPROVED') statusBadge = '<span class="badge badge-success">✅ Đã chuyển khoản</span>';
      if (w.status === 'REJECTED') statusBadge = '<span class="badge badge-danger">❌ Bị từ chối</span>';

      html += `
        <tr>
          <td><b>#WD-${w.id}</b></td>
          <td><b style="color:#059669; font-size:15px;">${formatVND(w.amount)}</b></td>
          <td>
            <div><b>${w.bank_name}</b> - ${w.bank_account_number}</div>
            <div style="font-size:11px; color:#64748b;">Chủ TK: ${w.bank_account_holder}</div>
          </td>
          <td>${w.note || 'Rút tiền định kỳ'}</td>
          <td>${new Date(w.created_at).toLocaleDateString('vi-VN')} ${new Date(w.created_at).toLocaleTimeString('vi-VN', {hour:'2-digit', minute:'2-digit'})}</td>
          <td>${statusBadge}</td>
        </tr>
      `;
    });
    container.innerHTML = html;
  } catch (e) {}
}

function openWithdrawalModal() {
  if (!state.currentUser) {
    requireLoginForAction('Rút tiền doanh thu');
    return;
  }

  const profile = sellerState.profile || {};
  const currentBalance = sellerState.stats ? sellerState.stats.seller_balance : 0;
  
  const availElem = document.getElementById('withdraw-available-balance');
  if (availElem) availElem.textContent = formatVND(currentBalance);

  const bankElem = document.getElementById('withdraw-bank-input');
  if (bankElem) bankElem.value = profile.bank_name || 'Vietcombank';

  const accElem = document.getElementById('withdraw-accnumber-input');
  if (accElem) accElem.value = profile.bank_account_number || '0071001234567';

  const holderElem = document.getElementById('withdraw-holder-input');
  if (holderElem) holderElem.value = profile.bank_account_holder || state.currentUser.shop_name || state.currentUser.full_name;

  const amountInput = document.getElementById('withdraw-amount-input');
  if (amountInput) amountInput.value = '';

  document.getElementById('withdrawal-modal').classList.add('open');
}

async function submitWithdrawalRequest() {
  const amount = parseFloat(document.getElementById('withdraw-amount-input').value);
  const bankName = document.getElementById('withdraw-bank-input').value;
  const accNum = document.getElementById('withdraw-accnumber-input').value;
  const holder = document.getElementById('withdraw-holder-input').value;
  const note = document.getElementById('withdraw-note-input').value;

  if (!amount || amount < 50000) {
    showToast('Số tiền rút tối thiểu là 50.000 đ', 'warning');
    return;
  }

  const currentBalance = sellerState.stats ? sellerState.stats.seller_balance : 0;
  if (amount > currentBalance) {
    showToast('Số dư khả dụng không đủ để thực hiện giao dịch!', 'warning');
    return;
  }

  try {
    await apiCall('/api/seller/withdrawals', {
      method: 'POST',
      body: JSON.stringify({
        amount,
        bank_name: bankName,
        bank_account_number: accNum,
        bank_account_holder: holder,
        note
      })
    });
    showToast(`Đã gửi yêu cầu rút ${formatVND(amount)} thành công! Tiền sẽ về TK trong 24h.`, 'success');
    closeModal('withdrawal-modal');
    await loadSellerDashboard();
  } catch (e) {}
}


// =============================================================
// TAB 2: 📚 QUẢN LÝ SẢN PHẨM & KHO (PRODUCTS & INVENTORY)
// =============================================================
async function loadSellerBooks() {
  try {
    const books = await apiCall('/api/seller/books');
    sellerState.books = books;
    sellerState.selectedBookIds.clear();
    updateSellerBulkBarUI();

    // Cập nhật số lượng đếm trên các Tab lọc
    const countAll = books.length;
    const countApproved = books.filter(b => b.status === 'APPROVED').length;
    const countPending = books.filter(b => b.status === 'PENDING').length;
    const countLowStock = books.filter(b => b.stock <= 5).length;
    const countRejected = books.filter(b => b.status === 'REJECTED').length;

    if (document.getElementById('count-book-all')) document.getElementById('count-book-all').textContent = countAll;
    if (document.getElementById('count-book-approved')) document.getElementById('count-book-approved').textContent = countApproved;
    if (document.getElementById('count-book-pending')) document.getElementById('count-book-pending').textContent = countPending;
    if (document.getElementById('count-book-lowstock')) document.getElementById('count-book-lowstock').textContent = countLowStock;
    if (document.getElementById('count-book-rejected')) document.getElementById('count-book-rejected').textContent = countRejected;

    filterSellerBooksUI();
  } catch (e) {
    console.error('Lỗi tải danh sách sách seller:', e);
  }
}

function setSellerBookFilter(filter, btn) {
  sellerState.bookFilter = filter;
  document.querySelectorAll('.seller-pill-btn').forEach(b => b.classList.remove('active'));
  if (btn) {
    btn.classList.add('active');
  } else {
    const targetBtn = document.querySelector(`.seller-pill-btn[data-filter="${filter}"]`);
    if (targetBtn) targetBtn.classList.add('active');
  }
  filterSellerBooksUI();
}

function filterSellerBooksUI() {
  const search = (document.getElementById('seller-book-search-input')?.value || '').toLowerCase().trim();
  const filter = sellerState.bookFilter;
  const container = document.getElementById('seller-books-table-body');
  if (!container) return;

  let filtered = sellerState.books.filter(b => {
    // Lọc theo từ khóa
    const matchSearch = !search || 
      b.title.toLowerCase().includes(search) || 
      b.author.toLowerCase().includes(search) || 
      (b.isbn && b.isbn.toLowerCase().includes(search));

    // Lọc theo trạng thái
    let matchFilter = true;
    if (filter === 'APPROVED') matchFilter = (b.status === 'APPROVED');
    else if (filter === 'PENDING') matchFilter = (b.status === 'PENDING');
    else if (filter === 'LOW_STOCK') matchFilter = (b.stock <= 5);
    else if (filter === 'REJECTED') matchFilter = (b.status === 'REJECTED');

    return matchSearch && matchFilter;
  });

  if (filtered.length === 0) {
    container.innerHTML = `<tr><td colspan="10" style="text-align:center; padding:30px; color:#94a3b8;">Không tìm thấy cuốn sách nào phù hợp</td></tr>`;
    return;
  }

  let html = '';
  filtered.forEach(b => {
    let statusBadge = '<span class="badge badge-success">✓ Đang mở bán</span>';
    if (b.status === 'PENDING') statusBadge = '<span class="badge badge-warning">⏳ Chờ duyệt</span>';
    if (b.status === 'REJECTED') statusBadge = '<span class="badge badge-danger">❌ Bị từ chối</span>';

    // Cảnh báo tồn kho thấp + clickable inline edit
    const isLow = b.stock <= 5;
    const safeTitle = (b.title || '').replace(/'/g, "\\'");
    let stockBadge = `
      <span class="inline-stock-badge ${isLow ? 'low-stock' : ''}" onclick="openQuickStockModal(${b.id}, '${safeTitle}', ${b.stock})" title="Bấm để sửa nhanh tồn kho">
        <span>${b.stock} cuốn</span>
        <span class="stock-edit-icon">✏️</span>
      </span>
    `;

    let formatLabel = b.book_format === 'EBOOK' ? 'Ebook' : (b.book_format === 'AUDIOBOOK' ? 'Audiobook' : 'Sách giấy');
    const isChecked = sellerState.selectedBookIds.has(b.id) ? 'checked' : '';

    html += `
      <tr>
        <td style="text-align:center;">
          <input type="checkbox" class="seller-book-select-cb" data-id="${b.id}" ${isChecked} onchange="toggleSelectSellerBook(${b.id}, this.checked)">
        </td>
        <td>
          <div style="display:flex; align-items:center; gap:12px;">
            <img src="${b.cover_image || 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&q=80&w=100'}" style="width:42px; height:58px; object-fit:cover; border-radius:4px; box-shadow:0 2px 4px rgba(0,0,0,0.1);">
            <div>
              <div style="font-weight:700; font-size:14px; color:#1e293b; max-width:240px; line-height:1.3;">${b.title}</div>
              <div style="font-size:11px; color:#64748b; margin-top:2px;">
                Tác giả: <b>${b.author}</b> ${b.translator ? `(Dịch: ${b.translator})` : ''}
              </div>
              <div style="font-size:10px; color:#94a3b8; margin-top:2px;">
                ISBN: ${b.isbn || 'Chưa cập nhật'} | ${formatLabel} | ${b.publication_year || 2024}
              </div>
            </div>
          </div>
        </td>
        <td><span class="badge badge-info">${b.category_name || 'Tổng hợp'}</span></td>
        <td>
          <div><b style="color:#ef4444; font-size:14px;">${formatVND(b.discount_price || b.price)}</b></div>
          ${b.discount_price ? `<div style="font-size:11px; text-decoration:line-through; color:#94a3b8;">${formatVND(b.price)}</div>` : ''}
        </td>
        <td>${stockBadge}</td>
        <td><b>${b.sold_count || 0}</b> cuốn</td>
        <td>
          <span class="seller-rating-pill">⭐ ${Number(b.rating || 5.0).toFixed(1)}</span>
        </td>
        <td>${statusBadge}</td>
        <td>
          ${b.is_featured_ad 
            ? '<span class="badge badge-warning" style="font-size:11px;">⭐ Đang chạy Top Ads</span>' 
            : `<button class="btn-vip-gold" style="padding:4px 8px; font-size:11px;" onclick="openBuyAdModal(${b.id}, '${safeTitle}')">🚀 Đẩy Top</button>`}
        </td>
        <td>
          <div style="display:flex; gap:6px;">
            <button class="btn-preview" style="padding:4px 8px; font-size:11px;" onclick="openEditBookModal(${b.id})" title="Chỉnh sửa sách">✏️ Sửa</button>
            <button class="btn-danger" style="padding:4px 8px; font-size:11px;" onclick="deleteBookBySeller(${b.id})" title="Xóa sách khỏi kho">🗑️</button>
          </div>
        </td>
      </tr>
    `;
  });
  container.innerHTML = html;
}

// Bulk Selection cho Sách
function toggleSelectSellerBook(bookId, isChecked) {
  if (isChecked) {
    sellerState.selectedBookIds.add(bookId);
  } else {
    sellerState.selectedBookIds.delete(bookId);
  }
  updateSellerBulkBarUI();
}

function toggleSelectAllSellerBooks(allCheckbox) {
  const isChecked = allCheckbox.checked;
  const checkboxes = document.querySelectorAll('.seller-book-select-cb');
  checkboxes.forEach(cb => {
    cb.checked = isChecked;
    const id = parseInt(cb.getAttribute('data-id'));
    if (isChecked) sellerState.selectedBookIds.add(id);
    else sellerState.selectedBookIds.delete(id);
  });
  updateSellerBulkBarUI();
}

function deselectAllSellerBooks() {
  sellerState.selectedBookIds.clear();
  const selectAll = document.getElementById('select-all-seller-books');
  if (selectAll) selectAll.checked = false;
  document.querySelectorAll('.seller-book-select-cb').forEach(cb => cb.checked = false);
  updateSellerBulkBarUI();
}

function updateSellerBulkBarUI() {
  const bulkBar = document.getElementById('seller-books-bulk-bar');
  const countSpan = document.getElementById('seller-selected-books-count');
  const count = sellerState.selectedBookIds.size;

  if (countSpan) countSpan.textContent = count;
  if (bulkBar) {
    bulkBar.style.display = count > 0 ? 'flex' : 'none';
  }
}

// Modal Cập nhật nhanh tồn kho 1 cuốn
function openQuickStockModal(bookId, bookTitle, currentStock) {
  document.getElementById('quick-stock-book-id').value = bookId;
  document.getElementById('quick-stock-book-title').textContent = bookTitle;
  document.getElementById('quick-stock-input').value = currentStock;
  document.getElementById('quick-stock-modal').classList.add('open');
}

async function submitQuickStock() {
  const bookId = parseInt(document.getElementById('quick-stock-book-id').value);
  const newStock = parseInt(document.getElementById('quick-stock-input').value);

  if (isNaN(newStock) || newStock < 0) {
    showToast('Vui lòng nhập số lượng tồn kho hợp lệ (≥ 0)', 'warning');
    return;
  }

  try {
    await apiCall(`/api/seller/books/${bookId}/quick-stock`, {
      method: 'PUT',
      body: JSON.stringify({ stock: newStock })
    });
    showToast('Đã cập nhật số lượng tồn kho thành công!', 'success');
    closeModal('quick-stock-modal');
    await loadSellerBooks();
    await loadSellerDashboard();
  } catch (e) {}
}

// Cập nhật tồn kho hàng loạt cho các sách được tick
async function bulkSetStockPrompt() {
  const count = sellerState.selectedBookIds.size;
  if (count === 0) return;

  const valStr = prompt(`Nhập số lượng tồn kho mới áp dụng cho ${count} cuốn sách đã chọn:`, '50');
  if (valStr === null) return;
  const newStock = parseInt(valStr);
  if (isNaN(newStock) || newStock < 0) {
    showToast('Số lượng tồn kho không hợp lệ', 'warning');
    return;
  }

  let updatedCount = 0;
  for (const bookId of sellerState.selectedBookIds) {
    try {
      await apiCall(`/api/seller/books/${bookId}/quick-stock`, {
        method: 'PUT',
        body: JSON.stringify({ stock: newStock })
      });
      updatedCount++;
    } catch (e) {}
  }

  showToast(`Đã cập nhật tồn kho thành ${newStock} cho ${updatedCount} cuốn sách!`, 'success');
  deselectAllSellerBooks();
  await loadSellerBooks();
  await loadSellerDashboard();
}

// Xóa hàng loạt sách đã chọn
async function bulkDeleteBooks() {
  const count = sellerState.selectedBookIds.size;
  if (count === 0) return;

  if (!confirm(`Bạn có chắc chắn muốn xóa ${count} cuốn sách đã chọn khỏi gian hàng?`)) return;

  let deletedCount = 0;
  for (const bookId of sellerState.selectedBookIds) {
    try {
      await apiCall(`/api/seller/books/${bookId}`, { method: 'DELETE' });
      deletedCount++;
    } catch (e) {}
  }

  showToast(`Đã xóa thành công ${deletedCount} cuốn sách!`, 'success');
  deselectAllSellerBooks();
  await loadSellerBooks();
  await loadSellerDashboard();
}

// Xuất file CSV Kho Sách
function exportSellerBooksCSV() {
  if (!sellerState.books || sellerState.books.length === 0) {
    showToast('Kho sách hiện đang trống để xuất CSV', 'warning');
    return;
  }

  const rows = [
    ['ID', 'Ten_Sach', 'Tac_Gia', 'The_Loai', 'Gia_Niem_Yet', 'Gia_Khuyen_Mai', 'Ton_Kho', 'Da_Ban', 'Trang_Thai', 'ISBN']
  ];

  sellerState.books.forEach(b => {
    rows.push([
      b.id,
      `"${(b.title || '').replace(/"/g, '""')}"`,
      `"${(b.author || '').replace(/"/g, '""')}"`,
      `"${(b.category_name || '').replace(/"/g, '""')}"`,
      b.price,
      b.discount_price || b.price,
      b.stock,
      b.sold_count || 0,
      b.status,
      `"${b.isbn || ''}"`
    ]);
  });

  const csvContent = '\uFEFF' + rows.map(r => r.join(',')).join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `Kho_Sach_${new Date().toISOString().slice(0,10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToast('Đã xuất file CSV kho sách thành công!', 'success');
}

function openAddBookModal() {
  if (!state.currentUser) {
    requireLoginForAction('Đăng sách mới');
    return;
  }

  const catSelect = document.getElementById('new-book-category');
  if (catSelect) {
    let html = '';
    state.categories.forEach(c => {
      html += `<option value="${c.id}">${c.name}</option>`;
    });
    catSelect.innerHTML = html;
  }

  document.getElementById('add-book-modal').classList.add('open');
}

async function submitNewBook() {
  const title = document.getElementById('new-book-title').value.trim();
  const author = document.getElementById('new-book-author').value.trim();
  const translator = document.getElementById('new-book-translator')?.value.trim() || null;
  const category_id = parseInt(document.getElementById('new-book-category').value);
  const price = parseFloat(document.getElementById('new-book-price').value);
  const discount_price = parseFloat(document.getElementById('new-book-discount').value) || null;
  const stock = parseInt(document.getElementById('new-book-stock').value) || 10;
  const isbn = document.getElementById('new-book-isbn')?.value.trim() || null;
  const publication_year = parseInt(document.getElementById('new-book-year')?.value) || 2024;
  const page_count = parseInt(document.getElementById('new-book-pages')?.value) || null;
  const book_format = document.getElementById('new-book-format')?.value || 'PAPER';
  const cover_type = document.getElementById('new-book-cover-type')?.value || 'SOFT';
  const language = document.getElementById('new-book-language')?.value.trim() || 'Tiếng Việt';
  const cover_image = document.getElementById('new-book-cover').value.trim();
  const description = document.getElementById('new-book-desc').value.trim();
  const sample_content = document.getElementById('new-book-sample').value.trim();
  const full_ebook_content = document.getElementById('new-book-full-ebook')?.value.trim() || null;

  if (!title || !author || !price) {
    showToast('Vui lòng điền tên sách, tác giả và giá bán niêm yết', 'warning');
    return;
  }

  const payload = {
    title, author, translator, category_id, price, discount_price, stock,
    isbn, publication_year, page_count, book_format, cover_type, language,
    cover_image, description, sample_content, full_ebook_content
  };

  try {
    await apiCall('/api/seller/books', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    showToast(`Đã đăng tải thành công cuốn sách "${title}"!`, 'success');
    closeModal('add-book-modal');
    await loadSellerBooks();
    await loadSellerDashboard();
  } catch (e) {}
}

function openEditBookModal(bookId) {
  const book = sellerState.books.find(b => b.id === bookId);
  if (!book) return;

  document.getElementById('edit-book-id').value = book.id;
  document.getElementById('edit-book-title').value = book.title;
  document.getElementById('edit-book-author').value = book.author;
  if (document.getElementById('edit-book-translator')) document.getElementById('edit-book-translator').value = book.translator || '';
  if (document.getElementById('edit-book-isbn')) document.getElementById('edit-book-isbn').value = book.isbn || '';
  if (document.getElementById('edit-book-year')) document.getElementById('edit-book-year').value = book.publication_year || 2024;
  if (document.getElementById('edit-book-pages')) document.getElementById('edit-book-pages').value = book.page_count || '';
  document.getElementById('edit-book-price').value = book.price;
  document.getElementById('edit-book-discount').value = book.discount_price || '';
  document.getElementById('edit-book-stock').value = book.stock;
  document.getElementById('edit-book-cover').value = book.cover_image || '';
  document.getElementById('edit-book-desc').value = book.description || '';
  document.getElementById('edit-book-sample').value = book.sample_content || '';

  const catSelect = document.getElementById('edit-book-category');
  if (catSelect) {
    let html = '';
    state.categories.forEach(c => {
      html += `<option value="${c.id}" ${c.id === book.category_id ? 'selected' : ''}>${c.name}</option>`;
    });
    catSelect.innerHTML = html;
  }

  document.getElementById('edit-book-modal').classList.add('open');
}

async function submitEditBook() {
  const bookId = parseInt(document.getElementById('edit-book-id').value);
  const title = document.getElementById('edit-book-title').value.trim();
  const author = document.getElementById('edit-book-author').value.trim();
  const translator = document.getElementById('edit-book-translator')?.value.trim() || null;
  const category_id = parseInt(document.getElementById('edit-book-category').value);
  const price = parseFloat(document.getElementById('edit-book-price').value);
  const discount_price = parseFloat(document.getElementById('edit-book-discount').value) || null;
  const stock = parseInt(document.getElementById('edit-book-stock').value) || 0;
  const isbn = document.getElementById('edit-book-isbn')?.value.trim() || null;
  const publication_year = parseInt(document.getElementById('edit-book-year')?.value) || 2024;
  const page_count = parseInt(document.getElementById('edit-book-pages')?.value) || null;
  const cover_image = document.getElementById('edit-book-cover').value.trim();
  const description = document.getElementById('edit-book-desc').value.trim();
  const sample_content = document.getElementById('edit-book-sample').value.trim();

  if (!title || !author || !price) {
    showToast('Vui lòng điền đầy đủ tên sách, tác giả và giá bán', 'warning');
    return;
  }

  const payload = {
    title, author, translator, category_id, price, discount_price, stock,
    isbn, publication_year, page_count, cover_image, description, sample_content
  };

  try {
    await apiCall(`/api/seller/books/${bookId}`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    });
    showToast('Cập nhật thông tin sách thành công!', 'success');
    closeModal('edit-book-modal');
    await loadSellerBooks();
    await loadSellerDashboard();
  } catch (e) {}
}

async function deleteBookBySeller(bookId) {
  if (!confirm('Bạn có chắc chắn muốn xóa cuốn sách này khỏi kho của gian hàng?')) return;
  try {
    const res = await apiCall(`/api/seller/books/${bookId}`, { method: 'DELETE' });
    showToast(res.message, 'success');
    await loadSellerBooks();
    await loadSellerDashboard();
  } catch (e) {}
}


// =============================================================
// TAB 3: 📦 QUẢN LÝ ĐƠN HÀNG & VẬN ĐƠN (ORDERS & FULFILLMENT)
// =============================================================
async function loadSellerOrders() {
  try {
    const status = sellerState.orderStatusFilter;
    let url = '/api/seller/orders';
    if (status && status !== 'ALL') {
      url += `?status_filter=${status}`;
    }

    const orders = await apiCall(url);
    sellerState.orders = orders;

    // Tải tất cả đơn để cập nhật count badge
    if (status === 'ALL') {
      updateSellerOrderCounts(orders);
    } else {
      apiCall('/api/seller/orders').then(allOrders => updateSellerOrderCounts(allOrders)).catch(()=>{});
    }

    await loadSellerReturnRequests();
    filterSellerOrdersUI();
  } catch (e) {
    console.error('Lỗi khi tải đơn hàng seller:', e);
  }
}

async function loadSellerReturnRequests() {
  try {
    const list = await apiCall('/api/seller/returns');
    const root = document.getElementById('seller-return-requests-list');
    if (!root) return;

    if (!list || list.length === 0) {
      root.innerHTML = '<div style="padding: 16px; color: #64748b;">Chưa có yêu cầu trả hàng nào cho gian hàng của bạn.</div>';
      return;
    }

    root.innerHTML = list.map(item => `
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; padding:14px 16px; border:1px solid #e2e8f0; border-radius:10px; background:#f8fafc; margin-bottom:10px;">
        <div>
          <div style="font-weight:800; color:#1e293b; margin-bottom:6px;">#${item.id} • Đơn ${item.order_id}</div>
          <div style="font-size:12px; color:#475569; margin-bottom:4px;">Lý do: <b>${item.reason}</b></div>
          <div style="font-size:12px; color:#475569; margin-bottom:4px;">Số tiền hoàn dự kiến: <b>${formatVND(item.refund_amount)}</b></div>
          <div style="font-size:12px; color:#475569;">Trạng thái: <span class="badge ${item.status === 'PENDING' ? 'badge-warning' : item.status === 'REJECTED' ? 'badge-danger' : item.status === 'REFUNDED' ? 'badge-success' : 'badge-info'}">${item.status}</span></div>
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end;">
          ${item.status === 'PENDING' ? `<button class="btn-success" style="padding:5px 10px; font-size:12px;" onclick="handleSellerReturnAction(${item.id}, 'approve')">Duyệt</button>` : ''}
          ${item.status === 'PENDING' ? `<button class="btn-danger" style="padding:5px 10px; font-size:12px;" onclick="handleSellerReturnAction(${item.id}, 'reject')">Từ chối</button>` : ''}
        </div>
      </div>
    `).join('');
  } catch (error) {
    const root = document.getElementById('seller-return-requests-list');
    if (root) root.innerHTML = `<div style="padding:16px; color:#dc2626;">Không thể tải yêu cầu trả hàng: ${error.message}</div>`;
  }
}

async function handleSellerReturnAction(returnId, action) {
  try {
    let payload = undefined;
    if (action === 'reject') {
      const rejectionReason = prompt('Nhập lý do từ chối yêu cầu trả hàng:');
      if (rejectionReason === null || !rejectionReason.trim()) {
        showToast('Bạn phải nhập lý do từ chối trước khi tiếp tục.', 'warning');
        return;
      }
      payload = JSON.stringify({ rejection_reason: rejectionReason.trim() });
    }

    const endpoint = action === 'approve' ? `/api/seller/returns/${returnId}/approve` : `/api/seller/returns/${returnId}/reject`;
    await apiCall(endpoint, { method: 'PATCH', body: payload });
    showToast(action === 'approve' ? 'Đã duyệt yêu cầu trả hàng.' : 'Đã từ chối yêu cầu trả hàng.', 'success');
    await loadSellerOrders();
    await loadSellerDashboard();
  } catch (error) {
    showToast(error.message || 'Không thể cập nhật yêu cầu trả hàng.', 'error');
  }
}

function filterSellerOrdersUI() {
  const search = (document.getElementById('seller-order-search-input')?.value || '').toLowerCase().trim();
  const container = document.getElementById('seller-orders-table-body');
  if (!container) return;

  let filtered = sellerState.orders.filter(o => {
    if (!search) return true;
    const matchCode = (o.order_code || '').toLowerCase().includes(search);
    const matchName = (o.shipping_name || '').toLowerCase().includes(search);
    const matchPhone = (o.shipping_phone || '').toLowerCase().includes(search);
    const matchCarrier = (o.shipping_carrier || '').toLowerCase().includes(search);
    const matchTracking = (o.tracking_number || '').toLowerCase().includes(search);
    return matchCode || matchName || matchPhone || matchCarrier || matchTracking;
  });

  if (filtered.length === 0) {
    container.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:30px; color:#94a3b8;">Không tìm thấy đơn hàng nào phù hợp</td></tr>`;
    return;
  }

  let html = '';
  filtered.forEach(o => {
    let actionBtns = '';
    if (o.status === 'PENDING') {
      actionBtns = `
        <button class="btn-success" style="padding:6px 10px; font-size:12px; width:100%; margin-bottom:4px;" onclick="advanceOrderStatus(${o.id}, 'PACKING')">
          📦 Xác Nhận Đóng Gói
        </button>
      `;
    } else if (o.status === 'PACKING') {
      actionBtns = `
        <button class="btn-primary" style="padding:6px 10px; font-size:12px; width:100%; margin-bottom:4px;" onclick="advanceOrderStatus(${o.id}, 'SHIPPING')">
          🚚 Giao Shipper GHN
        </button>
      `;
    } else if (o.status === 'SHIPPING') {
      actionBtns = `
        <button class="btn-success" style="padding:6px 10px; font-size:12px; width:100%; margin-bottom:4px;" onclick="advanceOrderStatus(${o.id}, 'DELIVERED')">
          ✅ Đã Giao Thành Công
        </button>
      `;
    } else if (o.return_status === 'REQUESTED') {
      actionBtns = `
        <div style="display:flex; gap:4px; margin-bottom:4px;">
          <button class="btn-success" style="padding:4px 8px; font-size:11px; flex:1;" onclick="handleSellerOrderReturn(${o.id}, 'APPROVE')">Duyệt Đổi</button>
          <button class="btn-danger" style="padding:4px 8px; font-size:11px; flex:1;" onclick="handleSellerOrderReturn(${o.id}, 'REJECT')">Từ Chối</button>
        </div>
      `;
    } else {
      actionBtns = `<span class="badge badge-success" style="display:inline-block; margin-bottom:4px;">Giao hoàn tất</span>`;
    }

    // Nút in phiếu gửi hàng
    actionBtns += `
      <button class="btn-preview" style="padding:4px 8px; font-size:11px; width:100%; justify-content:center;" onclick="openShippingLabelModal(${o.id})">
        🖨️ In Vận Đơn GHN
      </button>
    `;

    let statusBadge = '<span class="badge badge-warning">Chờ xử lý</span>';
    if (o.status === 'PACKING') statusBadge = '<span class="badge badge-info">Đang đóng gói</span>';
    if (o.status === 'SHIPPING') statusBadge = '<span class="badge badge-info">Đang vận chuyển</span>';
    if (o.status === 'DELIVERED') statusBadge = '<span class="badge badge-success">Giao thành công</span>';
    if (o.status === 'CANCELLED') statusBadge = '<span class="badge badge-danger">Đã hủy</span>';
    if (o.return_status === 'REQUESTED') statusBadge = '<span class="badge badge-danger">🔄 Khách yêu cầu đổi trả</span>';

    html += `
      <tr>
        <td>
          <div style="font-weight:800; color:#1e293b; font-size:14px;">${o.order_code}</div>
          <div style="font-size:11px; color:#64748b;">${new Date(o.created_at).toLocaleDateString('vi-VN')} ${new Date(o.created_at).toLocaleTimeString('vi-VN', {hour:'2-digit', minute:'2-digit'})}</div>
          <div style="font-size:10px; color:#4f46e5; margin-top:2px;">TT: ${o.payment_method} (${o.payment_status === 'PAID' ? 'Đã TT' : 'Thu COD'})</div>
        </td>
        <td>
          <div style="font-weight:700;">${o.shipping_name} - ${o.shipping_phone}</div>
          <div style="font-size:11px; color:#64748b; margin-top:2px;">📍 ${o.shipping_address}</div>
        </td>
        <td>
          <div class="seller-order-items-mini">
            ${o.items.map(it => `
              <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px; font-size:12px;">
                <img src="${it.book_cover || 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&q=80&w=80'}" style="width:24px; height:32px; object-fit:cover; border-radius:3px;">
                <span>${it.book_title} (x<b>${it.quantity}</b>)</span>
              </div>
            `).join('')}
          </div>
        </td>
        <td>
          <div style="font-size:13px;">Tổng: <b>${formatVND(o.seller_total)}</b></div>
          <div style="font-size:11px; color:#10b981; font-weight:700; margin-top:2px;">Thực nhận 90%: ${formatVND(o.seller_net)}</div>
          <div style="font-size:10px; color:#94a3b8;">Phí sàn 10%: ${formatVND(o.seller_fee)}</div>
        </td>
        <td>
          <div style="margin-bottom:4px;">${statusBadge}</div>
          <div style="font-size:11px; color:#475569;">🚚 ${o.shipping_carrier || 'GHN Express'}</div>
          <div style="font-size:10px; font-family:monospace; color:#2563eb;">Mã VĐ: ${o.tracking_number || 'Chưa tạo'}</div>
        </td>
        <td>
          ${actionBtns}
        </td>
      </tr>
    `;
  });
  container.innerHTML = html;
}

function updateSellerOrderCounts(orders) {
  const countAll = orders.length;
  const countPending = orders.filter(o => o.status === 'PENDING').length;
  const countPacking = orders.filter(o => o.status === 'PACKING').length;
  const countShipping = orders.filter(o => o.status === 'SHIPPING').length;
  const countDelivered = orders.filter(o => o.status === 'DELIVERED').length;
  const countReturn = orders.filter(o => (o.return_status === 'REQUESTED' || o.return_status === 'APPROVED')).length;
  const countCancelled = orders.filter(o => o.status === 'CANCELLED').length;

  if (document.getElementById('order-count-all')) document.getElementById('order-count-all').textContent = countAll;
  if (document.getElementById('order-count-pending')) document.getElementById('order-count-pending').textContent = countPending;
  if (document.getElementById('order-count-packing')) document.getElementById('order-count-packing').textContent = countPacking;
  if (document.getElementById('order-count-shipping')) document.getElementById('order-count-shipping').textContent = countShipping;
  if (document.getElementById('order-count-delivered')) document.getElementById('order-count-delivered').textContent = countDelivered;
  if (document.getElementById('order-count-return')) document.getElementById('order-count-return').textContent = countReturn;
  if (document.getElementById('order-count-cancelled')) document.getElementById('order-count-cancelled').textContent = countCancelled;
}

function setSellerOrderStatusFilter(status, btn) {
  sellerState.orderStatusFilter = status;
  document.querySelectorAll('.order-tab-btn').forEach(b => b.classList.remove('active'));
  if (btn) {
    btn.classList.add('active');
  } else {
    const targetBtn = document.querySelector(`.order-tab-btn[data-status="${status}"]`);
    if (targetBtn) targetBtn.classList.add('active');
  }
  loadSellerOrders();
}

async function advanceOrderStatus(orderId, nextStatus) {
  try {
    const res = await apiCall(`/api/seller/orders/${orderId}/update-status?new_status=${nextStatus}`, { method: 'POST' });
    showToast(res.message, 'success');
    await loadSellerOrders();
    await loadSellerDashboard();
  } catch (e) {}
}

// Xác nhận hàng loạt tất cả các đơn hàng PENDING
async function bulkConfirmOrdersUI() {
  const pendingOrders = sellerState.orders.filter(o => o.status === 'PENDING');
  if (pendingOrders.length === 0) {
    showToast('Hiện không có đơn hàng nào đang ở trạng thái Chờ xác nhận', 'info');
    return;
  }

  if (!confirm(`Bạn có muốn tự động xác nhận và chuyển sang đóng gói cho ${pendingOrders.length} đơn hàng chờ?`)) return;

  const orderIds = pendingOrders.map(o => o.id);
  try {
    const res = await apiCall('/api/seller/orders/bulk-confirm', {
      method: 'POST',
      body: JSON.stringify({ order_ids: orderIds })
    });
    showToast(res.message, 'success');
    await loadSellerOrders();
    await loadSellerDashboard();
  } catch (e) {}
}

// Xuất file CSV danh sách đơn hàng
function exportSellerOrdersCSV() {
  if (!sellerState.orders || sellerState.orders.length === 0) {
    showToast('Chưa có đơn hàng nào để xuất file CSV', 'warning');
    return;
  }

  const rows = [
    ['Ma_Don', 'Ngay_Dat', 'Khach_Hang', 'SDT', 'Dia_Chi', 'Tong_Tien', 'Thuc_Nhan_90', 'Trang_Thai', 'Van_Don', 'Thanh_Toan']
  ];

  sellerState.orders.forEach(o => {
    rows.push([
      `"${o.order_code}"`,
      `"${new Date(o.created_at).toLocaleDateString('vi-VN')}"`,
      `"${(o.shipping_name || '').replace(/"/g, '""')}"`,
      `"${o.shipping_phone || ''}"`,
      `"${(o.shipping_address || '').replace(/"/g, '""')}"`,
      o.seller_total,
      o.seller_net,
      o.status,
      `"${o.tracking_number || ''}"`,
      o.payment_method
    ]);
  });

  const csvContent = '\uFEFF' + rows.map(r => r.join(',')).join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `Don_Hang_${new Date().toISOString().slice(0,10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToast('Đã xuất file CSV đơn hàng thành công!', 'success');
}

async function handleSellerOrderReturn(orderId, action) {
  try {
    const res = await apiCall(`/api/seller/orders/${orderId}/handle-return?action=${action}`, { method: 'POST' });
    showToast(res.message, 'success');
    await loadSellerOrders();
    await loadSellerDashboard();
  } catch (e) {}
}

// In phiếu giao nhận hàng (Shipping Label)
function openShippingLabelModal(orderId) {
  const order = sellerState.orders.find(o => o.id === orderId);
  if (!order) return;

  const profile = sellerState.profile || {};
  const warehouse = profile.warehouse_address || 'Kho 1: 55 Quang Trung, P. Nguyễn Du, Q. Hai Bà Trưng, Hà Nội';
  const shopName = profile.shop_name || state.currentUser?.shop_name || 'NXB Kim Đồng Official';
  const phoneSender = state.currentUser?.phone || '0243 943 4730';

  const container = document.getElementById('shipping-label-print-area');
  if (!container) return;

  const formattedTracking = order.tracking_number || `VN-${String(order.id).padStart(6, '0')}-GHN`;

  container.innerHTML = `
    <div class="shipping-label-paper" id="printable-shipping-slip">
      <div class="label-header">
        <div class="label-brand">
          <h2>Book<span>Hub</span> EXPRESS</h2>
          <p>Sàn Thương Mại Điện Tử Sách Chính Hãng</p>
        </div>
        <div class="label-carrier-badge">
          <b>${order.shipping_carrier || 'GIAO HÀNG NHANH (GHN)'}</b>
          <div>Mã Vận Đơn: <b>${formattedTracking}</b></div>
        </div>
      </div>

      <!-- Simulated Barcode & QR code -->
      <div class="label-barcode-row">
        <div class="barcode-visual">
          <div class="barcode-lines">||| | |||| || | ||||| || ||| |||| | || |||</div>
          <div class="barcode-num">${order.order_code}</div>
        </div>
        <div class="label-qr-visual">
          <div class="mock-qr">▣▤▥</div>
          <span>Scan GHN</span>
        </div>
      </div>

      <!-- Sender & Receiver Grid -->
      <div class="label-address-grid">
        <div class="label-address-col">
          <div class="addr-title">TỪ (NGƯỜI GỬI):</div>
          <div class="addr-name">${shopName}</div>
          <div class="addr-phone">SĐT: ${phoneSender}</div>
          <div class="addr-detail">Địa chỉ: ${warehouse}</div>
        </div>
        <div class="label-address-col">
          <div class="addr-title">ĐẾN (NGƯỜI NHẬN):</div>
          <div class="addr-name">${order.shipping_name}</div>
          <div class="addr-phone">SĐT: ${order.shipping_phone}</div>
          <div class="addr-detail">Địa chỉ: ${order.shipping_address}</div>
        </div>
      </div>

      <!-- Item Checklist -->
      <div class="label-items-table">
        <div style="font-weight:700; font-size:12px; margin-bottom:6px; border-bottom:1px solid #000; padding-bottom:4px;">
          DANH SÁCH SÁCH ĐÓNG GÓI (${order.items.reduce((s,i)=>s+i.quantity, 0)} cuốn):
        </div>
        ${order.items.map((it, idx) => `
          <div style="display:flex; justify-content:space-between; font-size:11px; padding:3px 0;">
            <span>${idx + 1}. ${it.book_title}</span>
            <span>SL: <b>${it.quantity}</b></span>
          </div>
        `).join('')}
      </div>

      <!-- COD & Signature -->
      <div class="label-footer-grid">
        <div class="label-cod-box">
          <div style="font-size:11px;">TIỀN THU NGƯỜI NHẬN (COD):</div>
          <div style="font-size:18px; font-weight:800; color:#000;">
            ${order.payment_method === 'COD' ? formatVND(order.seller_total) : '0 đ (ĐÃ THANH TOÁN ONLINE)'}
          </div>
        </div>
        <div class="label-signature-box">
          <div>Chữ ký người nhận</div>
          <small>(Xác nhận sách nguyên vẹn, không móp rách)</small>
        </div>
      </div>
    </div>
  `;

  document.getElementById('shipping-label-modal').classList.add('open');
}

function printShippingLabelContent() {
  window.print();
}


// =============================================================
// TAB 4: 🏷️ KHUYẾN MÃI & MARKETING (MARKETING CENTER)
// =============================================================
async function loadSellerMarketing() {
  await loadSellerVouchers();
  renderSellerAdsSummary();
  renderSellerReviews();
}

async function loadSellerVouchers() {
  try {
    const vouchers = await apiCall('/api/seller/vouchers');
    sellerState.vouchers = vouchers;

    // Cập nhật thẻ thống kê Voucher
    const activeCount = vouchers.filter(v => v.is_active).length;
    const usedTotal = vouchers.reduce((acc, v) => acc + (v.used_count || 0), 0);
    const activeAds = (sellerState.books || []).filter(b => b.is_featured_ad).length;

    const activeVouchersCountElem = document.getElementById('mkt-active-vouchers-count');
    if (activeVouchersCountElem) activeVouchersCountElem.textContent = `${activeCount} mã`;
    const usedVouchersCountElem = document.getElementById('mkt-used-vouchers-count');
    if (usedVouchersCountElem) usedVouchersCountElem.textContent = `${usedTotal} lượt`;
    const activeAdsCountElem = document.getElementById('mkt-active-ads-count');
    if (activeAdsCountElem) activeAdsCountElem.textContent = `${activeAds} cuốn`;

    const container = document.getElementById('seller-vouchers-table-body');
    if (!container) return;

    if (vouchers.length === 0) {
      container.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:20px; color:#94a3b8;">Chưa tạo mã voucher nào. Hãy bấm "Tạo Mã Voucher Mới" để tăng doanh thu!</td></tr>`;
      return;
    }

    let html = '';
    vouchers.forEach(v => {
      let discountText = v.discount_type === 'PERCENT' ? `${v.discount_value}%` : formatVND(v.discount_value);
      let expiryText = v.expires_at ? new Date(v.expires_at).toLocaleDateString('vi-VN') : 'Không thời hạn';
      let isActive = v.is_active ? '<span class="badge badge-success">Đang phát hành</span>' : '<span class="badge badge-danger">Đã kết thúc</span>';

      html += `
        <tr>
          <td>
            <div style="display:flex; align-items:center; gap:6px;">
              <b style="font-family:monospace; font-size:14px; color:#4f46e5; background:#eef2ff; padding:3px 8px; border-radius:4px;">${v.code}</b>
              <button class="btn-sm btn-outline" style="padding:2px 6px; font-size:10px;" onclick="copyVoucherCode('${v.code}')" title="Sao chép mã">📋</button>
            </div>
          </td>
          <td><b>${v.name}</b></td>
          <td><b style="color:#ef4444;">${discountText}</b></td>
          <td>${formatVND(v.min_order_amount)}</td>
          <td>${v.used_count} / ${v.usage_limit || '∞'} lượt</td>
          <td>${expiryText}</td>
          <td>${isActive}</td>
          <td>
            <button class="btn-danger" style="padding:4px 8px; font-size:11px;" onclick="deleteSellerVoucher(${v.id})">🗑️ Xóa</button>
          </td>
        </tr>
      `;
    });
    container.innerHTML = html;
  } catch (e) {}
}

function copyVoucherCode(code) {
  navigator.clipboard.writeText(code).then(() => {
    showToast(`Đã sao chép mã voucher "${code}" vào clipboard!`, 'success');
  }).catch(() => {
    showToast(`Mã voucher: ${code}`, 'info');
  });
}

function openAddVoucherModal() {
  if (!state.currentUser) {
    requireLoginForAction('Tạo mã voucher');
    return;
  }
  document.getElementById('voucher-code-input').value = '';
  document.getElementById('voucher-name-input').value = '';
  document.getElementById('voucher-value-input').value = '';
  document.getElementById('add-voucher-modal').classList.add('open');
}

async function submitCreateVoucher() {
  const code = document.getElementById('voucher-code-input').value.trim().toUpperCase();
  const name = document.getElementById('voucher-name-input').value.trim();
  const discount_type = document.getElementById('voucher-type-input').value;
  const discount_value = parseFloat(document.getElementById('voucher-value-input').value);
  const min_order_amount = parseFloat(document.getElementById('voucher-minorder-input').value) || 0;
  const usage_limit = parseInt(document.getElementById('voucher-limit-input').value) || 100;
  const days = parseInt(document.getElementById('voucher-duration-input').value) || 30;

  if (!code || !name || !discount_value) {
    showToast('Vui lòng điền mã code, tên chương trình và mức giảm giá', 'warning');
    return;
  }

  const payload = {
    code,
    name,
    discount_type,
    discount_value,
    min_order_amount,
    usage_limit
  };

  try {
    await apiCall('/api/seller/vouchers', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    showToast(`Đã phát hành mã voucher ${code} thành công!`, 'success');
    closeModal('add-voucher-modal');
    await loadSellerVouchers();
  } catch (e) {}
}

async function deleteSellerVoucher(voucherId) {
  if (!confirm('Bạn có chắc muốn xóa mã voucher này?')) return;
  try {
    const res = await apiCall(`/api/seller/vouchers/${voucherId}`, { method: 'DELETE' });
    showToast(res.message, 'success');
    await loadSellerVouchers();
  } catch (e) {}
}

// Flash Sale Creator Modal
async function openFlashSaleModal() {
  if (!state.currentUser) {
    requireLoginForAction('Tạo Flash Sale');
    return;
  }

  // Đảm bảo sách đã được tải
  if (sellerState.books.length === 0) {
    await loadSellerBooks();
  }

  const select = document.getElementById('flash-sale-book-select');
  if (!select) return;

  if (sellerState.books.length === 0) {
    showToast('Gian hàng chưa có sách nào. Vui lòng đăng sách trước!', 'warning');
    return;
  }

  let html = '<option value="">-- Chọn cuốn sách áp dụng Flash Sale --</option>';
  sellerState.books.forEach(b => {
    html += `<option value="${b.id}">${b.title} (Giá gốc: ${formatVND(b.price)})</option>`;
  });
  select.innerHTML = html;

  document.getElementById('flash-sale-book-info').style.display = 'none';
  document.getElementById('flash-sale-price-input').value = '';
  document.getElementById('flash-sale-modal').classList.add('open');
}

function updateFlashSaleBookDetails() {
  const bookId = parseInt(document.getElementById('flash-sale-book-select').value);
  const infoBox = document.getElementById('flash-sale-book-info');
  if (!bookId) {
    infoBox.style.display = 'none';
    return;
  }

  const book = sellerState.books.find(b => b.id === bookId);
  if (!book) return;

  infoBox.style.display = 'block';
  document.getElementById('flash-sale-book-img').src = book.cover_image || '';
  document.getElementById('flash-sale-book-title-display').textContent = book.title;
  document.getElementById('flash-sale-original-price').textContent = formatVND(book.price);
  document.getElementById('flash-sale-book-stock').textContent = `${book.stock} cuốn`;

  calculateFlashSalePrice();
}

function calculateFlashSalePrice() {
  const bookId = parseInt(document.getElementById('flash-sale-book-select').value);
  const percent = parseFloat(document.getElementById('flash-sale-percent-input').value) || 0;
  if (!bookId) return;

  const book = sellerState.books.find(b => b.id === bookId);
  if (!book) return;

  const discounted = Math.round(book.price * (1 - percent / 100));
  document.getElementById('flash-sale-price-input').value = discounted;
}

async function submitFlashSale() {
  const bookId = parseInt(document.getElementById('flash-sale-book-select').value);
  const discountedPrice = parseFloat(document.getElementById('flash-sale-price-input').value);
  const hours = parseInt(document.getElementById('flash-sale-hours-select').value);
  const percent = parseFloat(document.getElementById('flash-sale-percent-input').value);

  if (!bookId || !discountedPrice) {
    showToast('Vui lòng chọn cuốn sách áp dụng Flash Sale', 'warning');
    return;
  }

  const book = sellerState.books.find(b => b.id === bookId);
  if (!book) return;

  try {
    await apiCall(`/api/seller/books/${bookId}`, {
      method: 'PUT',
      body: JSON.stringify({
        title: book.title,
        author: book.author,
        category_id: book.category_id,
        price: book.price,
        discount_price: discountedPrice,
        stock: book.stock
      })
    });
    showToast(`🔥 Đã kích hoạt Flash Sale giảm ${percent}% cho "${book.title}" trong ${hours} giờ!`, 'success');
    closeModal('flash-sale-modal');
    await loadSellerBooks();
    await loadSellerDashboard();
  } catch (e) {}
}

// Render các chiến dịch quảng cáo
function renderSellerAdsSummary() {
  const container = document.getElementById('seller-active-ads-list');
  if (!container) return;

  const featuredBooks = (sellerState.books || []).filter(b => b.is_featured_ad);

  if (featuredBooks.length === 0) {
    container.innerHTML = `
      <div style="background:#fff7ed; border:1px solid #fed7aa; border-radius:8px; padding:20px; text-align:center; color:#9a3412;">
        <div style="font-size:24px; margin-bottom:6px;">🚀</div>
        <div style="font-weight:700; font-size:15px;">Bạn chưa chạy chiến dịch Quảng Cáo Ghim Top nào</div>
        <p style="font-size:12px; margin:6px 0 12px; color:#c2410c;">Ghim sách lên đầu trang chủ để tăng 300% lượt đọc thử và đặt mua ngay hôm nay.</p>
        <button class="btn-vip-gold" onclick="switchSellerTab('products')">Khám Phá Sách & Đẩy Top Ngay</button>
      </div>
    `;
    return;
  }

  let html = '';
  featuredBooks.forEach(b => {
    html += `
      <div class="seller-ad-card">
        <img src="${b.cover_image}" class="ad-card-cover">
        <div class="ad-card-info">
          <span class="badge badge-warning" style="font-size:10px;">⭐ ĐANG CHẠY ADS</span>
          <div style="font-weight:700; font-size:14px; margin-top:4px;">${b.title}</div>
          <div style="font-size:12px; color:#64748b;">Vị trí: Ghim Đầu Trang Chủ BookHub</div>
          <div style="font-size:11px; color:#10b981; margin-top:4px;">Hiệu quả: +1.240 lượt xem | Đã bán: ${b.sold_count} cuốn</div>
        </div>
      </div>
    `;
  });
  container.innerHTML = html;
}

// Render trung tâm phản hồi đánh giá
function renderSellerReviews() {
  const container = document.getElementById('seller-reviews-list');
  if (!container) return;

  const mockReviews = [
    { id: 1, user: 'Độc giả An', rating: 5, book: 'Dế Mèn Phiêu Lưu Ký', comment: 'Sách in đẹp, giấy xịn, bìa cứng đóng gói cẩn thận không bị móp góc. Giao nhanh 1 ngày là có!', time: '2 giờ trước' },
    { id: 2, user: 'Minh Thư VIP', rating: 5, book: 'Kính Vạn Hoa - Tập 1', comment: 'Bộ truyện tuổi thơ tuyệt vời, NXB Kim Đồng tái bản bìa rất đẹp. Sẽ ủng hộ tiếp!', time: '1 ngày trước' }
  ];

  let html = '';
  mockReviews.forEach(r => {
    html += `
      <div class="seller-review-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <div>
            <b>${r.user}</b> <span style="color:#f59e0b;">${'⭐'.repeat(r.rating)}</span>
            <span style="font-size:12px; color:#64748b; margin-left:8px;">sách <i>${r.book}</i></span>
          </div>
          <span style="font-size:11px; color:#94a3b8;">${r.time}</span>
        </div>
        <div style="font-size:13px; color:#334155; margin-bottom:8px;">"${r.comment}"</div>
        <div style="display:flex; gap:8px;">
          <input type="text" class="form-control" style="font-size:12px; padding:4px 8px;" placeholder="Nhập câu trả lời của NXB..." id="reply-input-${r.id}">
          <button class="btn-primary" style="padding:4px 12px; font-size:12px;" onclick="showToast('Đã gửi phản hồi đến độc giả thành công!', 'success')">Gửi</button>
        </div>
      </div>
    `;
  });
  container.innerHTML = html;
}


// =============================================================
// TAB 5: ⚙️ CÀI ĐẶT GIAN HÀNG & TÀI CHÍNH (SETTINGS & PROFILE)
// =============================================================
async function loadSellerSettings() {
  try {
    const profile = await apiCall('/api/seller/profile');
    sellerState.profile = profile;

    // Điền form hồ sơ
    if (document.getElementById('seller-set-shopname')) document.getElementById('seller-set-shopname').value = profile.shop_name || '';
    if (document.getElementById('seller-set-desc')) document.getElementById('seller-set-desc').value = profile.shop_description || '';
    if (document.getElementById('seller-set-license')) document.getElementById('seller-set-license').value = profile.business_license || '';
    if (document.getElementById('seller-set-warehouse')) document.getElementById('seller-set-warehouse').value = profile.warehouse_address || '';
    if (document.getElementById('seller-set-logo')) {
      document.getElementById('seller-set-logo').value = profile.shop_logo || '';
      previewShopLogo(profile.shop_logo || '');
    }
    if (document.getElementById('seller-set-banner')) {
      document.getElementById('seller-set-banner').value = profile.shop_banner || '';
      previewShopBanner(profile.shop_banner || '');
    }

    // Điền form tài chính
    if (document.getElementById('seller-set-tax')) document.getElementById('seller-set-tax').value = profile.tax_code || '0101234567-001';
    if (document.getElementById('seller-set-bankname')) document.getElementById('seller-set-bankname').value = profile.bank_name || 'Vietcombank';
    if (document.getElementById('seller-set-accountnumber')) document.getElementById('seller-set-accountnumber').value = profile.bank_account_number || '0071001234567';
    if (document.getElementById('seller-set-accountholder')) document.getElementById('seller-set-accountholder').value = profile.bank_account_holder || profile.shop_name || '';

    await loadSellerStaff();
  } catch (e) {}
}

function previewShopLogo(url) {
  const box = document.getElementById('seller-logo-preview-box');
  const img = document.getElementById('seller-logo-preview-img');
  if (box && img) {
    if (url && url.trim()) {
      img.src = url.trim();
      box.style.display = 'block';
    } else {
      box.style.display = 'none';
    }
  }
}

function previewShopBanner(url) {
  const box = document.getElementById('seller-banner-preview-box');
  const img = document.getElementById('seller-banner-preview-img');
  if (box && img) {
    if (url && url.trim()) {
      img.src = url.trim();
      box.style.display = 'block';
    } else {
      box.style.display = 'none';
    }
  }
}

function copyWarehouseAddress() {
  const addr = document.getElementById('seller-set-warehouse')?.value || '';
  if (!addr) {
    showToast('Chưa có địa chỉ kho hàng để sao chép', 'warning');
    return;
  }
  navigator.clipboard.writeText(addr).then(() => {
    showToast('Đã sao chép địa chỉ kho hàng vào clipboard!', 'success');
  });
}

function copyBankDetails() {
  const bank = document.getElementById('seller-set-bankname')?.value || '';
  const stk = document.getElementById('seller-set-accountnumber')?.value || '';
  const holder = document.getElementById('seller-set-accountholder')?.value || '';

  const text = `Ngân hàng: ${bank}\nSố TK: ${stk}\nChủ TK: ${holder}`;
  navigator.clipboard.writeText(text).then(() => {
    showToast('Đã sao chép thông tin tài khoản ngân hàng!', 'success');
  });
}

async function handleUpdateSellerProfile(e) {
  e.preventDefault();
  const shop_name = document.getElementById('seller-set-shopname').value.trim();
  const shop_description = document.getElementById('seller-set-desc').value.trim();
  const business_license = document.getElementById('seller-set-license').value.trim();
  const warehouse_address = document.getElementById('seller-set-warehouse').value.trim();
  const shop_logo = document.getElementById('seller-set-logo').value.trim();
  const shop_banner = document.getElementById('seller-set-banner').value.trim();

  try {
    const res = await apiCall('/api/seller/profile', {
      method: 'PUT',
      body: JSON.stringify({
        shop_name,
        shop_description,
        business_license,
        warehouse_address,
        shop_logo,
        shop_banner
      })
    });
    showToast(res.message, 'success');
    await loadSellerDashboard();
  } catch (e) {}
}

async function handleUpdateSellerFinance(e) {
  e.preventDefault();
  const tax_code = document.getElementById('seller-set-tax').value.trim();
  const bank_name = document.getElementById('seller-set-bankname').value;
  const bank_account_number = document.getElementById('seller-set-accountnumber').value.trim();
  const bank_account_holder = document.getElementById('seller-set-accountholder').value.trim().toUpperCase();

  try {
    const res = await apiCall('/api/seller/profile', {
      method: 'PUT',
      body: JSON.stringify({
        tax_code,
        bank_name,
        bank_account_number,
        bank_account_holder
      })
    });
    showToast('Cập nhật tài khoản ngân hàng thụ hưởng thành công!', 'success');
  } catch (e) {}
}

async function loadSellerStaff() {
  try {
    const staff = await apiCall('/api/seller/staff');
    sellerState.staff = staff;
    const container = document.getElementById('seller-staff-table-body');
    if (!container) return;

    if (staff.length === 0) {
      container.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:20px; color:#94a3b8;">Chưa có nhân viên phụ trách nào</td></tr>`;
      return;
    }

    let html = '';
    staff.forEach(s => {
      let roleBadge = '<span class="badge badge-info">📦 Quản lý Kho</span>';
      if (s.role === 'MARKETING') roleBadge = '<span class="badge badge-warning">🏷️ Marketing</span>';
      if (s.role === 'ACCOUNTANT') roleBadge = '<span class="badge badge-success">💰 Kế toán</span>';

      html += `
        <tr>
          <td><b>${s.staff_name}</b></td>
          <td>${s.staff_email}</td>
          <td>${s.staff_phone || 'Chưa cập nhật'}</td>
          <td>${roleBadge}</td>
          <td><span class="badge badge-success">Hoạt động</span></td>
          <td>
            <button class="btn-danger" style="padding:3px 8px; font-size:11px;" onclick="deleteSellerStaff(${s.id})">🗑️ Xóa</button>
          </td>
        </tr>
      `;
    });
    container.innerHTML = html;
  } catch (e) {}
}

function openAddStaffModal() {
  if (!state.currentUser) {
    requireLoginForAction('Thêm nhân viên');
    return;
  }
  document.getElementById('staff-name-input').value = '';
  document.getElementById('staff-email-input').value = '';
  document.getElementById('staff-phone-input').value = '';
  document.getElementById('add-staff-modal').classList.add('open');
}

async function submitAddStaff() {
  const staff_name = document.getElementById('staff-name-input').value.trim();
  const staff_email = document.getElementById('staff-email-input').value.trim();
  const staff_phone = document.getElementById('staff-phone-input').value.trim();
  const role = document.getElementById('staff-role-input').value;

  if (!staff_name || !staff_email) {
    showToast('Vui lòng nhập họ tên và email nhân viên', 'warning');
    return;
  }

  try {
    await apiCall('/api/seller/staff', {
      method: 'POST',
      body: JSON.stringify({ staff_name, staff_email, staff_phone, role })
    });
    showToast(`Đã thêm nhân viên ${staff_name} thành công!`, 'success');
    closeModal('add-staff-modal');
    await loadSellerStaff();
  } catch (e) {}
}

async function deleteSellerStaff(staffId) {
  if (!confirm('Bạn có chắc muốn xóa quyền nhân viên này?')) return;
  try {
    const res = await apiCall(`/api/seller/staff/${staffId}`, { method: 'DELETE' });
    showToast(res.message, 'success');
    await loadSellerStaff();
  } catch (e) {}
}

// Seller Buy Ad Modal (Tài trợ đẩy Top trang chủ)
function openBuyAdModal(bookId, bookTitle) {
  if (!state.currentUser) {
    requireLoginForAction('Mua quảng cáo');
    return;
  }

  document.getElementById('ad-book-id').value = bookId;
  document.getElementById('ad-book-title').textContent = bookTitle;
  document.getElementById('buy-ad-modal').classList.add('open');
}

async function submitBuyAd() {
  const bookId = parseInt(document.getElementById('ad-book-id').value);
  const days = parseInt(document.getElementById('ad-duration-select').value);
  
  let fee = 500000;
  if (days === 15) fee = 300000;
  if (days === 60) fee = 900000;

  try {
    const res = await apiCall('/api/seller/ads/purchase', {
      method: 'POST',
      body: JSON.stringify({
        book_id: bookId,
        duration_days: days,
        fee_paid: fee
      })
    });
    showToast(res.message, 'success');
    closeModal('buy-ad-modal');
    await loadSellerBooks();
    await loadSellerDashboard();
  } catch (e) {}
}


// -------------------------------------------------------------
// CÁNH CỬA 3: ADMIN CHỦ SÀN (ADMIN PORTAL)
// -------------------------------------------------------------
async function loadAdminDashboard() {
  try {
    const overview = await apiCall('/api/admin/financial-overview');
    const summary = overview.financial_summary;
    const stats = overview.stats;
    const orderCounts = stats.order_status_counts || {};
    const pendingOrderCount = Number(orderCounts.PENDING || 0);
    const setAdminCount = (id, value) => { const element = document.getElementById(id); if (element) element.textContent = String(value ?? 0); };
    setAdminCount('admin-orders-badge', pendingOrderCount);
    setAdminCount('admin-disputes-badge', stats.pending_disputes);
    setAdminCount('admin-products-badge', stats.pending_books);
    setAdminCount('admin-sellers-badge', stats.pending_sellers);
    setAdminCount('admin-payouts-badge', stats.pending_payouts);
    setAdminCount('admin-payouts-menu-badge', stats.pending_payouts);
    setAdminCount('admin-returns-badge', stats.pending_returns || 0);
    setAdminCount('admin-notification-count', pendingOrderCount + Number(stats.pending_disputes || 0) + Number(stats.pending_sellers || 0) + Number(stats.pending_books || 0) + Number(stats.pending_payouts || 0) + Number(stats.pending_returns || 0));
    const kpis = [
      ['GMV', formatVND(summary.gmv ?? summary.total_gmv_gross), 'Tổng giá trị hàng hóa', 'money', 'dashboard'],
      ['Doanh thu sàn', formatVND(summary.platform_revenue ?? summary.total_platform_profit), 'Phí hoa hồng thực tế trên đơn hàng', 'revenue', 'finance'],
      ['Hoa hồng', formatVND(summary.commission_revenue || 0), 'Phí trên đơn hàng', 'commission', 'finance'],
      ['Đơn hàng', stats.total_orders, 'Đơn không bị hủy', 'orders', 'orders'],
      ['Người dùng', stats.total_users, 'Buyer, seller và admin', 'users', 'users'],
      ['Seller / NXB', stats.total_sellers, `${stats.pending_sellers} hồ sơ chờ duyệt`, 'sellers', 'sellers'],
      ['Sản phẩm', stats.total_books, `${stats.pending_books} chờ duyệt · ${stats.active_books} đang hiển thị`, 'books', 'products'],
      ['Ads & VIP', `${stats.total_ad_campaigns} / ${stats.total_vip_members}`, 'Campaign / thành viên', 'growth', 'marketing']
    ];
    const icons = { money: '₫', revenue: '↗', commission: '%', orders: '▤', users: '♙', sellers: '⌂', books: '▥', growth: '✦' };
    document.getElementById('admin-kpi-grid').innerHTML = kpis.map(([label, value, note, icon, view]) => `<button class="admin-kpi-card" onclick="switchAdminView('${view}')"><span class="admin-kpi-icon ${icon}">${icons[icon]}</span><span><b>${label}</b><strong>${value}</strong><small>${note}</small></span><i>→</i></button>`).join('');
    document.getElementById('admin-revenue-streams-wrap').innerHTML = summary.revenue_streams.map(stream => `<div class="admin-revenue-row"><span class="admin-revenue-icon">${stream.code === 'COMMISSION_FEE' ? '%' : stream.code === 'AD_REVENUE' ? '✦' : '♢'}</span><span><b>${stream.code === 'COMMISSION_FEE' ? 'Commission Revenue' : stream.code === 'AD_REVENUE' ? 'Advertising Revenue' : 'Other Revenue'}</b><small>${stream.description}</small></span><strong>${formatVND(stream.amount)}</strong></div>`).join('');
    const platformRevenueValue = Number(summary.platform_revenue ?? summary.total_platform_profit ?? 0);
    const gmvValue = Number(summary.gmv ?? summary.total_gmv_gross ?? 0);
    if (platformRevenueValue > gmvValue && gmvValue > 0) {
      console.warn('Dashboard revenue mismatch: platform revenue exceeds GMV. Using canonical commission-based metric.', { gmvValue, platformRevenueValue });
    }
    document.getElementById('admin-action-queue').innerHTML = [`${stats.pending_books} sản phẩm chờ duyệt|products|Xem hàng đợi`, `${stats.pending_sellers} hồ sơ seller chờ duyệt|sellers|Kiểm tra hồ sơ`, `${stats.pending_payouts} yêu cầu rút tiền|payouts|Mở payout`, `${stats.pending_disputes} khiếu nại cần xử lý|disputes|Xem khiếu nại`].map(item => { const [text, view, action] = item.split('|'); return `<button onclick="switchAdminView('${view}')"><span>${text}</span><b>${action} →</b></button>`; }).join('');
    document.getElementById('admin-recent-activity').innerHTML = ['Doanh thu commission đã được cập nhật', `${stats.pending_books} sách mới được gửi xét duyệt`, `${stats.pending_sellers} hồ sơ seller đang chờ kiểm tra`, 'Hệ thống đối soát hoạt động bình thường'].map((text, index) => `<div><i class="admin-activity-dot dot-${index}"></i><span>${text}<small>${index + 1} giờ trước</small></span></div>`).join('');
    renderAdminGrowthChart(summary.gmv || summary.total_gmv_gross || 0, summary.platform_revenue || summary.total_platform_profit || 0);
  } catch (e) {}
}

const adminMockService = { modules: {
  orders: { title: 'Đơn hàng & khiếu nại', description: 'Theo dõi fulfillment, hoàn tiền và tranh chấp', columns: ['Mã đơn', 'Người mua', 'Seller', 'Tổng tiền', 'Thanh toán', 'Trạng thái', 'Ngày tạo'], rows: [['#BH-10482', 'Nguyễn Minh Anh', 'NXB Kim Đồng', '₫428.000', 'Đã thanh toán', 'Đang giao', '10/09/2026'], ['#BH-10481', 'Trần Quốc Bảo', 'Nhã Nam', '₫215.000', 'COD', 'Chờ xử lý', '10/09/2026'], ['#BH-10479', 'Lê Hoài Phương', 'Alpha Books', '₫890.000', 'Đã thanh toán', 'Tranh chấp', '09/09/2026']] },
  finance: { title: 'Tài chính & đối soát', description: 'Revenue, giao dịch và yêu cầu rút tiền', columns: ['Mã giao dịch', 'Seller', 'Loại', 'Gross', 'Fee', 'Net', 'Trạng thái'], rows: [['TX-92831', 'NXB Kim Đồng', 'Commission', '₫1.200.000', '₫120.000', '₫120.000', 'Đã đối soát'], ['TX-92830', 'Nhã Nam', 'Payout', '₫4.500.000', '₫0', '₫4.500.000', 'Chờ duyệt'], ['TX-92826', 'Alpha Books', 'Advertising', '₫800.000', '₫0', '₫800.000', 'Hoàn tất']] },
  marketing: { title: 'Marketing', description: 'Campaign, quảng cáo và voucher của marketplace', columns: ['Campaign', 'Seller', 'Ngân sách', 'Đã chi', 'Doanh thu', 'ROAS', 'Trạng thái'], rows: [['Back to school', 'NXB Kim Đồng', '₫20.000.000', '₫8.400.000', '₫64.200.000', '7.6x', 'Đang chạy'], ['Sách mới tháng 9', 'Nhã Nam', '₫8.000.000', '₫2.100.000', '₫14.800.000', '7.0x', 'Đang chạy']] },
  analytics: { title: 'Analytics', description: 'GMV, doanh thu, người dùng và sản phẩm', columns: ['Chỉ số', 'Hôm nay', '7 ngày', '30 ngày', 'So với kỳ trước'], rows: [['GMV', '₫10.250.000', '₫68.430.000', '₫248.900.000', '+12,4%'], ['Doanh thu sàn', '₫1.250.000', '₫7.950.000', '₫29.800.000', '+9,8%'], ['Người dùng mới', '48', '312', '1.284', '+18,2%']] },
  settings: { title: 'Cài đặt hệ thống', description: 'Thiết lập marketplace và phân quyền vận hành', columns: ['Nhóm thiết lập', 'Giá trị hiện tại', 'Cập nhật'], rows: [['Commission', '10%', 'Cấu hình'], ['Minimum payout', '₫100.000', 'Cấu hình'], ['Payout schedule', 'Hàng tuần', 'Cấu hình'], ['Roles & Permissions', '6 vai trò', 'Mở ma trận']] }
} };

function switchAdminView(view, button) {
  if (state.currentPortal !== 'ADMIN') return;
  const adminPath = view === 'dashboard' ? '/admin' : view === 'permissions' ? '/admin/settings/permissions' : `/admin/${view}`;
  if (window.location.pathname !== adminPath) history.pushState({ adminView: view }, '', adminPath);
  document.querySelectorAll('.admin-nav-item').forEach(item => item.classList.toggle('active', button ? item === button : item.dataset.adminView === view && !item.classList.contains('admin-nav-subitem')));
  document.getElementById('admin-breadcrumb-label').textContent = document.querySelector(`[data-admin-view="${view}"]`)?.textContent.trim().replace(/\d+$/, '') || 'Tổng quan';
  const dashboard = document.getElementById('admin-dashboard-view');
  const module = document.getElementById('admin-module-view');
  dashboard.style.display = view === 'dashboard' ? 'block' : 'none';
  module.style.display = view === 'dashboard' ? 'none' : 'block';
  if (view === 'dashboard') return loadAdminDashboard();
  if (view === 'orders') return renderAdminOrdersLive();
  if (view === 'finance') return renderAdminTransactionsLive();
  if (view === 'analytics') return renderAdminAnalyticsLive();
  if (view === 'products') return loadPendingBooks();
  if (view === 'sellers') return loadPendingSellers();
  if (view === 'users') return loadAllUsersAdmin();
  if (view === 'returns') return renderAdminReturnsLive();
  if (view === 'disputes') return renderAdminDisputes();
  if (view === 'payouts') return renderAdminPayouts();
  if (view === 'permissions') return renderAdminPermissions();
  renderAdminMockModule(view);
  document.getElementById('admin-sidebar').classList.remove('open');
}

function renderAdminMockModule(view) {
  const module = adminMockService.modules[view] || adminMockService.modules.orders;
  const table = `<div class="admin-table-wrap"><div class="admin-table-toolbar"><input id="admin-module-search" type="search" placeholder="Tìm trong ${module.title.toLowerCase()}..." oninput="filterAdminTable(this.value)"><button class="admin-button secondary" onclick="showToast('Đang chuẩn bị file xuất dữ liệu.', 'info')">⚲ Xuất dữ liệu</button><button class="admin-button primary" onclick="showToast('Tạo mới cần API backend tương ứng.', 'info')">+ Tạo mới</button></div><div class="admin-table-scroll"><table class="admin-data-table"><thead><tr><th><input type="checkbox" onchange="toggleAdminSelection(this)"></th>${module.columns.map(c => `<th>${c}</th>`).join('')}<th>Thao tác</th></tr></thead><tbody>${module.rows.map(row => `<tr><td><input type="checkbox" class="admin-row-check"></td>${row.map((cell, index) => `<td>${index === row.length - 1 || cell.includes('Chờ') || cell.includes('Tranh chấp') || cell.includes('Đang') ? `<span class="admin-status ${cell.includes('Chờ') || cell.includes('Tranh chấp') ? 'warning' : 'success'}">${cell}</span>` : cell}</td>`).join('')}<td><button class="admin-row-action" onclick="${view === 'orders' ? `openAdminOrder('${row[0]}')` : `showAdminRecord('${row[0]}')`}">Xem chi tiết</button></td></tr>`).join('')}</tbody></table></div><div class="admin-table-footer">Hiển thị ${module.rows.length} trên ${module.rows.length} bản ghi <span>‹ &nbsp; <b>1</b> &nbsp; ›</span></div></div>`;
  document.getElementById('admin-module-view').innerHTML = `<div class="admin-page-heading"><div><span class="admin-eyebrow">ADMIN MODULE</span><h1>${module.title}</h1><p>${module.description}</p></div></div>${table}`;
}

async function renderAdminOrdersLive() {
  const root = document.getElementById('admin-module-view');
  root.innerHTML = adminModuleHeading('LIVE API', 'Đơn hàng & khiếu nại', 'Danh sách đơn hàng lấy trực tiếp từ database.') + '<div class="admin-table-wrap"><div class="admin-table-toolbar"><input type="search" placeholder="Tìm mã đơn, buyer, seller..." oninput="filterAdminTable(this.value)"></div><div class="admin-table-scroll"><table class="admin-data-table"><thead><tr><th>Mã đơn</th><th>Buyer</th><th>Seller</th><th>Số sản phẩm</th><th>Tổng tiền</th><th>Thanh toán</th><th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody id="admin-live-orders-body"><tr><td colspan="8" class="admin-empty-state">Đang tải...</td></tr></tbody></table></div></div>';
  try {
    const orders = await apiCall('/api/admin/orders');
    document.getElementById('admin-live-orders-body').innerHTML = orders.length ? orders.map(order => `<tr><td><b>${order.order_code}</b></td><td>${order.buyer}</td><td>${order.seller}</td><td>${order.items}</td><td>${formatVND(order.total)}</td><td>${order.payment}</td><td><span class="admin-status ${order.status === 'PENDING' ? 'warning' : 'success'}">${order.status}</span></td><td><button class="admin-row-action" onclick="openAdminOrder(${order.id})">Xem chi tiết</button></td></tr>`).join('') : '<tr><td colspan="8" class="admin-empty-state">Chưa có đơn hàng</td></tr>';
  } catch (error) {
    document.getElementById('admin-live-orders-body').innerHTML = `<tr><td colspan="8" class="admin-empty-state">Không thể tải dữ liệu: ${error.message}</td></tr>`;
  }
}

async function renderAdminTransactionsLive() {
  const root = document.getElementById('admin-module-view');
  root.innerHTML = adminModuleHeading('LIVE API', 'Tài chính & đối soát', 'Giao dịch đã ghi nhận trong database.') + '<div class="admin-table-wrap"><div class="admin-table-scroll"><table class="admin-data-table"><thead><tr><th>Mã giao dịch</th><th>Seller ID</th><th>Loại</th><th>Gross</th><th>Fee</th><th>Net</th><th>Trạng thái</th></tr></thead><tbody id="admin-live-transactions-body"><tr><td colspan="7" class="admin-empty-state">Đang tải...</td></tr></tbody></table></div></div>';
  try { const transactions = await apiCall('/api/admin/transactions'); document.getElementById('admin-live-transactions-body').innerHTML = transactions.length ? transactions.map(item => `<tr><td>${item.transaction_code}</td><td>${item.seller_id || '-'}</td><td>${item.transaction_type}</td><td>${formatVND(item.gross)}</td><td>${formatVND(item.fee)}</td><td>${formatVND(item.net)}</td><td><span class="admin-status ${item.status === 'PENDING' ? 'warning' : 'success'}">${item.status}</span></td></tr>`).join('') : '<tr><td colspan="7" class="admin-empty-state">Chưa có giao dịch được ghi nhận</td></tr>'; } catch (error) { document.getElementById('admin-live-transactions-body').innerHTML = `<tr><td colspan="7" class="admin-empty-state">Không thể tải dữ liệu: ${error.message}</td></tr>`; }
}

async function renderAdminReturnsLive() {
  const root = document.getElementById('admin-module-view');
  root.innerHTML = adminModuleHeading('RETURN & REFUND', 'Quản lý trả hàng', 'Danh sách yêu cầu trả hàng từ khách hàng cần xử lý.') + '<div class="admin-table-wrap"><div class="admin-table-toolbar"><input type="search" placeholder="Tìm mã trả hàng, đơn hàng, khách hàng..." oninput="filterAdminTable(this.value)"></div><div class="admin-table-scroll"><table class="admin-data-table"><thead><tr><th>ID</th><th>Đơn</th><th>Khách</th><th>Lý do</th><th>Số tiền</th><th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody id="admin-live-returns-body"><tr><td colspan="7" class="admin-empty-state">Đang tải...</td></tr></tbody></table></div></div>';
  try {
    const requests = await apiCall('/api/admin/returns');
    const rows = requests.length ? requests.map(req => `
      <tr>
        <td><b>#${req.id}</b></td>
        <td>${req.order_id}</td>
        <td>${req.user_id}</td>
        <td>${req.reason}</td>
        <td>${formatVND(req.refund_amount)}</td>
        <td><span class="admin-status ${req.status === 'PENDING' ? 'warning' : req.status === 'REJECTED' ? 'danger' : req.status === 'REFUNDED' ? 'success' : 'info'}">${req.status}</span></td>
        <td>
          ${req.status === 'PENDING' ? `<button class="admin-row-action" onclick="handleAdminReturnAction(${req.id}, 'approve')">Duyệt</button>` : ''}
          ${req.status === 'PENDING' ? `<button class="admin-row-action" onclick="handleAdminReturnAction(${req.id}, 'reject')">Từ chối</button>` : ''}
          ${req.status === 'APPROVED' || req.status === 'CUSTOMER_SHIPPED' ? `<button class="admin-row-action" onclick="handleAdminReturnAction(${req.id}, 'received')">Đã nhận hàng</button>` : ''}
          ${(req.status === 'RECEIVED' || req.status === 'REFUND_PROCESSING') ? `<button class="admin-row-action" onclick="handleAdminReturnAction(${req.id}, 'refund')">Hoàn tiền</button>` : ''}
        </td>
      </tr>
    `).join('') : '<tr><td colspan="7" class="admin-empty-state">Chưa có yêu cầu trả hàng nào</td></tr>';
    document.getElementById('admin-live-returns-body').innerHTML = rows;
    document.getElementById('admin-returns-badge') && (document.getElementById('admin-returns-badge').textContent = String(requests.length));
  } catch (error) {
    document.getElementById('admin-live-returns-body').innerHTML = `<tr><td colspan="7" class="admin-empty-state">Không thể tải dữ liệu: ${error.message}</td></tr>`;
  }
}

async function handleAdminReturnAction(returnId, action) {
  try {
    const endpointMap = {
      approve: `/api/admin/returns/${returnId}/approve`,
      reject: `/api/admin/returns/${returnId}/reject`,
      received: `/api/admin/returns/${returnId}/received`,
      refund: `/api/admin/returns/${returnId}/refund`
    };
    const method = 'PATCH';
    const body = action === 'reject' ? JSON.stringify({ rejection_reason: 'Không đạt tiêu chí hoàn trả' }) : undefined;
    await apiCall(endpointMap[action], { method, body });
    showToast('Đã cập nhật trạng thái trả hàng.', 'success');
    await renderAdminReturnsLive();
  } catch (error) {
    showToast(error.message || 'Không thể cập nhật trạng thái trả hàng.', 'error');
  }
}

async function renderAdminAnalyticsLive() {
  const root = document.getElementById('admin-module-view');
  root.innerHTML = adminModuleHeading('LIVE API', 'Analytics', 'Các chỉ số lấy từ Admin financial overview của backend.') + '<div class="admin-table-wrap"><div class="admin-table-scroll"><table class="admin-data-table"><thead><tr><th>Chỉ số</th><th>Giá trị thực tế</th></tr></thead><tbody id="admin-live-analytics-body"><tr><td colspan="2" class="admin-empty-state">Đang tải...</td></tr></tbody></table></div></div>';
  try { const overview = await apiCall('/api/admin/financial-overview'); const summary = overview.financial_summary; const stats = overview.stats; const rows = [['GMV', formatVND(summary.gmv)], ['Platform Revenue', formatVND(summary.platform_revenue)], ['Commission Revenue', formatVND(summary.commission_revenue)], ['Tổng sản phẩm', stats.total_books], ['Sản phẩm đang hiển thị', stats.active_books], ['Tổng người dùng', stats.total_users], ['Tổng seller', stats.total_sellers], ['Tổng đơn hàng', stats.total_orders]]; document.getElementById('admin-live-analytics-body').innerHTML = rows.map(row => `<tr><td>${row[0]}</td><td><b>${row[1]}</b></td></tr>`).join(''); } catch (error) { document.getElementById('admin-live-analytics-body').innerHTML = `<tr><td colspan="2" class="admin-empty-state">Không thể tải dữ liệu: ${error.message}</td></tr>`; }
}

function adminService() { return window.AdminServices; }
function adminModuleHeading(eyebrow, title, description) { return `<div class="admin-page-heading"><div><span class="admin-eyebrow">${eyebrow}</span><h1>${title}</h1><p>${description}</p></div></div>`; }
function renderAdminDisputes() {
  const root = document.getElementById('admin-module-view');
  root.innerHTML = adminModuleHeading('RISK & SUPPORT', 'Khiếu nại / tranh chấp', 'Mọi quyết định đều được ghi vào AuditLogService và cần được backend xác thực lại.') + '<div class="admin-table-wrap"><div class="admin-table-toolbar"><input type="search" placeholder="Tìm mã tranh chấp, đơn hàng, buyer..." oninput="filterAdminTable(this.value)"><button class="admin-button secondary">⚲ Xuất dữ liệu</button></div><div class="admin-table-scroll"><table class="admin-data-table"><thead><tr><th>Dispute ID</th><th>Order</th><th>Buyer</th><th>Seller</th><th>Lý do</th><th>Số tiền</th><th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody id="admin-disputes-body"><tr><td colspan="8" class="admin-empty-state">Đang tải tranh chấp...</td></tr></tbody></table></div></div>';
  adminService().DisputeService.getDisputes().then(disputes => { document.getElementById('admin-disputes-body').innerHTML = disputes.length ? disputes.map(item => `<tr><td><b>${item.id}</b></td><td>${item.orderId}</td><td>${item.buyer}</td><td>${item.seller}</td><td>${item.reason}</td><td>${formatVND(item.amount)}</td><td><span class="admin-status warning">${item.status}</span></td><td><button class="admin-row-action" onclick="openAdminDispute('${item.id}')">Xem chi tiết</button></td></tr>`).join('') : '<tr><td colspan="8" class="admin-empty-state">Chưa có khiếu nại nào</td></tr>'; }).catch(error => { document.getElementById('admin-disputes-body').innerHTML = `<tr><td colspan="8" class="admin-empty-state">Không thể tải dữ liệu: ${error.message}</td></tr>`; });
}
function renderAdminPayouts() {
  const root = document.getElementById('admin-module-view');
  root.innerHTML = adminModuleHeading('FINANCE', 'Yêu cầu rút tiền', 'Số tài khoản luôn được mask; việc duyệt thật cần payment/bank backend.') + '<div class="admin-table-wrap"><div class="admin-table-toolbar"><input type="search" placeholder="Tìm request, seller..." oninput="filterAdminTable(this.value)"><button class="admin-button secondary">⚲ Xuất CSV</button></div><div class="admin-table-scroll"><table class="admin-data-table"><thead><tr><th>Request ID</th><th>Seller</th><th>Số tiền</th><th>Ngân hàng</th><th>Ngày yêu cầu</th><th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody id="admin-payouts-body"><tr><td colspan="7" class="admin-empty-state">Đang tải yêu cầu...</td></tr></tbody></table></div></div>';
  adminService().PayoutService.getPayoutRequests().then(payouts => { document.getElementById('admin-payouts-body').innerHTML = payouts.length ? payouts.map(item => `<tr><td><b>${item.id}</b></td><td>${item.seller}</td><td>${formatVND(item.amount)}</td><td>${item.bankName}<small>${item.accountNumberMasked}</small></td><td>${new Date(item.requestedAt).toLocaleDateString('vi-VN')}</td><td><span class="admin-status ${item.status === 'PENDING' ? 'warning' : item.status === 'REJECTED' ? 'danger' : 'success'}">${item.status}</span></td><td><button class="admin-row-action" onclick="openAdminPayout('${item.id}')">Xem chi tiết</button></td></tr>`).join('') : '<tr><td colspan="7" class="admin-empty-state">Chưa có yêu cầu rút tiền</td></tr>'; }).catch(error => { document.getElementById('admin-payouts-body').innerHTML = `<tr><td colspan="7" class="admin-empty-state">Không thể tải dữ liệu: ${error.message}</td></tr>`; });
}
function renderAdminPermissions() {
  Promise.all([adminService().PermissionService.getRoles(), adminService().PermissionService.getPermissions()]).then(([roles, permissions]) => {
    document.getElementById('admin-module-view').innerHTML = adminModuleHeading('SYSTEM', 'Phân quyền', 'Frontend permission checks chỉ phục vụ UI/UX. Backend phải enforce authorization thực sự.') + `<section class="admin-panel admin-permission-panel"><div class="admin-panel-heading"><div><h2>Permission matrix</h2><p>Thay đổi trong mock mode chưa được lưu vào database.</p></div><span class="admin-mode-badge">DEMO / MOCK MODE</span></div><div class="admin-table-scroll"><table class="admin-data-table admin-permission-table"><thead><tr><th>Role</th>${permissions.map(permission => `<th title="${permission}">${permission.split('.')[1]}</th>`).join('')}</tr></thead><tbody>${roles.map(role => `<tr><td><b>${role.label}</b></td>${permissions.map(permission => `<td><input type="checkbox" data-role="${role.id}" data-permission="${permission}" ${role.permissions.includes(permission) ? 'checked' : ''}></td>`).join('')}</tr>`).join('')}</tbody></table></div><div class="admin-permission-actions"><button class="admin-button primary" onclick="saveAdminPermissions()">Lưu thay đổi</button></div></section>`;
  }).catch(error => showToast(`Không thể tải permission matrix: ${error.message}`, 'error'));
}
function saveAdminPermissions() {
  const roles = [...new Set([...document.querySelectorAll('[data-role]')].map(input => input.dataset.role))];
  Promise.all(roles.map(role => adminService().PermissionService.updateRolePermissions(role, [...document.querySelectorAll(`[data-role="${role}"]:checked`)].map(input => input.dataset.permission)))).then(() => showToast('Đã cập nhật mock permission state. Backend vẫn phải enforce quyền.', 'success')).catch(error => showToast(`Không thể lưu permission: ${error.message}`, 'error'));
}
function openAdminDispute(id) { history.pushState({ adminDetail: true }, '', `/admin/disputes/${id}`); renderAdminDetail('disputes', id); }
function openAdminPayout(id) { history.pushState({ adminDetail: true }, '', `/admin/payouts/${id}`); renderAdminDetail('payouts', id); }
function renderAdminDetail(type, id) { document.querySelectorAll('.admin-nav-item').forEach(item => item.classList.toggle('active', item.dataset.adminView === type)); document.getElementById('admin-dashboard-view').style.display = 'none'; document.getElementById('admin-module-view').style.display = 'block'; if (type === 'disputes') renderDisputeDetail(id); if (type === 'payouts') renderPayoutDetail(id); }
function renderDisputeDetail(id) { adminService().DisputeService.getDispute(id).then(item => { const root = document.getElementById('admin-module-view'); if (!item) { root.innerHTML = adminModuleHeading('RISK & SUPPORT', 'Không tìm thấy tranh chấp', 'Dữ liệu có thể đã bị xóa hoặc chưa được đồng bộ.'); return; } root.innerHTML = adminModuleHeading('DISPUTE DETAIL', `${item.id} · ${item.reason}`, `Đơn hàng ${item.orderId} · ${item.status}`) + `<div class="admin-detail-grid"><section class="admin-panel"><h2>Thông tin đơn hàng</h2><div class="admin-detail-list"><p><b>Buyer</b>${item.buyer}</p><p><b>Seller</b>${item.seller}</p><p><b>Số tiền</b>${formatVND(item.amount)}</p><p><b>Mô tả</b>${item.description}</p><p><b>Buyer response</b>${item.buyerResponse || 'Chưa có'}</p><p><b>Seller response</b>${item.sellerResponse || 'Chưa có'}</p></div></section><section class="admin-panel"><h2>Evidence & timeline</h2><div class="admin-evidence-list">${item.evidence.map(doc => `<button class="admin-document-link" onclick="openAdminDocument('${doc.id || 'DOC-01'}')">▧ ${doc.fileName}</button>`).join('')}</div><div class="admin-timeline">${item.timeline.map(event => `<div><i></i><span>${event.label}<small>${new Date(event.at).toLocaleString('vi-VN')}</small></span></div>`).join('')}</div></section></div><div class="admin-detail-actions"><button class="admin-button secondary" onclick="runAdminAction(this, () => adminService().DisputeService.requestSellerResponse('${item.id}'), 'Đã yêu cầu seller phản hồi.')">Yêu cầu seller phản hồi</button><button class="admin-button primary" onclick="confirmAdminAction('Hoàn tiền buyer?', () => runAdminAction(this, () => adminService().DisputeService.resolveDispute('${item.id}', 'REFUND_BUYER', 'Mock refund decision'), 'Đã cập nhật quyết định mock: hoàn tiền buyer.'))">Hoàn tiền buyer</button><button class="admin-button secondary" onclick="confirmAdminAction('Giải quyết cho seller?', () => runAdminAction(this, () => adminService().DisputeService.resolveDispute('${item.id}', 'RESOLVE_FOR_SELLER', 'Mock seller resolution'), 'Đã cập nhật quyết định mock cho seller.'))">Giải quyết cho seller</button><button class="admin-button danger" onclick="promptAdminReason('Từ chối khiếu nại', reason => runAdminAction(this, () => adminService().DisputeService.rejectDispute('${item.id}', reason), 'Đã từ chối khiếu nại trong mock state.'))">Từ chối khiếu nại</button></div>`; }).catch(error => showToast(`Không thể tải tranh chấp: ${error.message}`, 'error')); }
function renderPayoutDetail(id) { adminService().PayoutService.getPayout(id).then(item => { const root = document.getElementById('admin-module-view'); if (!item) { root.innerHTML = adminModuleHeading('FINANCE', 'Không tìm thấy yêu cầu', 'Dữ liệu payout chưa được đồng bộ.'); return; } root.innerHTML = adminModuleHeading('PAYOUT DETAIL', item.id, `${item.seller} · ${item.status}`) + `<div class="admin-detail-grid"><section class="admin-panel"><h2>Thông tin payout</h2><div class="admin-detail-list"><p><b>Seller</b>${item.seller}</p><p><b>Số dư khả dụng</b>${formatVND(item.availableBalance)}</p><p><b>Số tiền yêu cầu</b>${formatVND(item.amount)}</p><p><b>Ngân hàng</b>${item.bankName}</p><p><b>Chủ tài khoản</b>${item.accountName}</p><p><b>Số tài khoản</b>${item.accountNumberMasked}</p></div></section><section class="admin-panel"><h2>Lịch sử request</h2><div class="admin-timeline">${item.history.map(event => `<div><i></i><span>${event.label}<small>${new Date(event.at).toLocaleString('vi-VN')}</small></span></div>`).join('')}</div></section></div><div class="admin-detail-actions"><button class="admin-button primary" onclick="confirmAdminAction('Duyệt yêu cầu rút tiền?', () => runAdminAction(this, () => adminService().PayoutService.approvePayout('${item.id}'), 'Đã duyệt trong mock state. Chưa có chuyển tiền thật.'))">Duyệt yêu cầu</button><button class="admin-button danger" onclick="promptAdminReason('Từ chối payout', reason => runAdminAction(this, () => adminService().PayoutService.rejectPayout('${item.id}', reason), 'Đã từ chối payout trong mock state.'))">Từ chối</button></div>`; }).catch(error => showToast(`Không thể tải payout: ${error.message}`, 'error')); }
function runAdminAction(button, operation, successMessage) { const target = button && button instanceof HTMLElement ? button : null; const original = target?.textContent || ''; if (target) { target.disabled = true; target.textContent = 'Đang xử lý...'; } return operation().then(() => { showToast(successMessage, 'success'); return true; }).catch(error => { showToast(`Không thể xử lý: ${error.message}`, 'error'); return false; }).finally(() => { if (target) { target.disabled = false; target.textContent = original; } }); }
function confirmAdminAction(title, callback) { if (window.confirm(`${title}\n\nĐây là thao tác mock; backend cần xác thực lại.`)) callback(); }
function promptAdminReason(title, callback) { const reason = window.prompt(`${title}\nNhập lý do:`); if (reason?.trim()) callback(reason.trim()); else if (reason !== null) showToast('Vui lòng nhập lý do.', 'warning'); }
function openAdminDocument(id) { adminService().DocumentService.getDocumentPreview(id).then(doc => { const message = doc.available ? `<iframe class="admin-document-frame" src="${doc.fileUrl}" title="${doc.fileName}"></iframe>` : `<div class="admin-document-unavailable">${doc.message}</div>`; const overlay = document.createElement('div'); overlay.className = 'admin-dialog-overlay'; overlay.innerHTML = `<div class="admin-dialog"><div class="admin-dialog-heading"><h2>Document Viewer</h2><button onclick="this.closest('.admin-dialog-overlay').remove()">×</button></div><p><b>${doc.fileName}</b> · ${doc.type}</p>${message}<div class="admin-dialog-actions"><button class="admin-button secondary" onclick="this.closest('.admin-dialog-overlay').remove()">Đóng</button>${doc.available ? `<button class="admin-button primary" onclick="AdminServices.DocumentService.downloadDocument('${id}')">Download</button>` : ''}</div></div>`; document.body.appendChild(overlay); }).catch(error => showToast(`Không thể mở tài liệu: ${error.message}`, 'error')); }

function renderAdminGrowthChart(gmv, revenue) {
  const chart = document.getElementById('admin-growth-chart');
  if (!chart) return;
  const points = [0.52, 0.62, 0.57, 0.74, 0.68, 0.86, 1];
  const chartMax = Math.max(Number(gmv) || 0, Number(revenue) || 0, 1);
  const gmvScale = Math.max(8, (Number(gmv) / chartMax) * 100);
  const revenueScale = Math.max(8, (Number(revenue) / chartMax) * 100);
  chart.innerHTML = `<div class="admin-chart-axis"><span>${formatVND(chartMax)}</span><span>${formatVND(chartMax * 0.5)}</span><span>₫0</span></div><div class="admin-chart-bars">${points.map((point, index) => `<div class="admin-chart-column"><div class="admin-bar gmv-bar" style="height:${Math.min(100, point * gmvScale)}%" title="GMV: ${formatVND(gmv * point)}"></div><div class="admin-bar revenue-bar" style="height:${Math.min(100, point * revenueScale)}%" title="Doanh thu sàn: ${formatVND(revenue * point)}"></div><small>${['04/09', '05/09', '06/09', '07/09', '08/09', '09/09', 'Hôm nay'][index]}</small></div>`).join('')}</div>`;
}

function setAdminPeriod(period, button) { document.querySelectorAll('.admin-segmented button').forEach(item => item.classList.remove('active')); button.classList.add('active'); showToast(`Đã chuyển sang ${period === '7D' ? '7 ngày' : period === '30D' ? '30 ngày' : '3 tháng'}.`, 'info'); }
function toggleAdminSidebar() { document.getElementById('admin-sidebar')?.classList.toggle('open'); }
function toggleAdminAccountMenu() { document.getElementById('admin-account-menu')?.classList.toggle('open'); }
function handleAdminGlobalSearch(value) { if (value.trim().length > 2) showToast(`Đang tìm kiếm: ${value}`, 'info'); }
function filterAdminTable(value) { document.querySelectorAll('.admin-data-table tbody tr').forEach(row => row.style.display = row.textContent.toLowerCase().includes(value.toLowerCase()) ? '' : 'none'); }
function toggleAdminSelection(source) { document.querySelectorAll('.admin-row-check').forEach(item => item.checked = source.checked); updateAdminSelection(); }

window.addEventListener('popstate', () => {
  const match = window.location.pathname.match(/^\/admin(?:\/([A-Za-z0-9_-]+))?(?:\/([A-Za-z0-9_-]+))?$/);
  if (match && state.currentPortal === 'ADMIN') {
    if (match[1] === 'settings' && match[2] === 'permissions') return switchAdminView('permissions');
    if (match[2] && ['disputes', 'payouts'].includes(match[1])) return renderAdminDetail(match[1], match[2]);
    if (match[2] && ['sellers', 'products', 'users', 'orders'].includes(match[1])) return renderAdminEntityDetail(match[1], match[2]);
    switchAdminView(match[1] || 'dashboard');
  }
});

function renderAdminApiTable(title, description, columns, rows, actionBuilder) {
  const module = { title, description, columns, rows };
  const mockKey = `admin-api-${Date.now()}`;
  const isProducts = title.includes('Sản phẩm');
  const bulkToolbar = isProducts ? '<div id="admin-bulk-toolbar" class="admin-bulk-toolbar" hidden><strong><span id="admin-selected-count">0</span> sản phẩm được chọn</strong><button class="admin-button primary" onclick="confirmBulkAdminAction(\'approve\')">Duyệt hàng loạt</button><button class="admin-button danger" onclick="promptBulkAdminReject()">Từ chối hàng loạt</button></div>' : '';
  document.getElementById('admin-module-view').innerHTML = `<div class="admin-page-heading"><div><span class="admin-eyebrow">LIVE API</span><h1>${title}</h1><p>${description}</p></div></div><div class="admin-table-wrap"><div class="admin-table-toolbar"><input type="search" placeholder="Tìm kiếm..." oninput="filterAdminTable(this.value)"><button class="admin-button secondary" onclick="showToast('Đang chuẩn bị file xuất dữ liệu.', 'info')">⚲ Xuất dữ liệu</button></div>${bulkToolbar}<div class="admin-table-scroll"><table class="admin-data-table"><thead><tr><th><input type="checkbox" onchange="toggleAdminSelection(this)"></th>${columns.map(column => `<th>${column}</th>`).join('')}<th>Thao tác</th></tr></thead><tbody>${rows.length ? rows.map(row => `<tr data-record-id="${row.id}"><td><input type="checkbox" class="admin-row-check" data-record-id="${row.id}" onchange="updateAdminSelection()"></td>${row.cells.map(cell => `<td>${cell}</td>`).join('')}<td>${actionBuilder ? actionBuilder(row.id, row.record) : `<button class="admin-row-action" onclick="showAdminRecord('${row.id}')">Xem</button>`}</td></tr>`).join('') : `<tr><td colspan="${columns.length + 2}" class="admin-empty-state">Chưa có dữ liệu cần xử lý</td></tr>`}</tbody></table></div><div class="admin-table-footer">Hiển thị ${rows.length} trên ${rows.length} bản ghi <span>‹ &nbsp; <b>1</b> &nbsp; ›</span></div></div>`;
  function updateAdminSelection() { const selected = document.querySelectorAll('.admin-row-check:checked').length; const count = document.getElementById('admin-selected-count'); const toolbar = document.getElementById('admin-bulk-toolbar'); if (count) count.textContent = selected; if (toolbar) toolbar.hidden = selected === 0; }
  function selectedAdminIds() { return [...document.querySelectorAll('.admin-row-check:checked')].map(item => item.dataset.recordId); }
  function confirmBulkAdminAction(action) { const ids = selectedAdminIds(); if (!ids.length) return showToast('Vui lòng chọn ít nhất một sản phẩm.', 'warning'); confirmAdminAction(`Duyệt ${ids.length} sản phẩm?`, () => runBulkProductAction(ids, action)); }
  function promptBulkAdminReject() { const ids = selectedAdminIds(); if (!ids.length) return showToast('Vui lòng chọn ít nhất một sản phẩm.', 'warning'); promptAdminReason(`Từ chối ${ids.length} sản phẩm`, reason => runBulkProductAction(ids, 'reject', reason)); }
  async function runBulkProductAction(ids, action, reason = '') { const button = document.querySelector('.admin-bulk-toolbar .admin-button.primary'); if (button) { button.disabled = true; button.textContent = 'Đang xử lý...'; } let success = 0; let failed = 0; for (const id of ids) { try { const service = adminService().ProductService; if (action === 'approve') await service.approveProduct(id); else await service.rejectProduct(id, reason); success += 1; } catch (error) { failed += 1; } } showToast(`Đã xử lý ${success} sản phẩm${failed ? `, ${failed} sản phẩm không thể xử lý` : ''}.`, failed ? 'warning' : 'success'); if (button) { button.disabled = false; button.textContent = 'Duyệt hàng loạt'; } await loadPendingBooks(); }
  function showAdminRecord(id) { showToast(`Đã chọn bản ghi ${id}.`, 'info'); }
  function showAdminSeller(id) { history.pushState({ adminDetail: true }, '', `/admin/sellers/${id}`); renderAdminEntityDetail('sellers', id); }
  function showAdminProduct(id) { history.pushState({ adminDetail: true }, '', `/admin/products/${id}`); renderAdminEntityDetail('products', id); }
  function showAdminUser(id) { history.pushState({ adminDetail: true }, '', `/admin/users/${id}`); renderAdminEntityDetail('users', id); }
  function openAdminOrder(id) { history.pushState({ adminDetail: true }, '', `/admin/orders/${encodeURIComponent(id)}`); renderAdminOrderDetail(id); }
  function renderAdminOrderDetail(id) { const record = adminMockService.modules.orders.rows.find(row => row[0] === id); const root = document.getElementById('admin-module-view'); document.getElementById('admin-dashboard-view').style.display = 'none'; root.style.display = 'block'; if (!record) { root.innerHTML = adminModuleHeading('ORDER DETAIL', 'Không tìm thấy dữ liệu', `Không tìm thấy đơn hàng ${id}.`) + '<button class="admin-button secondary" onclick="history.back()">← Quay lại</button>'; return; } root.innerHTML = adminModuleHeading('ORDER DETAIL', id, 'Chi tiết đơn hàng trong Mock Mode.') + `<div class="admin-detail-grid"><section class="admin-panel"><h2>Thông tin đơn hàng</h2><div class="admin-detail-list"><p><b>Buyer</b>${record[1]}</p><p><b>Seller</b>${record[2]}</p><p><b>Tổng tiền</b>${record[3]}</p><p><b>Payment</b>${record[4]}</p><p><b>Status</b>${record[5]}</p><p><b>Ngày tạo</b>${record[6]}</p></div></section><section class="admin-panel"><h2>Timeline</h2><div class="admin-timeline"><div><i></i><span>Đặt hàng<small>${record[6]}</small></span></div><div><i></i><span>Thanh toán / xử lý<small>${record[4]}</small></span></div><div><i></i><span>${record[5]}<small>Mock timeline</small></span></div></div></section></div><div class="admin-detail-actions"><button class="admin-button secondary" onclick="history.back()">← Quay lại</button></div>`; }
  function renderAdminEntityDetail(type, id) {
    document.getElementById('admin-dashboard-view').style.display = 'none';
    document.getElementById('admin-module-view').style.display = 'block';
    if (type === 'orders') return renderAdminOrderDetail(id);
    const serviceMap = { sellers: ['SellerService', 'getSeller', 'Gian hàng'], products: ['ProductService', 'getProduct', 'Sản phẩm'], users: ['UserService', 'getUser', 'Người dùng'] };
    const [serviceName, method, label] = serviceMap[type];
    document.getElementById('admin-module-view').innerHTML = adminModuleHeading('DETAIL', `${label} ${id}`, 'Đang tải dữ liệu bản ghi...');
    adminService()[serviceName][method](id).then(record => {
      if (!record) { document.getElementById('admin-module-view').innerHTML = adminModuleHeading('DETAIL', 'Không tìm thấy dữ liệu', `Không tìm thấy ${label.toLowerCase()} với mã ${id}.`) + '<button class="admin-button secondary" onclick="history.back()">← Quay lại</button>'; return; }
      const fields = type === 'products' ? [['Tên sách', record.title], ['Tác giả', record.author], ['ISBN', record.isbn || 'Chưa có'], ['Giá', formatVND(record.discount_price || record.price)], ['Tồn kho', record.stock], ['Trạng thái', record.status]] : type === 'sellers' ? [['Tên gian hàng', record.shop_name || record.full_name], ['Owner', record.full_name], ['Email', record.email], ['Số điện thoại', record.phone || 'Chưa có'], ['Giấy phép', record.business_license || 'Chưa tải lên'], ['Trạng thái', record.status]] : [['Họ tên', record.full_name || record.username], ['Email', record.email], ['Username', record.username], ['Vai trò', record.role], ['Số điện thoại', record.phone || 'Chưa có'], ['Trạng thái', record.status]];
      document.getElementById('admin-module-view').innerHTML = adminModuleHeading('DETAIL', `${label} ${id}`, 'Dữ liệu được tải theo đúng ID record.') + `<section class="admin-panel"><div class="admin-detail-list">${fields.map(([key, value]) => `<p><b>${key}</b><span>${value}</span></p>`).join('')}</div><div class="admin-detail-actions"><button class="admin-button secondary" onclick="history.back()">← Quay lại</button>${type === 'products' && record.status === 'PENDING' ? `<button class="admin-button primary" onclick="confirmAdminAction('Duyệt sản phẩm?', () => runAdminAction(this, () => adminService().ProductService.approveProduct('${id}'), 'Đã duyệt sản phẩm.'))">Duyệt</button><button class="admin-button danger" onclick="promptAdminReason('Từ chối sản phẩm', reason => runAdminAction(this, () => adminService().ProductService.rejectProduct('${id}', reason), 'Đã từ chối sản phẩm.'))">Từ chối</button>` : ''}${type === 'sellers' && record.status === 'PENDING_SELLER_APPROVAL' ? `<button class="admin-button primary" onclick="confirmAdminAction('Duyệt hồ sơ seller?', () => runAdminAction(this, () => adminService().SellerService.approveSeller('${id}'), 'Đã duyệt seller.'))">Duyệt</button><button class="admin-button danger" onclick="promptAdminReason('Từ chối seller', reason => runAdminAction(this, () => adminService().SellerService.rejectSeller('${id}', reason), 'Đã từ chối seller.'))">Từ chối</button>` : ''}${type === 'users' ? `<button class="admin-button danger" onclick="confirmAdminAction('${record.status === 'BANNED' ? 'Mở khóa' : 'Khóa'} tài khoản?', () => runAdminAction(this, () => adminService().UserService.toggleUser('${id}'), 'Đã cập nhật trạng thái tài khoản.'))">${record.status === 'BANNED' ? 'Mở khóa' : 'Khóa'}</button>` : ''}</div></section>`;
    }).catch(error => { document.getElementById('admin-module-view').innerHTML = adminModuleHeading('DETAIL', 'Không thể tải dữ liệu', error.message) + '<button class="admin-button secondary" onclick="history.back()">← Quay lại</button>'; });
  }
  return mockKey;
}

// Global handlers used by HTML generated for live Admin tables.
function updateAdminSelection() { const selected = document.querySelectorAll('.admin-row-check:checked').length; const count = document.getElementById('admin-selected-count'); const toolbar = document.getElementById('admin-bulk-toolbar'); if (count) count.textContent = selected; if (toolbar) toolbar.hidden = selected === 0; }
function selectedAdminIds() { return [...document.querySelectorAll('.admin-row-check:checked')].map(item => item.dataset.recordId); }
function confirmBulkAdminAction(action) { const ids = selectedAdminIds(); if (!ids.length) return showToast('Vui lòng chọn ít nhất một sản phẩm.', 'warning'); confirmAdminAction(`Duyệt ${ids.length} sản phẩm?`, () => runBulkProductAction(ids, action)); }
function promptBulkAdminReject() { const ids = selectedAdminIds(); if (!ids.length) return showToast('Vui lòng chọn ít nhất một sản phẩm.', 'warning'); promptAdminReason(`Từ chối ${ids.length} sản phẩm`, reason => runBulkProductAction(ids, 'reject', reason)); }
async function runBulkProductAction(ids, action, reason = '') { const button = document.querySelector('.admin-bulk-toolbar .admin-button.primary'); if (button) { button.disabled = true; button.textContent = 'Đang xử lý...'; } let success = 0; let failed = 0; for (const id of ids) { try { const service = adminService().ProductService; if (action === 'approve') await service.approveProduct(id); else await service.rejectProduct(id, reason); success += 1; } catch (error) { failed += 1; } } showToast(`Đã xử lý ${success} sản phẩm${failed ? `, ${failed} sản phẩm không thể xử lý` : ''}.`, failed ? 'warning' : 'success'); if (button) { button.disabled = false; button.textContent = 'Duyệt hàng loạt'; } await loadPendingBooks(); }
function showAdminRecord(id) { showToast(`Đã chọn bản ghi ${id}.`, 'info'); }
function showAdminSeller(id) { history.pushState({ adminDetail: true }, '', `/admin/sellers/${id}`); renderAdminEntityDetail('sellers', id); }
function showAdminProduct(id) { history.pushState({ adminDetail: true }, '', `/admin/products/${id}`); renderAdminEntityDetail('products', id); }
function showAdminUser(id) { history.pushState({ adminDetail: true }, '', `/admin/users/${id}`); renderAdminEntityDetail('users', id); }
function openAdminOrder(id) { history.pushState({ adminDetail: true }, '', `/admin/orders/${encodeURIComponent(id)}`); renderAdminOrderDetail(id); }
async function renderAdminOrderDetail(id) { const root = document.getElementById('admin-module-view'); document.getElementById('admin-dashboard-view').style.display = 'none'; root.style.display = 'block'; root.innerHTML = adminModuleHeading('ORDER DETAIL', `Đơn hàng #${id}`, 'Đang tải dữ liệu từ database...'); try { const order = await apiCall(`/api/admin/orders/${id}`); root.innerHTML = adminModuleHeading('ORDER DETAIL', order.order_code, 'Chi tiết đơn hàng từ backend.') + `<div class="admin-detail-grid"><section class="admin-panel"><h2>Thông tin đơn hàng</h2><div class="admin-detail-list"><p><b>Buyer</b>${order.buyer}</p><p><b>Seller</b>${order.seller}</p><p><b>Tổng tiền</b>${formatVND(order.total)}</p><p><b>Payment</b>${order.payment}</p><p><b>Status</b>${order.status}</p><p><b>Địa chỉ giao</b>${order.shipping}</p><p><b>Ngày tạo</b>${new Date(order.created_at).toLocaleString('vi-VN')}</p></div></section><section class="admin-panel"><h2>Sản phẩm</h2><div class="admin-detail-list">${order.items.map(item => `<p><b>${item.title}</b><span>${item.quantity} × ${formatVND(item.price)}</span></p>`).join('')}</div></section></div><div class="admin-detail-actions"><button class="admin-button secondary" onclick="history.back()">← Quay lại</button></div>`; } catch (error) { root.innerHTML = adminModuleHeading('ORDER DETAIL', 'Không thể tải dữ liệu', error.message) + '<button class="admin-button secondary" onclick="history.back()">← Quay lại</button>'; } }
function renderAdminEntityDetail(type, id) {
  document.getElementById('admin-dashboard-view').style.display = 'none'; document.getElementById('admin-module-view').style.display = 'block';
  if (type === 'orders') return renderAdminOrderDetail(id);
  const serviceMap = { sellers: ['SellerService', 'getSeller', 'Gian hàng'], products: ['ProductService', 'getProduct', 'Sản phẩm'], users: ['UserService', 'getUser', 'Người dùng'] }; const [serviceName, method, label] = serviceMap[type];
  document.getElementById('admin-module-view').innerHTML = adminModuleHeading('DETAIL', `${label} ${id}`, 'Đang tải dữ liệu bản ghi...');
  adminService()[serviceName][method](id).then(record => { if (!record) { document.getElementById('admin-module-view').innerHTML = adminModuleHeading('DETAIL', 'Không tìm thấy dữ liệu', `Không tìm thấy ${label.toLowerCase()} với mã ${id}.`) + '<button class="admin-button secondary" onclick="history.back()">← Quay lại</button>'; return; } const fields = type === 'products' ? [['Tên sách', record.title], ['Tác giả', record.author], ['ISBN', record.isbn || 'Chưa có'], ['Giá', formatVND(record.discount_price || record.price)], ['Tồn kho', record.stock], ['Trạng thái', record.status]] : type === 'sellers' ? [['Tên gian hàng', record.shop_name || record.full_name], ['Owner', record.full_name], ['Email', record.email], ['Số điện thoại', record.phone || 'Chưa có'], ['Giấy phép', record.business_license || 'Chưa tải lên'], ['Trạng thái', record.status]] : [['Họ tên', record.full_name || record.username], ['Email', record.email], ['Username', record.username], ['Vai trò', record.role], ['Số điện thoại', record.phone || 'Chưa có'], ['Trạng thái', record.status]]; document.getElementById('admin-module-view').innerHTML = adminModuleHeading('DETAIL', `${label} ${id}`, 'Dữ liệu được tải theo đúng ID record.') + `<section class="admin-panel"><div class="admin-detail-list">${fields.map(([key, value]) => `<p><b>${key}</b><span>${value}</span></p>`).join('')}</div><div class="admin-detail-actions"><button class="admin-button secondary" onclick="history.back()">← Quay lại</button></div></section>`; }).catch(error => { document.getElementById('admin-module-view').innerHTML = adminModuleHeading('DETAIL', 'Không thể tải dữ liệu', error.message) + '<button class="admin-button secondary" onclick="history.back()">← Quay lại</button>'; });
}

async function loadPendingSellers() {
  try {
    const sellers = await apiCall('/api/admin/sellers/pending');
    const container = document.getElementById('admin-pending-sellers-table');
    if (!container) {
      renderAdminApiTable('Gian hàng & hồ sơ chờ duyệt', 'Kiểm tra thông tin pháp lý trước khi cấp quyền bán hàng.', ['Gian hàng', 'Owner', 'Email', 'Giấy phép', 'Trạng thái'], sellers.map(s => ({ id: s.id, record: s, cells: [s.shop_name || s.full_name, s.full_name, s.email, s.business_license || 'Chưa tải lên', '<span class="admin-status warning">Chờ duyệt</span>'] })), (id, record) => `<button class="admin-row-action" onclick="showAdminSeller('${id}')">Xem chi tiết</button>${record.business_license ? `<button class="admin-row-action" onclick="openAdminDocument('DOC-01')">Xem giấy phép</button>` : ''}<button class="admin-row-action" onclick="confirmAdminAction('Duyệt hồ sơ seller?', () => runAdminAction(this, () => adminService().SellerService.approveSeller('${id}'), 'Đã duyệt seller.').then(() => loadPendingSellers()))">Duyệt</button><button class="admin-row-action danger-text" onclick="promptAdminReason('Từ chối hồ sơ seller', reason => runAdminAction(this, () => adminService().SellerService.rejectSeller('${id}', reason), 'Đã từ chối seller.').then(() => loadPendingSellers()))">Từ chối</button>`);
      return;
    }
    
    if (sellers.length === 0) {
      container.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:20px; color:#94a3b8;">Không có NXB nào đang chờ duyệt</td></tr>`;
      return;
    }

    let html = '';
    sellers.forEach(s => {
      html += `
        <tr>
          <td>
            <b>${s.shop_name || s.full_name}</b>
            <div style="font-size:11px; color:#64748b;">Username: ${s.username} | SĐT: ${s.phone || 'Chưa có'}</div>
          </td>
          <td><span style="font-size:12px; background:#e0e7ff; padding:3px 8px; border-radius:4px;">${s.business_license || 'Chưa nộp GPKD'}</span></td>
          <td>${s.shop_description || 'Chưa có mô tả'}</td>
          <td><span class="badge badge-warning">Chờ thẩm định</span></td>
          <td>
            <div style="display:flex; gap:6px;">
              <button class="btn-success" onclick="approveSellerByAdmin(${s.id})">✅ Duyệt Cấp Phép</button>
              <button class="btn-danger" onclick="rejectSellerByAdmin(${s.id})">❌ Từ Chối</button>
            </div>
          </td>
        </tr>
      `;
    });
    container.innerHTML = html;
  } catch (e) {}
}

async function approveSellerByAdmin(sellerId) {
  confirmAdminAction('Duyệt hồ sơ seller?', () => runAdminAction(document.activeElement, () => adminService().SellerService.approveSeller(sellerId), 'Đã duyệt seller.').then(() => loadPendingSellers()));
}

async function rejectSellerByAdmin(sellerId) {
  promptAdminReason('Từ chối hồ sơ seller', reason => runAdminAction(document.activeElement, () => adminService().SellerService.rejectSeller(sellerId, reason), 'Đã từ chối seller.').then(() => loadPendingSellers()));
}

async function loadPendingBooks() {
  try {
    const books = await apiCall('/api/admin/books/pending');
    const container = document.getElementById('admin-pending-books-table');
    if (!container) {
      renderAdminApiTable('Sản phẩm & duyệt sách', 'Thẩm định nội dung và thông tin sách trước khi xuất hiện trên marketplace.', ['Sản phẩm', 'ISBN', 'Seller / NXB', 'Giá', 'Tồn kho', 'Trạng thái'], books.map(b => ({ id: b.id, record: b, cells: [`<b>${b.title}</b><small>${b.author}</small>`, b.isbn || 'Chưa có', b.seller_shop_name, formatVND(b.discount_price || b.price), b.stock, '<span class="admin-status warning">Chờ duyệt</span>'] })), (id, record) => `<button class="admin-row-action" onclick="showAdminProduct('${id}')">Xem</button><button class="admin-row-action" onclick="confirmAdminAction('Duyệt sản phẩm?', () => runAdminAction(this, () => adminService().ProductService.approveProduct('${id}'), 'Đã duyệt sản phẩm.').then(() => loadPendingBooks()))">Duyệt</button><button class="admin-row-action danger-text" onclick="promptAdminReason('Từ chối sản phẩm', reason => runAdminAction(this, () => adminService().ProductService.rejectProduct('${id}', reason), 'Đã từ chối sản phẩm.').then(() => loadPendingBooks()))">Từ chối</button>`);
      return;
    }

    if (books.length === 0) {
      container.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:20px; color:#94a3b8;">Hiện không có cuốn sách nào chờ duyệt</td></tr>`;
      return;
    }

    let html = '';
    books.forEach(b => {
      html += `
        <tr>
          <td>
            <div style="display:flex; align-items:center; gap:8px;">
              <img src="${b.cover_image}" style="width:36px; height:48px; object-fit:cover; border-radius:4px;">
              <div>
                <b>${b.title}</b>
                <div style="font-size:11px; color:#64748b;">Tác giả: ${b.author}</div>
              </div>
            </div>
          </td>
          <td>${b.seller_shop_name}</td>
          <td><b>${formatVND(b.discount_price || b.price)}</b> (Kho: ${b.stock})</td>
          <td>
            <button class="btn-preview" style="padding:3px 8px; font-size:11px;" onclick="openBookReaderModal(${b.id})">📖 Đọc thử thẩm định</button>
          </td>
          <td>
            <div style="display:flex; gap:6px;">
              <button class="btn-success" onclick="approveBookByAdmin(${b.id})">✅ Duyệt Lên Sàn</button>
              <button class="btn-danger" onclick="rejectBookByAdmin(${b.id})">❌ Từ Chối</button>
            </div>
          </td>
        </tr>
      `;
    });
    container.innerHTML = html;
  } catch (e) {}
}

async function approveBookByAdmin(bookId) {
  confirmAdminAction('Duyệt sản phẩm?', () => runAdminAction(document.activeElement, () => adminService().ProductService.approveProduct(bookId), 'Đã duyệt sản phẩm.').then(() => loadPendingBooks()));
}

async function rejectBookByAdmin(bookId) {
  promptAdminReason('Từ chối sản phẩm', reason => runAdminAction(document.activeElement, () => adminService().ProductService.rejectProduct(bookId, reason), 'Đã từ chối sản phẩm.').then(() => loadPendingBooks()));
}

async function loadAllUsersAdmin() {
  try {
    const users = await apiCall('/api/admin/users');
    const container = document.getElementById('admin-users-table');
    if (!container) {
      renderAdminApiTable('Người dùng', 'Quản lý buyer, seller, admin và trạng thái tài khoản.', ['Người dùng', 'Email', 'Vai trò', 'Trạng thái', 'Ngày tham gia'], users.map(u => ({ id: u.id, record: u, cells: [`<b>${u.full_name || u.username}</b><small>@${u.username}</small>`, u.email, u.role, `<span class="admin-status ${u.status === 'BANNED' ? 'danger' : 'success'}">${u.status === 'BANNED' ? 'Đã khóa' : 'Hoạt động'}</span>`, new Date(u.created_at).toLocaleDateString('vi-VN')] })), (id, record) => `<button class="admin-row-action" onclick="showAdminUser('${id}')">Xem</button><button class="admin-row-action" onclick="confirmAdminAction('${record.status === 'BANNED' ? 'Mở khóa' : 'Khóa'} tài khoản?', () => runAdminAction(this, () => adminService().UserService.toggleUser('${id}'), 'Đã cập nhật trạng thái tài khoản.').then(() => loadAllUsersAdmin()))">${record.status === 'BANNED' ? 'Mở khóa' : 'Khóa'}</button>`);
      return;
    }

    let html = '';
    users.forEach(u => {
      const isBanned = u.status === 'BANNED';
      html += `
        <tr>
          <td>
            <b>${u.full_name || u.username}</b>
            <div style="font-size:11px; color:#64748b;">@${u.username} (${u.email})</div>
          </td>
          <td><span class="badge badge-info">${u.role}</span></td>
          <td>
            ${isBanned 
              ? '<span class="badge badge-danger">🔒 Đang bị khóa</span>' 
              : '<span class="badge badge-success">Hoạt động</span>'}
          </td>
          <td>${u.is_vip ? '👑 VIP Member' : 'Thường'}</td>
          <td>
            <button class="${isBanned ? 'btn-success' : 'btn-danger'}" style="padding:4px 8px; font-size:11px;" onclick="toggleBanUserByAdmin(${u.id})">
              ${isBanned ? '🔓 Mở khóa tài khoản' : '🔒 Khóa gian lận'}
            </button>
          </td>
        </tr>
      `;
    });
    container.innerHTML = html;
  } catch (e) {}
}

async function toggleBanUserByAdmin(userId) {
  confirmAdminAction('Thay đổi trạng thái tài khoản?', () => runAdminAction(document.activeElement, () => adminService().UserService.toggleUser(userId), 'Đã cập nhật trạng thái tài khoản.').then(() => loadAllUsersAdmin()));
}

// Modal helper
function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('open');
}

// ================================================================
// AUTH PAGE FUNCTIONS - Đăng Nhập / Đăng Ký / Đăng Xuất
// ================================================================

let selectedRegisterRole = 'BUYER';
let pendingSellerDocument = null;
let pendingPublisherDocument = null;

function clearFileInput(inputId, metaId, stateKey) {
  const input = document.getElementById(inputId);
  const meta = document.getElementById(metaId);
  if (input) input.value = '';
  if (meta) meta.textContent = 'Chưa có tệp nào được chọn';
  if (stateKey === 'pendingSellerDocument') pendingSellerDocument = null;
  if (stateKey === 'pendingPublisherDocument') pendingPublisherDocument = null;
}

function showPolicyPage(type) {
  const url = type === 'terms' ? '/terms' : '/privacy';
  window.location.href = url;
}

function showRegisterFormAgain() {
  const registerForm = document.getElementById('register-form');
  const verificationForm = document.getElementById('seller-verification-form');
  if (registerForm) registerForm.classList.add('active');
  if (verificationForm) verificationForm.classList.remove('active');
  switchAuthTab('register');
}

function updateSellerVerificationVisibility() {
  const sameAsOffice = document.getElementById('seller-same-address');
  const shippingBlock = document.getElementById('seller-shipping-address-block');
  if (!sameAsOffice || !shippingBlock) return;
  const shouldShow = !sameAsOffice.checked;
  shippingBlock.classList.toggle('hidden', !shouldShow);
}

function bindSellerVerificationEvents() {
  const fileInput = document.getElementById('seller-document-input');
  if (fileInput) {
    fileInput.addEventListener('change', (event) => {
      const file = event.target.files && event.target.files[0];
      const meta = document.getElementById('seller-document-meta');
      if (!file) {
        pendingSellerDocument = null;
        if (meta) meta.textContent = 'Chưa có tệp nào được chọn';
        return;
      }
      const validTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'];
      if (!validTypes.includes(file.type) && !['pdf', 'jpg', 'jpeg', 'png'].includes((file.name || '').split('.').pop()?.toLowerCase())) {
        showToast('File không hợp lệ. Chỉ chấp nhận PDF, JPG, JPEG, PNG.', 'error');
        event.target.value = '';
        pendingSellerDocument = null;
        if (meta) meta.textContent = 'Chưa có tệp nào được chọn';
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        showToast('Dung lượng file tối đa là 5MB.', 'error');
        event.target.value = '';
        pendingSellerDocument = null;
        if (meta) meta.textContent = 'Chưa có tệp nào được chọn';
        return;
      }
      pendingSellerDocument = file;
      if (meta) {
        const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
        meta.textContent = `${file.name} • ${sizeMb} MB • Đã upload`;
      }
    });
  }

  const publisherFileInput = document.getElementById('seller-publisher-document-input');
  if (publisherFileInput) {
    publisherFileInput.addEventListener('change', (event) => {
      const file = event.target.files && event.target.files[0];
      const meta = document.getElementById('seller-publisher-document-meta');
      if (!file) {
        pendingPublisherDocument = null;
        if (meta) meta.textContent = 'Chưa có tệp nào được chọn';
        return;
      }
      const validTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'];
      if (!validTypes.includes(file.type) && !['pdf', 'jpg', 'jpeg', 'png'].includes((file.name || '').split('.').pop()?.toLowerCase())) {
        showToast('File xuất bản không hợp lệ. Chỉ chấp nhận PDF, JPG, JPEG, PNG.', 'error');
        event.target.value = '';
        pendingPublisherDocument = null;
        if (meta) meta.textContent = 'Chưa có tệp nào được chọn';
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        showToast('Dung lượng file xuất bản tối đa là 5MB.', 'error');
        event.target.value = '';
        pendingPublisherDocument = null;
        if (meta) meta.textContent = 'Chưa có tệp nào được chọn';
        return;
      }
      pendingPublisherDocument = file;
      if (meta) {
        const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
        meta.textContent = `${file.name} • ${sizeMb} MB • Đã upload`;
      }
    });
  }

  const sameAddressToggle = document.getElementById('seller-same-address');
  if (sameAddressToggle) {
    sameAddressToggle.addEventListener('change', updateSellerVerificationVisibility);
  }

  const sellerBusinessType = document.getElementById('seller-business-type');
  if (sellerBusinessType) {
    sellerBusinessType.addEventListener('change', () => {
      const isPublisher = sellerBusinessType.value === 'PUBLISHER';
      const publisherSection = document.getElementById('seller-publisher-doc-upload');
      if (publisherSection) publisherSection.classList.toggle('hidden', !isPublisher);
    });
  }
}

function showPublicMarketplace() {
  const authPage = document.getElementById('auth-page');
  const mainAppWrapper = document.getElementById('main-app-wrapper');
  if (authPage) authPage.style.display = 'none';
  if (mainAppWrapper) mainAppWrapper.style.display = 'block';
  const checkoutRoot = document.getElementById('single-checkout-root');
  const successRoot = document.getElementById('order-success-root');
  const detailRoot = document.getElementById('book-detail-root');
  if (checkoutRoot) checkoutRoot.style.display = 'none';
  if (successRoot) successRoot.style.display = 'none';
  if (detailRoot) detailRoot.style.display = 'none';
  resetPageScroll();
  renderUserProfileWidget();
  loadCategories();
  initFlashSaleCountdown();
  switchPortal('BUYER');
}

function showAuthPage() {
  document.getElementById('auth-page').style.display = 'flex';
  document.getElementById('main-app-wrapper').style.display = 'none';
}

function hideAuthPage() {
  document.getElementById('auth-page').style.display = 'none';
  document.getElementById('main-app-wrapper').style.display = 'block';
}

async function enterMainApp() {
  hideAuthPage();
  renderUserProfileWidget();
  
  // Update demo role buttons
  document.querySelectorAll('.role-btn[data-username]').forEach(btn => {
    btn.classList.remove('active');
    if (state.currentUser && btn.dataset.username === state.currentUser.username) {
      btn.classList.add('active');
    }
  });

  await loadCategories();

  // Route to correct portal based on role
  if (state.currentUser.role === 'ADMIN') {
    switchPortal('ADMIN');
  } else if (state.currentUser.role === 'SELLER') {
    switchPortal('SELLER');
  } else {
    switchPortal('BUYER');
  }
}

function switchAuthTab(tab) {
  const loginTab = document.getElementById('tab-login');
  const registerTab = document.getElementById('tab-register');
  const loginForm = document.getElementById('login-form');
  const registerForm = document.getElementById('register-form');
  const verificationForm = document.getElementById('seller-verification-form');

  if (loginTab) loginTab.classList.toggle('active', tab === 'login');
  if (registerTab) registerTab.classList.toggle('active', tab === 'register');
  if (loginForm) loginForm.classList.toggle('active', tab === 'login');
  if (registerForm) registerForm.classList.toggle('active', tab === 'register');
  if (verificationForm) verificationForm.classList.toggle('active', tab === 'seller-verification');
}

function selectRegisterRole(role) {
  selectedRegisterRole = role;
  document.querySelectorAll('.role-card').forEach(card => {
    card.classList.toggle('selected', card.dataset.role === role);
  });

  const registerForm = document.getElementById('register-form');
  const verificationForm = document.getElementById('seller-verification-form');
  const sellerFields = document.getElementById('seller-extra-fields');
  const loginForm = document.getElementById('login-form');
  const registerTab = document.getElementById('tab-register');
  const loginTab = document.getElementById('tab-login');

  if (role === 'SELLER') {
    if (registerForm) registerForm.classList.remove('active');
    if (verificationForm) verificationForm.classList.add('active');
    if (loginForm) loginForm.classList.remove('active');
    if (registerTab) registerTab.classList.add('active');
    if (loginTab) loginTab.classList.remove('active');
  } else {
    if (registerForm) registerForm.classList.add('active');
    if (verificationForm) verificationForm.classList.remove('active');
    if (loginForm) loginForm.classList.remove('active');
    if (registerTab) registerTab.classList.add('active');
    if (loginTab) loginTab.classList.remove('active');
  }

  if (sellerFields) {
    sellerFields.classList.toggle('visible', role === 'SELLER');
  }
}

function togglePasswordVisibility(inputId, btn) {
  const input = document.getElementById(inputId);
  if (input.type === 'password') {
    input.type = 'text';
    btn.textContent = '🙈';
  } else {
    input.type = 'password';
    btn.textContent = '👁️';
  }
}

// Handle Login Form Submit
async function handleLogin(event) {
  event.preventDefault();
  
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;

  if (!username || !password) {
    showToast('Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu', 'warning');
    return;
  }

  try {
    const data = await apiCall('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username: username, password: password })
    });

    state.token = data.access_token;
    state.currentUser = data.user;

    // Save session to localStorage
    localStorage.setItem('bookhub_token', data.access_token);
    localStorage.setItem('bookhub_user', JSON.stringify(data.user));

    showToast(`Đăng nhập thành công! Chào mừng ${data.user.full_name || data.user.username}`, 'success');

    const pendingBuyNow = JSON.parse(localStorage.getItem('bookhub_pending_buy_now') || 'null');
    if (pendingBuyNow) {
      localStorage.removeItem('bookhub_pending_buy_now');
      await openCheckoutForSingleProduct(pendingBuyNow.bookId, pendingBuyNow.quantity || 1, true);
      return;
    }

    await enterMainApp();
  } catch (e) {
    // Error already shown by apiCall
  }
}

// Handle Register Form Submit
async function handleRegister(event) {
  event.preventDefault();

  const fullName = document.getElementById('reg-fullname').value.trim();
  const email = document.getElementById('reg-email').value.trim();
  const phone = document.getElementById('reg-phone').value.trim();
  const username = document.getElementById('reg-username').value.trim();
  const password = document.getElementById('reg-password').value;
  const passwordConfirm = document.getElementById('reg-password-confirm').value;

  if (!email || !phone || !username || !password || !fullName || !passwordConfirm) {
    showToast('Vui lòng điền đầy đủ các trường bắt buộc (*)', 'warning');
    return;
  }

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    showToast('Email không hợp lệ', 'error');
    return;
  }

  const digits = phone.replace(/\D/g, '');
  if (digits.length < 9 || digits.length > 11) {
    showToast('Số điện thoại không hợp lệ', 'error');
    return;
  }

  if (password !== passwordConfirm) {
    showToast('Mật khẩu xác nhận không khớp! Vui lòng nhập lại.', 'error');
    return;
  }

  if (password.length < 8 || !/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) {
    showToast('Mật khẩu phải có ít nhất 8 ký tự, bao gồm chữ và số.', 'warning');
    return;
  }

  const payload = {
    username: username,
    email: email,
    phone: phone,
    password: password,
    password_confirmation: passwordConfirm,
    full_name: fullName,
    role: selectedRegisterRole,
  };

  try {
    const data = await apiCall('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    state.token = data.access_token;
    state.currentUser = data.user;
    localStorage.setItem('bookhub_token', data.access_token);
    localStorage.setItem('bookhub_user', JSON.stringify(data.user));

    if (selectedRegisterRole === 'SELLER') {
      showToast('Tạo tài khoản thành công! Hệ thống đã chuyển sang bước xác thực gian hàng.', 'success');
      const registerForm = document.getElementById('register-form');
      const verificationForm = document.getElementById('seller-verification-form');
      if (registerForm) registerForm.classList.remove('active');
      if (verificationForm) verificationForm.classList.add('active');
      switchAuthTab('register');
      const verificationFormElement = document.getElementById('seller-verification-form');
      if (verificationFormElement) verificationFormElement.classList.add('active');
      document.getElementById('seller-company-name')?.focus();
      return;
    }

    showToast(`Tạo tài khoản thành công! Chào mừng ${data.user.full_name} đến BookHub!`, 'success');

    const pendingBuyNow = JSON.parse(localStorage.getItem('bookhub_pending_buy_now') || 'null');
    if (pendingBuyNow) {
      localStorage.removeItem('bookhub_pending_buy_now');
      await openCheckoutForSingleProduct(pendingBuyNow.bookId, pendingBuyNow.quantity || 1, true);
      return;
    }

    await enterMainApp();
  } catch (e) {
    // Error already shown by apiCall
  }
}

async function handleSellerVerification(event) {
  event.preventDefault();
  if (selectedRegisterRole !== 'SELLER') {
    showToast('Bước xác thực chỉ dành cho doanh nghiệp / nhà xuất bản.', 'warning');
    return;
  }

  if (!state.currentUser) {
    showToast('Bạn cần đăng nhập lại để tiếp tục xác thực gian hàng.', 'warning');
    return;
  }

  const sellerBusinessType = document.getElementById('seller-business-type').value;
  const sellerLegalBusinessName = document.getElementById('seller-legal-business-name').value.trim();
  const sellerStoreName = document.getElementById('seller-store-name').value.trim();
  const sellerTaxCode = document.getElementById('seller-tax-code').value.trim();
  const sellerRepresentativeName = document.getElementById('seller-representative-name').value.trim();
  const sellerRepresentativePosition = document.getElementById('seller-representative-position').value.trim();
  const sellerRepresentativeId = document.getElementById('seller-representative-id').value.trim();
  const sellerOfficeProvince = document.getElementById('seller-office-province').value.trim();
  const sellerOfficeDistrict = document.getElementById('seller-office-district').value.trim();
  const sellerOfficeWard = document.getElementById('seller-office-ward').value.trim();
  const sellerOfficeStreet = document.getElementById('seller-office-street').value.trim();
  const sellerBankHolder = document.getElementById('seller-bank-holder').value.trim();
  const sellerBankAccount = document.getElementById('seller-bank-account').value.trim();
  const sellerBankName = document.getElementById('seller-bank-name').value.trim();
  const hasAcceptService = document.getElementById('seller-terms-service').checked;
  const hasAcceptPrivacy = document.getElementById('seller-privacy-policy').checked;

  const payload = {
    business_type: sellerBusinessType,
    company_name: sellerLegalBusinessName,
    shop_name: sellerStoreName,
    tax_code: sellerTaxCode,
    company_email: document.getElementById('seller-company-email').value.trim(),
    company_phone: document.getElementById('seller-company-phone').value.trim(),
    legal_representative_name: sellerRepresentativeName,
    legal_representative_position: sellerRepresentativePosition,
    legal_representative_id_number: sellerRepresentativeId,
    office_province: sellerOfficeProvince,
    office_district: sellerOfficeDistrict,
    office_ward: sellerOfficeWard,
    office_street: sellerOfficeStreet,
    shipping_same_as_office: document.getElementById('seller-same-address').checked,
    shipping_province: document.getElementById('seller-shipping-province').value.trim(),
    shipping_district: document.getElementById('seller-shipping-district').value.trim(),
    shipping_ward: document.getElementById('seller-shipping-ward').value.trim(),
    shipping_street: document.getElementById('seller-shipping-street').value.trim(),
    bank_name: sellerBankName,
    bank_account_number: sellerBankAccount,
    bank_account_holder: sellerBankHolder,
    terms_accepted: hasAcceptService && hasAcceptPrivacy,
    documents: pendingSellerDocument ? [{ document_type: 'BUSINESS_LICENSE', document_id: 0 }] : []
  };

  const required = [
    sellerBusinessType,
    sellerLegalBusinessName,
    sellerTaxCode,
    sellerStoreName,
    sellerRepresentativeName,
    sellerRepresentativePosition,
    sellerRepresentativeId,
    sellerOfficeProvince,
    sellerOfficeDistrict,
    sellerOfficeWard,
    sellerOfficeStreet,
    sellerBankHolder,
    sellerBankAccount,
    sellerBankName,
  ];
  if (required.some(value => !value || !String(value).trim())) {
    showToast('Vui lòng điền đầy đủ các trường bắt buộc trong hồ sơ doanh nghiệp.', 'warning');
    return;
  }

  if (!hasAcceptService || !hasAcceptPrivacy) {
    showToast('Bạn cần đồng ý với Điều khoản dịch vụ và Chính sách bảo mật trước khi gửi hồ sơ.', 'warning');
    return;
  }

  if (!pendingSellerDocument) {
    showToast('Bạn phải upload Giấy chứng nhận đăng ký doanh nghiệp / Giấy phép kinh doanh.', 'warning');
    return;
  }

  if (sellerBusinessType === 'PUBLISHER' && !pendingPublisherDocument) {
    showToast('Nhà xuất bản phải upload thêm Giấy tờ hoạt động xuất bản.', 'warning');
    return;
  }

  try {
    const uploadedFiles = [];
    const businessUpload = await apiCall('/api/auth/seller/upload-document', {
      method: 'POST',
      body: (() => {
        const formData = new FormData();
        formData.append('file', pendingSellerDocument);
        formData.append('document_type', 'BUSINESS_LICENSE');
        return formData;
      })()
    });
    uploadedFiles.push({ document_type: 'BUSINESS_LICENSE', document_id: businessUpload.id });

    if (sellerBusinessType === 'PUBLISHER' && pendingPublisherDocument) {
      const publisherUpload = await apiCall('/api/auth/seller/upload-document', {
        method: 'POST',
        body: (() => {
          const formData = new FormData();
          formData.append('file', pendingPublisherDocument);
          formData.append('document_type', 'PUBLISHER_LICENSE');
          return formData;
        })()
      });
      uploadedFiles.push({ document_type: 'PUBLISHER_LICENSE', document_id: publisherUpload.id });
    }

    payload.documents = uploadedFiles;
    const verificationResponse = await apiCall('/api/auth/seller/verification', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    state.currentUser = verificationResponse;
    localStorage.setItem('bookhub_user', JSON.stringify(verificationResponse));

    const statusEl = document.getElementById('seller-success-status');
    if (statusEl) {
      statusEl.classList.remove('hidden');
      statusEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    const verificationForm = document.getElementById('seller-verification-form');
    if (verificationForm) {
      verificationForm.querySelector('button[type="submit"]').disabled = true;
      verificationForm.querySelector('button[type="submit"]').textContent = 'Đã gửi hồ sơ';
    }

    showToast('Hồ sơ đã được gửi thành công. Trạng thái: ĐANG CHỜ DUYỆT.', 'success');
  } catch (error) {
    // Error already shown by apiCall
  }
}

// Quick Demo Login (from auth page)
async function quickDemoLogin(username) {
  try {
    const data = await apiCall(`/api/auth/demo-switch-user?username=${username}`, { method: 'POST' });
    state.token = data.access_token;
    state.currentUser = data.user;

    localStorage.setItem('bookhub_token', data.access_token);
    localStorage.setItem('bookhub_user', JSON.stringify(data.user));

    showToast(`Đăng nhập demo: ${data.user.full_name || data.user.username} (${data.user.role})`, 'success');
    await enterMainApp();
  } catch (e) {}
}

// Logout
function handleLogout() {
  state.token = null;
  state.currentUser = null;
  state.cart = [];

  localStorage.removeItem('bookhub_token');
  localStorage.removeItem('bookhub_user');
  localStorage.removeItem('bookhub_cart');
  updateCartBadge();

  showToast('Đã đăng xuất thành công!', 'info');
  renderUserProfileWidget();
  showPublicMarketplace();
}

// Full checkout screen used by Buy Now. Cart keeps its existing modal flow.
function renderSingleCheckoutPage(checkout) {
  const appWrapper = document.getElementById('main-app-wrapper');
  const authPage = document.getElementById('auth-page');
  if (appWrapper) appWrapper.style.display = 'block';
  if (authPage) authPage.style.display = 'none';
  document.querySelectorAll('.portal-container').forEach(portal => { portal.style.display = 'none'; });
  const successRoot = document.getElementById('order-success-root');
  if (successRoot) successRoot.style.display = 'none';

  const root = document.getElementById('single-checkout-root');
  if (!root) return;
  const shipping = checkout.shipping_methods || [];
  const shippingOptions = shipping.length ? shipping : [
    { code: 'STANDARD', name: 'Giao tiết kiệm', description: 'Dự kiến nhận sau 2-4 ngày', fee: 25000, delivery_estimate: '12/09 - 14/09' },
    { code: 'EXPRESS', name: 'Giao nhanh', description: 'Ưu tiên xử lý đơn hàng', fee: 40000, delivery_estimate: '11/09 - 12/09' },
    { code: 'SAME_DAY', name: 'Giao hỏa tốc', description: 'Trong khu vực hỗ trợ', fee: 60000, delivery_estimate: '10/09' }
  ];
  const selectedShipping = checkout.shipping_method || 'STANDARD';
  const shippingMarkup = shippingOptions.map(method => `
    <label class="shipping-option"><input type="radio" name="checkout-shipping" value="${method.code}" data-fee="${method.fee}" data-estimate="${method.delivery_estimate}" ${method.code === selectedShipping ? 'checked' : ''} onchange="updateSingleCheckoutSummary()"><span><strong>${method.name}</strong><small>${method.description}<br>Dự kiến nhận hàng: ${method.delivery_estimate}</small></span><b>${formatVND(method.fee)}</b></label>
  `).join('');
  const subtotal = Number(checkout.subtotal || 0);
  const discount = Number(checkout.discount_amount || 0);
  const fee = Number((shippingOptions.find(item => item.code === selectedShipping) || shippingOptions[0]).fee || 0);

  root.innerHTML = `
    <div class="checkout-page">
      <div class="checkout-header"><div><span class="checkout-eyebrow">BOOKHUB CHECKOUT</span><h2>Hoàn tất đơn hàng</h2><p>Kiểm tra thông tin và chọn phương thức giao hàng trước khi đặt.</p></div><button class="text-link-btn" onclick="showPublicMarketplace(); localStorage.removeItem('bookhub_checkout_single');">← Tiếp tục mua sắm</button></div>
      <div class="checkout-layout">
        <section class="checkout-panel">
          <div class="checkout-step-heading"><span>1</span><div><h3>Địa chỉ nhận hàng</h3><p>Chọn địa chỉ đã lưu hoặc nhập địa chỉ mới</p></div></div>
          <div id="saved-addresses-wrap" class="saved-addresses-wrap"><button type="button" class="btn-preview" onclick="loadSavedCheckoutAddresses()">📍 Chọn địa chỉ đã lưu</button></div>
          <div class="checkout-form-grid"><div class="form-group"><label class="form-label">Họ tên người nhận</label><input id="checkout-name" class="form-control" value="${checkout.shipping_name || ''}" autocomplete="name"></div><div class="form-group"><label class="form-label">Số điện thoại</label><input id="checkout-phone" class="form-control" value="${checkout.shipping_phone || ''}" autocomplete="tel"></div></div>
          <div class="checkout-form-grid"><div class="form-group"><label class="form-label">Tỉnh/Thành phố</label><select id="checkout-province" class="form-control" onchange="loadCheckoutDistricts()"><option value="">Chọn Tỉnh/Thành phố</option></select></div><div class="form-group"><label class="form-label">Quận/Huyện</label><select id="checkout-district" class="form-control" onchange="loadCheckoutWards()" disabled><option value="">Chọn Quận/Huyện</option></select></div></div>
          <div class="checkout-form-grid"><div class="form-group"><label class="form-label">Phường/Xã</label><select id="checkout-ward" class="form-control" disabled><option value="">Chọn Phường/Xã</option></select></div><div class="form-group"><label class="form-label">Số nhà, tên đường</label><input id="checkout-street" class="form-control" placeholder="Ví dụ: 12 Nguyễn Trãi" value="${checkout.shipping_street || ''}"></div></div>
          <div class="form-group"><label class="form-label">Ghi chú <span class="form-optional">(không bắt buộc)</span></label><textarea id="checkout-notes" class="form-control" rows="2" placeholder="Ví dụ: Giao trong giờ hành chính..."></textarea></div>

          <div class="checkout-step-heading"><span>2</span><div><h3>📚 Sản phẩm</h3><p>Mua ngay, không qua giỏ hàng</p></div></div>
          <div class="checkout-product"><img src="${checkout.cover_image || ''}" alt="${checkout.title}" class="checkout-product-image"><div class="checkout-product-info"><div class="checkout-product-label">SÁCH ĐANG CHỌN</div><h3>${checkout.title}</h3><p>Tác giả: <strong>${checkout.author || 'Đang cập nhật'}</strong></p><div class="checkout-product-meta"><span>Đơn giá <strong>${formatVND(checkout.unit_price)}</strong></span><span class="quantity-control"><button type="button" onclick="changeSingleCheckoutQuantity(-1)">−</button><strong id="checkout-quantity">${checkout.quantity}</strong><button type="button" onclick="changeSingleCheckoutQuantity(1)">+</button></span></div></div><strong id="checkout-product-total" class="checkout-product-total">${formatVND(subtotal)}</strong></div>

          <div class="checkout-step-heading"><span>3</span><div><h3>🚚 Phương thức vận chuyển</h3><p>Chọn dịch vụ phù hợp</p></div></div><div class="shipping-options">${shippingMarkup}</div>
          <div class="checkout-step-heading"><span>4</span><div><h3>🎟 Voucher</h3><p>Nhập hoặc chọn mã giảm giá của bạn</p></div></div><div class="voucher-entry"><input id="checkout-voucher" class="form-control" placeholder="Nhập mã voucher"><button type="button" class="btn-preview" onclick="applySingleCheckoutVoucher()">Áp dụng</button><button type="button" class="btn-preview" onclick="showAvailableCheckoutVouchers()">Chọn Voucher</button></div><div id="checkout-voucher-status" class="checkout-inline-status"></div>

          <div class="checkout-step-heading"><span>5</span><div><h3>💳 Phương thức thanh toán</h3><p>Thanh toán online chỉ ở trạng thái chờ xác nhận khi chưa tích hợp gateway</p></div></div><div class="payment-options"><label><input type="radio" name="checkout-payment" value="COD" checked onchange="toggleCheckoutQr()"> COD <small>Thanh toán khi nhận hàng</small></label><label><input type="radio" name="checkout-payment" value="VIETQR" onchange="toggleCheckoutQr()"> VietQR / Chuyển khoản <small>Chờ xác nhận thanh toán</small></label><label><input type="radio" name="checkout-payment" value="MOMO" onchange="toggleCheckoutQr()"> MoMo <small>Chờ kết nối cổng thanh toán</small></label><label><input type="radio" name="checkout-payment" value="ZALOPAY" onchange="toggleCheckoutQr()"> ZaloPay</label><label><input type="radio" name="checkout-payment" value="SHOPEEPAY" onchange="toggleCheckoutQr()"> ShopeePay</label><label><input type="radio" name="checkout-payment" value="CARD" onchange="toggleCheckoutQr()"> ATM / Visa / Mastercard</label></div><div id="checkout-payment-note" class="checkout-payment-note"></div>
        </section>
        <aside class="checkout-summary"><div class="checkout-summary-title"><span>6</span><h3>Tổng thanh toán</h3></div><div class="checkout-summary-line"><span>Tạm tính</span><strong id="checkout-subtotal">${formatVND(subtotal)}</strong></div><div class="checkout-summary-line"><span>Phí vận chuyển</span><strong id="checkout-shipping-fee">${formatVND(fee)}</strong></div><div class="checkout-summary-line checkout-discount"><span>Giảm giá / Voucher</span><strong id="checkout-discount">- ${formatVND(discount)}</strong></div><div class="checkout-total"><span>Tổng thanh toán</span><strong id="checkout-grand-total">${formatVND(Math.max(0, subtotal + fee - discount))}</strong></div><label class="terms-check"><input id="checkout-terms" type="checkbox"> Tôi đồng ý với <a href="#" onclick="showCheckoutPolicy(event, 'Điều khoản dịch vụ')">Điều khoản dịch vụ</a>, <a href="#" onclick="showCheckoutPolicy(event, 'Chính sách mua hàng/đổi trả')">Chính sách mua hàng</a> và <a href="#" onclick="showCheckoutPolicy(event, 'Chính sách bảo mật')">Chính sách bảo mật</a>.</label><button class="btn-primary checkout-submit-btn" onclick="submitSingleProductOrder()">Đặt hàng</button><p class="checkout-secure-note">🔒 Không lưu số thẻ hoặc CVV trên BookHub.</p></aside>
      </div>
    </div>`;
  root.style.display = 'block';
  root.dataset.checkoutSubtotal = subtotal;
  root.dataset.checkoutDiscount = discount;
  root.dataset.checkoutStock = checkout.stock || 1;
  root.dataset.checkoutVoucher = checkout.voucher_code || '';
  loadCheckoutOptions(checkout);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function loadCheckoutOptions(checkout) {
  try {
    const [methods, locations] = await Promise.all([apiCall('/api/orders/shipping-methods'), apiCall('/api/orders/locations')]);
    checkout.shipping_methods = methods;
    window.bookhubLocations = locations.locations || [];
    const province = document.getElementById('checkout-province');
    province.innerHTML = '<option value="">Chọn Tỉnh/Thành phố</option>' + locations.locations.map(item => `<option value="${item.code}">${item.name}</option>`).join('');
    if (checkout.shipping_province_code) { province.value = checkout.shipping_province_code; loadCheckoutDistricts(checkout.shipping_district_code, locations.locations); }
    toggleCheckoutQr();
  } catch (error) { console.error(error); }
}

function loadCheckoutDistricts(selected = '', locationData = null) {
  const province = document.getElementById('checkout-province')?.value;
  const district = document.getElementById('checkout-district');
  if (!district) return;
  const locations = locationData || window.bookhubLocations || [];
  const selectedProvince = locations.find(item => String(item.code) === String(province));
  window.bookhubLocations = locations;
  district.innerHTML = '<option value="">Chọn Quận/Huyện</option>' + (selectedProvince?.districts || []).map(item => `<option value="${item.code}">${item.name}</option>`).join('');
  district.disabled = !selectedProvince;
  const ward = document.getElementById('checkout-ward');
  if (ward) { ward.innerHTML = '<option value="">Chọn Phường/Xã</option>'; ward.disabled = true; }
  if (selected) { district.value = selected; loadCheckoutWards(); }
}

function loadCheckoutWards(selected = '') {
  const province = document.getElementById('checkout-province')?.value;
  const district = document.getElementById('checkout-district')?.value;
  const ward = document.getElementById('checkout-ward');
  const selectedProvince = (window.bookhubLocations || []).find(item => String(item.code) === String(province));
  const selectedDistrict = selectedProvince?.districts.find(item => String(item.code) === String(district));
  if (!ward) return;
  ward.innerHTML = '<option value="">Chọn Phường/Xã</option>' + (selectedDistrict?.wards || []).map(item => `<option value="${item.code}">${item.name}</option>`).join('');
  ward.disabled = !selectedDistrict;
  if (selected) ward.value = selected;
}

async function loadSavedCheckoutAddresses() {
  const wrap = document.getElementById('saved-addresses-wrap');
  try {
    const addresses = await apiCall('/api/orders/addresses');
    wrap.innerHTML = addresses.length ? `<select class="form-control" onchange="selectSavedCheckoutAddress(this.value)"><option value="">📍 Chọn địa chỉ đã lưu</option>${addresses.map(address => `<option value="${address.id}">${address.recipient_name} - ${address.street}, ${address.ward}, ${address.district}, ${address.province}${address.is_default ? ' (Mặc định)' : ''}</option>`).join('')}</select><button type="button" class="btn-preview" onclick="saveCurrentCheckoutAddress()">+ Lưu địa chỉ mới</button>` : '<span class="checkout-inline-status">Chưa có địa chỉ lưu. Hãy nhập và bấm “Lưu địa chỉ mới”.</span><button type="button" class="btn-preview" onclick="saveCurrentCheckoutAddress()">+ Lưu địa chỉ mới</button>';
    window.bookhubAddresses = addresses;
  } catch (error) { console.error(error); }
}

function selectSavedCheckoutAddress(addressId) {
  const address = (window.bookhubAddresses || []).find(item => String(item.id) === String(addressId));
  if (!address) return;
  document.getElementById('checkout-name').value = address.recipient_name;
  document.getElementById('checkout-phone').value = address.phone;
  document.getElementById('checkout-province').value = address.province_code;
  loadCheckoutDistricts(address.district_code);
  setTimeout(() => { loadCheckoutWards(address.ward_code); }, 0);
  document.getElementById('checkout-street').value = address.street;
}

async function saveCurrentCheckoutAddress() {
  const payload = getCheckoutLocationPayload();
  payload.recipient_name = document.getElementById('checkout-name').value.trim();
  payload.phone = document.getElementById('checkout-phone').value.trim();
  payload.street = document.getElementById('checkout-street').value.trim();
  payload.is_default = false;
  if (Object.values(payload).some(value => !value && value !== false)) { showToast('Vui lòng nhập đầy đủ địa chỉ trước khi lưu.', 'warning'); return; }
  await apiCall('/api/orders/addresses', { method: 'POST', body: JSON.stringify(payload) });
  showToast('Đã lưu địa chỉ giao hàng.', 'success');
  loadSavedCheckoutAddresses();
}

function getCheckoutLocationPayload() {
  const province = document.getElementById('checkout-province');
  const district = document.getElementById('checkout-district');
  const ward = document.getElementById('checkout-ward');
  return { province: province?.selectedOptions[0]?.textContent || '', province_code: province?.value || '', district: district?.selectedOptions[0]?.textContent || '', district_code: district?.value || '', ward: ward?.selectedOptions[0]?.textContent || '', ward_code: ward?.value || '' };
}

function changeSingleCheckoutQuantity(delta) {
  const root = document.getElementById('single-checkout-root');
  const checkout = JSON.parse(localStorage.getItem('bookhub_checkout_single') || '{}');
  const quantity = Math.max(1, Math.min(Number(root.dataset.checkoutStock || checkout.stock || 1), Number(checkout.quantity || 1) + delta));
  if (quantity === Number(checkout.quantity || 1) && delta > 0) { showToast('Số lượng vượt quá tồn kho hiện tại.', 'warning'); return; }
  checkout.quantity = quantity;
  checkout.subtotal = Number(checkout.unit_price) * quantity;
  localStorage.setItem('bookhub_checkout_single', JSON.stringify(checkout));
  document.getElementById('checkout-quantity').textContent = quantity;
  document.getElementById('checkout-product-total').textContent = formatVND(checkout.subtotal);
  root.dataset.checkoutSubtotal = checkout.subtotal;
  updateSingleCheckoutSummary();
}

function updateSingleCheckoutSummary() {
  const root = document.getElementById('single-checkout-root');
  const subtotal = Number(root.dataset.checkoutSubtotal || 0);
  const discount = Number(root.dataset.checkoutDiscount || 0);
  const selected = document.querySelector('input[name="checkout-shipping"]:checked');
  const fee = Number(selected?.dataset.fee || 0);
  document.getElementById('checkout-subtotal').textContent = formatVND(subtotal);
  document.getElementById('checkout-shipping-fee').textContent = formatVND(fee);
  document.getElementById('checkout-grand-total').textContent = formatVND(Math.max(0, subtotal + fee - discount));
}

async function applySingleCheckoutVoucher() {
  const root = document.getElementById('single-checkout-root');
  const code = document.getElementById('checkout-voucher').value.trim();
  if (!code) { showToast('Vui lòng nhập mã voucher.', 'warning'); return; }
  try {
    const result = await apiCall('/api/orders/vouchers/apply', { method: 'POST', body: JSON.stringify({ code, subtotal: Number(root.dataset.checkoutSubtotal || 0) }) });
    root.dataset.checkoutDiscount = result.discount_amount;
    root.dataset.checkoutVoucher = result.code;
    document.getElementById('checkout-discount').textContent = `- ${formatVND(result.discount_amount)}`;
    document.getElementById('checkout-voucher-status').textContent = `${result.name} (${result.code}) đã áp dụng.`;
    updateSingleCheckoutSummary();
  } catch (error) { root.dataset.checkoutDiscount = '0'; }
}

async function showAvailableCheckoutVouchers() {
  try {
    const vouchers = await apiCall('/api/orders/vouchers/available');
    const status = document.getElementById('checkout-voucher-status');
    if (!vouchers.length) { status.textContent = 'Hiện chưa có voucher khả dụng.'; return; }
    status.innerHTML = vouchers.map(voucher => `<button type="button" class="voucher-chip" onclick="document.getElementById('checkout-voucher').value='${voucher.code}'; applySingleCheckoutVoucher()">${voucher.code} - ${voucher.name}</button>`).join(' ');
  } catch (error) { console.error(error); }
}

function toggleCheckoutQr() {
  const method = document.querySelector('input[name="checkout-payment"]:checked')?.value;
  const note = document.getElementById('checkout-payment-note');
  if (note) note.textContent = method && method !== 'COD' ? 'Phương thức này chưa kết nối gateway thật. Đơn hàng sẽ ở trạng thái PENDING, không tự đánh dấu đã thanh toán.' : '';
}

function showCheckoutPolicy(event, title) {
  event.preventDefault();
  const content = {
    'Điều khoản dịch vụ': 'Bạn đồng ý cung cấp thông tin nhận hàng chính xác và sử dụng BookHub theo quy định pháp luật.',
    'Chính sách mua hàng/đổi trả': 'Sách được đóng gói và giao theo trạng thái đơn hàng. Vui lòng liên hệ BookHub khi sản phẩm có lỗi hoặc không đúng đơn.',
    'Chính sách bảo mật': 'BookHub chỉ sử dụng thông tin cần thiết để xác thực, xử lý đơn hàng và giao hàng; không lưu số thẻ hoặc CVV.'
  }[title] || 'Thông tin chính sách đang được cập nhật.';
  const existing = document.getElementById('checkout-policy-overlay');
  if (existing) existing.remove();
  document.body.insertAdjacentHTML('beforeend', `<div id="checkout-policy-overlay" class="checkout-policy-overlay" onclick="if(event.target === this) this.remove()"><div class="checkout-policy-dialog"><button type="button" class="checkout-policy-close" onclick="document.getElementById('checkout-policy-overlay').remove()">×</button><h3>${title}</h3><p>${content}</p><button type="button" class="btn-primary" onclick="document.getElementById('checkout-policy-overlay').remove()">Đã hiểu</button></div></div>`);
}

async function submitSingleProductOrder() {
  const checkout = JSON.parse(localStorage.getItem('bookhub_checkout_single') || '{}');
  const root = document.getElementById('single-checkout-root');
  const name = document.getElementById('checkout-name')?.value.trim();
  const phone = document.getElementById('checkout-phone')?.value.trim();
  const location = getCheckoutLocationPayload();
  const province = location.province;
  const district = location.district;
  const ward = location.ward;
  const street = document.getElementById('checkout-street')?.value.trim();
  const shipping = document.querySelector('input[name="checkout-shipping"]:checked');
  const payment = document.querySelector('input[name="checkout-payment"]:checked')?.value;
  if (!name || !phone || !province || !district || !ward || !street) { showToast('Vui lòng chọn đầy đủ địa chỉ nhận hàng.', 'warning'); return; }
  if (!shipping) { showToast('Vui lòng chọn phương thức vận chuyển.', 'warning'); return; }
  if (!payment) { showToast('Vui lòng chọn phương thức thanh toán.', 'warning'); return; }
  if (!document.getElementById('checkout-terms').checked) { showToast('Vui lòng đồng ý với Điều khoản dịch vụ và Chính sách mua hàng.', 'warning'); return; }
  const button = document.querySelector('.checkout-submit-btn');
  button.disabled = true; button.textContent = 'Đang tạo đơn hàng...';
  try {
    const order = await apiCall('/api/orders', { method: 'POST', body: JSON.stringify({ items: [{ book_id: checkout.book_id, quantity: checkout.quantity }], shipping_name: name, shipping_phone: phone, shipping_address: `${street}, ${ward}, ${district}, ${province}`, shipping_province: province, shipping_province_code: location.province_code, shipping_district: district, shipping_district_code: location.district_code, shipping_ward: ward, shipping_ward_code: location.ward_code, shipping_street: street, shipping_method: shipping.value, voucher_code: root.dataset.checkoutVoucher || null, payment_method: payment, terms_accepted: true, notes: document.getElementById('checkout-notes').value.trim() }) });
    localStorage.removeItem('bookhub_checkout_single'); localStorage.removeItem('bookhub_pending_buy_now'); root.style.display = 'none'; showOrderSuccess(order);
  } catch (error) { button.disabled = false; button.textContent = 'Đặt hàng'; }
}

// =============================================================================
// HỆ THỐNG THÔNG BÁO HAI CHIỀU (NXB ↔ Admin)
// =============================================================================

/** State thông báo - lưu trạng thái hiện tại */
const notifState = {
  notifications: [],
  unreadCount: 0,
  pollingInterval: null,
  dropdownOpen: null // 'seller' | 'admin' | null
};

/**
 * Lấy danh sách thông báo từ API và cập nhật UI.
 * Gọi mỗi khi portal được mở hoặc theo polling interval.
 */
async function fetchAndUpdateNotifications() {
  if (!state.token || !state.currentUser) return;
  try {
    const [notifications, countData] = await Promise.all([
      fetch('/api/notifications?limit=20', {
        headers: { 'Authorization': `Bearer ${state.token}` }
      }).then(r => r.ok ? r.json() : []),
      fetch('/api/notifications/unread-count', {
        headers: { 'Authorization': `Bearer ${state.token}` }
      }).then(r => r.ok ? r.json() : { unread_count: 0 })
    ]);

    notifState.notifications = notifications;
    notifState.unreadCount = countData.unread_count || 0;

    updateNotifBadge();

    // Nếu dropdown đang mở, cập nhật nội dung luôn
    if (notifState.dropdownOpen) {
      renderNotifList(notifState.dropdownOpen);
    }
  } catch (e) {
    // Silently fail - notifications are non-critical
  }
}

/** Cập nhật badge đếm số chưa đọc trên Bell Icon */
function updateNotifBadge() {
  const count = notifState.unreadCount;
  const role = state.currentUser?.role;

  // Seller Bell Badge
  const sellerBadge = document.getElementById('seller-notif-badge');
  if (sellerBadge) {
    if (role === 'SELLER' && count > 0) {
      sellerBadge.textContent = count > 99 ? '99+' : count;
      sellerBadge.style.display = 'flex';
    } else {
      sellerBadge.style.display = 'none';
    }
  }

  // Admin Bell Badge
  const adminBadge = document.getElementById('admin-notif-badge');
  if (adminBadge) {
    if (role === 'ADMIN' && count > 0) {
      adminBadge.textContent = count > 99 ? '99+' : count;
      adminBadge.style.display = 'flex';
    } else {
      adminBadge.style.display = 'none';
    }
  }
}

/** Render danh sách thông báo trong dropdown */
function renderNotifList(portal) {
  const listEl = document.getElementById(`${portal}-notif-list`);
  if (!listEl) return;

  if (!notifState.notifications.length) {
    listEl.innerHTML = '<div class="notif-empty">Bạn chưa có thông báo nào 🎉</div>';
    return;
  }

  listEl.innerHTML = notifState.notifications.map(n => {
    const typeIcon = {
      'NEW_BOOK_SUBMITTED': '📚',
      'BOOK_APPROVED': '✅',
      'BOOK_REJECTED': '❌'
    }[n.type] || '🔔';

    const timeAgo = formatTimeAgo(n.created_at);
    const unreadClass = n.is_read ? '' : 'notif-item-unread';

    return `
      <div class="notif-item ${unreadClass}" 
           onclick="handleNotifClick(${n.id}, ${n.reference_id || 'null'}, '${portal}')"
           role="button" tabindex="0">
        <div class="notif-item-icon">${typeIcon}</div>
        <div class="notif-item-body">
          <div class="notif-item-title">${escapeHtml(n.title)}</div>
          <div class="notif-item-message">${escapeHtml(n.message)}</div>
          <div class="notif-item-time">${timeAgo}</div>
        </div>
        ${!n.is_read ? '<span class="notif-item-dot"></span>' : ''}
      </div>
    `;
  }).join('');
}

/** Toggle dropdown mở/đóng */
function toggleNotifDropdown(portal) {
  const dropdown = document.getElementById(`${portal}-notif-dropdown`);
  if (!dropdown) return;

  const isOpen = dropdown.style.display !== 'none';

  // Đóng tất cả dropdown khác trước
  closeAllNotifDropdowns();

  if (isOpen) {
    notifState.dropdownOpen = null;
  } else {
    dropdown.style.display = 'block';
    notifState.dropdownOpen = portal;

    // Animate vào
    dropdown.style.opacity = '0';
    dropdown.style.transform = 'translateY(-8px)';
    requestAnimationFrame(() => {
      dropdown.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
      dropdown.style.opacity = '1';
      dropdown.style.transform = 'translateY(0)';
    });

    // Render notifications
    renderNotifList(portal);

    // Fetch fresh data
    fetchAndUpdateNotifications();
  }
}

/** Đóng tất cả notification dropdown */
function closeAllNotifDropdowns() {
  ['seller', 'admin'].forEach(p => {
    const dd = document.getElementById(`${p}-notif-dropdown`);
    if (dd) dd.style.display = 'none';
  });
  notifState.dropdownOpen = null;
}

/**
 * Xử lý click vào một thông báo:
 * 1. Đánh dấu đã đọc (gọi API)
 * 2. Chuyển hướng tới sách nếu có reference_id
 */
async function handleNotifClick(notifId, bookId, portal) {
  // Đánh dấu đã đọc ngay trên UI (optimistic update)
  const notif = notifState.notifications.find(n => n.id === notifId);
  if (notif && !notif.is_read) {
    notif.is_read = true;
    notifState.unreadCount = Math.max(0, notifState.unreadCount - 1);
    updateNotifBadge();
    renderNotifList(portal);

    // Gọi API trong background
    try {
      await fetch(`/api/notifications/${notifId}/read`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${state.token}` }
      });
    } catch (e) {}
  }

  // Đóng dropdown
  closeAllNotifDropdowns();

  // Chuyển hướng tới sách liên quan
  if (bookId) {
    if (state.currentUser?.role === 'ADMIN') {
      // Admin: mở trang quản lý sản phẩm
      switchAdminView('products');
      showToast(`Đang tải thông tin sách #${bookId}...`, 'info');
    } else if (state.currentUser?.role === 'SELLER') {
      // NXB: chuyển sang tab Quản Lý Sách
      switchSellerTab('products');
      showToast(`Đang mở danh sách sách của bạn...`, 'info');
    }
  }
}

/** Đánh dấu tất cả thông báo là đã đọc */
async function markAllRead(portal) {
  try {
    await fetch('/api/notifications/mark-all-read', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${state.token}` }
    });

    // Cập nhật local state
    notifState.notifications.forEach(n => n.is_read = true);
    notifState.unreadCount = 0;
    updateNotifBadge();
    renderNotifList(portal);
    showToast('Đã đánh dấu tất cả thông báo là đã đọc', 'success');
  } catch (e) {
    showToast('Không thể cập nhật thông báo', 'error');
  }
}

/** Format thời gian tương đối (vd: "5 phút trước") */
function formatTimeAgo(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString + (isoString.endsWith('Z') ? '' : 'Z'));
  const now = new Date();
  const diffMs = now - date;
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return 'Vừa xong';
  if (diffMins < 60) return `${diffMins} phút trước`;
  if (diffHours < 24) return `${diffHours} giờ trước`;
  if (diffDays < 7) return `${diffDays} ngày trước`;
  return date.toLocaleDateString('vi-VN');
}

/** Escape HTML để tránh XSS */
function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/** Bắt đầu auto-polling thông báo mỗi 30 giây */
function startNotifPolling() {
  stopNotifPolling();
  fetchAndUpdateNotifications(); // Lấy ngay lần đầu
  notifState.pollingInterval = setInterval(fetchAndUpdateNotifications, 30000);
}

/** Dừng polling */
function stopNotifPolling() {
  if (notifState.pollingInterval) {
    clearInterval(notifState.pollingInterval);
    notifState.pollingInterval = null;
  }
}

// Đóng dropdown khi click bên ngoài
document.addEventListener('click', (e) => {
  if (!e.target.closest('.notif-bell-wrap')) {
    closeAllNotifDropdowns();
  }
});

// Hook vào switchPortal để bắt đầu/dừng polling theo portal
const _origSwitchPortal = typeof switchPortal === 'function' ? switchPortal : null;
if (_origSwitchPortal) {
  window.switchPortal = function(portal) {
    _origSwitchPortal(portal);
    if (portal === 'SELLER' || portal === 'ADMIN') {
      startNotifPolling();
    } else {
      stopNotifPolling();
      updateNotifBadge();
    }
  };
}

// =============================================================================
// FLASH SALE REAL-TIME DYNAMIC COUNTDOWN TIMER
// =============================================================================
let flashSaleTimerInterval = null;

function initFlashSaleCountdown() {
  const daysEl = document.getElementById('fs-days');
  const hoursEl = document.getElementById('fs-hours');
  const minutesEl = document.getElementById('fs-minutes');
  const secondsEl = document.getElementById('fs-seconds');
  const countdownBox = document.getElementById('flash-sale-countdown');

  if (!daysEl || !hoursEl || !minutesEl || !secondsEl) return;

  const STORAGE_KEY = 'bookhub_flash_sale_target';
  let targetTime = parseInt(localStorage.getItem(STORAGE_KEY), 10);
  const now = Date.now();

  // Mốc thời gian kết thúc Flash Sale (Target Date).
  // Mặc định: 2 ngày, 8 giờ, 32 phút, 18 giây
  if (!targetTime || isNaN(targetTime) || targetTime <= now) {
    const durationMs = (2 * 86400 + 8 * 3600 + 32 * 60 + 18) * 1000;
    targetTime = now + durationMs;
    localStorage.setItem(STORAGE_KEY, targetTime.toString());
  }

  function updateCountdown() {
    const currentTime = Date.now();
    const remainingMs = targetTime - currentTime;

    if (remainingMs <= 0) {
      // Khi hết thời gian đếm ngược (về 00:00:00:00), tự động dừng đếm ngược và xử lý trạng thái hết sale
      if (flashSaleTimerInterval) {
        clearInterval(flashSaleTimerInterval);
        flashSaleTimerInterval = null;
      }
      daysEl.textContent = '00';
      hoursEl.textContent = '00';
      minutesEl.textContent = '00';
      secondsEl.textContent = '00';
      if (countdownBox) {
        countdownBox.classList.add('flash-sale-ended');
      }
      return;
    }

    const totalSeconds = Math.floor(remainingMs / 1000);
    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    // Định dạng số hiển thị luôn có 2 chữ số (dùng padStart(2, '0'))
    daysEl.textContent = String(days).padStart(2, '0');
    hoursEl.textContent = String(hours).padStart(2, '0');
    minutesEl.textContent = String(minutes).padStart(2, '0');
    secondsEl.textContent = String(seconds).padStart(2, '0');
  }

  // Xóa interval cũ nếu đã tồn tại
  if (flashSaleTimerInterval) {
    clearInterval(flashSaleTimerInterval);
    flashSaleTimerInterval = null;
  }

  // Cập nhật ngay tức thì
  updateCountdown();

  // Sử dụng setInterval để cập nhật liên tục mỗi 1000ms (1 giây)
  flashSaleTimerInterval = setInterval(updateCountdown, 1000);
}

window.initFlashSaleCountdown = initFlashSaleCountdown;
