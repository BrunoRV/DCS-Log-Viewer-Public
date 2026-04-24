import { describe, it, expect, vi, beforeEach } from 'vitest';

// We must mock globals before the module is evaluated if it uses them at top level,
// but grid.js uses navigator inside a callback, so setting it here should work
// IF we use vi.stubGlobal.
vi.stubGlobal('document', {
  createElement: vi.fn((tag) => ({
    tagName: tag.toUpperCase(),
    className: '',
    style: {},
    appendChild: vi.fn(),
    addEventListener: vi.fn(),
    set innerHTML(val) { this._innerHTML = val; },
    get innerHTML() { return this._innerHTML; },
    classList: { add: vi.fn(), remove: vi.fn() }
  })),
});

vi.stubGlobal('window', {
  addEventListener: vi.fn(),
});

vi.stubGlobal('navigator', {
  clipboard: {
    writeText: vi.fn(() => Promise.resolve()),
  },
});

import { createGrid } from '../../dcs_log_viewer/static/js/grid.js';

describe('Grid Component (Virtual Scroll)', () => {
  let container;
  let grid;

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock container
    container = {
      appendChild: vi.fn(),
      addEventListener: vi.fn(),
      scrollTop: 0,
      clientHeight: 500,
      scrollHeight: 1000,
      // Helper to trigger events
      _trigger: function(event, data) {
        const handler = this.addEventListener.mock.calls.find(c => c[0] === event)[1];
        if (handler) handler(data);
      }
    };

    grid = createGrid(container);
  });

  it('should initialize and create spacer and rows elements', () => {
    // createGrid calls container.appendChild twice: once for spacer, once for rows
    expect(container.appendChild).toHaveBeenCalledTimes(2);
    
    const spacer = container.appendChild.mock.calls[0][0];
    const rowsEl = container.appendChild.mock.calls[1][0];
    
    expect(spacer.className).toBe('grid-spacer');
    expect(rowsEl.className).toBe('grid-rows');
  });

  it('should render visible rows', () => {
    const entries = Array.from({ length: 100 }, (_, i) => ({
      id: i,
      timestamp: '10:00:00',
      level: 'INFO',
      emitter: 'TEST',
      thread: '1',
      message: `Message ${i}`
    }));

    grid.render(entries);

    const rowsEl = container.appendChild.mock.calls[1][0];
    // With clientHeight=500 and ROW_HEIGHT=22, plus OVERSCAN=30
    // We expect around 500/22 + 30 rows
    expect(rowsEl.innerHTML).toContain('Message 0');
    expect(rowsEl.innerHTML).toContain('Message 50'); // Should be within overscan
  });

  it('should handle scroll events and update view', () => {
    const entries = Array.from({ length: 200 }, (_, i) => ({
      id: i,
      timestamp: '10:00:00',
      level: 'INFO',
      emitter: 'TEST',
      thread: '1',
      message: `Message ${i}`
    }));

    grid.render(entries);
    
    const rowsEl = container.appendChild.mock.calls[1][0];
    const initialHtml = rowsEl.innerHTML;

    // Simulate scroll down to row 100
    // ROW_HEIGHT is 22. 100 * 22 = 2200.
    container.scrollTop = 2200;
    container._trigger('scroll');

    expect(rowsEl.innerHTML).not.toBe(initialHtml);
    expect(rowsEl.innerHTML).toContain('Message 100');
  });

  it('should check if near bottom', () => {
    container.scrollHeight = 1000;
    container.clientHeight = 200;
    
    container.scrollTop = 0;
    expect(grid.isNearBottom()).toBe(false);

    // Near bottom is < 100px difference
    container.scrollTop = 750; // 1000 - 200 - 750 = 50
    expect(grid.isNearBottom()).toBe(true);
  });

  it('should scroll to bottom', () => {
    container.scrollHeight = 2000;
    grid.scrollToBottom();
    expect(container.scrollTop).toBe(2000);
  });

  it('should handle copy button click', async () => {
    const entry = { id: 123, timestamp: '10:00', level: 'INFO', emitter: 'A', thread: '1', message: 'msg', raw: 'RAW DATA' };
    grid.render([entry]);
    
    // We can simulate the click event on rowsEl
    const mockEvent = {
      target: {
        closest: vi.fn((selector) => {
          if (selector === '.copy-btn') return { 
            dataset: { id: '123' }, 
            innerHTML: '',
            classList: { add: vi.fn(), remove: vi.fn() }
          };
          return null;
        })
      },
      stopPropagation: vi.fn()
    };
    
    // Find rowsEl (second child appended to container)
    const rowsEl = container.appendChild.mock.calls[1][0];
    const clickHandler = rowsEl.addEventListener.mock.calls.find(c => c[0] === 'click')[1];
    clickHandler(mockEvent);
    
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('RAW DATA');
  });
});
