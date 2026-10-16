// Checks: every check the run made, worst first, filterable and paged so the screen never scrolls.
// Opening one shows it on its own, sized to the room there is.
import { platformName, plural, say, shortHash, when } from '../lexicon.mjs';
import { byAttention, counts, resultCounts, resultParts, statusTone } from '../model.mjs';
import { pageList } from '../pack.mjs';
import { toneOf } from '../theme.mjs';
import { oneLine } from '../wire.mjs';

const FILTERS = { all: 'all', fail: 'fails', unknown: 'unknowns', pass: 'passes' };

export function findings(kit, ctx) {
  const { snapshot, state, context, budget } = ctx;
  const selectedFinding = item => context?.kind === 'finding' && item.platform === context.platform && item.finding.control_id === context.controlId;
  if (!snapshot.findings.length) {
    return [kit.t('No checks recorded yet.', { bold: true }), kit.hint('They appear here when a step records a result.')];
  }
  const opened = snapshot.findings.find(selectedFinding);
  if (opened) return detail(kit, ctx, opened, snapshot.findings.indexOf(opened));

  const c = counts(snapshot);
  if (state.details) return ledger(kit, ctx);
  const out = [kit.stackBar(resultParts(resultCounts(snapshot.findings)))];

  // The list: worst first, optionally narrowed to one result.
  const filter = FILTERS[state.filter] ? state.filter : 'all';
  const ordered = byAttention(snapshot.findings).filter(({ item }) => filter === 'all' || item.finding.status === filter);
  const noSupport = snapshot.findings.filter(f => f.evidence_status === 'missing').length;
  const several = new Set(snapshot.findings.map(f => f.platform)).size > 1;
  // The title leads; the id trails for anyone who knows it. The platform appears only when the run has several.
  const label = (item, old) => { const id = item.finding.control_id; const lead = `${several ? `${platformName(item.platform)}: ` : ''}${item.control_title}${old}`; return `${oneLine(lead, Math.max(12, kit.width - 8 - id.length))}  ${id}`; };
  const quiet = noSupport * 2 > snapshot.findings.length;
  const showSupport = budget >= 14;
  // Filter and pager share one line when they fit; on a narrow pane the pager takes its own line.
  const split = kit.width < 58;
  const controlLines = split ? 2 : 1;
  const listRows = Math.max(1, budget - 1 - controlLines - (showSupport ? 1 : 0));
  const pages = Math.max(1, Math.ceil(ordered.length / listRows));
  const page = Math.min(state.page, pages - 1);
  const pager = kit.pager(page, pages, { back: () => ctx.controls.page(-1), next: () => ctx.controls.page(1) });
  const filterButton = kit.button('filter', filter === 'all' ? `Showing all ${ordered.length}` : `Showing ${FILTERS[filter]} ${ordered.length}`, 'f', () => ctx.controls.filter(), { plain: true });
  if (split) out.push(filterButton, ...(pager ? [pager] : [kit.t(' ')]));
  else out.push(kit.row([filterButton, ...(pager ? [pager] : [])], { gap: 3 }));
  if (!ordered.length) out.push(kit.hint('No checks match this filter. Press f to change it.', { wrap: 'truncate-end' }));
  for (const { item, index } of ordered.slice(page * listRows, (page + 1) * listRows)) {
    const old = item.evidence_status === 'current' || (quiet && item.evidence_status === 'missing') ? '' : `  · ${say('support', item.evidence_status).word}`;
    out.push(kit.row([kit.mark(statusTone(item.finding.status)), kit.button(`finding-open-${index}`, label(item, old), undefined, () => ctx.go('Evidence', { platform: item.platform, controlId: item.finding.control_id }), { plain: true })], { gap: 1 }));
  }
  if (showSupport) {
    // When most checks have no registered support, say so once instead of on every line.
    const note = quiet
      ? `${noSupport} of ${snapshot.findings.length} checks have no registered source support yet. That is normal for most of the catalog.`
      : c.supportTotal ? `${c.supportCurrent} of ${c.supportTotal} checks, claims and sources are up to date. Dates come from saved ledgers.` : 'Nothing recorded yet.';
    out.push(kit.hint(note, { wrap: 'truncate-end' }));
  }
  return out;
}

// The ledger behind the checks: every claim and source, and the run's fingerprint. Paged to fit.
function ledger(kit, ctx) {
  const { snapshot, state, budget } = ctx;
  const lines = [
    ...snapshot.claims.map(x => kit.line([{ text: `${x.id}  `, bold: true }, { text: say('support', x.effective_status).word, tone: say('support', x.effective_status).tone }, { text: `${x.classification}, ${x.verdict}; controls ${x.control_ids.join(', ') || 'none'}`, dim: true }], { gap: 2, wrap: 'truncate-end' })),
    ...snapshot.sources.map(x => kit.line([{ text: `${x.id}  `, bold: true }, { text: say('support', x.status).word, tone: say('support', x.status).tone }, { text: `${x.confidence} confidence; ${x.locator || 'no public link'}`, dim: true }], { gap: 2, wrap: 'truncate-end' })),
  ];
  const footer = kit.clamp(`Evaluated ${when(snapshot.evaluated_at)}. Run fingerprint ${shortHash(snapshot.fingerprint)} (a short code that changes whenever the run data changes).`, 3, { dimColor: true });
  const c = counts(snapshot);
  const head = kit.heading('Ledger', `${plural(snapshot.claims.length, 'claim')}, ${plural(snapshot.sources.length, 'source')}`);
  const summary = kit.t(c.supportTotal ? `${c.supportCurrent} of ${c.supportTotal} checks, claims and sources are up to date.` : 'Nothing recorded yet.', { wrap: 'truncate-end', ...(c.supportOld ? kit.toneStyle('warn') : {}) });
  const { per, pages, pagerLine } = pageList(lines.length, budget - 2 - footer.length);
  const page = Math.min(state.page, pages - 1);
  const pager = kit.pager(page, pages, { back: () => ctx.controls.page(-1), next: () => ctx.controls.page(1) });
  return [head, summary, ...lines.slice(page * per, (page + 1) * per), ...(pager && pagerLine ? [pager] : []), ...footer];
}

