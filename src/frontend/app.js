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

  // LOGIN TEMPORAL - quitar cuando el backend esté listo
  if (username === 'admin' && password === 'admin123') {
    session.token = 'mock-token';
    session.username = username;
    closeLoginModal();
    updateNavbar();
    navigateTo('dashboard');
  return;
  }
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
      showAlert('loginError', data.detail || 'Usuario o contrasena incorrectos.');
      return;
    }

    // Guardar sesion en memoria
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

  // Limpiar sesion de memoria
  session.token = null;
  session.username = null;

  // Destruir graficos
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

//  CARGA DE ARCHIVOS

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

  // Validar extensión
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['csv', 'xlsx'].includes(ext)) {
    showAlert('uploadError', 'Formato no válido. Solo se permiten archivos .csv y .xlsx');
    event.target.value = '';
    return;
  }

  // Validar tamaño (max 50MB)
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

//  SIDEBAR TABS

function showDashboardTab(tab) {
  document.querySelectorAll('.sidebar-item').forEach(i => i.classList.remove('active'));
  event.currentTarget.classList.add('active');
}

//  ALERTAS

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
