// Chooser: no run selected yet. Pick a registered run, or try the practice demo. Drawn to fit ctx.budget lines.
import { say } from '../lexicon.mjs';
import { pack, pageList } from '../pack.mjs';
import { toneOf } from '../theme.mjs';

export function chooser(kit, ctx) {
  const { state, controls, budget } = ctx;
  const doctor = state.doctor;
  const blocks = [];
  blocks.push({
    pri: 0, need: 2, want: 3,
    build: n => [
      kit.col([
        kit.t('Choose a run', { bold: true }),
        ...(n >= 3 || !doctor ? kit.clamp('A run is a saved Claude Ads audit on this computer. Nothing here changes an ad account.', 1, { dimColor: true }) : []),
      ], { key: 'chooser' }),
      ...(doctor ? [kit.line([{ text: `${toneOf(doctor.status === 'ok' ? 'ok' : 'bad').mark} `, tone: doctor.status === 'ok' ? 'ok' : 'bad' }, { text: `Engine ${doctor.core_version} · scoring policy ${doctor.status === 'ok' ? 'ready' : 'blocked'}`, dim: true }], { gap: 1, wrap: 'truncate-end' })] : []),
    ].slice(0, 3),
  });
  blocks.push({ pri: 1, need: 2, want: 2, build: () => [kit.button('demo', 'Start the practice demo', 'd', controls.demo, { primary: true, off: state.busy }), kit.hint('A short guided tour on made-up data. Nothing real is read.', { wrap: 'truncate-end' })] });
  if (doctor) {
    if (!doctor.runs.length) {
      blocks.push({ pri: 2, need: 2, want: 2, build: () => [kit.t('No runs found yet', { bold: true }), kit.hint('Set runsRoot to a folder of Claude Ads runs, or try the practice demo.', { wrap: 'truncate-end' })] });
    } else {
      const runs = doctor.runs.slice(0, 100);
      blocks.push({
        pri: 2, need: 2, want: 1 + runs.length + 1,
        build: n => {
          const { per, pages, pagerLine } = pageList(runs.length, n - 1);
          const page = Math.min(state.page, pages - 1);
          const pager = kit.pager(page, pages, { back: () => controls.page(-1), next: () => controls.page(1) });
          return [
            kit.heading('Registered runs', `${doctor.runs.length}`),
            ...runs.slice(page * per, (page + 1) * per).map((run, i) => {
              const s = say('workflow', run.status);
              const n9 = page * per + i;
              return kit.row([kit.button(`run-${run.id}`, run.id, n9 < 9 ? String(n9 + 1) : undefined, () => controls.select(run.id), { off: state.busy, plain: true }), kit.t(s.word, kit.toneStyle(s.tone))], { gap: 2 });
            }),
            ...(pager && pagerLine ? [pager] : []),
          ];
        },
      });
    }
  }
  if (kit.ui.Input && budget >= 14) blocks.push({ pri: 4, need: 3, want: 3, build: () => [kit.ui.Input({ key: 'open-run', label: 'Run ID', value: '', placeholder: 'Registered run ID', submitLabel: 'open', onSubmit: value => controls.select(value) })] });
  return pack(kit, budget, blocks, { gap: budget >= 22 });
}
