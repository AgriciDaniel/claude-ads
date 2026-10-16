// Overview: where the run is, what needs the person, and what to press next.
// Drawn to fit ctx.budget lines. The most useful sections get room first; the rest give way.
import { platformName, plural, say, when } from '../lexicon.mjs';
import { allScoresOff, areaRows, byAttention, counts, coverage, platforms, resultCounts, scoreLine, statusTone, verdict } from '../model.mjs';
import { fitList, pack } from '../pack.mjs';
import { toneOf } from '../theme.mjs';
import { coverageRing } from '../svg.mjs';
import { oneLine } from '../wire.mjs';

const cut = (text, width) => oneLine(text, width);

export function overview(kit, ctx) {
  const { snapshot, state } = ctx;
  const c = counts(snapshot);
  const v = verdict(snapshot);
  const room = kit.width - 4;

  const notes = snapshot.workers.flatMap(w => [
    ...w.recovery_hints.map(text => ({ label: 'Try', text, w })),
    ...w.contradictions.map(text => ({ label: 'Conflict', text, w })),
    ...w.stale_sources.map(text => ({ label: 'Out-of-date source', text, w })),
  ]);
  const noteLine = n => kit.line([{ text: '↳ ', dim: true }, { text: `${platformName(n.w.platform)}  `, dim: true }, cut(`${n.label}: ${n.text}`, Math.max(20, room - 14))], { wrap: 'truncate-end' });

  // The verdict: one line that says where the run stands, then the one thing to press.
  const verdictBlock = {
    pri: 0, need: v.action ? 2 : 1, want: v.action ? 2 : 1,
    build: () => [
      kit.line([{ text: `${toneOf(v.tone).mark} `, tone: v.tone }, { text: v.headline, bold: true, tone: v.tone }, { text: v.detail, dim: true }], { gap: 2, wrap: 'truncate-end' }),
      ...(v.action ? [kit.button('verdict-action', v.action.label, 'g', () => ctx.go(v.action.tab, v.action.target), { primary: true })] : []),
    ],
  };

  // Details view: everything the main view leaves out, listed and paged.
  if (state.details) {
    const info = [
      kit.line([{ text: 'Evaluated  ', dim: true }, when(snapshot.evaluated_at)]),
      kit.line([{ text: 'Privacy    ', dim: true }, say('privacy', snapshot.privacy_class).word]),
      kit.line([{ text: 'Run state  ', dim: true }, cut(`${say('workflow', snapshot.workflow_status).word}, ${say('completeness', snapshot.completeness).word.toLowerCase()}${snapshot.phase ? `, phase ${snapshot.phase}` : ''}`, room - 12)], { wrap: 'truncate-end' }),
      ...snapshot.limitations.flatMap(text => kit.clamp(`· ${text}`, 2, { dimColor: true })),
      ...notes.map(noteLine),
      kit.hint('Progress comes from recorded results. Nothing is inferred from elapsed time.'),
    ];
    const per = Math.max(3, ctx.budget - 3);
    const pages = Math.max(1, Math.ceil(info.length / per));
    const page = Math.min(state.page, pages - 1);
    const pager = kit.pager(page, pages, { back: () => ctx.controls.page(-1), next: () => ctx.controls.page(1) });
    return [verdictBlock.build()[0], kit.heading('Details', notes.length ? plural(notes.length, 'note') : undefined), ...info.slice(page * per, (page + 1) * per), ...(pager ? [pager] : [])];
  }

  const blocks = [verdictBlock];

  // Coverage: how much of the audit could be judged, and how the judged part came out.
  const cov = coverage(snapshot.findings);
  if (snapshot.findings.length && cov.applicable) {
    const ring = kit.ui.Svg ? coverageRing(kit.ui.Svg, cov) : null;
    const legend = () => kit.line([
      { text: `✓ ${cov.pass} passing`, tone: 'ok' }, { text: `✗ ${cov.fail} need work`, tone: cov.fail ? 'bad' : 'muted' },
      { text: `? ${cov.unknown} not enough data`, tone: 'unclear' }, ...(cov.na ? [{ text: `${cov.na} do not apply`, dim: true }] : []),
    ], { gap: 2, wrap: 'truncate-end' });
    const headline = () => (!cov.judged ? kit.line([{ text: 'Nothing judged yet', bold: true, tone: 'info' }, { text: `${plural(cov.applicable, 'check')} ${cov.applicable === 1 ? 'needs' : 'need'} data first`, dim: true }], { gap: 2, wrap: 'truncate-end' }) : kit.line([{ text: `${cov.percent}%`, bold: true, tone: 'info' }, { text: 'judged', bold: true }, { text: `${cov.judged} of ${cov.applicable} applicable checks had enough data`, dim: true }], { gap: 1, wrap: 'truncate-end' }));
    const bar = length => kit.line(kit.meterParts(cov, length), { gap: 0 });
    blocks.push({
      pri: 1, need: 1, want: ring ? 7 : 3,
      build: n => {
        if (ring && n >= 7) return [kit.row([ring, kit.col([kit.heading('Coverage'), headline(), bar(Math.min(44, kit.width - 16)), legend()])], { gap: 3 })];
        if (n >= 3) return [headline(), bar(Math.min(48, kit.width - 6)), legend()];
        if (n === 2) return [headline(), legend()];
        return [legend()];
      },
    });
  }

  // The same meter per platform (only when the run covers more than one) and per topic.
  // Platforms show every count. Topics show only what matters: how many to fix, else that all is well, else how many lack data.
  const meterRow = (label, r, wide, brief = false) => [
    { text: label, bold: true },
    { parts: kit.meterParts(r, wide), gap: 0 },
    { parts: brief
      ? [r.fail ? { text: `✗ ${r.fail} to fix`, tone: 'bad' } : r.unknown ? { text: `? ${r.unknown} no data`, tone: 'unclear' } : { text: '✓ all good', tone: 'ok' }]
      : [...(r.pass ? [{ text: `✓ ${r.pass}`, tone: 'ok' }] : []), ...(r.fail ? [{ text: `✗ ${r.fail}`, tone: 'bad' }] : []), ...(r.unknown ? [{ text: `? ${r.unknown}`, tone: 'unclear' }] : [])], gap: 1 },
  ];
  const meterColumns = (head, labelMax) => [{ head, max: labelMax }, { head: 'Checks', max: 40 }, { head: 'Result', grow: true }];
  const meterLength = kit.narrow ? 10 : kit.width < 80 ? 16 : 24;

  const rows = platforms(snapshot).filter(r => r.findings.length);
  // On a short pane the story is verdict, coverage, topics and fixes. Platforms, inputs and notes wait for a taller one.
  const roomy = ctx.budget >= 26;
  if (rows.length > 1 && roomy) {
    blocks.push({
      pri: 3, need: Math.min(3, 1 + rows.length), want: 1 + rows.length,
      build: n => {
        const { shown: count, more } = fitList(rows.length, n - 1);
        return [kit.heading('By platform'), kit.table(meterColumns('Platform', 16), rows.slice(0, count).map(r => meterRow(platformName(r.platform), resultCounts(r.findings), meterLength)), { header: false }), ...(more ? [kit.hint(`+ ${rows.length - count} more platforms`)] : [])];
      },
    });
  }

  const areas = areaRows(snapshot.findings);
  if (areas.length) {
    blocks.push({
      pri: 4, need: Math.min(5, 1 + areas.length), want: 1 + Math.min(7, areas.length) + (areas.length > 7 ? 1 : 0),
      build: n => {
        const { shown: count, more } = fitList(areas.length, n - 1);
        return [
          kit.heading('Health by topic'),
          kit.table(meterColumns('Topic', 26), areas.slice(0, count).map(a => meterRow(a.area, a, meterLength, true)), { header: false }),
          ...(more ? [kit.hint(`+ ${areas.length - count} more topics`)] : []),
        ];
      },
    });
  }

  // What to fix first: the checks that failed, each with the step that fixes it.
  // With nothing failing, the first things worth settling are the checks that lack data.
  const ranked = byAttention(snapshot.findings);
  const failing = ranked.filter(e => e.item.finding.status === 'fail');
  const fails = failing.length ? failing : ranked.filter(e => e.item.finding.status === 'unknown');
  if (fails.length) {
    const several = rows.length > 1;
    blocks.push({
      pri: 2, need: 3, want: 1 + 2 * Math.min(3, fails.length) + (fails.length > 3 ? 1 : 0),
      build: n => {
        const room = n - 1;
        const per = room >= 4 ? 2 : 1;
        let count = Math.min(Math.floor(room / per), fails.length, 5);
        let more = fails.length > count;
        if (more) { count = Math.max(1, Math.min(Math.floor((room - 1) / per), 5)); more = fails.length > count && room > count * per; }
        const out = [(failing.length ? kit.heading('Fix first', `${fails.length} need work`) : kit.heading('Settle next', `${fails.length} lack data`))];
        for (const { item, index } of fails.slice(0, count)) {
          const label = `${several ? `${platformName(item.platform)}: ` : ''}${item.control_title}`;
          out.push(kit.row([kit.mark(statusTone(item.finding.status)), kit.button(`finding-evidence-${index}`, cut(label, Math.max(20, kit.width - 6)), undefined, () => ctx.go('Evidence', { platform: item.platform, controlId: item.finding.control_id }), { plain: true })], { gap: 1 }));
          if (per === 2) out.push(kit.indent([kit.t(cut(item.finding.recommendation || item.finding.diagnosis || '', Math.max(20, kit.width - 6)), { dimColor: true, wrap: 'truncate-end' })], 2));
        }
        if (more) out.push(kit.button('see-findings', `See all ${snapshot.findings.length} checks`, undefined, () => ctx.go('Evidence'), { plain: true }));
        return out;
      },
    });
  }

  if (c.missing.length > 1 && ctx.budget >= 30) {
    blocks.push({
      pri: 5, need: 2, want: 1 + Math.min(3, c.missing.length) + 1,
      build: n => {
        const { shown: count, more } = fitList(c.missing.length, n - 1);
        const shown = c.missing.slice(0, count);
        return [
          kit.heading('Needs your input', `${c.missing.length} items`),
          ...shown.map(m => kit.line([{ text: '▲ ', tone: 'warn' }, cut(`${platformName(m.platform)}: ${m.text}`, Math.max(20, room))], { wrap: 'truncate-end' })),
          ...(more ? [kit.button('worker-input-all', `See all ${c.missing.length} on Inputs`, undefined, () => ctx.go('Inputs'), { plain: true })] : []),
        ];
      },
    });
  }

  if (notes.length && ctx.budget >= 30) {
    blocks.push({
      pri: 8, need: 1, want: 1 + Math.min(4, notes.length),
      build: n => (n <= 1
        ? [kit.hint(`${plural(notes.length, 'note')} from the audit. Press d for details.`, { wrap: 'truncate-end' })]
        : [kit.heading('Notes from the audit', notes.length > n - 1 ? `${notes.length} notes` : undefined), ...notes.slice(0, n - 1).map(noteLine)]),
    });
  }

  blocks.push({
    pri: 6, need: 1, want: 1,
    build: () => (allScoresOff(snapshot)
      ? [kit.hint('Scoring is off: no scoring profile is approved, so nothing is rated.', { wrap: 'truncate-end' })]
      : snapshot.scoring.map(s => { const sl = scoreLine(s); return kit.line([{ text: `${platformName(s.platform)}  `, bold: true }, sl.shown ? `${sl.text}${sl.coverage ? `, ${sl.coverage}` : ''}` : { text: 'Not scored', dim: true }], { wrap: 'truncate-end' }); })),
  });

  blocks.push({ pri: 10, need: 0, want: 1, build: () => [kit.hint(`${plural(snapshot.limitations.length, 'note')} on limits. Press d for details.`, { wrap: 'truncate-end' })] });

  return pack(kit, ctx.budget, blocks, { gap: ctx.budget >= 28 });
}
