// Reports: make a report, see what was saved, and the history of local actions.
import { bytes, say, shortHash, when } from '../lexicon.mjs';
import { toneOf } from '../theme.mjs';
import { receiptStrip } from '../svg.mjs';

const fileName = path => String(path).split('/').pop();

export function reports(kit, ctx) {
  const { snapshot, state } = ctx;
  const can = op => snapshot.permitted_actions.includes(op);
  const off = state.busy;
  const out = [];
  if (can('render-report')) {
    out.push(kit.row([
      kit.button('render-markdown', 'Markdown', 'm', () => ctx.action('render-report', null, 'markdown'), { off, primary: true }),
      kit.button('render-html', 'HTML', 'l', () => ctx.action('render-report', null, 'html'), { off, primary: true }),
      kit.button('render-pdf', 'PDF', 'p', () => ctx.action('render-report', null, 'pdf'), { off }),
      ...(can('validate-run') ? [kit.button('validate-run', 'Check run', 'k', () => ctx.action('validate-run'), { off })] : []),
    ], { gap: 2, wrap: true }));
    out.push(kit.hint('Make a report from the validated run data. PDF needs an optional renderer.'));
  }
  const receiptCard = (receipt, { latest = false } = {}) => {
    const outcome = say('outcome', receipt.outcome);
    const body = [
      kit.line([{ text: `${toneOf(outcome.tone).mark} `, tone: outcome.tone }, { text: say('operation', receipt.operation).word, bold: true }, { text: `  ${outcome.word}`, tone: outcome.tone }, { text: `  ${when(receipt.finished_at)}`, dim: true }]),
      ...receipt.outputs.map(o => kit.line([{ text: '  saved ', dim: true }, fileName(o.path), { text: `  ${bytes(o.size)}${state.details ? `  sha ${shortHash(o.sha256)}` : ''}`, dim: true }])),
      ...receipt.diagnostics.map(d => kit.hint(`  ${d}`)),
    ];
    if (state.details) body.push(kit.hint(`  ran ${when(receipt.started_at)}; input ${shortHash(receipt.input_fingerprint)}, policy ${shortHash(receipt.policy_fingerprint)}`));
    return latest ? kit.card(body, { tone: outcome.tone, key: 'latest-receipt' }) : kit.col(body);
  };
  if (state.receipt) out.push(kit.section([kit.heading('Just now'), receiptCard(state.receipt, { latest: true })]));
  if (snapshot.artifacts.length) {
    out.push(kit.section([
      kit.heading('Saved files', `${snapshot.artifacts.length}`),
      kit.table([{ head: 'File', grow: true }, { head: 'Kind', max: 14 }, { head: 'Size', max: 8, align: 'right' }], snapshot.artifacts.map(a => [{ text: a.path, bold: true }, a.kind, bytes(a.size)])),
    ]));
  }
  const strip = kit.ui.Svg ? receiptStrip(kit.ui.Svg, snapshot.receipts.map(r => r.receipt.outcome)) : null;
  out.push(kit.section([
    kit.heading('History', snapshot.receipts.length ? `${snapshot.receipts.length} saved` : undefined),
    ...(strip ? [strip] : []),
    ...(snapshot.receipts.length ? snapshot.receipts.map(r => receiptCard(r.receipt)) : [kit.t('No reports or checks yet.', { dimColor: true }), kit.hint('Each one you run leaves a receipt here, even a failed one.')]),
  ]));
  out.push(kit.section([kit.hint('Reports are made from validated run data. They do not prove advertising results.')]));
  return out;
}
