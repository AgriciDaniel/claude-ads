// Inputs: what the steps asked for, and the files registered for this run. Drawn to fit ctx.budget lines.
import { platformName, say, shortHash } from '../lexicon.mjs';
import { counts } from '../model.mjs';
import { fitList, pack, pageList } from '../pack.mjs';
import { toneOf } from '../theme.mjs';
import { oneLine } from '../wire.mjs';

const MATCH_NOTE = {
  text: 'Files whose ID or path appears in that request are shown first. A text match is not a recorded link.',
  platform: 'Files for the same platform are shown first. Nothing links this request to a specific file.',
  none: 'No registered file matches. Register the requested file, then check it here.',
};

export function inputs(kit, ctx) {
  const { snapshot, state, context, budget } = ctx;
  const c = counts(snapshot);
  const can = op => snapshot.permitted_actions.includes(op);
  const off = state.busy;
  const room = kit.width - 4;
  const selectedInput = input => context?.kind === 'inputs' && context.inputIds.includes(input.id);
  const blocks = [];

  // What the steps are waiting for, or what the person came here to supply.
  if (context?.kind === 'inputs') {
    blocks.push({
      pri: 0, need: 2, want: 3,
      build: n => [
        kit.line([{ text: '▲ ', tone: 'warn' }, { text: 'Looking for', bold: true }, oneLine(context.missingInput, room - 14)], { gap: 1, wrap: 'truncate-end' }),
        ...kit.clamp(MATCH_NOTE[context.match] ?? MATCH_NOTE.none, n - 1, { dimColor: true }),
        ...(n >= 3 ? [kit.button('input-context-back', 'Back to all inputs', undefined, () => ctx.controls.clearContext(), { plain: true })] : []),
      ].slice(0, n),
    });
  } else if (c.missing.length) {
    blocks.push({
      pri: 1, need: 2, want: 1 + c.missing.length,
      build: n => {
        const { shown: count, more } = fitList(c.missing.length, n - 1);
        const shown = c.missing.slice(0, count);
        return [
          kit.heading('Steps are waiting for', `${c.missing.length} items`),
          ...shown.map(m => kit.line([{ text: '▲ ', tone: 'warn' }, oneLine(`${platformName(m.platform)}: ${m.text}`, room)], { gap: 1, wrap: 'truncate-end' })),
          ...(more ? [kit.hint(`+ ${c.missing.length - count} more`)] : []),
        ];
      },
    });
  }

  // The registered files, one or two lines each, paged.
  if (!snapshot.inputs.length) {
    blocks.push({ pri: 0, need: 2, want: 2, build: () => [kit.t('No input files are registered for this run.', { bold: true }), kit.hint('Files that are not registered are never opened.')] });
  } else {
    const ordered = [...snapshot.inputs.filter(selectedInput), ...snapshot.inputs.filter(i => !selectedInput(i))];
    blocks.push({
      pri: 2, need: 3, want: 1 + ordered.length * (state.details ? 2 : 1) + 1,
      build: n => {
        // Path, kind and contract are in details; by default each file is one line.
        const lines = state.details && n >= 1 + ordered.length * 2 ? 2 : 1;
        const { per: fits, pages: pageCount, pagerLine } = pageList(ordered.length * lines, n - 1);
        const per = Math.max(1, Math.floor(fits / lines));
        const pages = pageCount > 1 ? Math.ceil(ordered.length / per) : 1;
        const page = Math.min(state.page, pages - 1);
        const pager = kit.pager(page, pages, { back: () => ctx.controls.page(-1), next: () => ctx.controls.page(1) });
        return [
          kit.heading('Input files', `${snapshot.inputs.length} registered`),
          ...ordered.slice(page * per, (page + 1) * per).flatMap(input => {
            const s = say('input', input.validation);
            const head = kit.row([
              kit.line([{ text: `${selectedInput(input) ? '▸ ' : ''}${toneOf(s.tone).mark} `, tone: s.tone }, { text: input.id, bold: true }, { text: s.word, tone: s.tone }], { gap: 2, wrap: 'truncate-end' }),
              can('validate-input') ? kit.button(`validate-input-${input.id}`, 'Check', undefined, () => ctx.action('validate-input', input.id), { off }) : kit.hint('Checks unavailable'),
            ], { gap: 2 });
            const meta = kit.hint(`  ${input.path}  ·  ${input.kind}  ·  ${input.contract || 'no declared contract'}  ·  ${input.platform ? platformName(input.platform) : 'shared'}${state.details ? `  ·  sha ${shortHash(input.sha256)}` : ''}`, { wrap: 'truncate-end' });
            return lines === 2 ? [head, meta] : [head];
          }),
          ...(pager && pagerLine ? [pager] : []),
        ];
      },
    });
  }
  if (can('validate-run')) blocks.push({ pri: 1, need: 1, want: 1, build: () => [kit.row([kit.button('validate-run', 'Check whole run', 'k', () => ctx.action('validate-run'), { off })])] });
  blocks.push({ pri: 5, need: 0, want: 1, build: () => [kit.hint('A valid structure does not prove account facts, platform eligibility, consent or approval.', { wrap: 'truncate-end' })] });
  return pack(kit, budget, blocks, { gap: budget >= 24 });
}
