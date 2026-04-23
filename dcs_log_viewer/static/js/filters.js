/**
 * filters.js — in-memory entry store + filter engine.
 *
 * Exports:
 *   initLevels()            — fetch canonical level list from /api/levels (call once at boot)
 *   store.add(entries)      — append parsed entries
 *   store.reset()           — clear all entries
 *   store.filtered()        — return currently filtered + searched entries
 *   store.setSearch(text)   — update search string
 *   store.setLevels(arr)    — update level whitelist ([] = show all)
 *   store.setCategory(str)  — update category filter ('' = show all)
 *   store.getStats()        — { total, counts: {<level>: N, ...} }
 *   store.getLevels()       — ordered list of known levels
 */

/** @type {string[]} Populated by initLevels() before first use. */
let ALL_LEVELS = [];

/**
 * Fetch the canonical level list from the Python backend (parser.LEVELS).
 * Must be awaited before calling store.getStats() or store.getLevels().
 */
export async function initLevels() {
  try {
    const resp = await fetch('/api/levels');
    const { levels } = await resp.json();
    ALL_LEVELS = levels;
  } catch (err) {
    // Fallback to a sensible default so the UI still works offline
    console.warn('[filters] Could not fetch /api/levels, using defaults:', err);
    ALL_LEVELS = ['ERROR', 'WARN', 'INFO', 'DEBUG', 'TRACE'];
  }
}

function makeStore() {
  let _entries  = [];   // all entries in the sliding window
  let _search   = '';
  let _levels   = [];   // [] means "all"
  let _category = '';

  function _matches(entry) {
    // Level filter
    if (_levels.length > 0 && !_levels.includes(entry.level)) return false;

    // Category filter
    if (_category && entry.category !== _category) return false;

    // Text search (case-insensitive across all visible fields)
    if (_search) {
      const needle = _search.toLowerCase();
      const haystack = [
        entry.timestamp,
        entry.level,
        entry.category,
        entry.thread,
        entry.message,
        ...(entry.continuation || []),
      ].join(' ').toLowerCase();
      if (!haystack.includes(needle)) return false;
    }

    return true;
  }

  return {
    add(entries) {
      _entries.push(...entries);
    },
    reset() {
      _entries = [];
    },
    filtered() {
      return _entries.filter(_matches);
    },
    setSearch(text) { _search = text; },
    setLevels(arr)  { _levels = arr; },
    setCategory(s)  { _category = s; },

    getLevels() {
      return ALL_LEVELS;
    },

    getCategories() {
      const set = new Set(_entries.map(e => e.category));
      return [...set].sort();
    },

    getStats() {
      const counts = Object.fromEntries(ALL_LEVELS.map(l => [l, 0]));
      for (const e of _entries) if (counts[e.level] !== undefined) counts[e.level]++;
      return { total: _entries.length, counts };
    },
  };
}

export const store = makeStore();
