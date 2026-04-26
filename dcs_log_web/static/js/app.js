/**
 * app.js — main orchestrator.
 * Wires together: WebSocket (ws.js) ↔ store (filters.js) ↔ grid (grid.js) ↔ UI controls.
 */

import { init as wsInit, send, Bus } from './ws.js';
import { store, initLevels }         from './filters.js';
import { createGrid }                from './grid.js';

// ── DOM refs ──────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const emptyState = $('empty-state');

const gridContainer  = $('grid-container');
const statusDot      = $('status-dot');
const statusText     = $('status-text');
const pathInput      = $('path-input');
const browseBtn      = $('browse-btn');
const pathBtn        = $('path-btn');
const searchInput    = $('search-input');
const regexChk       = $('regex-chk');
const windowInput    = $('window-input');

const emitterSelect  = $('emitter-select');
const clearBtn       = $('clear-btn');
const reloadBtn      = $('reload-btn');
const autoScrollChk  = $('autoscroll-chk');
const themeBtn       = $('theme-btn');
const totalEl        = $('stat-total');
const countEls       = {
  ERROR: $('cnt-error'),
  WARN:  $('cnt-warn'),
  INFO:  $('cnt-info'),
  DEBUG: $('cnt-debug'),
  TRACE: $('cnt-trace'),
};

// ── Grid instance ─────────────────────────────────────────────────────────────
const grid = createGrid(gridContainer);

// ── State ─────────────────────────────────────────────────────────────────────
let autoScroll = true;
let theme      = 'dark';
let _renderScheduled = false;

// ── Render ────────────────────────────────────────────────────────────────────
function scheduleRender() {
  if (_renderScheduled) return;
  _renderScheduled = true;
  requestAnimationFrame(() => {
    _renderScheduled = false;
    const entries = store.filtered();
    grid.render(entries);
    if (autoScroll) grid.scrollToBottom();
    updateStats();
    updateEmitterOptions();
    // Toggle empty state
    if (emptyState) emptyState.classList.toggle('hidden', entries.length > 0);
  });
}

function updateStats() {
  const { total, counts } = store.getStats();
  if (totalEl) totalEl.textContent = total.toLocaleString();
  for (const [lvl, el] of Object.entries(countEls)) {
    if (el) el.textContent = (counts[lvl] || 0).toLocaleString();
  }
}

function updateEmitterOptions() {
  if (!emitterSelect) return;
  const prev = emitterSelect.value;
  const emis = store.getEmitters();
  // keep options in sync without full rebuild if possible
  const existing = new Set([...emitterSelect.options].map(o => o.value));
  for (const emi of emis) {
    if (!existing.has(emi)) {
      const opt = document.createElement('option');
      opt.value = opt.textContent = emi;
      emitterSelect.appendChild(opt);
    }
  }
  emitterSelect.value = prev;
}

// ── WebSocket events ──────────────────────────────────────────────────────────
Bus.on('status', s => {
  const connected = s === 'connected';
  statusDot.className  = 'dot ' + (connected ? 'dot-ok' : 'dot-err');
  if (connected) {
    statusText.textContent = 'Connected';
  } else {
    statusText.textContent = 'Reconnecting…';
  }
});

Bus.on('config', ({ data }) => {
  if (data.log_path)  pathInput.value = data.log_path;
  if (data.theme)     applyTheme(data.theme);
  if (data.auto_scroll !== undefined) {
    autoScroll = data.auto_scroll;
    autoScrollChk.checked = autoScroll;
  }
  if (data.window_lines !== undefined) {
    windowInput.value = data.window_lines;
  }
});

Bus.on('init', ({ entries }) => {
  store.reset();
  store.add(entries);
  scheduleRender();
  // Clear error status on success
  statusText.textContent = 'Connected';
  statusDot.className = 'dot dot-ok';
});

Bus.on('append', ({ entries }) => {
  store.add(entries);
  scheduleRender();
  // Ensure status is clear
  statusText.textContent = 'Connected';
  statusDot.className = 'dot dot-ok';
});

Bus.on('clear', () => {
  store.reset();
  scheduleRender();
});

Bus.on('error', ({ message }) => {
  statusText.textContent = '⚠ ' + message;
  statusDot.className = 'dot dot-err';
});

// ── Controls ──────────────────────────────────────────────────────────────────
browseBtn.addEventListener('click', async () => {
  try {
    const resp = await fetch('/api/browse');
    const { path } = await resp.json();
    if (path) {
      pathInput.value = path;
      send({ action: 'set_path', path: path });
    }
  } catch (err) {
    console.error('Browse failed', err);
  }
});

regexChk.addEventListener('change', () => {
  store.setUseRegex(regexChk.checked);
  scheduleRender();
});

pathBtn.addEventListener('click', () => {
  const p = pathInput.value.trim();
  if (p) send({ action: 'set_path', path: p });
});

pathInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') pathBtn.click();
});

searchInput.addEventListener('input', () => {
  store.setSearch(searchInput.value);
  scheduleRender();
});

// Level filter — multi-select checkboxes via custom dropdown
document.querySelectorAll('.level-chk').forEach(chk => {
  chk.addEventListener('change', () => {
    const checked = [...document.querySelectorAll('.level-chk:checked')].map(c => c.value);
    store.setLevels(checked);
    scheduleRender();
  });
});

emitterSelect.addEventListener('change', () => {
  store.setEmitter(emitterSelect.value);
  scheduleRender();
});

clearBtn.addEventListener('click', () => send({ action: 'clear' }));

reloadBtn.addEventListener('click', () => send({ action: 'reload' }));

windowInput.addEventListener('change', () => {
  const val = parseInt(windowInput.value);
  if (!isNaN(val) && val > 0) {
    send({ action: 'set_config', window_lines: val });
  }
});

autoScrollChk.addEventListener('change', () => {
  autoScroll = autoScrollChk.checked;
  send({ action: 'set_config', auto_scroll: autoScroll });
  if (autoScroll) grid.scrollToBottom();
});

// Pause auto-scroll if user scrolls up
gridContainer.addEventListener('scroll', () => {
  if (!grid.isNearBottom() && autoScroll) {
    autoScroll = false;
    autoScrollChk.checked = false;
  }
}, { passive: true });

// ── Theme ─────────────────────────────────────────────────────────────────────
function applyTheme(t) {
  theme = t;
  document.documentElement.setAttribute('data-theme', t);
  themeBtn.textContent = t === 'dark' ? '☀ Light' : '🌙 Dark';
}

themeBtn.addEventListener('click', () => {
  const next = theme === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  send({ action: 'set_config', theme: next });
});

// ── Boot ──────────────────────────────────────────────────────────────────────
applyTheme(theme);
await initLevels();
wsInit();
