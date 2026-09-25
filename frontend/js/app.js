/**
 * SentinelCam Monitoring Dashboard Logic
 */

// Application State
const state = {
  cameras: [],
  summary: null,
  activeFilter: 'ALL',
  searchQuery: '',
  refreshInterval: 30, // seconds
  countdownRemaining: 30,
  timerId: null,
  isLoading: false,
};

// DOM Elements Cache
const elements = {
  // Stats
  statTotal: document.getElementById('statTotal'),
  statOk: document.getElementById('statOk'),
  statError: document.getElementById('statError'),
  statHealthPct: document.getElementById('statHealthPct'),
  healthBarFill: document.getElementById('healthBarFill'),
  lastScanTime: document.getElementById('lastScanTime'),

  // Filter Counts
  countFilterAll: document.getElementById('countFilterAll'),
  countFilterError: document.getElementById('countFilterError'),
  countFilterOk: document.getElementById('countFilterOk'),
  countFilterPaused: document.getElementById('countFilterPaused'),

  // Filters & Search
  filterButtons: document.querySelectorAll('.filter-btn'),
  searchInput: document.getElementById('searchInput'),
  btnSearchClear: document.getElementById('btnSearchClear'),

  // Refresh
  countdownText: document.getElementById('countdownText'),
  btnManualRefresh: document.getElementById('btnManualRefresh'),

  // Grid Containers
  camerasContainer: document.getElementById('camerasContainer'),
  loadingState: document.getElementById('loadingState'),
  emptyState: document.getElementById('emptyState'),
  emptyStateMessage: document.getElementById('emptyStateMessage'),

  // Evidence Dialog Modal
  screenshotDialog: document.getElementById('screenshotDialog'),
  dialogCameraTitle: document.getElementById('dialogCameraTitle'),
  dialogCameraIp: document.getElementById('dialogCameraIp'),
  dialogStatusBadge: document.getElementById('dialogStatusBadge'),
  dialogImage: document.getElementById('dialogImage'),
  dialogImgSpinner: document.getElementById('dialogImgSpinner'),
  dialogDetails: document.getElementById('dialogDetails'),
  dialogTimestamp: document.getElementById('dialogTimestamp'),
};

// ==========================================
// Initialization & Event Listeners
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  initDialogFallbacks();
  fetchDashboardData();
  startCountdownTimer();
});

function initEventListeners() {
  // Manual refresh button
  elements.btnManualRefresh.addEventListener('click', () => {
    fetchDashboardData(true);
    resetCountdown();
  });

  // Filter buttons
  elements.filterButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      elements.filterButtons.forEach((b) => {
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
      });
      btn.classList.add('active');
      btn.setAttribute('aria-selected', 'true');
      state.activeFilter = btn.dataset.filter;
      renderCameras();
    });
  });

  // Search input
  elements.searchInput.addEventListener('input', (e) => {
    state.searchQuery = e.target.value.trim().toLowerCase();
    elements.btnSearchClear.style.display = state.searchQuery ? 'block' : 'none';
    renderCameras();
  });

  elements.btnSearchClear.addEventListener('click', () => {
    elements.searchInput.value = '';
    state.searchQuery = '';
    elements.btnSearchClear.style.display = 'none';
    elements.searchInput.focus();
    renderCameras();
  });
}

/**
 * Fallback for <dialog closedby="any"> in browsers without native closedby support
 */
function initDialogFallbacks() {
  const dialog = elements.screenshotDialog;
  if (!dialog) return;

  if (!('closedBy' in HTMLDialogElement.prototype)) {
    dialog.addEventListener('click', (event) => {
      if (event.target !== dialog) return;
      const rect = dialog.getBoundingClientRect();
      const isDialogContent = (
        rect.top <= event.clientY &&
        event.clientY <= rect.top + rect.height &&
        rect.left <= event.clientX &&
        event.clientX <= rect.left + rect.width
      );
      if (!isDialogContent) {
        dialog.close();
      }
    });
  }
}

// ==========================================
// Data Fetching
// ==========================================

