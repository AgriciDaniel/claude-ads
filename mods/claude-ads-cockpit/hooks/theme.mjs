// Semantic tones. Colors are theme keys, so the pane follows the person's dark or light theme.
// No hex values here: a hex color would not adapt. Marks are single-width glyphs.
export const TONES = Object.freeze({
  ok: Object.freeze({ mark: '✓', color: 'success' }),
  warn: Object.freeze({ mark: '▲', color: 'warning' }),
  bad: Object.freeze({ mark: '✗', color: 'error' }),
  info: Object.freeze({ mark: '●', color: 'suggestion' }),
  muted: Object.freeze({ mark: '○', color: null }),
  unclear: Object.freeze({ mark: '?', color: null }),
});
export const toneOf = name => TONES[name] || TONES.muted;
// Hex only inside Svg, where theme keys do not apply. Mid-tones that hold on light and dark.
export const SVG_COLORS = Object.freeze({ ok: '#16a34a', warn: '#d97706', bad: '#dc2626', info: '#3b82f6', muted: '#8a8f98', unclear: '#8a8f98' });
