/**
 * app.js — Lógica de interfaz de StockPulse
 * Depende de session.js (debe cargarse antes).
 */
 
const charts = {};
 
// ─── AUTENTICACIÓN ──────────────────────────────────────────────────────────
 
function openLoginModal() {
  const modal = document.getElementById('loginModal');
  if (!modal) return;
  modal.classList.add('show');
  setTimeout(() => { const u = document.getElementById('loginUsername'); if (u) u.focus(); }, 50);
  hideAlert('loginError');
}
 
function closeLoginModal() {
  const modal = document.getElementById('loginModal');
  if (!modal) return;
  modal.classList.remove('show');
  const u = document.getElementById('loginUsername');
  const p = document.getElementById('loginPassword');
  if (u) u.value = '';
  if (p) p.value = '';
}
 
async function submitLogin() {
  const usernameEl = document.getElementById('loginUsername');
  const passwordEl = document.getElementById('loginPassword');
  const btn        = document.getElementById('loginBtn');
  if (!usernameEl || !passwordEl || !btn) return;
 
  const username = usernameEl.value.trim();
  const password = passwordEl.value;
 
  if (!username || !password) { showAlert('loginError', 'Rellena todos los campos.'); return; }
 
  btn.disabled = true;
  btn.textContent = 'Entrando...';
 
  try {
    const res  = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
 
    if (!res.ok) { showAlert('loginError', data.detail || 'Usuario o contraseña incorrectos.'); return; }
 
    session.token    = data.token;
    session.username = data.username || username;
 
    closeLoginModal();
    updateNavbar();
 
    // Si ya estamos en dashboard, cargar directamente sin redirigir
    if (window.location.pathname.includes('dashboard')) {
      loadDashboard();
    } else {
      window.location.href = '/frontend/dashboard.html';
    }
 
  } catch (err) {
    showAlert('loginError', 'No se pudo conectar con el servidor.');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Entrar';
  }
}
 
async function logout() {
  if (session.token) {
    try {
      await fetch(`${API_BASE}/api/auth/logout`, {
        method: 'POST',
        headers: authHeaders()
      });
    } catch (_) {}
  }
  Object.values(charts).forEach(c => { if (c) c.destroy(); });
  Object.keys(charts).forEach(k => delete charts[k]);
  session.clear();
  window.location.href = '/frontend/index.html';
}
 
function updateNavbar() {
  const guest       = document.getElementById('navGuest');
  const user        = document.getElementById('navUser');
  const dashItem    = document.getElementById('navDashboardItem');
  const navUsername = document.getElementById('navUsername');
  const navAvatar   = document.getElementById('navAvatar');
  const uploadArea  = document.getElementById('uploadArea'); // solo en index.html
 
  if (session.isLoggedIn()) {
    if (guest)       guest.style.display    = 'none';
    if (user)        user.style.display     = 'flex';
    if (dashItem)    dashItem.style.display = 'block';
    if (navUsername) navUsername.textContent = session.username;
    if (navAvatar)   navAvatar.textContent   = session.username.charAt(0).toUpperCase();
    if (uploadArea)  uploadArea.style.display = 'block';
  } else {
    if (guest)      guest.style.display    = 'block';
    if (user)       user.style.display     = 'none';
    if (dashItem)   dashItem.style.display = 'none';
    if (uploadArea) uploadArea.style.display = 'none';
  }
}
 
function authHeaders() {
  return { 'Authorization': `Bearer ${session.token}`, 'Content-Type': 'application/json' };
}
 
// ─── CARGA DE ARCHIVOS ──────────────────────────────────────────────────────
 
function handleUploadClick() {
  if (!session.isLoggedIn()) { openLoginModal(); return; }
  triggerFileInput();
}
 
function triggerFileInput() {
  const fi = document.getElementById('fileInput');
  if (fi) fi.click();
}
 
