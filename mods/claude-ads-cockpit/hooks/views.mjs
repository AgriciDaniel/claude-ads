// The pane shell: header, practice-demo strip, tabs, one screen, then the footer.
// Pure. It reads cached state and calls the same controls the controller has always exposed.
import { makeKit } from './kit.mjs';
import { say } from './lexicon.mjs';
import { counts } from './model.mjs';
import { toneOf } from './theme.mjs';
import { TABS } from './wire.mjs';
import { chooser } from './screens/chooser.mjs';
import { compare } from './screens/compare.mjs';
import { findings } from './screens/findings.mjs';
import { inputs } from './screens/inputs.mjs';
import { overview } from './screens/overview.mjs';
import { reports } from './screens/reports.mjs';
export { drawBand } from './band.mjs';

const LABEL = { Run: 'Overview', Evidence: 'Checks', Inputs: 'Inputs', Compare: 'Compare', Reports: 'Reports' };
const SCREENS = { Run: overview, Evidence: findings, Inputs: inputs, Compare: compare, Reports: reports };
const COACH = [
  'Press Next (n) to follow one problem from start to finish.',
  'The card names the file it needs. Press Next (n) to see it.',
  'Registered files, with a red cross where one is missing.',
  'Press the Check button beside it (or k to check the whole run) and read the result.',
  'Look for "Out of date" beside the check.',
  'The finished work is still shown. Nothing is hidden.',
  'Only what the evidence says. Nothing is claimed as fixed.',
  'A receipt is saved for every attempt, even one that fails.',
];

// One plain sentence per step, shown large. The longer line beneath says what to look at.
const HEADLINES = [
  'A whole audit at a glance',
  'Google Ads is stuck: it needs a file',
  'The file it needs is missing',
  'The corrected file is in. Check it.',
  'One check rests on an expired source',
  'One step failed, the rest still shows',
  'Before and after, nothing claimed as fixed',
  'Make a report and keep a receipt',
];

// Lines a row of plain buttons takes at this width ("1: Label" each, a gap between them).
const rowLines = (labels, gap, width) => {
  let lines = 1, used = 0;
  for (const label of labels) {
    const w = label.length + 3;
    if (used && used + gap + w > width) { lines++; used = w; } else used += (used ? gap : 0) + w;
  }
  return lines;
};

function tabLabels(state, c) {
  const badge = { Run: '', Evidence: c ? ` ${c.findings}` : '', Inputs: c && (c.missing.length || c.invalidInputs) ? ' ▲' : '', Compare: '', Reports: c && c.receipts ? ` ${c.receipts}` : '' };
  return TABS.map(tab => `${tab === state.tab ? '▸ ' : ''}${LABEL[tab]}${badge[tab]}`);
}

function tabBar(kit, state, c, controls) {
  const labels = tabLabels(state, c);
  return kit.row(TABS.map((tab, index) => kit.button(`tab-${tab.toLowerCase()}`, labels[index], String(index + 1), () => controls.tab(tab), { plain: true })), { gap: 2, wrap: true });
}

// First line of the practice strip. The disclosure is worded to fit; it is never dropped.
function demoHeader(kit, demo) {
  const step = `Step ${demo.index + 1} of ${demo.steps.length}`;
  const fixed = 'PRACTICE DATA'.length + step.length + (demo.steps.length * 2 - 1) + 6;
  const note = ['Made-up data, not a real account', 'Made-up data'].find(text => fixed + text.length <= kit.width) ?? 'Made-up';
  return kit.row([
    kit.line([{ text: 'PRACTICE DATA', bold: true, color: 'warning' }, { text: step, dim: true }], { gap: 2, wrap: 'truncate-end' }),
    kit.dots(demo.index, demo.steps.length),
    kit.t(note, { dimColor: true, wrap: 'truncate-end' }),
  ], { gap: 2 });
}

// The practice strip: what this step is, and what to look at. Height is fixed by `coachLines`.
function demoStrip(kit, state, coachLines) {
  const demo = state.demo;
  const step = demo.steps[demo.index];
  return [
    demoHeader(kit, demo),
    kit.t(demo.steps.length === HEADLINES.length ? HEADLINES[demo.index] : step.title, { bold: true, wrap: 'truncate-end', ...kit.toneStyle('info') }),
    ...(coachLines > 0 && demo.steps.length === COACH.length ? kit.clamp(COACH[demo.index], coachLines, { dimColor: true }) : []),
  ];
}

function demoControls(kit, state, controls) {
  const off = state.busy;
  const demo = state.demo;
  return kit.row([
    kit.button('demo-back', 'Back', 'b', () => controls.step(-1), { plain: true, off: off || demo.index === 0 }),
    kit.button('demo-next', 'Next', 'n', () => controls.step(1), { primary: true, off: off || demo.index === demo.steps.length - 1 }),
    kit.button('demo-reset', 'Reset', 'z', controls.reset, { plain: true, off }),
    kit.button('demo-exit', 'Exit demo', 'q', controls.chooser, { plain: true }),
  ], { gap: 2 });
}

