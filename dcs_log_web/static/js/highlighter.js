/**
 * highlighter.js — Modular, regex-based log syntax highlighter.
 * Optimized for performance by processing only visible rows in the virtual grid.
 */

export class Highlighter {
  /**
   * @param {Array<{name: string, regex: RegExp}>} rules
   */
  constructor(rules) {
    this.rules = rules;
  }

  /**
   * Highlights a string by wrapping matches in <span class="hl-..."> tags.
   * Uses a single-pass non-destructive strategy to avoid nested tag issues.
   * @param {string} text
   * @returns {string} HTML string
   */
  highlight(text) {
    if (!text) return '';

    // 1. Escape HTML basics
    let escaped = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // 2. Collect all matches from all rules
    const matches = [];
    for (const rule of this.rules) {
      let match;
      rule.regex.lastIndex = 0; // Ensure we start from the beginning
      while ((match = rule.regex.exec(escaped)) !== null) {
        let start = match.index;
        let content = match[0];

        // If the regex has a capturing group, we use that as the actual content.
        // This allows for boundary checks without styling the boundary characters.
        if (match[1] !== undefined) {
          const offset = match[0].indexOf(match[1]);
          if (offset !== -1) {
            start += offset;
            content = match[1];
          }
        }

        matches.push({
          start: start,
          end: start + content.length,
          content: content,
          className: `hl-${rule.name}`
        });
      }
    }

    if (matches.length === 0) return escaped;

    // 3. Sort by start position, then by priority (links first), then by length
    matches.sort((a, b) => {
      // Priority: if one match contains the other, prioritize 'link' types
      const aContainsB = a.start <= b.start && a.end >= b.end;
      const bContainsA = b.start <= a.start && b.end >= a.end;

      if (aContainsB || bContainsA) {
        const aIsLink = a.className.includes('link');
        const bIsLink = b.className.includes('link');
        if (aIsLink && !bIsLink) return -1;
        if (bIsLink && !aIsLink) return 1;
      }

      return a.start - b.start || b.end - a.end;
    });

    // 4. Filter out overlapping matches (keep the first/longest)
    const filtered = [];
    let lastEnd = 0;
    for (const m of matches) {
      if (m.start >= lastEnd) {
        filtered.push(m);
        lastEnd = m.end;
      }
    }

    // 5. Rebuild the string with spans
    let result = '';
    let pos = 0;
    for (const m of filtered) {
      result += escaped.substring(pos, m.start);
      result += `<span class="${m.className}">${m.content}</span>`;
      pos = m.end;
    }
    result += escaped.substring(pos);

    return result;
  }
}
