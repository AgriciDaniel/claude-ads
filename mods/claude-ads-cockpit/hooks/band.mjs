// The one-line status band above the prompt. It keeps every other mod's band underneath it.
import { counts, verdict } from './model.mjs';
import { toneOf } from './theme.mjs';
import { MESSAGES } from './lexicon.mjs';
import { makeKit } from './kit.mjs';

export function drawBand(ui, state, other, controls, width = 60) {
  const kit = makeKit(ui, width);
  const children = [other];
  const lead = { text: ' CLAUDE ADS ', bold: true, inverse: true, color: 'claude', raw: true };
  if (state.error) children.push(kit.t(state.error === MESSAGES.setup ? MESSAGES.bandSetup : MESSAGES.bandUnavailable, kit.toneStyle('warn')));
  const s = state.snapshot;
  const where = state.selected ? `run ${state.selected}` : 'no run chosen';
  if (!s) {
    children.push(kit.row([kit.line([lead, ...(state.demo ? [{ text: '  PRACTICE', tone: 'warn', bold: true }] : []), { text: `  ${where}`, dim: true }, { text: '  Choose a run or the practice demo.', dim: true }], { wrap: 'truncate-end' }), kit.button('open-workbench', 'Open', 'o', () => controls.workbench(state.selected), { plain: true })], { gap: 2, wrap: true }));
    return ui.Box({ flexDirection: 'column', children });
  }
  const c = counts(s);
  const v = verdict(s);
  const parts = [lead, ...(state.demo ? [{ text: '  PRACTICE', tone: 'warn', bold: true }] : []), { text: `  ${state.selected}`, dim: true }, { text: `  ${toneOf(v.tone).mark} ${v.headline}`, tone: v.tone }, { text: `  steps ${c.done}/${c.workers}`, dim: true }];
  if (c.missing.length) parts.push({ text: `  ${c.missing.length} missing`, tone: 'warn' });
  if (c.supportOld) parts.push({ text: `  ${c.supportOld} out of date`, tone: 'warn' });
  if (c.contradictions) parts.push({ text: `  ${c.contradictions} conflicts`, tone: 'bad' });
  children.push(kit.row([kit.line(parts, { wrap: 'truncate-end' }), kit.button('open-workbench', 'Open', 'o', () => controls.workbench(state.selected), { plain: true })], { gap: 2, wrap: true }));
  return ui.Box({ flexDirection: 'column', children });
}