async function fetchDashboardData(isManual = false) {
  if (state.isLoading) return;
  state.isLoading = true;

  if (isManual) {
    elements.btnManualRefresh.classList.add('is-spinning');
  }

  try {
    const [summaryRes, camerasRes] = await Promise.all([
      fetch('/api/summary'),
      fetch('/api/cameras'),
    ]);

    if (!summaryRes.ok || !camerasRes.ok) {
      throw new Error('Error al consultar datos desde la API');
    }

    state.summary = await summaryRes.json();
    state.cameras = await camerasRes.json();

    updateMetricsView();
    renderCameras();
  } catch (err) {
    console.error('Error fetching dashboard data:', err);
    showToast('Error de conexión con el servidor. Reintentando...', 'error');
  } finally {
    state.isLoading = false;
    if (elements.loadingState) {
      elements.loadingState.style.display = 'none';
    }
    elements.btnManualRefresh.classList.remove('is-spinning');
  }
}

// ==========================================
// Countdown & Timer
// ==========================================

function startCountdownTimer() {
  if (state.timerId) clearInterval(state.timerId);

  state.countdownRemaining = state.refreshInterval;
  updateCountdownDisplay();

  state.timerId = setInterval(() => {
    state.countdownRemaining -= 1;
    updateCountdownDisplay();

    if (state.countdownRemaining <= 0) {
      state.countdownRemaining = state.refreshInterval;
      fetchDashboardData(false);
    }
  }, 1000);
}

function resetCountdown() {
  state.countdownRemaining = state.refreshInterval;
  updateCountdownDisplay();
}

function updateCountdownDisplay() {
  if (elements.countdownText) {
    elements.countdownText.textContent = `${state.countdownRemaining}s`;
  }
}

// ==========================================
// UI Rendering: Metrics & Counters
// ==========================================

function updateMetricsView() {
  if (!state.summary) return;

  const {
    total_cameras,
    active_cameras,
    paused_cameras,
    ok_cameras,
    error_cameras,
    health_percentage,
    last_scan_at,
  } = state.summary;

  // Global Metric Cards
  elements.statTotal.textContent = total_cameras;
  elements.statOk.textContent = ok_cameras;
  elements.statError.textContent = error_cameras;
  elements.statHealthPct.textContent = `${health_percentage}%`;
  elements.healthBarFill.style.width = `${Math.min(100, Math.max(0, health_percentage))}%`;

  // Change health bar color based on percentage
  if (health_percentage >= 80) {
    elements.healthBarFill.style.background = 'linear-gradient(90deg, #10b981, #06b6d4)';
  } else if (health_percentage >= 50) {
    elements.healthBarFill.style.background = 'linear-gradient(90deg, #f59e0b, #eab308)';
  } else {
    elements.healthBarFill.style.background = 'linear-gradient(90deg, #f43f5e, #fb7185)';
  }

  // Filter Tab Badges
  elements.countFilterAll.textContent = total_cameras;
  elements.countFilterError.textContent = error_cameras;
  elements.countFilterOk.textContent = ok_cameras;
  elements.countFilterPaused.textContent = paused_cameras;

  // Last check timestamp
  if (last_scan_at) {
    elements.lastScanTime.textContent = formatDateTime(last_scan_at);
  } else {
    elements.lastScanTime.textContent = 'Sin chequeos recientes';
  }
}

// ==========================================
// UI Rendering: Camera Cards Grid
// ==========================================

function renderCameras() {
  const container = elements.camerasContainer;
  const filtered = filterCameras(state.cameras);

  // Clear existing cards
  container.innerHTML = '';

  if (filtered.length === 0) {
    elements.emptyState.style.display = 'flex';
    if (state.searchQuery) {
      elements.emptyStateMessage.textContent = `No se encontraron cámaras que coincidan con "${state.searchQuery}".`;
    } else {
      elements.emptyStateMessage.textContent = 'No hay cámaras en esta categoría.';
    }
    return;
  }

  elements.emptyState.style.display = 'none';

  // Render cards
  const fragment = document.createDocumentFragment();
  filtered.forEach((camera) => {
    const card = createCameraCard(camera);
    fragment.appendChild(card);
  });

  container.appendChild(fragment);
}

