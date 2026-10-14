// Overview: where the run is, what needs the person, and what to press next.
import { platformName, plural, say, when } from '../lexicon.mjs';
import { allScoresOff, byAttention, counts, platforms, resultCounts, resultParts, scoreLine, statusTone, verdict } from '../model.mjs';
import { toneOf } from '../theme.mjs';
import { runRing } from '../svg.mjs';
import { oneLine } from '../wire.mjs';

const cut = (text, width) => oneLine(text, width);

export function overview(kit, ctx) {
  const { snapshot } = ctx;
  const c = counts(snapshot);
  const v = verdict(snapshot);
  const results = resultCounts(snapshot.findings);
  const out = [];

  // 1. One line of orientation for anyone opening this for the first time.
  if (!ctx.state.demo) out.push(kit.hint('A saved Claude Ads audit: how far it got, what it needs from you, and what its checks found.'));

  // 2. The verdict, in one card.
  const body = [kit.line([{ text: `${toneOf(v.tone).mark} `, tone: v.tone }, { text: v.headline, bold: true, tone: v.tone }]), kit.t(v.detail)];
  if (v.action) body.push(kit.button('verdict-action', v.action.label, 'g', () => ctx.go(v.action.tab, v.action.target), { primary: true }));
  out.push(kit.card(body, { tone: v.tone, key: 'verdict' }));

  // 3. Four numbers as tiles.
  out.push(kit.section([kit.tiles([
    [`${c.done}/${c.workers}`, 'steps done', c.workers && c.done === c.workers ? 'ok' : c.failed || c.blocked ? 'bad' : 'muted'],
    [c.findings, 'checks run', 'muted'],
    [c.missing.length, 'need you', c.missing.length ? 'warn' : 'muted'],
    [`${c.supportCurrent}/${c.supportTotal}`, 'evidence ok', c.supportTotal ? (c.supportOld ? 'warn' : 'ok') : 'muted'],
  ])]));

  // 4. How the checks came out, as one colored bar (and a ring on surfaces that draw Svg).
  if (snapshot.findings.length) {
    const ring = kit.ui.Svg ? runRing(kit.ui.Svg, c, v.tone) : null;
    const bar = kit.col([kit.heading('Results', plural(snapshot.findings.length, 'check')), kit.stackBar(resultParts(results))]);
    out.push(kit.section(ring ? [kit.row([ring, bar], { gap: 3 })] : [bar]));
  }

  // 5. One row per platform: its state, and one square per check.
  const rows = platforms(snapshot);
  if (rows.length) {
    const room = Math.max(6, kit.width - 16 - 22 - 6);
    const columns = [{ head: 'Platform', max: 16 }, { head: 'Status', max: kit.narrow ? 22 : 24 }, ...(kit.narrow ? [] : [{ head: 'Checks', grow: true }])];
    out.push(kit.section([
      kit.heading('By platform', kit.narrow ? undefined : '■ one square per check'),
      kit.table(columns, rows.map(r => [
        { text: `${toneOf(r.tone).mark} ${platformName(r.platform)}`, tone: r.tone, bold: true },
        { text: r.word, tone: r.tone },
        ...(kit.narrow ? [] : [r.findings.length ? { parts: kit.squares(r.findings.map(f => statusTone(f.finding.status)), room), gap: 0 } : { text: 'no checks', tone: 'muted' }]),
      ])),
    ]));
  }

  // 6. What the person has to supply, when there are several things.
  if (c.missing.length > 1) {
    out.push(kit.section([
      kit.heading('Needs your input'),
      ...c.missing.map((m, i) => kit.row([
        kit.line([{ text: '▲ ', tone: 'warn' }, `${platformName(m.platform)}: ${m.text}`]),
        kit.button(`worker-input-${m.workerId}-${i}`, 'Open Inputs', undefined, () => ctx.go('Inputs', { workerId: m.workerId, missingInput: m.text }), { plain: true }),
      ], { gap: 2, wrap: true })),
    ]));
  }

  // 7. The few checks that most need a look, worst first. The rest live on the Checks screen.
  const attention = byAttention(snapshot.findings).filter(e => e.item.finding.status === 'fail' || e.item.finding.status === 'unknown');
  if (attention.length) {
    const shown = attention.slice(0, 5);
    out.push(kit.section([
      kit.heading('Needs attention', `${attention.length} of ${snapshot.findings.length} checks`),
      ...shown.map(({ item, index }) => {
        const f = item.finding;
        const tone = statusTone(f.status);
        const support = item.evidence_status === 'current' ? '' : `  · ${say('support', item.evidence_status).word}`;
        return kit.row([kit.mark(tone), kit.button(`finding-evidence-${index}`, cut(`${platformName(item.platform)} ${f.control_id}  ${item.control_title}${support}`, Math.max(20, kit.width - 6)), undefined, () => ctx.go('Evidence', { platform: item.platform, controlId: f.control_id }), { plain: true })], { gap: 1 });
      }),
      ...(attention.length > shown.length ? [kit.button('see-findings', `See all ${snapshot.findings.length} checks`, undefined, () => ctx.go('Evidence'), { plain: true })] : []),
    ]));
  }

  // 8. Worker notes, only when the workers recorded some.
  const notes = snapshot.workers.flatMap(w => [
    ...w.recovery_hints.map(text => ({ label: 'Try', text, w })),
    ...w.contradictions.map(text => ({ label: 'Conflict', text, w })),
    ...w.stale_sources.map(text => ({ label: 'Out-of-date source', text, w })),
  ]);
  if (notes.length) out.push(kit.section([kit.heading('Notes from the audit'), ...notes.map(n => kit.line([{ text: '↳ ', dim: true }, { text: `${platformName(n.w.platform)}  `, dim: true }, `${n.label}: ${n.text}`]))]));

  // 9. Scores. A disabled profile is never shown as a number.
  out.push(kit.section(allScoresOff(snapshot)
    ? [kit.t('Scoring is off. No scoring profile is approved yet, so nothing here is rated.', { dimColor: true })]
    : snapshot.scoring.map(s => { const sl = scoreLine(s); return kit.line([{ text: `${platformName(s.platform)}  `, bold: true }, sl.shown ? `${sl.text}${sl.coverage ? `, ${sl.coverage}` : ''}` : { text: 'Not scored', dim: true }]); })));

  // 10. Details on demand.
  if (ctx.state.details) {
    out.push(kit.section([
      kit.heading('Details'),
      kit.line([{ text: 'Evaluated  ', dim: true }, when(snapshot.evaluated_at)]),
      kit.line([{ text: 'Privacy    ', dim: true }, say('privacy', snapshot.privacy_class).word]),
      kit.line([{ text: 'Run state  ', dim: true }, `${say('workflow', snapshot.workflow_status).word}, ${say('completeness', snapshot.completeness).word.toLowerCase()}${snapshot.phase ? `, phase ${snapshot.phase}` : ''}`]),
      ...snapshot.limitations.map(text => kit.line([{ text: '· ', dim: true }, { text, dim: true }])),
      kit.hint('Progress comes from recorded results. Nothing is inferred from elapsed time.'),
    ]));
  } else {
    out.push(kit.section([kit.hint(`${plural(snapshot.limitations.length, 'note')} on limits. Press d for details.`)]));
  }
  return out;
}
