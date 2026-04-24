/**
 * grid.js — lightweight virtual-scroll log grid with variable row heights.
 *
 * Only the rows visible in the scroll viewport + a small overscan buffer
 * are in the DOM at any time, keeping rendering fast even at 10 000+ entries.
 *
 * Variable height support:
 *   Expanded rows calculate an estimated height based on continuation line count.
 *   Binary search is used to find visible rows in O(log N).
 */

import { dcsHighlighter } from './highlighter_dcs.js';

const ROW_HEIGHT   = 22;    // px — must match CSS .row height
const OVERSCAN     = 30;    // extra rows above/below viewport

const LEVEL_CLASS = {
  ERROR: 'lvl-error',
  WARN:  'lvl-warn',
  INFO:  'lvl-info',
  DEBUG: 'lvl-debug',
  TRACE: 'lvl-trace',
};
 
const ICON_COPY = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>`;
const ICON_CHECK = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function buildRowHtml(entry, top, isExpanded) {
  const lc  = LEVEL_CLASS[entry.level] || 'lvl-info';
  const hasCont = entry.continuation && entry.continuation.length > 0;

  // Continuation lines are embedded and shown if expanded
  const contHtml = (hasCont && isExpanded)
    ? `<div class="continuation">${entry.continuation.map(l => `<div>${dcsHighlighter.highlight(l)}</div>`).join('')}</div>`
    : '';

  if (entry.emitter === undefined) console.warn('[grid] emitter is undefined for entry', entry);

  return `<div class="row ${lc}${hasCont ? ' has-cont' : ''}${isExpanded ? ' expanded' : ''}" style="top:${top}px" data-id="${entry.id}" tabindex="-1">
  <span class="col-id">${entry.id}</span>
  <span class="col-ts">${escHtml(entry.timestamp)}</span>
  <span class="col-lvl"><span class="badge ${lc}">${escHtml(entry.level)}</span></span>
  <span class="col-emi">${escHtml(entry.emitter || '')}</span>
  <span class="col-thr">(${escHtml(entry.thread)})</span>
  <span class="col-msg">${dcsHighlighter.highlight(entry.message)}${hasCont ? `<button class="exp-btn" aria-label="expand">${isExpanded ? '▾' : '▸'}</button>` : ''}</span>
  <div class="row-actions">
    <button class="copy-btn" title="Copy entry" aria-label="copy entry" data-id="${entry.id}">
      ${ICON_COPY}
    </button>
  </div>
  ${contHtml}
</div>`;
}

export function createGrid(container) {
  let _entries     = [];
  let _expandedIds = new Set();
  let _offsets     = []; // Pre-calculated top positions
  let _startIdx    = -1;
  let _endIdx      = -1;

  // Spacer keeps the scrollbar sized correctly for the full entry count
  const spacer = document.createElement('div');
  spacer.className = 'grid-spacer';
  container.appendChild(spacer);

  const rowsEl = document.createElement('div');
  rowsEl.className = 'grid-rows';
  container.appendChild(rowsEl);

  /** Calculate 'top' for every row based on expansion state */
  function _updateOffsets() {
    _offsets = new Array(_entries.length);
    let top = 0;
    for (let i = 0; i < _entries.length; i++) {
      _offsets[i] = top;
      const entry = _entries[i];
      if (_expandedIds.has(entry.id)) {
        // Estimate: 22px for main line + 16px per continuation line + 8px padding
        top += 22 + (entry.continuation.length * 16) + 8;
      } else {
        top += ROW_HEIGHT;
      }
    }
    spacer.style.height = `${top}px`;
  }

  // ── Delegation: expand/collapse or copy ──────────────────────────────────
  rowsEl.addEventListener('click', e => {
    // 1. Copy button
    const copyBtn = e.target.closest('.copy-btn');
    if (copyBtn) {
      e.stopPropagation();
      const id = parseInt(copyBtn.dataset.id);
      const entry = _entries.find(ent => ent.id === id);
      if (entry && entry.raw) {
        navigator.clipboard.writeText(entry.raw).then(() => {
          copyBtn.innerHTML = ICON_CHECK;
          copyBtn.classList.add('success');
          setTimeout(() => {
            copyBtn.innerHTML = ICON_COPY;
            copyBtn.classList.remove('success');
          }, 1500);
        });
      }
      return;
    }

    // 2. Expand button
    const btn = e.target.closest('.exp-btn');
    if (!btn) return;
    const row = btn.closest('.row');
    if (!row) return;
    const id = parseInt(row.dataset.id);

    if (_expandedIds.has(id)) {
      _expandedIds.delete(id);
    } else {
      _expandedIds.add(id);
    }

    _updateOffsets();
    _startIdx = -1; // force repaint
    _paint();
  });

  // ── Virtual scroll ─────────────────────────────────────────────────────────
  function _visibleRange() {
    if (_entries.length === 0) return { start: 0, end: 0 };

    const scrollTop = container.scrollTop;
    const height    = container.clientHeight;

    // Binary search to find start index (first row where top + height > scrollTop)
    let start = 0;
    let low = 0, high = _entries.length - 1;
    while (low <= high) {
      let mid = (low + high) >> 1;
      if (_offsets[mid] <= scrollTop) {
        start = mid;
        low = mid + 1;
      } else {
        high = mid - 1;
      }
    }
    start = Math.max(0, start - OVERSCAN);

    // Binary search to find end index (first row where top > scrollTop + height)
    let end = start;
    low = start, high = _entries.length - 1;
    const scrollBottom = scrollTop + height;
    while (low <= high) {
      let mid = (low + high) >> 1;
      if (_offsets[mid] <= scrollBottom) {
        end = mid;
        low = mid + 1;
      } else {
        high = mid - 1;
      }
    }
    end = Math.min(_entries.length, end + OVERSCAN + 1);

    return { start, end };
  }

  function _paint() {
    const { start, end } = _visibleRange();
    if (start === _startIdx && end === _endIdx) return;
    _startIdx = start;
    _endIdx   = end;

    const html = [];
    for (let i = start; i < end; i++) {
      const entry = _entries[i];
      html.push(buildRowHtml(entry, _offsets[i], _expandedIds.has(entry.id)));
    }
    rowsEl.innerHTML = html.join('');
  }

  container.addEventListener('scroll', _paint, { passive: true });
  window.addEventListener('resize', _paint, { passive: true });

  // ── Public API ─────────────────────────────────────────────────────────────
  return {
    render(entries) {
      _entries = entries;
      _updateOffsets();
      _startIdx = -1; // force repaint
      _endIdx   = -1;
      _paint();
    },

    scrollToBottom() {
      container.scrollTop = container.scrollHeight;
    },

    isNearBottom() {
      const { scrollTop, scrollHeight, clientHeight } = container;
      // Use a larger buffer (100px) since expanded rows can be tall
      return scrollHeight - scrollTop - clientHeight < 100;
    },
  };
}
