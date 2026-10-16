// Reports: make a report, see what was saved, and the history of local actions. Drawn to fit ctx.budget lines.
import { bytes, say, shortHash, when } from '../lexicon.mjs';
import { fitList, pack, pageList } from '../pack.mjs';
import { toneOf } from '../theme.mjs';
import { receiptStrip } from '../svg.mjs';

const fileName = path => String(path).split('/').pop();

export function reports(kit, ctx) {
  const { snapshot, state, budget } = ctx;
  const can = op => snapshot.permitted_actions.includes(op);
  const off = state.busy;
  const blocks = [];
  if (can('render-report')) {
    // Four framed buttons are about 64 columns wide; on a narrower pane they wrap onto a second line.
    const buttonLines = kit.width < 66 ? 2 : 1;
    blocks.push({
      pri: 0, need: buttonLines, want: buttonLines + 1,
      build: n => [kit.row([
        kit.button('render-markdown', 'Markdown', 'm', () => ctx.action('render-report', null, 'markdown'), { off, primary: true }),
        kit.button('render-html', 'HTML', 'l', () => ctx.action('render-report', null, 'html'), { off, primary: true }),
        kit.button('render-pdf', 'PDF', 'p', () => ctx.action('render-report', null, 'pdf'), { off }),
        ...(can('validate-run') ? [kit.button('validate-run', 'Check run', 'k', () => ctx.action('validate-run'), { off })] : []),
      ], { gap: 2, wrap: true }), ...(n > buttonLines ? [kit.hint('Make a report from the validated run data. PDF needs an optional renderer.', { wrap: 'truncate-end' })] : [])],
    });
  }
  // One receipt, one line: what ran, how it ended, when, and what it saved.
  const receiptLine = receipt => {
    const outcome = say('outcome', receipt.outcome);
    const saved = receipt.outputs.map(o => ({ text: `${fileName(o.path)} ${bytes(o.size)}${state.details ? ` sha ${shortHash(o.sha256)}` : ''}`, dim: true }));
    const reason = receipt.diagnostics.slice(0, 1).map(d => ({ text: d, dim: receipt.outcome === 'succeeded' }));
    // A failed or blocked attempt leads with its reason, so a narrow pane trims the date, never the reason.
    return kit.line([
      { text: `${toneOf(outcome.tone).mark} `, tone: outcome.tone },
      { text: say('operation', receipt.operation).word, bold: true },
      { text: outcome.word, tone: outcome.tone },
      ...(receipt.outcome === 'succeeded' ? [{ text: when(receipt.finished_at), dim: true }, ...(saved.length ? saved : reason)] : [...reason, { text: when(receipt.finished_at), dim: true }]),
    ], { gap: 2, wrap: 'truncate-end' });
  };
  const latest = state.receipt;
  if (latest) blocks.push({ pri: 1, need: 2, want: 2, build: () => [kit.heading('Just now'), receiptLine(latest)] });

  // Receipts are listed under History; the file list shows reports first and the run's own files after.
  const files = snapshot.artifacts.filter(a => !String(a.path).startsWith('cockpit/receipts/')).sort((a, b) => String(b.path).startsWith('cockpit/reports/') - String(a.path).startsWith('cockpit/reports/'));
  if (files.length) {
    blocks.push({
      pri: 3, need: 2, want: 2 + Math.min(4, files.length) + 1,
      build: n => {
        const { shown: count, more } = fitList(files.length, n - 1);
        const shown = files.slice(0, count);
        return [
          kit.heading('Saved files', `${files.length}`),
          kit.table([{ head: 'File', grow: true }, { head: 'Kind', max: 14 }, { head: 'Size', max: 8, align: 'right' }], shown.map(a => [{ text: a.path, bold: true }, a.kind, bytes(a.size)]), { header: false }),
          ...(more ? [kit.hint(`+ ${files.length - count} more`)] : []),
        ];
      },
    });
  }

  // History: newest receipt first, one line each, paged.
  const history = [...snapshot.receipts].sort((a, b) => String(b.receipt.finished_at).localeCompare(String(a.receipt.finished_at)));
  blocks.push({
    pri: 2, need: 2, want: 1 + history.length * (state.details ? 2 : 1) + 1,
    build: n => {
      if (!history.length) return [kit.heading('History'), kit.hint('No reports or checks yet. Each one you run leaves a receipt here, even a failed one.', { wrap: 'truncate-end' })].slice(0, n);
      // With details on, each receipt gets a second line: when it ran and the fingerprints it was bound to.
      const lines = state.details ? 2 : 1;
      const { per: fits, pages: pageCount, pagerLine } = pageList(history.length * lines, n - 1);
      const per = Math.max(1, Math.floor(fits / lines));
      const pages = pageCount > 1 ? Math.ceil(history.length / per) : 1;
      const page = Math.min(state.page, pages - 1);
      const pager = kit.pager(page, pages, { back: () => ctx.controls.page(-1), next: () => ctx.controls.page(1) });
      return [kit.heading('History', `${history.length} saved`), ...history.slice(page * per, (page + 1) * per).flatMap(r => (state.details ? [receiptLine(r.receipt), kit.hint(`  ran ${when(r.receipt.started_at)}; input ${shortHash(r.receipt.input_fingerprint)}, policy ${shortHash(r.receipt.policy_fingerprint)}`, { wrap: 'truncate-end' })] : [receiptLine(r.receipt)])), ...(pager && pagerLine ? [pager] : [])];
    },
  });
  const strip = kit.ui.Svg && history.length ? receiptStrip(kit.ui.Svg, snapshot.receipts.map(r => r.receipt.outcome)) : null;
  if (strip) blocks.push({ pri: 6, need: 0, want: 1, build: () => [strip] });
  blocks.push({ pri: 5, need: 0, want: 1, build: () => [kit.hint('Reports are made from validated run data. They do not prove advertising results.', { wrap: 'truncate-end' })] });
  return pack(kit, budget, blocks, { gap: budget >= 24 });
}