// One check on its own. Each paragraph gets as many lines as the room allows.
function detail(kit, ctx, item, index) {
  const { snapshot, state, budget } = ctx;
  const f = item.finding;
  const status = say('finding', f.status);
  const support = say('support', item.evidence_status);
  const severity = say('severity', item.severity);
  const claimById = new Map(snapshot.claims.map(x => [x.id, x]));
  const sourceById = new Map(snapshot.sources.map(x => [x.id, x]));
  const claims = item.claim_ids.map(id => claimById.get(id)).filter(Boolean);
  const sources = item.source_ids.map(id => sourceById.get(id)).filter(Boolean);
  const oldCount = [...claims, ...sources].filter(x => (x.effective_status ?? x.status) !== 'current').length;
  const evidenceText = e => (e && typeof e === 'object' && typeof e.value === 'string' && typeof e.kind === 'string' ? `${e.kind.replace(/_/g, ' ')}: ${e.value}` : JSON.stringify(e));

  // The card reads in three sentences: what we saw, what it means, what to do. Everything else is behind d.
  const title = kit.line([{ text: `▸ ${toneOf(status.tone).mark} `, tone: status.tone }, { text: item.control_title || f.control_id, bold: true }, { text: status.word, tone: status.tone }], { gap: 2, wrap: 'truncate-end' });
  const who = kit.hint(`${platformName(item.platform)} · ${f.control_id}`, { wrap: 'truncate-end' });
  if (!state.details) {
    const each = Math.max(1, Math.min(3, Math.floor((budget - 5) / 3)));
    return [
      title, who,
      ...kit.field('What we saw', f.observation, each, 14),
      ...kit.field('What it means', f.diagnosis, each, 14),
      ...kit.field('What to do', f.recommendation, each, 14),
      ...(budget >= 9 ? [kit.hint('Press d for severity, evidence and sources.', { wrap: 'truncate-end' })] : []),
      kit.button('finding-back', 'Back to all checks', undefined, () => ctx.controls.clearContext(), { plain: true }),
    ];
  }
  const fixed = 6; // title line, name line, chips, evidence line, support line, back button
  const spare = Math.max(3, budget - fixed);
  const each = Math.max(1, Math.min(4, Math.floor(spare / 3)));
  const out = [
    title, who,
    kit.line([{ text: 'Severity ', dim: true }, { text: severity.word, tone: severity.tone }, { text: 'Confidence ', dim: true }, say('confidence', f.confidence).word, { text: 'Support ', dim: true }, { text: support.word, tone: support.tone }], { gap: 1, wrap: 'truncate-end' }),
    ...kit.field('What we saw', f.observation, each, 14),
    ...kit.field('What it means', f.diagnosis, each, 14),
    ...kit.field('What to do', f.recommendation, each, 14),
    kit.line([{ text: 'Evidence   ', dim: true, raw: true }, f.evidence.length ? plural(f.evidence.length, 'item') : { text: 'none recorded', tone: 'warn' }, { text: `   Support  ${plural(item.claim_ids.length, 'claim')}, ${plural(item.source_ids.length, 'source')}${oldCount ? ` (${oldCount} out of date)` : ''}`, dim: true }], { gap: 0, wrap: 'truncate-end' }),
  ];
  // The evidence items and the claims and sources behind them fill whatever room is left.
  const left = budget - out.length - 1;
  const extra = [
    ...f.evidence.map((e, i) => kit.hint(`evidence ${i + 1}: ${evidenceText(e)}`, { wrap: 'truncate-end' })),
    ...claims.map(claim => kit.hint(`claim ${claim.id}  ${say('support', claim.effective_status).word}  verified ${claim.last_verified ?? 'unknown'}, refresh due ${claim.refresh_due ?? 'unknown'}`, { wrap: 'truncate-end' })),
    ...sources.map(source => kit.hint(`source ${source.id}  ${say('support', source.status).word}  ${source.title}, retrieved ${source.retrieved_at ?? 'unknown'}`, { wrap: 'truncate-end' })),
  ];
  if (left > 0) {
    out.push(...extra.slice(0, left));
    if (extra.length > left) out[out.length - 1] = kit.hint(`${extra.length - left + 1} more lines. Make the pane taller to see them.`, { wrap: 'truncate-end' });
  }
  out.push(kit.button('finding-back', 'Back to all checks', undefined, () => ctx.controls.clearContext(), { plain: true }));
  return out;
}
