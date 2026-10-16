// Fits a screen into a fixed number of lines. A block is one section of a screen:
//   need  the fewest lines it is useful at (0 means it may be dropped entirely)
//   want  the most lines it can use
//   pri   lower numbers are given room first
//   build(n) returns the elements for n lines and never more than n lines
// Blocks keep the order they are listed in. With `gap`, one blank line separates them and is counted in the budget.
export function pack(kit, budget, blocks, { gap = true } = {}) {
  const live = blocks.filter(Boolean).map((b, order) => ({ ...b, order, lines: 0 }));
  const byPri = [...live].sort((a, b) => a.pri - b.pri || a.order - b.order);
  let used = 0;
  let included = 0;
  const gapFor = () => (gap && included > 0 ? 1 : 0);
  for (const block of byPri) {
    const extra = gapFor();
    if (block.need > 0 && used + extra + block.need <= budget) { block.lines = block.need; used += extra + block.need; included++; }
  }
  for (const block of byPri) {
    if (!block.lines) continue;
    const grow = Math.min(block.want - block.lines, budget - used);
    if (grow > 0) { block.lines += grow; used += grow; }
  }
  const shown = live.filter(b => b.lines > 0);
  const out = [];
  shown.forEach((block, i) => {
    if (i > 0 && gap) out.push(kit.t(' '));
    out.push(...[].concat(block.build(block.lines)));
  });
  return out;
}

// How many of `total` items fit in `room` lines when a "+N more" line may be needed.
// shown + more never exceeds room: with a single line left, the item wins over the "more" note.
export function fitList(total, room) {
  if (total <= room) return { shown: total, more: 0 };
  if (room >= 2) return { shown: room - 1, more: 1 };
  return { shown: Math.max(0, room), more: 0 };
}

// Paging for `total` items in `room` lines (after the heading): a pager line only when it fits.
export function pageList(total, room) {
  if (total <= room) return { per: Math.max(1, room), pages: 1, pagerLine: 0 };
  if (room >= 3) { const per = room - 1; return { per, pages: Math.ceil(total / per), pagerLine: 1 }; }
  return { per: Math.max(1, room), pages: Math.ceil(total / Math.max(1, room)), pagerLine: 0 };
}