function filterCameras(cameras) {
  return cameras.filter((cam) => {
    // 1. Status Filter
    if (state.activeFilter === 'OK') {
      if (cam.status !== 'OK' || !cam.enabled) return false;
    } else if (state.activeFilter === 'PROBLEMS') {
      if (!cam.enabled) return false;
      const isProblem = ['OFFLINE', 'AUTH_FAILED', 'NO_RECORDINGS', 'ERROR'].includes(cam.status) || cam.status === null;
      if (!isProblem) return false;
    } else if (state.activeFilter === 'PAUSED') {
      if (cam.enabled) return false;
    }

    // 2. Search Text
    if (state.searchQuery) {
      const q = state.searchQuery;
      const matchName = cam.name.toLowerCase().includes(q);
      const matchIp = cam.ip_or_url.toLowerCase().includes(q);
      const matchDetails = cam.details && cam.details.toLowerCase().includes(q);
      const matchStatus = cam.status && cam.status.toLowerCase().includes(q);
      if (!matchName && !matchIp && !matchDetails && !matchStatus) return false;
    }

    return true;
  });
}

function createCameraCard(camera) {
  const card = document.createElement('article');
  card.className = `camera-card ${getCardStatusClass(camera)}`;
  card.id = `camera-${camera.id}`;

  const statusConfig = getStatusConfig(camera);

  card.innerHTML = `
    <div class="card-header">
      <div class="camera-meta">
        <div class="cam-icon-box" aria-hidden="true">
          ${getCameraSvgIcon(camera)}
        </div>
        <div class="cam-title-group">
          <h2 class="cam-name" title="${escapeHtml(camera.name)}">${escapeHtml(camera.name)}</h2>
          <div class="cam-sub">
            <span>${escapeHtml(camera.ip_or_url)}</span>
            <span class="tag-interface">${camera.interface === 1 ? 'Moderna' : 'Clásica'}</span>
          </div>
        </div>
      </div>
      <div class="status-badge ${statusConfig.badgeClass}">
        <span class="badge-pulse-dot"></span>
        <span>${statusConfig.label}</span>
      </div>
    </div>

    <div class="card-stats-grid">
      <div class="stat-item">
        <span class="stat-item-label">Grabaciones 24h</span>
        <span class="stat-item-val ${camera.recordings_count > 0 ? 'val-ok' : 'val-alert'}">
          ${camera.recordings_count} grab.
        </span>
      </div>
      <div class="stat-item">
        <span class="stat-item-label">Última Grabación</span>
        <span class="stat-item-val" title="${camera.latest_recording_time || 'N/A'}">
          ${formatLatestRecord(camera.latest_recording_time)}
        </span>
      </div>
    </div>

    ${camera.details ? `
      <div class="diagnostic-banner" title="${escapeHtml(camera.details)}">
        ${escapeHtml(camera.details)}
      </div>
    ` : ''}

    <div class="card-footer">
      <span class="last-checked-label">
        Verif: ${camera.last_checked_at ? formatTimeAgo(camera.last_checked_at) : 'Nunca'}
      </span>
      ${camera.has_screenshot && camera.screenshot_url ? `
        <button class="btn-evidence" data-cam-id="${camera.id}" aria-label="Ver captura de evidencia">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
            <circle cx="12" cy="13" r="4"/>
          </svg>
          <span>Evidencia</span>
        </button>
      ` : ''}
    </div>
  `;

  // Attach evidence modal trigger
  const btnEvidence = card.querySelector('.btn-evidence');
  if (btnEvidence) {
    btnEvidence.addEventListener('click', () => openEvidenceDialog(camera));
  }

  return card;
}

// ==========================================
// Evidence Modal Viewer
// ==========================================

