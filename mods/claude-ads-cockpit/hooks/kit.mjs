// The small design kit every screen uses. Pure: it only builds elements from the surface's own
// Box, Text and Button. Props are filtered so no undefined value reaches the strict validator, and
// every string passes through safeText before it is drawn.
import { toneOf } from './theme.mjs';
import { oneLine, safeText } from './wire.mjs';

const defined = object => Object.fromEntries(Object.entries(object).filter(([, value]) => value !== undefined && value !== null));
const cellText = cell => (cell !== null && typeof cell === 'object' ? (cell.parts ? cell.parts.map(p => (typeof p === 'string' ? p : p.text)).join('') : cell.text) : cell) ?? '';

export function makeKit(ui, width = 60, rows = 34) {
  const { Box, Text, Button } = ui;
  const narrow = width < 54;
  const wide = width >= 100;
  const toneStyle = name => { const tone = toneOf(name); return tone.color ? { color: tone.color } : { dimColor: true }; };

  const t = (content, options = {}) => Text({ children: [safeText(content)], ...defined(options) });
  // A line of mixed styles. Parts are strings or {text, tone, bold, dim, color, inverse}.
  // Color is applied reliably only to a Text that stands alone, so a line with any colored part is
  // built from sibling Texts in a row. A line with no color keeps nested Texts, which wrap as one paragraph.
  // Explicit style wins over the tone, but only where it is set: an undefined value must never erase the tone's color.
  const partStyle = part => ({ ...(part.tone ? toneStyle(part.tone) : {}), ...defined({ bold: part.bold, dimColor: part.dim, color: part.color, inverse: part.inverse }) });
  const line = (parts, options = {}) => {
    const colored = parts.some(part => typeof part === 'object' && (part.tone || part.color));
    if (colored) {
      // Spacing comes from the row's gap, never from leading or trailing spaces inside a part.
      const gap = options.gap ?? 1;
      const piece = part => (typeof part === 'string' ? { text: part } : part);
      const kids = parts.map(piece).map(part => ({ ...part, text: gap > 0 && !part.raw ? safeText(part.text).trim() : safeText(part.text) })).filter(part => part.text !== '');
      if (options.wrap === 'truncate-end') {
        // A line that must stay one line: trim from the end, last part first, so it never wraps.
        let over = kids.reduce((a, part) => a + part.text.length, 0) + gap * Math.max(0, kids.length - 1) - (width - 1);
        for (let i = kids.length - 1; i >= 0 && over > 0; i--) {
          const keep = Math.max(1, kids[i].text.length - over);
          if (keep < kids[i].text.length) { over -= kids[i].text.length - keep; kids[i] = { ...kids[i], text: `${kids[i].text.slice(0, Math.max(0, keep - 1))}…` }; }
        }
        return Box({ flexDirection: 'row', columnGap: gap, children: kids.map(part => Text({ children: [part.text], wrap: 'truncate-end', ...partStyle(part) })) });
      }
      return Box({ flexDirection: 'row', columnGap: gap, flexWrap: 'wrap', children: kids.map(part => Text({ children: [part.text], ...partStyle(part) })) });
    }
    const { gap, ...rest } = options;
    return Text({ children: parts.map(part => (typeof part === 'string' ? safeText(part) : Text({ children: [safeText(part.text)], ...partStyle(part) }))), ...defined(rest) });
  };
  const hint = (content, options = {}) => t(content, { dimColor: true, ...options });
  // A list item that may wrap. The glyph and text stay in one paragraph, so a wrapped line never leaves the glyph alone.
  const item = (glyph, content) => Text({ children: [Text({ children: [`${glyph} `], bold: true }), safeText(content)] });
  const mark = name => t(toneOf(name).mark, toneStyle(name));
  const row = (children, { gap = 1, wrap = false, key } = {}) => Box({ ...defined({ key }), flexDirection: 'row', columnGap: gap, ...(wrap ? { flexWrap: 'wrap' } : {}), children });
  const col = (children, { gap, key } = {}) => Box({ ...defined({ key, rowGap: gap }), flexDirection: 'column', children });
  const section = children => Box({ flexDirection: 'column', marginTop: 1, children });
  const indent = (children, by = 2) => Box({ flexDirection: 'column', marginLeft: by, children });
  const card = (children, { tone = 'muted', key } = {}) => {
    const t0 = toneOf(tone);
    return Box({ ...defined({ key }), flexDirection: 'column', borderStyle: 'round', ...(t0.color ? { borderColor: t0.color } : { borderDimColor: true }), paddingX: 1, children });
  };
  const rule = () => t('─'.repeat(Math.max(8, Math.min(width, 120))), { dimColor: true, wrap: 'truncate-end' });
  // A section title drawn as a rule: "── Title · note ─────". One line, never wraps.
  const heading = (title, note) => {
    const label = note ? `${title} · ${note}` : title;
    return line([{ text: '── ', dim: true, raw: true }, { text: label, bold: true }, { text: ` ${'─'.repeat(Math.max(2, Math.min(width, 100) - label.length - 5))}`, dim: true, raw: true }], { gap: 0, wrap: 'truncate-end' });
  };
  // Text wrapped by hand into at most `n` lines of at most `room` characters. The last line ends with an
  // ellipsis when the text did not fit, so a screen can budget its height exactly.
  const wrapLines = (content, n, room) => {
    const words = safeText(content).split(/\s+/).filter(Boolean);
    const out = [];
    let current = '';
    for (const word of words) {
      const next = current ? `${current} ${word}` : word;
      if (next.length <= room) current = next;
      else { if (current) out.push(current); current = word.length > room ? `${word.slice(0, room - 1)}…` : word; }
    }
    if (current) out.push(current);
    const shown = out.slice(0, Math.max(1, n));
    if (out.length > shown.length) shown[shown.length - 1] = `${shown[shown.length - 1].slice(0, Math.max(0, room - 1)).replace(/\s+$/, '')}…`;
    return shown;
  };
  // How many lines `content` takes when wrapped to this width (after `indent` columns).
  const countLines = (content, indent = 0) => wrapLines(content, 99, Math.max(8, width - indent)).length;
  const clamp = (content, n, { indent = 0, ...style } = {}) => wrapLines(content, n, Math.max(8, width - indent))
    .map(text => Text({ children: [indent ? `${' '.repeat(indent)}${text}` : text], wrap: 'truncate-end', ...defined(style) }));
  // A labeled paragraph of at most `n` lines: a dim label, then the text wrapped beside it.
  const field = (label, content, n, labelWidth = 11) => {
    const pad = label.padEnd(labelWidth);
    const lines = wrapLines(content, n, Math.max(8, width - labelWidth));
    return lines.map((text, i) => (i === 0
      ? line([{ text: pad, dim: true, raw: true }, { text, raw: true }], { gap: 0, wrap: 'truncate-end' })
      : Text({ children: [`${' '.repeat(labelWidth)}${text}`], wrap: 'truncate-end' })));
  };
  const chip = (label, value, name = 'muted') => line([{ text: `${label} `, dim: true }, { text: String(value), bold: true, ...(name === 'muted' ? {} : { tone: name }) }]);
  const bar = (done, total, length = 10, name = 'ok') => {
    const filled = total > 0 ? Math.round((Math.min(done, total) / total) * length) : 0;
    return line([{ text: '█'.repeat(filled), tone: name }, { text: '░'.repeat(length - filled), dim: true }]);
  };
  const dots = (index, total) => line(Array.from({ length: total }, (_, i) => ({ text: i <= index ? '●' : '○', ...(i === index ? { tone: 'info', bold: true } : i < index ? { tone: 'info' } : { dim: true }) })));
  // A control, or its dim label when it cannot act right now. No disabled prop is ever drawn.
  // Every label is one bounded line, whatever the run data held. The terminal draws a key only on a
  // plain button, so a framed button names its key in the label: "Next (n)".
  const button = (key, label, hotkey, onPress, { primary = false, plain = false, off = false } = {}) => {
    const text = oneLine(label);
    return off
      ? t(text, { dimColor: true })
      : Button({ key, label: hotkey && !plain ? `${text} (${hotkey})` : text, ...defined({ hotkey, plain: plain ? true : undefined, variant: primary && !plain ? 'primary' : undefined }), onPress });
  };
  // Aligned table from fixed-width cells. Cells are strings or {text, tone, bold}. One column may grow.
  const table = (columns, tableRows, { header = true } = {}) => {
    const gap = 2;
    const fixed = columns.map((column, i) => (column.grow ? 0 : Math.min(column.max ?? 20, Math.max(column.head.length, ...tableRows.map(r => String(cellText(r[i])).length)))));
    const used = fixed.reduce((a, b) => a + b, 0) + gap * (columns.length - 1) + 2;
    const grow = Math.max(8, width - used);
    const sizes = columns.map((column, i) => (column.grow ? grow : fixed[i]));
    // Never wider than the room: shrink the widest column a cell at a time (cells truncate with an ellipsis).
    let over = sizes.reduce((a, b) => a + b, 0) + gap * (columns.length - 1) - width;
    while (over > 0) {
      const widest = sizes.indexOf(Math.max(...sizes));
      if (sizes[widest] <= 4) break;
      sizes[widest] -= 1; over -= 1;
    }
    const cell = (column, i, content, header) => {
      const tone = !header && content !== null && typeof content === 'object' ? content.tone : undefined;
      const text = !header && content !== null && typeof content === 'object' && content.parts
        ? line(content.parts, { gap: content.gap ?? 1 })
        : t(cellText(content), { wrap: 'truncate-end', ...(header ? { dimColor: true } : tone ? toneStyle(tone) : {}), ...(!header && content?.bold ? { bold: true } : {}) });
      return Box({ width: sizes[i], ...(column.align === 'right' ? { justifyContent: 'flex-end' } : {}), children: [text] });
    };
    return col([
      ...(header ? [row(columns.map((column, i) => cell(column, i, column.head, true)), { gap })] : []),
      ...tableRows.map((r, rowIndex) => row(columns.map((column, i) => cell(column, i, r[i], false)), { gap, key: `row-${rowIndex}` })),
    ]);
  };
  // A bordered number tile: the value large and colored, a short label beneath.
  const tile = (value, label, name = 'muted', size = 16) => {
    const t0 = toneOf(name);
    return Box({ flexDirection: 'column', borderStyle: 'round', ...(t0.color ? { borderColor: t0.color } : { borderDimColor: true }), paddingX: 1, width: size, children: [
      t(String(value), { bold: true, wrap: 'truncate-end', ...(t0.color ? { color: t0.color } : {}) }),
      t(label, { dimColor: true, wrap: 'truncate-end' }),
    ] });
  };
  const tiles = list => {
    const per = width < 76 ? 2 : list.length;
    const size = Math.max(10, Math.floor((width - (per - 1)) / per));
    return row(list.map(([value, label, name]) => tile(value, label, name, size)), { gap: 1, wrap: true });
  };
  // Split `total` cells between named counts, at least one cell for any non-zero count.
  const allocate = (parts, length) => {
    const total = parts.reduce((a, p) => a + p.n, 0);
    if (!total) return parts.map(p => ({ ...p, cells: 0 }));
    const cells = parts.map(p => (p.n ? Math.max(1, Math.round((p.n / total) * length)) : 0));
    while (cells.reduce((a, b) => a + b, 0) > length) cells[cells.indexOf(Math.max(...cells))] -= 1;
    while (cells.reduce((a, b) => a + b, 0) < length && total) cells[cells.indexOf(Math.max(...cells))] += 1;
    return parts.map((p, i) => ({ ...p, cells: cells[i] }));
  };
  // One colored bar split by result, with its legend. Sized so bar and legend share a single line.
  const stackBar = (parts, length) => {
    const legend = parts.filter(p => p.n).map(p => ({ text: `${toneOf(p.tone).mark} ${p.n} ${p.label}`, tone: p.tone }));
    const legendWidth = legend.reduce((a, p) => a + p.text.length + 2, 0);
    const size = length ?? Math.max(8, Math.min(36, width - legendWidth - 2));
    return row([
      line(allocate(parts, size).filter(p => p.cells).map(p => ({ text: ({ ok: '█', bad: '▓', unclear: '░', muted: '▒' }[p.tone] || '█').repeat(p.cells), tone: p.tone, raw: true })), { gap: 0 }),
      line(legend, { gap: 2, wrap: 'truncate-end' }),
    ], { gap: 2 });
  };
  // A fixed-width meter for pass, fail and unclear counts: solid cells for what is known, light cells for what is not.
  // Returns line parts so it can sit in a table cell.
  const meterParts = (r, length) => allocate([{ n: r.pass, tone: 'ok', glyph: '█' }, { n: r.fail, tone: 'bad', glyph: '▓' }, { n: r.unknown, tone: 'unclear', glyph: '░' }], length)
    .filter(p => p.cells).map(p => ({ text: p.glyph.repeat(p.cells), tone: p.tone, raw: true }));
  // One square per check, colored by result. Truncated with a count when it would not fit.
  const squares = (tones, room) => {
    const fit = Math.max(4, room);
    const shown = tones.slice(0, tones.length > fit ? fit - 3 : fit);
    // Runs of one result share a Text, so a long audit stays a handful of elements.
    const runs = [];
    for (const name of shown) { if (runs.length && runs[runs.length - 1].tone === name) runs[runs.length - 1].text += '■'; else runs.push({ text: '■', tone: name }); }
    return [...runs, ...(tones.length > shown.length ? [{ text: ` +${tones.length - shown.length}`, dim: true }] : [])];
  };
  // Four numbers in two lines: the values large and colored, the labels beneath, in aligned columns.
  // On a narrow pane they become one line of text.
  const stats = (list, compact = false) => {
    if (compact || width < 56) return line(list.flatMap(([value, label, name]) => [{ text: String(value), bold: true, tone: name }, { text: label, dim: true }]), { gap: 1, wrap: 'truncate-end' });
    const size = Math.floor(width / list.length);
    const cells = (render) => row(list.map(item => Box({ width: size, children: [render(item)] })), { gap: 0 });
    return col([
      cells(([value, , name]) => t(String(value), { bold: true, wrap: 'truncate-end', ...toneStyle(name) })),
      cells(([, label]) => t(label, { dimColor: true, wrap: 'truncate-end' })),
    ]);
  };
  // Back and Next for a list that spans pages. One line; null when everything fits on one page.
  const pager = (page, pages, { back, next }) => (pages <= 1 ? null : row([
    button('page-back', 'Back', 'u', back, { plain: true, off: page <= 0 }),
    button('page-next', 'Next', 'j', next, { plain: true, off: page >= pages - 1 }),
    t(`page ${page + 1} of ${pages}`, { dimColor: true }),
  ], { gap: 2 }));
  const titleRule = title => line([{ text: `── ${title} `, bold: true }, { text: '─'.repeat(Math.max(2, Math.min(width, 100) - title.length - 4)), dim: true }], { wrap: 'truncate-end' });
  return { ui, width, rows, narrow, wide, meterParts, clamp, countLines, field, stats, pager, tile, tiles, stackBar, squares, titleRule, t, line, hint, item, mark, row, col, section, indent, card, rule, heading, chip, bar, dots, button, table, toneStyle };
}
