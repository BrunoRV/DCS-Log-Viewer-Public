/**
 * filters.js — in-memory entry store + filter engine.
 *
 * Exports:
 *   initLevels()            — fetch canonical level list from /api/levels (call once at boot)
 *   store.add(entries)      — append parsed entries
 *   store.reset()           — clear all entries
 *   store.filtered()        — return currently filtered + searched entries
 *   store.setSearch(text)   — update search string
 *   store.setUseRegex(bool) — toggle regex search
 *   store.setLevels(arr)    — update level whitelist ([] = show all)
 *   store.setEmitter(str)   — update emitter filter ('' = show all)
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
  let _useRegex = false;
  let _levels   = [];   // [] means "all"
  let _emitter  = '';

  function _matches(entry) {
    // Level filter
    if (_levels.length > 0 && !_levels.includes(entry.level)) return false;

    // Emitter filter
    if (_emitter && entry.emitter !== _emitter) return false;

    // Text search
    if (_search) {
      const haystack = [
        entry.timestamp,
        entry.level,
        entry.emitter,
        entry.thread,
        entry.message,
        ...(entry.continuation || []),
      ].join(' ');

      if (_useRegex) {
        try {
          const re = new RegExp(_search, 'i');
          if (!re.test(haystack)) return false;
        } catch (e) {
          // Invalid regex, fallback to simple include
          if (!haystack.toLowerCase().includes(_search.toLowerCase())) return false;
        }
      } else {
        if (!haystack.toLowerCase().includes(_search.toLowerCase())) return false;
      }
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
    setUseRegex(bool) { _useRegex = bool; },
    setLevels(arr)  { _levels = arr; },
    setEmitter(s)   { _emitter = s; },

    getLevels() {
      return ALL_LEVELS;
    },

    getEmitters() {
      const set = new Set(_entries.map(e => e.emitter));
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