function openEvidenceDialog(camera) {
  const dialog = elements.screenshotDialog;
  if (!dialog || !camera.screenshot_url) return;

  const statusConfig = getStatusConfig(camera);

  elements.dialogCameraTitle.textContent = `Cámara #${camera.id} • ${camera.name}`;
  elements.dialogCameraIp.textContent = camera.ip_or_url;
  
  elements.dialogStatusBadge.textContent = statusConfig.label;
  elements.dialogStatusBadge.className = `dialog-badge ${statusConfig.badgeClass}`;

  elements.dialogDetails.textContent = camera.details || 'Sin diagnóstico adicional registrado.';
  elements.dialogTimestamp.textContent = camera.last_checked_at ? formatDateTime(camera.last_checked_at) : '-';

  // Image loading logic
  elements.dialogImgSpinner.style.display = 'block';
  elements.dialogImage.style.opacity = '0';
  elements.dialogImage.src = camera.screenshot_url;

  elements.dialogImage.onload = () => {
    elements.dialogImgSpinner.style.display = 'none';
    elements.dialogImage.style.opacity = '1';
  };

  elements.dialogImage.onerror = () => {
    elements.dialogImgSpinner.style.display = 'none';
    elements.dialogDetails.textContent = 'No se pudo cargar la imagen de evidencia desde el servidor.';
  };

  dialog.showModal();
}

// ==========================================
// Helper Utilities & Formatting
// ==========================================

function getCardStatusClass(camera) {
  if (!camera.enabled) return 'status-paused';
  if (camera.status === 'OK') return 'status-ok';
  if (camera.status === 'NO_RECORDINGS') return 'status-warning';
  if (['OFFLINE', 'AUTH_FAILED', 'ERROR'].includes(camera.status)) return 'status-error';
  return 'status-warning';
}

function getStatusConfig(camera) {
  if (!camera.enabled) {
    return { label: 'Pausada', badgeClass: 'badge-paused' };
  }
  switch (camera.status) {
    case 'OK':
      return { label: 'Operativa (OK)', badgeClass: 'badge-ok' };
    case 'NO_RECORDINGS':
      return { label: 'Sin Grabaciones', badgeClass: 'badge-warning' };
    case 'OFFLINE':
      return { label: 'Desconectada', badgeClass: 'badge-error' };
    case 'AUTH_FAILED':
      return { label: 'Fallo Clave', badgeClass: 'badge-auth' };
    case 'ERROR':
      return { label: 'Error Verif.', badgeClass: 'badge-error' };
    default:
      return { label: 'Sin Probar', badgeClass: 'badge-warning' };
  }
}

function getCameraSvgIcon(camera) {
  // Return high-tech surveillance dome or bullet camera SVG icon
  if (camera.vendor_type === 'vivotek') {
    return `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/>
        <circle cx="12" cy="13" r="3.5"/>
        <line x1="12" y1="9.5" x2="12" y2="10.5"/>
      </svg>
    `;
  }
  return `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M15 10l5-5v14l-5-5"/>
      <rect x="2" y="6" width="13" height="12" rx="2" ry="2"/>
    </svg>
  `;
}

function formatLatestRecord(recordStr) {
  if (!recordStr) return 'Ninguna';
  // If it's a date string like "2026-09-25 09:30:00"
  try {
    const d = new Date(recordStr.replace(' ', 'T'));
    if (!isNaN(d.getTime())) {
      const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      return `${time} (${d.toLocaleDateString([], { month: 'numeric', day: 'numeric' })})`;
    }
  } catch (e) {
    // fallback
  }
  return recordStr.length > 18 ? recordStr.substring(0, 18) + '...' : recordStr;
}

function formatDateTime(isoString) {
  if (!isoString) return '-';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return d.toLocaleString([], {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  } catch (e) {
    return isoString;
  }
}

function formatTimeAgo(isoString) {
  if (!isoString) return 'Nunca';
  try {
    const d = new Date(isoString);
    const now = new Date();
    const diffMs = now - d;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);

    if (diffMins < 1) return 'Hace instantes';
    if (diffMins < 60) return `Hace ${diffMins}m`;
    if (diffHours < 24) return `Hace ${diffHours}h`;
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  } catch (e) {
    return isoString;
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function showToast(message, type = 'info') {
  console.log(`[${type.toUpperCase()}] ${message}`);
}
