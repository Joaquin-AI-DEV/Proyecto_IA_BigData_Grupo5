const API_BASE = 'http://localhost:8000';

// Estado de sesión (solo en memoria, sin localStorage)
const session = {
  token: null,
  username: null,
  isLoggedIn: function () { return !!this.token; }
};

const charts = {};

// NAVEGACIÓN

function navigateTo(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('[data-page]').forEach(a => a.classList.remove('active'));

  const target = document.getElementById('page-' + page);
  if (target) target.classList.add('active');

  const link = document.querySelector(`[data-page="${page}"]`);
  if (link) link.classList.add('active');

  if (page === 'dashboard') {
    if (!session.isLoggedIn()) { openLoginModal(); return; }
    loadDashboard();
  }

  return false;
}

// AUTENTICACIÓN

function openLoginModal() {
  document.getElementById('loginModal').classList.add('show');
  document.getElementById('loginUsername').focus();
  hideAlert('loginError');
}

function closeLoginModal() {
  document.getElementById('loginModal').classList.remove('show');
  document.getElementById('loginUsername').value = '';
  document.getElementById('loginPassword').value = '';
}

async function submitLogin() {
  const username = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value;
  const btn = document.getElementById('loginBtn');

  if (!username || !password) {
    showAlert('loginError', 'Rellena todos los campos.');
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Entrando...';

  try {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();

    if (!res.ok) {
      showAlert('loginError', data.detail || 'Usuario o contraseña incorrectos.');
      return;
    }

    // Guardar sesión en memoria
    session.token = data.token;
    session.username = data.username || username;

    closeLoginModal();
    updateNavbar();
    navigateTo('dashboard');

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

  // Limpiar sesión de memoria
  session.token = null;
  session.username = null;

  // Destruir gráficos
  Object.values(charts).forEach(c => { if (c) c.destroy(); });
  Object.keys(charts).forEach(k => delete charts[k]);

  updateNavbar();
  navigateTo('inicio');

  document.getElementById('uploadArea').style.display = 'none';
}

function updateNavbar() {
  const guest = document.getElementById('navGuest');
  const user = document.getElementById('navUser');
  const dashItem = document.getElementById('navDashboardItem');
  const navUsername = document.getElementById('navUsername');
  const navAvatar = document.getElementById('navAvatar');
  const uploadArea = document.getElementById('uploadArea');

  if (session.isLoggedIn()) {
    guest.style.display = 'none';
    user.style.display = 'flex';
    dashItem.style.display = 'block';
    navUsername.textContent = session.username;
    navAvatar.textContent = session.username.charAt(0).toUpperCase();
    uploadArea.style.display = 'block';
  } else {
    guest.style.display = 'block';
    user.style.display = 'none';
    dashItem.style.display = 'none';
    uploadArea.style.display = 'none';
  }
}

function authHeaders() {
  return {
    'Authorization': `Bearer ${session.token}`,
    'Content-Type': 'application/json'
  };
}

// CARGA DE ARCHIVOS

function handleUploadClick() {
  if (!session.isLoggedIn()) {
    openLoginModal();
    return;
  }
  triggerFileInput();
}

function triggerFileInput() {
  document.getElementById('fileInput').click();
}

async function handleFileChange(event) {
  const file = event.target.files[0];
  if (!file) return;

  hideAlert('uploadError');
  hideAlert('uploadSuccess');

  const ext = file.name.split('.').pop().toLowerCase();
  if (!['csv', 'xlsx'].includes(ext)) {
    showAlert('uploadError', 'Formato no válido. Solo se permiten archivos .csv y .xlsx');
    event.target.value = '';
    return;
  }

  if (file.size > 50 * 1024 * 1024) {
    showAlert('uploadError', 'El archivo es demasiado grande. Máximo 50MB.');
    event.target.value = '';
    return;
  }

  showAlert('uploadSuccess', `Archivo "${file.name}" seleccionado. Procesando...`);

  const formData = new FormData();
  formData.append('file', file);
  formData.append('username', session.username);

  try {
    const res = await fetch(`${API_BASE}/api/upload`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${session.token}` },
      body: formData
    });

    const data = await res.json();

    if (!res.ok) {
      showAlert('uploadError', data.detail || 'Error al procesar el archivo.');
      return;
    }

    showAlert('uploadSuccess', 'Archivo procesado correctamente. Redirigiendo al dashboard...');

    setTimeout(() => {
      hideAlert('uploadSuccess');
      navigateTo('dashboard');
    }, 1500);

  } catch (err) {
    showAlert('uploadError', 'No se pudo conectar con el servidor.');
  } finally {
    event.target.value = '';
  }
}

// DASHBOARD

async function loadDashboard() {
  const loading = document.getElementById('dashboardLoading');
  const content = document.getElementById('dashboardContent');

  loading.classList.add('show');
  content.style.display = 'none';

  try {
    // Cargar KPIs y lista de productos en paralelo
    const [kpisRes, productosRes] = await Promise.all([
      fetch(`${API_BASE}/api/dashboard/kpis`, { headers: authHeaders() }),
      fetch(`${API_BASE}/api/dashboard/productos`, { headers: authHeaders() }),
    ]);

    if (!kpisRes.ok || !productosRes.ok) {
      console.error('Error cargando datos del dashboard.');
      return;
    }

    const kpis = await kpisRes.json();
    const productos = await productosRes.json();

    // Actualizar KPIs
    document.getElementById('kpiVentasTotales').textContent =
      '£' + kpis.ventas_totales.toLocaleString('es-ES', { minimumFractionDigits: 2 });
    document.getElementById('kpiUnidades').textContent =
      kpis.unidades_totales.toLocaleString('es-ES');
    document.getElementById('kpiProductos').textContent =
      kpis.productos_distintos.toLocaleString('es-ES');

    // Mostrar usuario en cabecera del dashboard
    document.getElementById('dashboardUser').textContent = session.username;

    // Rellenar selector de productos
    const selector = document.getElementById('globalProductSelector');
    selector.innerHTML = '';
    productos.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.id_producto;
      opt.textContent = `${p.id_producto} — ${p.nombre.substring(0, 40)}`;
      selector.appendChild(opt);
    });

    // Cargar gráficos para el primer producto de la lista
    if (productos.length > 0) {
      await updateAllCharts();
    }

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

  // Cargar ventas, predicciones e inversión en paralelo
  const [ventasRes, predRes, invRes] = await Promise.all([
    fetch(`${API_BASE}/api/dashboard/ventas/${idProducto}`, { headers: authHeaders() }),
    fetch(`${API_BASE}/api/dashboard/predicciones/${idProducto}`, { headers: authHeaders() }),
    fetch(`${API_BASE}/api/dashboard/inversion/${idProducto}`, { headers: authHeaders() }),
  ]);

  const ventas      = await ventasRes.json();
  const predicciones = await predRes.json();
  const inversion   = await invRes.json();

  // Actualizar KPI de confianza del modelo
  const kpiConf = document.getElementById('kpiConfianza');
  if (predicciones.confianza !== null && predicciones.confianza !== undefined) {
    kpiConf.textContent = (predicciones.confianza * 100).toFixed(1) + '%';
  } else {
    kpiConf.textContent = 'Sin datos';
  }

  renderChart('chartVentasMes', {
    labels: ventas.fechas,
    datasets: [{
      label: 'Unidades vendidas',
      data: ventas.unidades,
      borderColor: '#1db954',
      backgroundColor: 'rgba(29,185,84,0.1)',
      borderWidth: 2,
      fill: true,
      tension: 0.3,
      pointRadius: 2,
    }]
  });

  renderChart('chartPrediccion', {
    labels: predicciones.fechas,
    datasets: [{
      label: 'Demanda estimada',
      data: predicciones.predichas,
      borderColor: '#2980b9',
      backgroundColor: 'rgba(41,128,185,0.1)',
      borderWidth: 2,
      fill: true,
      tension: 0.3,
      pointRadius: 2,
    }]
  });

  renderChart('chartInversion', {
    labels: inversion.fechas,
    datasets: [{
      label: 'Coste estimado (£)',
      data: inversion.inversion,
      borderColor: '#e67e22',
      backgroundColor: 'rgba(230,126,34,0.1)',
      borderWidth: 2,
      fill: true,
      tension: 0.3,
      pointRadius: 2,
    }]
  });

  // Gráfico de seguridad del modelo (dona con métricas de confianza)
  const conf = predicciones.confianza ? predicciones.confianza * 100 : 0;
  renderDoughnut('chartSeguridad', conf);
}

function renderChart(canvasId, data) {
  // Destruir gráfico anterior si existe
  if (charts[canvasId]) {
    charts[canvasId].destroy();
  }

  const ctx = document.getElementById(canvasId).getContext('2d');
  charts[canvasId] = new Chart(ctx, {
    type: 'line',
    data: data,
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: {
          ticks: { maxTicksLimit: 8, font: { size: 10 } },
          grid: { display: false },
        },
        y: {
          ticks: { font: { size: 10 } },
          grid: { color: 'rgba(0,0,0,0.05)' },
        }
      }
    }
  });
}

function renderDoughnut(canvasId, confianzaPct) {
  if (charts[canvasId]) {
    charts[canvasId].destroy();
  }

  const resto = 100 - confianzaPct;
  const ctx = document.getElementById(canvasId).getContext('2d');
  charts[canvasId] = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Confianza', 'Margen de error'],
      datasets: [{
        data: [confianzaPct, resto],
        backgroundColor: ['#1db954', '#dce4ed'],
        borderWidth: 0,
      }]
    },
    options: {
      responsive: true,
      cutout: '70%',
      plugins: {
        legend: { position: 'bottom', labels: { font: { size: 11 } } },
      }
    }
  });
}

// SIDEBAR TABS

function showDashboardTab(tab) {
  document.querySelectorAll('.sidebar-item').forEach(i => i.classList.remove('active'));
  event.currentTarget.classList.add('active');
}

// ALERTAS

function showAlert(id, message) {
  const el = document.getElementById(id);
  el.textContent = message;
  el.classList.add('show');
}

function hideAlert(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('show');
}

updateNavbar();
