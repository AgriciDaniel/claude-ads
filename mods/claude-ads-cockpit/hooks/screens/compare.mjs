// Compare: this run against a baseline, as a before and after table.
import { platformName, plural, say } from '../lexicon.mjs';
import { toneOf } from '../theme.mjs';

export function compare(kit, ctx) {
  const { snapshot, state } = ctx;
  const comparison = snapshot.comparison;
  const out = [];
  if (!comparison) {
    out.push(kit.card([
      kit.t('Pick a run to compare with', { bold: true }),
      kit.t('Compare shows what changed between two runs of the same account and platform.'),
    ], { tone: 'info', key: 'compare-empty' }));
  } else {
    const tone = comparison.comparable ? 'ok' : 'warn';
    out.push(kit.card([
      kit.line([{ text: `${toneOf(tone).mark} `, tone }, { text: `Compared with ${comparison.baseline_run_id}`, bold: true }]),
      kit.t(comparison.comparable ? 'These runs can be compared. Differences are listed below.' : 'These runs are not directly comparable. Read the differences first.'),
      ...comparison.differences.map(d => kit.line([{ text: '· ', dim: true }, d])),
    ], { tone, key: 'compare-head' }));
    if (comparison.findings.length) {
      const word = status => (status === null ? '-' : say('finding', status).word);
      out.push(kit.section([
        kit.heading('What changed', plural(comparison.findings.length, 'check')),
        kit.table([{ head: 'Check', grow: true }, { head: 'Before', max: 12 }, { head: 'After', max: 12 }, ...(kit.narrow ? [] : [{ head: 'Change', max: 14 }])], comparison.findings.map(item => {
          const change = say('change', item.change);
          return [
            { text: `${platformName(item.platform)} ${item.control_id}`, bold: true },
            { text: word(item.baseline_status), tone: item.baseline_status ? say('finding', item.baseline_status).tone : 'muted' },
            { text: `→ ${word(item.current_status)}`, tone: item.current_status ? say('finding', item.current_status).tone : 'muted' },
            ...(kit.narrow ? [] : [{ text: change.word, tone: change.tone }]),
          ];
        })),
      ]));
    }
  }
  if (kit.ui.Input && !state.demo) out.push(kit.section([kit.ui.Input({ key: 'baseline', label: 'Baseline run', value: state.baseline, placeholder: 'Registered run ID', submitLabel: 'compare', onSubmit: ctx.controls.baseline })]));
  out.push(kit.section([kit.hint('A check that is absent now is not counted as fixed. Differences are observations, not proof of improvement.')]));
  return out;
}
