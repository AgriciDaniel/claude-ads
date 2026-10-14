// Chooser: no run selected yet. Pick a registered run, or try the practice demo.
import { say } from '../lexicon.mjs';
import { toneOf } from '../theme.mjs';

export function chooser(kit, ctx) {
  const { state, controls } = ctx;
  const out = [];
  const doctor = state.doctor;
  out.push(kit.card([
    kit.t('Choose a run', { bold: true }),
    kit.t('A run is a saved Claude Ads audit on this computer. Nothing here changes an ad account.'),
    ...(doctor ? [kit.line([{ text: `${toneOf(doctor.status === 'ok' ? 'ok' : 'bad').mark} `, tone: doctor.status === 'ok' ? 'ok' : 'bad' }, { text: `Engine ${doctor.core_version} · scoring policy ${doctor.status === 'ok' ? 'ready' : 'blocked'}`, dim: true }])] : []),
  ], { tone: 'info', key: 'chooser' }));
  if (doctor) {
    if (!doctor.runs.length) {
      out.push(kit.card([kit.t('No runs found yet', { bold: true }), kit.hint('Set runsRoot to a folder of Claude Ads runs, or try the practice demo below.')], { tone: 'muted', key: 'no-runs' }));
    } else {
      out.push(kit.section([
        kit.heading('Registered runs', `${doctor.runs.length}`),
        ...doctor.runs.slice(0, 100).map((run, i) => {
          const s = say('workflow', run.status);
          return kit.row([kit.button(`run-${run.id}`, run.id, i < 9 ? String(i + 1) : undefined, () => controls.select(run.id), { off: state.busy, plain: true }), kit.t(s.word, kit.toneStyle(s.tone))], { gap: 2, wrap: true });
        }),
      ]));
    }
  }
  if (kit.ui.Input) out.push(kit.section([kit.ui.Input({ key: 'open-run', label: 'Run ID', value: '', placeholder: 'Registered run ID', submitLabel: 'open', onSubmit: value => controls.select(value) })]));
  out.push(kit.section([kit.button('demo', 'Start the practice demo', 'd', controls.demo, { primary: true, off: state.busy }), kit.hint('A short guided tour on made-up data. Nothing real is read.')]));
  return out;
}
