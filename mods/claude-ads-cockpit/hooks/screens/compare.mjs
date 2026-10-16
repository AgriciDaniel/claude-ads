// Compare: this run against a baseline, as a before and after table. Drawn to fit ctx.budget lines.
import { platformName, plural, say } from '../lexicon.mjs';
import { pack, pageList } from '../pack.mjs';
import { toneOf } from '../theme.mjs';
import { oneLine } from '../wire.mjs';

export function compare(kit, ctx) {
  const { snapshot, state, budget } = ctx;
  const comparison = snapshot.comparison;
  const room = kit.width - 4;
  const blocks = [];
  // The baseline box is the only way to pick a run to compare with, so it always keeps its room when drawn.
  const canInput = kit.ui.Input && !state.demo;
  const inputBlock = canInput ? { pri: 0, need: 3, want: 3, build: () => [kit.ui.Input({ key: 'baseline', label: 'Baseline run', value: state.baseline, placeholder: 'Registered run ID', submitLabel: 'compare', onSubmit: ctx.controls.baseline })] } : null;
  if (!comparison) {
    blocks.push({
      pri: 1, need: 2, want: 3,
      build: () => [kit.col([kit.t('Pick a run to compare with', { bold: true }), ...kit.clamp('Compare shows what changed between two runs of the same account and platform.', 2)], { key: 'compare-empty' })],
    });
  } else {
    const tone = comparison.comparable ? 'ok' : 'warn';
    // The engine lists one difference per check whose evidence changed. Those are counted, not listed;
    // the table below already names every check that changed.
    const evidenceDiffs = comparison.differences.filter(d => d.startsWith('Evidence differs'));
    const general = comparison.differences.filter(d => !d.startsWith('Evidence differs'));
    blocks.push({
      pri: 1, need: 2, want: 2 + Math.min(4, general.length) + 1,
      build: n => {
        const list = [
          ...general.map(d => kit.line([{ text: '· ', dim: true }, oneLine(d, room - 2)], { gap: 0, wrap: 'truncate-end' })),
          ...(evidenceDiffs.length ? [kit.hint(`· ${plural(evidenceDiffs.length, 'check')} with different evidence`)] : []),
        ];
        return [
          kit.line([{ text: `${toneOf(tone).mark} `, tone }, { text: `Compared with ${comparison.baseline_run_id}`, bold: true }, { text: comparison.comparable ? 'can be compared' : 'not directly comparable, read the differences first', dim: true }], { gap: 2, wrap: 'truncate-end' }),
          ...list.slice(0, n - 1),
        ];
      },
    });
    if (comparison.findings.length) {
      const word = status => (status === null ? '-' : say('finding', status).word);
      const rowsFor = list => list.map(item => {
        const change = say('change', item.change);
        return [
          { text: `${platformName(item.platform)} ${item.control_id}`, bold: true },
          { text: word(item.baseline_status), tone: item.baseline_status ? say('finding', item.baseline_status).tone : 'muted' },
          { text: `→ ${word(item.current_status)}`, tone: item.current_status ? say('finding', item.current_status).tone : 'muted' },
          ...(kit.narrow ? [] : [{ text: change.word, tone: change.tone }]),
        ];
      });
      blocks.push({
        pri: 2, need: 3, want: 2 + comparison.findings.length,
        build: n => {
          const { per, pages, pagerLine } = pageList(comparison.findings.length, n - 2);
          const page = Math.min(state.page, pages - 1);
          const pager = kit.pager(page, pages, { back: () => ctx.controls.page(-1), next: () => ctx.controls.page(1) });
          return [
            kit.heading('What changed', plural(comparison.findings.length, 'check')),
            kit.table([{ head: 'Check', grow: true }, { head: 'Before', max: 16 }, { head: 'After', max: 16 }, ...(kit.narrow ? [] : [{ head: 'Change', max: 14 }])], rowsFor(comparison.findings.slice(page * per, (page + 1) * per))),
            ...(pager && pagerLine ? [pager] : []),
          ];
        },
      });
    }
  }
  if (inputBlock && budget >= 12) blocks.push(inputBlock);
  blocks.push({ pri: 5, need: 0, want: 1, build: () => [kit.hint('A check that is absent now is not counted as fixed. Differences are observations, not proof of improvement.', { wrap: 'truncate-end' })] });
  return pack(kit, budget, blocks, { gap: budget >= 22 });
}
