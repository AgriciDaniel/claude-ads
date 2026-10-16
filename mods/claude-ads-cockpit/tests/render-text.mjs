// Test and preview helper: draws an element tree built by fake constructors as plain text.
// It approximates the terminal's flex layout (rows, columns, gaps, wrap, truncate, round borders).
// It is not the real renderer: it cannot show color, and the real Button chrome may differ slightly.
export const fakeUi = (extra = {}) => ({
  Box: props => ({ type: 'Box', props, children: props.children }),
  Text: props => ({ type: 'Text', props, children: props.children }),
  Button: props => ({ type: 'Button', props }),
  Input: props => ({ type: 'Input', props }),
  ...extra,
});
const kids = node => (node.children ?? node.props?.children ?? []).filter(c => c !== undefined && c !== null && c !== false);
const textOf = node => (typeof node === 'string' ? node : node.type === 'Button' ? buttonText(node) : kids(node).map(textOf).join(''));
function buttonText(node) {
  const { label, hotkey, plain } = node.props;
  return plain ? (hotkey ? `${hotkey}: ${label}` : label) : `[ ${label} ]`;
}
const chrome = box => ({ border: box.props.borderStyle ? 1 : 0, padX: box.props.paddingX ?? box.props.padding ?? 0, left: box.props.marginLeft ?? 0, top: box.props.marginTop ?? 0 });
function measure(node) {
  if (typeof node === 'string') return node.length;
  if (node.type === 'Text') return textOf(node).length;
  if (node.type === 'Button') return buttonText(node).length;
  if (node.type === 'Input') return (node.props.label?.length ?? 0) + (node.props.placeholder?.length ?? 8) + 6;
  if (node.type === 'Svg') return String(node.props.alt ?? '').length + 10;
  if (node.props.width !== undefined) return node.props.width + chrome(node).left;
  const c = chrome(node);
  const sizes = kids(node).map(measure);
  const gap = node.props.columnGap ?? node.props.gap ?? 0;
  const inner = node.props.flexDirection === 'row' ? sizes.reduce((a, b) => a + b, 0) + gap * Math.max(0, sizes.length - 1) : Math.max(0, ...sizes);
  return (node.props.width ?? inner) + c.border * 2 + c.padX * 2 + c.left;
}
const ellipsize = (text, width) => (text.length <= width ? text : `${text.slice(0, Math.max(0, width - 1))}…`);
function wrapText(text, width) {
  const out = [];
  for (const paragraph of text.split('\n')) {
    let current = '';
    for (let word of paragraph.split(' ')) {
      while (word.length > width) { if (current) { out.push(current); current = ''; } out.push(word.slice(0, width)); word = word.slice(width); }
      if (!current) current = word; else if (current.length + 1 + word.length <= width) current += ` ${word}`; else { out.push(current); current = word; }
    }
    out.push(current);
  }
  return out;
}
const pad = (text, width) => text + ' '.repeat(Math.max(0, width - text.length));
function render(node, width) {
  if (typeof node === 'string') return wrapText(node, width);
  if (node.type === 'Text') {
    const text = textOf(node);
    return node.props.wrap === 'truncate-end' ? [ellipsize(text, width)] : wrapText(text, width);
  }
  if (node.type === 'Button') return [ellipsize(buttonText(node), width)];
  if (node.type === 'Input') return [ellipsize(`${node.props.label ?? ''} [ ${node.props.placeholder ?? ''} ] ${node.props.submitLabel ?? ''}`.trim(), width)];
  if (node.type === 'Svg') return [ellipsize(`[chart: ${node.props.alt}]`, width)];
  const c = chrome(node);
  const inner = Math.max(4, Math.min(node.props.width ?? width, width) - c.border * 2 - c.padX * 2 - c.left);
  const children = kids(node);
  let lines;
  if (node.props.flexDirection === 'row') {
    const gap = node.props.columnGap ?? node.props.gap ?? 0;
    const place = items => {
      const widths = items.map(child => Math.min(measure(child), inner));
      let over = widths.reduce((a, b) => a + b, 0) + gap * Math.max(0, items.length - 1) - inner;
      while (over > 0) { const i = widths.indexOf(Math.max(...widths)); if (widths[i] <= 6) break; widths[i] -= 1; over -= 1; }
      const blocks = items.map((child, i) => render(child, widths[i]).map(l => (child.props?.justifyContent === 'flex-end' ? ' '.repeat(Math.max(0, widths[i] - l.length)) + l : pad(l, widths[i]))));
      const height = Math.max(1, ...blocks.map(b => b.length));
      return Array.from({ length: height }, (_, y) => blocks.map((b, i) => (b[y] ?? ' '.repeat(widths[i]))).join(' '.repeat(gap)).trimEnd());
    };
    if (node.props.flexWrap === 'wrap') {
      lines = []; let group = []; let used = 0;
      for (const child of children) {
        const w = Math.min(measure(child), inner);
        if (group.length && used + gap + w > inner) { lines.push(...place(group)); group = []; used = 0; }
        used += (group.length ? gap : 0) + w; group.push(child);
      }
      if (group.length) lines.push(...place(group));
    } else lines = place(children);
  } else {
    const gap = node.props.rowGap ?? 0;
    lines = children.flatMap((child, i) => [...(i && gap ? Array(gap).fill('') : []), ...(child.props?.marginTop ? Array(child.props.marginTop).fill('') : []), ...render(child, inner)]);
  }
  if (node.props.width !== undefined) lines = lines.map(l => pad(l, inner));
  if (c.padX) lines = lines.map(l => ' '.repeat(c.padX) + l);
  if (c.border) {
    const w = Math.max(inner, ...lines.map(l => l.length - c.padX)) + c.padX * 2;
    lines = [`╭${'─'.repeat(w)}╮`, ...lines.map(l => `│${pad(l, w)}│`), `╰${'─'.repeat(w)}╯`];
  }
  return lines.map(l => ' '.repeat(c.left) + l);
}
export function renderText(tree, columns = 60) {
  const lines = render(tree, columns).map(l => l.replace(/\s+$/, ''));
  const tooWide = lines.filter(l => l.length > columns);
  return { text: lines.join('\n'), lines, tooWide };
}
export { textOf, kids };
