import { describe, it, expect } from 'vitest';
import { Highlighter } from '../../dcs_log_viewer/static/js/highlighter.js';
import { dcsHighlighter } from '../../dcs_log_viewer/static/js/highlighter_dcs.js';

describe('Highlighter Core Logic', () => {
  it('should escape HTML characters', () => {
    const hl = new Highlighter([]);
    const input = '<div> & "path"';
    const output = hl.highlight(input);
    expect(output).toBe('&lt;div&gt; &amp; "path"');
  });

  it('should wrap matches in spans', () => {
    const rules = [{ name: 'test', regex: /world/g }];
    const hl = new Highlighter(rules);
    const output = hl.highlight('hello world');
    expect(output).toBe('hello <span class="hl-test">world</span>');
  });

  it('should handle overlapping matches by keeping the first/longest', () => {
    // 'abc' matches both 'abc' and 'bc'
    const rules = [
      { name: 'long', regex: /abc/g },
      { name: 'short', regex: /bc/g }
    ];
    const hl = new Highlighter(rules);
    const output = hl.highlight('abc');
    expect(output).toBe('<span class="hl-long">abc</span>');
  });

  it('should prioritize link types even if nested', () => {
    const rules = [
      { name: 'bracket', regex: /\[[^\]]+\]/g },
      { name: 'link', regex: /https?:\/\/[^\s\]]+/g }
    ];
    const hl = new Highlighter(rules);
    const input = '[see http://example.com]';
    // The link is inside the bracket. We want the link to be highlighted if it's a 'link' type.
    // In highlighter.js, sorting logic handles this.
    const output = hl.highlight(input);
    expect(output).toContain('class="hl-link"');
    expect(output).not.toContain('class="hl-bracket"');
  });

  it('should handle capturing groups for boundary checks', () => {
    // Match 'foo' only if preceded by '[' but don't include '[' in the span
    const rules = [{ name: 'bounded', regex: /\[(foo)/g }];
    const hl = new Highlighter(rules);
    const output = hl.highlight('[foo');
    expect(output).toBe('[<span class="hl-bounded">foo</span>');
  });
});

describe('DCS Highlighter Rules', () => {
  it('should highlight IPv4 addresses', () => {
    const input = 'Connected to 127.0.0.1:1234';
    const output = dcsHighlighter.highlight(input);
    expect(output).toContain('<span class="hl-link">127.0.0.1</span>');
  });

  it('should highlight Windows paths with spaces', () => {
    const input = 'Loading "C:\\Program Files\\DCS World\\bin\\DCS.exe"';
    const output = dcsHighlighter.highlight(input);
    expect(output).toContain('<span class="hl-link">C:\\Program Files\\DCS World\\bin\\DCS.exe</span>');
  });

  it('should highlight URLs', () => {
    const input = 'Visit https://www.digitalcombatsimulator.com for details';
    const output = dcsHighlighter.highlight(input);
    expect(output).toContain('<span class="hl-link">https://www.digitalcombatsimulator.com</span>');
  });

  it('should highlight Class::Method patterns', () => {
    const input = 'ERROR: Weather::Update failed';
    const output = dcsHighlighter.highlight(input);
    expect(output).toContain('<span class="hl-member">Weather::Update</span>');
  });

  it('should highlight bracketed units', () => {
    const input = '[ED_CORE] Info message';
    const output = dcsHighlighter.highlight(input);
    expect(output).toContain('<span class="hl-bracket">[ED_CORE]</span>');
  });
});
