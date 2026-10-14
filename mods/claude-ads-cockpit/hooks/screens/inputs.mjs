// Inputs: what the steps asked for, and a checklist of the files registered for this run.
import { platformName, say, shortHash } from '../lexicon.mjs';
import { counts } from '../model.mjs';
import { toneOf } from '../theme.mjs';

const MATCH_NOTE = {
  text: 'Files whose ID or path appears in that request are shown first. A text match is not a recorded link.',
  platform: 'Files for the same platform are shown first. Nothing links this request to a specific file.',
  none: 'No registered file matches. Register the requested file, then check it here.',
};

export function inputs(kit, ctx) {
  const { snapshot, state, context } = ctx;
  const c = counts(snapshot);
  const can = op => snapshot.permitted_actions.includes(op);
  const off = state.busy;
  const out = [];
  const selectedInput = input => context?.kind === 'inputs' && context.inputIds.includes(input.id);

  if (context?.kind === 'inputs') {
    out.push(kit.card([
      kit.line([{ text: '▲ ', tone: 'warn' }, { text: 'Looking for', bold: true }, `  ${context.missingInput}`]),
      kit.hint(MATCH_NOTE[context.match] ?? MATCH_NOTE.none),
    ], { tone: 'warn', key: 'input-context' }));
  } else if (c.missing.length) {
    out.push(kit.card([
      kit.t('Steps are waiting for:', { bold: true }),
      ...c.missing.map(m => kit.item('▲', `${platformName(m.platform)}: ${m.text}`)),
    ], { tone: 'warn', key: 'input-needs' }));
  }

  if (!snapshot.inputs.length) {
    out.push(kit.section([kit.t('No input files are registered for this run.', { bold: true }), kit.hint('Files that are not registered are never opened.')]));
  } else {
    const ordered = [...snapshot.inputs.filter(selectedInput), ...snapshot.inputs.filter(i => !selectedInput(i))];
    out.push(kit.section([
      kit.heading('Input files', `${snapshot.inputs.length} registered`),
      ...ordered.flatMap(input => {
        const s = say('input', input.validation);
        const head = kit.row([
          kit.line([{ text: `${selectedInput(input) ? '▸ ' : ''}${toneOf(s.tone).mark} `, tone: s.tone }, { text: input.id, bold: true }, { text: `  ${s.word}`, tone: s.tone }]),
          can('validate-input') ? kit.button(`validate-input-${input.id}`, 'Check', undefined, () => ctx.action('validate-input', input.id), { off }) : kit.hint('Checks unavailable'),
        ], { gap: 2, wrap: true });
        const meta = [kit.hint(`${input.path}  ·  ${input.kind}  ·  ${input.contract || 'no declared contract'}  ·  ${input.platform ? platformName(input.platform) : 'shared'}${state.details ? `  ·  sha ${shortHash(input.sha256)}` : ''}`, { wrap: 'truncate-end' }), ...input.details.map(d => kit.hint(d))];
        return [head, kit.indent(meta)];
      }),
    ]));
  }
  if (can('validate-run')) out.push(kit.section([kit.row([kit.button('validate-run', 'Check whole run', 'k', () => ctx.action('validate-run'), { off })])]));
  out.push(kit.section([kit.hint('A valid structure does not prove account facts, platform eligibility, consent or approval.')]));
  return out;
}