async function handleFileChange(event) {
  const file = event.target.files[0];
  if (!file) return;
 
  // Ocultar alertas antiguas (index.html)
  hideAlert('uploadError');
  hideAlert('uploadSuccess');
 
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['csv', 'xlsx'].includes(ext)) {
    setUploadStatus('error', 'Formato no válido. Solo .csv y .xlsx');
    showAlert('uploadError', 'Formato no válido. Solo se permiten archivos .csv y .xlsx');
    event.target.value = '';
    return;
  }
 
  if (file.size > 50 * 1024 * 1024) {
    setUploadStatus('error', 'Archivo demasiado grande. Máximo 50MB.');
    showAlert('uploadError', 'El archivo es demasiado grande. Máximo 50MB.');
    event.target.value = '';
    return;
  }
 
  // Feedback inmediato en sidebar
  setUploadStatus('loading', `Subiendo "${file.name}"...`);
  setSidebarUploadBtn(false);
  showAlert('uploadSuccess', `Archivo "${file.name}" seleccionado. Procesando...`);
 
  const formData = new FormData();
  formData.append('file', file);
  formData.append('username', session.username);
 
  try {
    const res  = await fetch(`${API_BASE}/api/upload`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${session.token}` },
      body: formData
    });
    const data = await res.json();
 
    if (!res.ok) {
      setUploadStatus('error', data.detail || 'Error al procesar el archivo.');
      showAlert('uploadError', data.detail || 'Error al procesar el archivo.');
      return;
    }
 
    setUploadStatus('success', `✓ "${file.name}" cargado`);
    showAlert('uploadSuccess', 'Archivo procesado correctamente.');
 
    // Si estamos en dashboard, recargar los datos directamente
    if (window.location.pathname.includes('dashboard')) {
      setTimeout(() => {
        setUploadStatus('hidden');
        loadDashboard();
      }, 1500);
    } else {
      setTimeout(() => { window.location.href = '/frontend/dashboard.html'; }, 1500);
    }
 
  } catch (err) {
    setUploadStatus('error', 'No se pudo conectar con el servidor.');
    showAlert('uploadError', 'No se pudo conectar con el servidor.');
  } finally {
    event.target.value = '';
    setSidebarUploadBtn(true);
  }
}
 
/** Muestra el estado de la subida en el sidebar (solo en dashboard) */
function setUploadStatus(state, message) {
  const box  = document.getElementById('uploadStatus');
  const text = document.getElementById('uploadStatusText');
  if (!box || !text) return;
 
  if (state === 'hidden') { box.style.display = 'none'; return; }
 
  box.style.display = 'block';
  text.textContent  = message;
 
  // Colores según estado
  box.style.background = state === 'error'   ? 'rgba(231,76,60,0.08)'
                       : state === 'success' ? 'rgba(29,185,84,0.08)'
                       : 'rgba(0,0,0,0.04)';
  text.style.color     = state === 'error'   ? '#e74c3c'
                       : state === 'success' ? 'var(--green-dark)'
                       : 'var(--text-muted)';
}
 
/** Habilita/deshabilita el botón de subida en el sidebar */
function setSidebarUploadBtn(enabled) {
  const btn = document.getElementById('sidebarUploadBtn');
  if (!btn) return;
  btn.style.opacity        = enabled ? '1' : '0.5';
  btn.style.pointerEvents  = enabled ? 'auto' : 'none';
}
 
// ─── DASHBOARD ──────────────────────────────────────────────────────────────
 
async function loadDashboard() {
  const loading = document.getElementById('dashboardLoading');
  const content = document.getElementById('dashboardContent');
  if (!loading || !content) return;
 
  loading.classList.add('show');
  content.style.display = 'none';
 
  try {
    const [kpisRes, productosRes] = await Promise.all([
      fetch(`${API_BASE}/api/dashboard/kpis`,     { headers: authHeaders() }),
      fetch(`${API_BASE}/api/dashboard/productos`, { headers: authHeaders() }),
    ]);
 
    if (!kpisRes.ok || !productosRes.ok) {
      console.error('Error cargando datos del dashboard.');
      loading.classList.remove('show');
      return;
    }
 
    const kpis      = await kpisRes.json();
    const productos = await productosRes.json();
 
    document.getElementById('kpiVentasTotales').textContent =
      '£' + kpis.ventas_totales.toLocaleString('es-ES', { minimumFractionDigits: 2 });
    document.getElementById('kpiUnidades').textContent  = kpis.unidades_totales.toLocaleString('es-ES');
    document.getElementById('kpiProductos').textContent = kpis.productos_distintos.toLocaleString('es-ES');
 
    const dashUser = document.getElementById('dashboardUser');
    if (dashUser) dashUser.textContent = session.username;
 
    const selector = document.getElementById('globalProductSelector');
    selector.innerHTML = '';
    productos.forEach(p => {
      const opt       = document.createElement('option');
      opt.value       = p.id_producto;
      opt.textContent = `${p.id_producto} — ${p.nombre.substring(0, 40)}`;
      selector.appendChild(opt);
    });
 
    if (productos.length > 0) await updateAllCharts();
 
    loading.classList.remove('show');
    content.style.display = 'block';
 
  } catch (err) {
    console.error('Error en loadDashboard:', err);
    loading.classList.remove('show');
  }
}
 
async function updateAllCharts() {
  const idProducto = document.getElementById('globalProductSelector').value;
  if (!idProducto) return;
 
  const [ventasRes, predRes, invRes] = await Promise.all([
    fetch(`${API_BASE}/api/dashboard/ventas/${idProducto}`,       { headers: authHeaders() }),
    fetch(`${API_BASE}/api/dashboard/predicciones/${idProducto}`, { headers: authHeaders() }),
    fetch(`${API_BASE}/api/dashboard/inversion/${idProducto}`,    { headers: authHeaders() }),
  ]);
 
  const ventas       = await ventasRes.json();
  const predicciones = await predRes.json();
  const inversion    = await invRes.json();
 
  const kpiConf = document.getElementById('kpiConfianza');
  if (kpiConf) {
    kpiConf.textContent = (predicciones.confianza !== null && predicciones.confianza !== undefined)
      ? (predicciones.confianza * 100).toFixed(1) + '%'
      : 'Sin datos';
  }
 
  renderChart('chartVentasMes', {
    labels: ventas.fechas,
    datasets: [{ label: 'Unidades vendidas', data: ventas.unidades,
      borderColor: '#1db954', backgroundColor: 'rgba(29,185,84,0.1)',
      borderWidth: 2, fill: true, tension: 0.3, pointRadius: 2 }]
  });
 
  renderChart('chartPrediccion', {
    labels: predicciones.fechas,
    datasets: [{ label: 'Demanda estimada', data: predicciones.predichas,
      borderColor: '#2980b9', backgroundColor: 'rgba(41,128,185,0.1)',
      borderWidth: 2, fill: true, tension: 0.3, pointRadius: 2 }]
  });
 
  renderChart('chartInversion', {
    labels: inversion.fechas,
    datasets: [{ label: 'Coste estimado (£)', data: inversion.inversion,
      borderColor: '#e67e22', backgroundColor: 'rgba(230,126,34,0.1)',
      borderWidth: 2, fill: true, tension: 0.3, pointRadius: 2 }]
  });
 
  renderDoughnut('chartSeguridad', predicciones.confianza ? predicciones.confianza * 100 : 0);
}
 
function renderChart(canvasId, data) {
  if (charts[canvasId]) charts[canvasId].destroy();
  const ctx = document.getElementById(canvasId).getContext('2d');
  charts[canvasId] = new Chart(ctx, {
    type: 'line', data,
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { maxTicksLimit: 8, font: { size: 10 } }, grid: { display: false } },
        y: { ticks: { font: { size: 10 } }, grid: { color: 'rgba(0,0,0,0.05)' } }
      }
    }
  });
}
 
function renderDoughnut(canvasId, confianzaPct) {
  if (charts[canvasId]) charts[canvasId].destroy();
  const ctx = document.getElementById(canvasId).getContext('2d');
  charts[canvasId] = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Confianza', 'Margen de error'],
      datasets: [{ data: [confianzaPct, 100 - confianzaPct],
        backgroundColor: ['#1db954', '#dce4ed'], borderWidth: 0 }]
    },
    options: {
      responsive: true, cutout: '70%',
      plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } }
    }
  });
}
 
// ─── SIDEBAR TABS ────────────────────────────────────────────────────────────
 
function showDashboardTab(tab) {
  document.querySelectorAll('.sidebar-item').forEach(i => i.classList.remove('active'));
  if (event && event.currentTarget) event.currentTarget.classList.add('active');
}
 
// ─── ALERTAS ─────────────────────────────────────────────────────────────────
 
function showAlert(id, message) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = message;
  el.classList.add('show');
}
 
function hideAlert(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('show');
}