/**
 * grid.js — lightweight virtual-scroll log grid.
 *
 * Only the rows visible in the scroll viewport + a small overscan buffer
 * are in the DOM at any time, keeping rendering fast even at 10 000+ entries.
 *
 * Usage:
 *   const grid = createGrid(containerEl);
 *   grid.render(entries);          // full re-render with new data
 *   grid.scrollToBottom();
 */

const ROW_HEIGHT   = 22;    // px — must match CSS .row height
const OVERSCAN     = 30;    // extra rows above/below viewport

const LEVEL_CLASS = {
  ERROR: 'lvl-error',
  WARN:  'lvl-warn',
  INFO:  'lvl-info',
  DEBUG: 'lvl-debug',
  TRACE: 'lvl-trace',
};

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function buildRowHtml(entry, idx) {
  const lc  = LEVEL_CLASS[entry.level] || 'lvl-info';
  const top  = idx * ROW_HEIGHT;
  const hasCont = entry.continuation && entry.continuation.length > 0;

  // Continuation lines are embedded but hidden by default; CSS toggle via data-attr
  const contHtml = hasCont
    ? `<div class="continuation">${entry.continuation.map(l => `<div>${escHtml(l)}</div>`).join('')}</div>`
    : '';

  return `<div class="row ${lc}${hasCont ? ' has-cont' : ''}" style="top:${top}px" data-id="${entry.id}" tabindex="-1">
  <span class="col-ts">${escHtml(entry.timestamp)}</span>
  <span class="col-lvl"><span class="badge ${lc}">${escHtml(entry.level)}</span></span>
  <span class="col-cat">${escHtml(entry.category)}</span>
  <span class="col-thr">(${escHtml(entry.thread)})</span>
  <span class="col-msg">${escHtml(entry.message)}${hasCont ? '<button class="exp-btn" aria-label="expand">▸</button>' : ''}</span>
  ${contHtml}
</div>`;
}

export function createGrid(container) {
  let _entries    = [];
  let _startIdx   = 0;
  let _endIdx     = 0;

  // Spacer keeps the scrollbar sized correctly for the full entry count
  const spacer = document.createElement('div');
  spacer.className = 'grid-spacer';
  container.appendChild(spacer);

  const rowsEl = document.createElement('div');
  rowsEl.className = 'grid-rows';
  container.appendChild(rowsEl);

  // ── Delegation: expand/collapse continuation on button click ──────────────
  rowsEl.addEventListener('click', e => {
    const btn = e.target.closest('.exp-btn');
    if (!btn) return;
    const row = btn.closest('.row');
    if (!row) return;
    const expanded = row.classList.toggle('expanded');
    btn.textContent = expanded ? '▾' : '▸';
    // Reflow needed because row height changed
    _paint();
  });

  // ── Virtual scroll ─────────────────────────────────────────────────────────
  function _visibleRange() {
    const scrollTop = container.scrollTop;
    const height    = container.clientHeight;
    const start = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
    const end   = Math.min(_entries.length, Math.ceil((scrollTop + height) / ROW_HEIGHT) + OVERSCAN);
    return { start, end };
  }

  function _paint() {
    const { start, end } = _visibleRange();
    if (start === _startIdx && end === _endIdx) return;
    _startIdx = start;
    _endIdx   = end;

    const html = [];
    for (let i = start; i < end; i++) {
      html.push(buildRowHtml(_entries[i], i));
    }
    rowsEl.innerHTML = html.join('');
  }

  container.addEventListener('scroll', _paint, { passive: true });
  window.addEventListener('resize', _paint, { passive: true });

  // ── Public API ─────────────────────────────────────────────────────────────
  return {
    render(entries) {
      _entries  = entries;
      _startIdx = -1; // force repaint
      _endIdx   = -1;
      spacer.style.height = `${entries.length * ROW_HEIGHT}px`;
      _paint();
    },

    scrollToBottom() {
      container.scrollTop = container.scrollHeight;
    },

    isNearBottom() {
      const { scrollTop, scrollHeight, clientHeight } = container;
      return scrollHeight - scrollTop - clientHeight < ROW_HEIGHT * 5;
    },
  };
}
