// Findings: one card per finding, with the evidence behind it and the support's age.
import { platformName, plural, say, shortHash, when } from '../lexicon.mjs';
import { byAttention, counts, resultCounts, resultParts, statusTone } from '../model.mjs';
import { toneOf } from '../theme.mjs';
import { supportBar } from '../svg.mjs';
import { oneLine } from '../wire.mjs';

export function findings(kit, ctx) {
  const { snapshot, state, context } = ctx;
  const out = [];
  const selectedFinding = item => context?.kind === 'finding' && item.platform === context.platform && item.finding.control_id === context.controlId;
  if (!snapshot.findings.length) {
    out.push(kit.card([kit.t('No checks recorded yet.', { bold: true }), kit.hint('They appear here when a step records a result.')], { tone: 'muted' }));
  }
  if (snapshot.findings.length) out.push(kit.col([kit.heading('Results', plural(snapshot.findings.length, 'check')), kit.stackBar(resultParts(resultCounts(snapshot.findings)))]));
  const entries = snapshot.findings.map((item, index) => ({ item, index }));
  const anySelected = entries.some(e => selectedFinding(e.item));
  const compact = snapshot.findings.length > 6 && !anySelected && !state.details;
  if (compact) {
    // Many checks: one line each, grouped by platform, worst first. Open one for its full card.
    const order = [...new Set(snapshot.findings.map(f => f.platform))];
    for (const platform of order) {
      const group = snapshot.findings.filter(f => f.platform === platform);
      const r = resultCounts(group);
      out.push(kit.section([
        kit.line([{ text: platformName(platform), bold: true }, { text: `${r.pass} pass`, tone: 'ok' }, { text: `${r.fail} fail`, tone: r.fail ? 'bad' : 'muted' }, { text: `${r.unknown} unknown`, tone: r.unknown ? 'warn' : 'muted' }], { gap: 2 }),
        ...byAttention(group).map(({ item }) => {
          const index = snapshot.findings.indexOf(item);
          const old = item.evidence_status === 'current' ? '' : `  · ${say('support', item.evidence_status).word}`;
          const label = `${item.finding.control_id}  ${item.control_title}${old}`;
          return kit.row([kit.mark(statusTone(item.finding.status)), kit.button(`finding-open-${index}`, oneLine(label, kit.width - 6), undefined, () => ctx.go('Evidence', { platform: item.platform, controlId: item.finding.control_id }), { plain: true })], { gap: 1 });
        }),
      ]));
    }
  }
  const ordered = compact ? [] : [...entries.filter(e => selectedFinding(e.item)), ...entries.filter(e => !selectedFinding(e.item))];
  const claimById = new Map(snapshot.claims.map(x => [x.id, x]));
  const sourceById = new Map(snapshot.sources.map(x => [x.id, x]));
  for (const { item, index } of ordered) {
    const f = item.finding;
    const status = say('finding', f.status);
    const support = say('support', item.evidence_status);
    const severity = say('severity', item.severity);
    const expanded = selectedFinding(item) || state.details;
    const claims = item.claim_ids.map(id => claimById.get(id)).filter(Boolean);
    const sources = item.source_ids.map(id => sourceById.get(id)).filter(Boolean);
    const oldCount = [...claims, ...sources].filter(x => (x.effective_status ?? x.status) !== 'current').length;
    const body = [
      kit.line([{ text: `${selectedFinding(item) ? '▸ ' : ''}${toneOf(status.tone).mark} `, tone: status.tone }, { text: `${platformName(item.platform)} ${f.control_id}`, bold: true }, { text: `   ${status.word}`, tone: status.tone }]),
      ...(item.control_title ? [kit.t(item.control_title, { bold: true })] : []),
      kit.row([kit.chip('Severity', severity.word, severity.tone), kit.chip('Confidence', say('confidence', f.confidence).word), kit.chip('Support', support.word, support.tone)], { gap: 3, wrap: true }),
      kit.line([{ text: 'Seen       ', dim: true }, f.observation]),
      kit.line([{ text: 'Diagnosis  ', dim: true }, f.diagnosis]),
      kit.line([{ text: 'Do next    ', dim: true }, f.recommendation]),
      f.evidence.length
        ? kit.line([{ text: 'Evidence   ', dim: true }, plural(f.evidence.length, 'item')])
        : kit.line([{ text: 'Evidence   ', dim: true }, { text: 'none recorded', tone: 'warn' }]),
      kit.line([{ text: 'Support    ', dim: true }, `${plural(item.claim_ids.length, 'claim')}, ${plural(item.source_ids.length, 'source')}${oldCount ? ` (${oldCount} out of date)` : ''}`]),
    ];
    if (expanded) {
      f.evidence.forEach((e, i) => body.push(kit.hint(`evidence ${i + 1}: ${JSON.stringify(e)}`)));
      for (const claim of claims) body.push(kit.line([{ text: `claim ${claim.id}  `, dim: true }, { text: say('support', claim.effective_status).word, tone: say('support', claim.effective_status).tone }, { text: `  verified ${claim.last_verified ?? 'unknown'}, refresh due ${claim.refresh_due ?? 'unknown'}`, dim: true }]), kit.hint(claim.statement));
      for (const source of sources) body.push(kit.line([{ text: `source ${source.id}  `, dim: true }, { text: say('support', source.status).word, tone: say('support', source.status).tone }, { text: `  ${source.title}, retrieved ${source.retrieved_at ?? 'unknown'}, refresh due ${source.refresh_due ?? 'unknown'}`, dim: true }]));
    } else {
      body.push(kit.button(`finding-open-${index}`, 'Open details', undefined, () => ctx.go('Evidence', { platform: item.platform, controlId: f.control_id }), { plain: true }));
    }
    out.push(kit.card(body, { tone: status.tone, key: `finding-${index}` }));
  }
  const c = counts(snapshot);
  const bar = kit.ui.Svg ? supportBar(kit.ui.Svg, c.supportCurrent, c.supportOld, 0) : null;
  out.push(kit.section([
    kit.heading('Support behind the checks', `${plural(snapshot.claims.length, 'claim')}, ${plural(snapshot.sources.length, 'source')}`),
    ...(bar ? [bar] : []),
    kit.t(c.supportTotal ? `${c.supportCurrent} of ${c.supportTotal} checks, claims and sources are up to date.` : 'Nothing recorded yet.', c.supportOld ? kit.toneStyle('warn') : {}),
    kit.hint('Dates come from saved ledgers. Opening this screen does not check any source live.'),
  ]));
  if (state.details) {
    out.push(kit.section([
      kit.heading('Ledger'),
      ...snapshot.claims.map(x => kit.line([{ text: `${x.id}  `, bold: true }, { text: say('support', x.effective_status).word, tone: say('support', x.effective_status).tone }, { text: `  ${x.classification}, ${x.verdict}; controls ${x.control_ids.join(', ') || 'none'}`, dim: true }])),
      ...snapshot.sources.map(x => kit.line([{ text: `${x.id}  `, bold: true }, { text: say('support', x.status).word, tone: say('support', x.status).tone }, { text: `  ${x.confidence} confidence; ${x.locator || 'no public link'}`, dim: true }])),
      kit.hint(`Evaluated ${when(snapshot.evaluated_at)}. Run fingerprint ${shortHash(snapshot.fingerprint)} (a short code that changes whenever the run data changes).`),
    ]));
  }
  return out;
}
