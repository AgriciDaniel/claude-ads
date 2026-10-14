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
  'A full synthetic audit of four platforms. Each square is one check: green passed, red failed, amber unknown. Press Next (n) to follow one problem from start to finish.',
  'Google Ads is stuck: it needs a keyword file that is not there yet. The card says what it needs.',
  'These are the registered files. The one the step asked for is registered but its file is missing, so nothing can be checked.',
  'Here is the corrected file. Press the Check button beside it (or k to check the whole run) and read the result.',
  'This check rests on a source that has expired. Look for "Out of date".',
  'One step failed, so the run is only partly done. The finished work is still shown.',
  'Compare the earlier run with the corrected one. Nothing is claimed as fixed.',
  'Make a report. A receipt is saved for every attempt, even one that fails.',
];

function tabBar(kit, state, c, controls) {
  const badge = { Run: '', Evidence: c ? ` ${c.findings}` : '', Inputs: c && (c.missing.length || c.invalidInputs) ? ' ▲' : '', Compare: '', Reports: c && c.receipts ? ` ${c.receipts}` : '' };
  return kit.row(TABS.map((tab, index) => kit.button(`tab-${tab.toLowerCase()}`, `${tab === state.tab ? '▸ ' : ''}${LABEL[tab]}${badge[tab]}`, String(index + 1), () => controls.tab(tab), { plain: true })), { gap: 2, wrap: true });
}

function demoStrip(kit, state) {
  const demo = state.demo;
  const step = demo.steps[demo.index];
  return kit.card([
    kit.row([kit.t('PRACTICE DATA', { bold: true, color: 'warning' }), kit.t(`Step ${demo.index + 1} of ${demo.steps.length}`, { dimColor: true }), kit.dots(demo.index, demo.steps.length)], { gap: 2, wrap: true }),
    kit.t(step.title, { bold: true }),
    ...(demo.steps.length === COACH.length ? [kit.t(COACH[demo.index])] : []),
    kit.hint('Made-up data. It says nothing about a real account.'),
  ], { tone: 'info', key: 'demo-strip' });
}

function footer(kit, state, controls, isFocused) {
  const off = state.busy;
  const demo = state.demo;
  const items = [];
  if (demo) {
    items.push(
      kit.button('demo-back', 'Back', 'b', () => controls.step(-1), { plain: true, off: off || demo.index === 0 }),
      kit.button('demo-next', 'Next', 'n', () => controls.step(1), { primary: true, off: off || demo.index === demo.steps.length - 1 }),
      kit.button('demo-reset', 'Reset', 'z', controls.reset, { plain: true, off }),
      kit.button('demo-exit', 'Exit demo', 'q', controls.chooser, { plain: true }),
    );
  }
  items.push(
    kit.button('refresh', 'Refresh', 'r', controls.refresh, { plain: true, off: off || !state.selected }),
    ...(state.selected ? [kit.button('chooser', 'Runs', 'c', controls.chooser, { plain: true, off })] : []),
    ...(controls.details && state.selected ? [kit.button('details', state.details ? 'Fewer details' : 'Details', 'd', controls.details, { plain: true })] : []),
    kit.button('hide', 'Hide', 'h', controls.hide, { plain: true }),
  );
  return kit.section([kit.rule(), kit.row(items, { gap: 2, wrap: true }), ...(isFocused ? [] : [kit.hint('ctrl+x tab to use the keys')])]);
}

export function drawPane(ui, state, controls, width = 60, isFocused = true) {
  const kit = makeKit(ui, width);
  const snapshot = state.snapshot;
  const c = snapshot ? counts(snapshot) : null;
  const subject = snapshot ? { runId: state.selected, fingerprint: snapshot.fingerprint, policyFingerprint: snapshot.policy_fingerprint } : null;
  const ctx = {
    state, snapshot, context: state.context, controls,
    action: (operation, inputId = null, format = 'markdown') => controls.action(operation, inputId, format, subject),
    go: (tab, target) => (target ? controls.navigate(tab, target, state.selected, snapshot.fingerprint) : controls.tab(tab)),
  };
  const out = [];
  out.push(kit.line([{ text: ' CLAUDE ADS ', bold: true, inverse: true, color: 'claude', raw: true }, ...(state.selected ? [{ text: `  ${state.selected}`, dim: true }] : []), ...(state.busy ? [{ text: '  working…', tone: 'info' }] : [])], { wrap: 'truncate-end' }));
  if (state.demo) out.push(kit.section([demoStrip(kit, state)]));
  if (state.error) out.push(kit.section([kit.card([kit.line([{ text: '✗ ', tone: 'bad' }, state.error])], { tone: 'bad', key: 'error' })]));
  if (!state.selected) {
    out.push(kit.section(chooser(kit, ctx)));
    out.push(footer(kit, state, controls, isFocused));
    return kit.col(out);
  }
  out.push(kit.section([tabBar(kit, state, c, controls)]));
  if (!snapshot) {
    out.push(kit.section([kit.t('No trusted data for this run yet.', { bold: true }), kit.hint('Press r to refresh, or choose another run.')]));
  } else {
    if (state.receipt && state.tab !== 'Reports') {
      const outcome = say('outcome', state.receipt.outcome);
      out.push(kit.section([kit.card([kit.line([{ text: `${toneOf(outcome.tone).mark} `, tone: outcome.tone }, { text: say('operation', state.receipt.operation).word, bold: true }, { text: `  ${outcome.word}`, tone: outcome.tone }]), ...state.receipt.diagnostics.map(d => kit.hint(d))], { tone: outcome.tone, key: 'receipt-note' })]));
    }
    out.push(kit.section(SCREENS[state.tab](kit, ctx)));
  }
  out.push(footer(kit, state, controls, isFocused));
  return kit.col(out);
}