function footer(kit, state, controls) {
  const off = state.busy;
  return kit.row([
    kit.button('refresh', 'Refresh', 'r', controls.refresh, { plain: true, off: off || !state.selected }),
    ...(state.selected ? [kit.button('chooser', 'Runs', 'c', controls.chooser, { plain: true, off })] : []),
    ...(controls.details && state.selected ? [kit.button('details', state.details ? 'Fewer details' : 'Details', 'd', controls.details, { plain: true })] : []),
    kit.button('hide', 'Hide', 'h', controls.hide, { plain: true }),
  ], { gap: 2 });
}

// The pane is drawn to fit `rows` lines (the host's body height), so no screen needs to scroll.
// Chrome (title, tabs, practice strip, notices, keys) is counted first; the rest is the screen's budget.
export const MIN_ROWS = 14;
export function drawPane(ui, state, controls, width = 60, isFocused = true, rows = 34) {
  const total = Math.max(MIN_ROWS, Math.floor(Number.isFinite(rows) ? rows : 34));
  const kit = makeKit(ui, width, total);
  const snapshot = state.snapshot;
  const c = snapshot ? counts(snapshot) : null;
  const subject = snapshot ? { runId: state.selected, fingerprint: snapshot.fingerprint, policyFingerprint: snapshot.policy_fingerprint } : null;
  const roomy = total >= 28;
  let wrapped = 0;
  const top = [];
  const brand = kit.line([{ text: ' CLAUDE ADS ', bold: true, inverse: true, color: 'claude', raw: true }, ...(state.selected && !state.demo ? [{ text: `  ${state.selected}`, dim: true }] : []), ...(state.busy ? [{ text: '  working…', tone: 'info' }] : []), ...(isFocused ? [] : [{ text: '  ctrl+x tab to use the keys', dim: true }])], { wrap: 'truncate-end' });
  // In the practice demo the run id means nothing, so the title and the tabs share one line when they fit.
  const tabWidth = state.selected ? tabLabels(state, c).reduce((a, label) => a + label.length + 3, 0) + 2 * (TABS.length - 1) : 0;
  const merged = Boolean(state.demo && state.selected && isFocused && 12 + 2 + tabWidth <= width);
  top.push(merged ? kit.row([brand, tabBar(kit, state, c, controls)], { gap: 2 }) : brand);
  const bottom = [];
  if (state.demo) {
    const coach = total >= 36 ? 3 : total >= 20 ? 2 : total >= 17 ? 1 : 0;
    top.push(...demoStrip(kit, state, coach));
    bottom.push(demoControls(kit, state, controls));
  }
  if (state.error) {
    // A setup or engine message is shown whole, never cut. Its lines count against the budget.
    top.push(kit.col([kit.row([kit.t('✗', kit.toneStyle('bad')), kit.t(state.error)], { gap: 1 })], { key: 'error' }));
    wrapped += kit.countLines(state.error, 2) - 1;
  }
  if (state.selected && !merged) {
    top.push(tabBar(kit, state, c, controls));
    // At a narrow width the tab row wraps; its extra lines count against the budget.
    wrapped += rowLines(tabLabels(state, c), 2, width) - 1;
  }
  if (state.selected && snapshot && state.receipt && state.tab !== 'Reports') {
    const outcome = say('outcome', state.receipt.outcome);
    top.push(kit.line([{ text: `${toneOf(outcome.tone).mark} `, tone: outcome.tone }, { text: say('operation', state.receipt.operation).word, bold: true }, { text: outcome.word, tone: outcome.tone }, ...(state.receipt.diagnostics[0] ? [{ text: state.receipt.diagnostics[0], dim: true }] : [])], { gap: 2, wrap: 'truncate-end' }));
  }
  bottom.push(footer(kit, state, controls));
  const budget = Math.max(4, total - top.length - wrapped - bottom.length - (roomy ? 1 : 0));
  const ctx = {
    state, snapshot, context: state.context, controls, budget,
    action: (operation, inputId = null, format = 'markdown') => controls.action(operation, inputId, format, subject),
    go: (tab, target) => (target ? controls.navigate(tab, target, state.selected, snapshot.fingerprint) : controls.tab(tab)),
  };
  let body;
  if (!state.selected) body = chooser(kit, ctx);
  else if (!snapshot) body = [kit.t('No trusted data for this run yet.', { bold: true }), kit.hint('Press r to refresh, or choose another run.')];
  else body = SCREENS[state.tab](kit, ctx);
  return kit.col([...top, ...(roomy ? [kit.t(' ')] : []), ...body, ...bottom]);
}
