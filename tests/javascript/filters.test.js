import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest';
import { store, initLevels } from '../../dcs_log_viewer/static/js/filters.js';

describe('Filter Store', () => {
  beforeAll(async () => {
    const mockLevels = ['ERROR', 'WARN', 'INFO', 'DEBUG', 'TRACE'];
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve({ levels: mockLevels }),
      })
    ));
    await initLevels();
  });

  beforeEach(() => {
    store.reset();
    store.setSearch('');
    store.setUseRegex(false);
    store.setLevels([]);
    store.setEmitter('');
  });

  it('should add and retrieve entries', () => {
    const entries = [
      { timestamp: '10:00', level: 'INFO', emitter: 'UI', message: 'Hello' }
    ];
    store.add(entries);
    expect(store.filtered()).toHaveLength(1);
    expect(store.filtered()[0].message).toBe('Hello');
  });

  it('should filter by level', () => {
    store.add([
      { level: 'INFO', emitter: 'A', message: '1' },
      { level: 'ERROR', emitter: 'B', message: '2' }
    ]);
    store.setLevels(['ERROR']);
    expect(store.filtered()).toHaveLength(1);
    expect(store.filtered()[0].level).toBe('ERROR');
  });

  it('should filter by emitter', () => {
    store.add([
      { level: 'INFO', emitter: 'CORE', message: '1' },
      { level: 'INFO', emitter: 'NET', message: '2' }
    ]);
    store.setEmitter('CORE');
    expect(store.filtered()).toHaveLength(1);
    expect(store.filtered()[0].emitter).toBe('CORE');
  });

  it('should search text', () => {
    store.add([
      { level: 'INFO', message: 'Target found' },
      { level: 'INFO', message: 'Nothing here' }
    ]);
    store.setSearch('target');
    expect(store.filtered()).toHaveLength(1);
    expect(store.filtered()[0].message).toBe('Target found');
  });

  it('should support regex search', () => {
    store.add([
      { level: 'INFO', message: 'ID: 123' },
      { level: 'INFO', message: 'ID: abc' }
    ]);
    store.setSearch('ID: \\d+');
    store.setUseRegex(true);
    expect(store.filtered()).toHaveLength(1);
    expect(store.filtered()[0].message).toBe('ID: 123');
  });

  it('should fallback to simple include if regex is invalid', () => {
    store.add([{ level: 'INFO', message: 'Hello (world)', emitter: 'A', timestamp: '', thread: '' }]);
    // Invalid regex: unclosed parenthesis
    store.setSearch('(');
    store.setUseRegex(true);
    // Should fallback to includes and find it because '(' is in the message
    expect(store.filtered()).toHaveLength(1);
  });

  it('should return known levels', () => {
    expect(store.getLevels()).toContain('INFO');
  });

  it('should return unique sorted emitters', () => {
    store.add([
      { level: 'INFO', emitter: 'B', message: '1' },
      { level: 'INFO', emitter: 'A', message: '2' },
      { level: 'INFO', emitter: 'B', message: '3' }
    ]);
    expect(store.getEmitters()).toEqual(['A', 'B']);
  });

  it('should calculate stats', () => {
    store.add([
      { level: 'INFO', message: 'a' },
      { level: 'INFO', message: 'b' },
      { level: 'ERROR', message: 'c' }
    ]);
    const stats = store.getStats();
    expect(stats.total).toBe(3);
    expect(stats.counts['INFO']).toBe(2);
    expect(stats.counts['ERROR']).toBe(1);
  });
});
