// Pure derivation: one snapshot in, the facts every screen and the band share out.
// Screens never recompute these, so the Overview and the detail views cannot disagree.
import { platformName, plural, say } from './lexicon.mjs';

export function counts(snapshot) {
  const workers = snapshot.workers;
  const done = workers.filter(w => w.status === 'completed').length;
  const failed = workers.filter(w => w.status === 'failed' || w.result_status === 'failed').length;
  const blocked = workers.filter(w => w.result_status === 'blocked').length;
  const missing = workers.flatMap(w => w.missing_inputs.map(text => ({ workerId: w.id, platform: w.platform, text })));
  const findingsOld = snapshot.findings.filter(f => f.evidence_status !== 'current').length;
  const claimsOld = snapshot.claims.filter(c => c.effective_status !== 'current').length;
  const sourcesOld = snapshot.sources.filter(s => s.status !== 'current').length;
  const supportTotal = snapshot.findings.length + snapshot.claims.length + snapshot.sources.length;
  const supportOld = findingsOld + claimsOld + sourcesOld;
  const invalidInputs = snapshot.inputs.filter(i => i.validation === 'invalid' || i.validation === 'missing').length;
  const uncheckedInputs = snapshot.inputs.filter(i => i.validation === 'unchecked').length;
  return {
    workers: workers.length, done, failed, blocked, missing,
    findings: snapshot.findings.length, findingsOld, claimsOld, sourcesOld,
    supportTotal, supportOld, supportCurrent: supportTotal - supportOld,
    contradictions: workers.reduce((n, w) => n + w.contradictions.length, 0),
    staleRefs: workers.reduce((n, w) => n + w.stale_sources.length, 0),
    invalidInputs, uncheckedInputs, inputs: snapshot.inputs.length, receipts: snapshot.receipts.length,
  };
}

// The single plain-language answer to "where is this run and what needs me".
export function verdict(snapshot) {
  const c = counts(snapshot);
  const n = c.workers;
  if (snapshot.workflow_status === 'failed' && snapshot.completeness === 'partial') return { tone: 'bad', headline: 'Partly done', detail: 'A step failed. What was recorded is still shown below.', action: { label: 'See checks', tab: 'Evidence', target: null } };
  if (snapshot.workflow_status === 'failed') return { tone: 'bad', headline: 'The run failed', detail: 'A step stopped with an error. Read the notes under each platform.', action: null };
  if (snapshot.workflow_status === 'blocked') return { tone: 'bad', headline: 'The run is blocked', detail: 'It cannot continue until the blocker is cleared.', action: null };
  if (c.missing.length) {
    const first = c.missing[0];
    const more = c.missing.length > 1 ? ` (+${c.missing.length - 1} more)` : '';
    return { tone: 'warn', headline: 'Waiting for you', detail: `${platformName(first.platform)} needs: ${first.text}${more}`, action: { label: 'Open Inputs', tab: 'Inputs', target: { workerId: first.workerId, missingInput: first.text } } };
  }
  if (c.failed || c.blocked) return { tone: 'bad', headline: 'Partly done', detail: `${c.done} of ${plural(n, 'step')} finished, ${plural(c.failed + c.blocked, 'step')} did not.`, action: { label: 'See checks', tab: 'Evidence', target: null } };
  if (snapshot.workflow_status === 'pending' || snapshot.workflow_status === 'running') return { tone: 'info', headline: 'Running', detail: `${c.done} of ${plural(n, 'step')} finished. Progress comes only from recorded results.`, action: null };
  if (snapshot.workflow_status === 'completed' && c.supportOld > 0) return { tone: 'warn', headline: 'Finished, with out-of-date support', detail: `${c.supportOld} of ${c.supportTotal} checks, claims and sources need a fresh look before you rely on them.`, action: { label: 'See checks', tab: 'Evidence', target: null } };
  if (snapshot.workflow_status === 'completed') return { tone: 'ok', headline: 'Finished', detail: `All ${plural(n, 'step')} reported and the support is up to date.`, action: null };
  return { tone: 'muted', headline: 'Status unknown', detail: 'The engine did not report a clear state.', action: null };
}

// One row per platform, built from whatever the snapshot actually records for it.
export function platforms(snapshot) {
  const seen = [];
  const add = p => { if (p && !seen.includes(p)) seen.push(p); };
  snapshot.workers.forEach(w => add(w.platform));
  snapshot.findings.forEach(f => add(f.platform));
  snapshot.scoring.forEach(s => add(s.platform));
  const hasShared = snapshot.workers.some(w => !w.platform);
  const rows = seen.map(platform => ({ platform, workers: snapshot.workers.filter(w => w.platform === platform), findings: snapshot.findings.filter(f => f.platform === platform), score: snapshot.scoring.find(s => s.platform === platform) || null }));
  if (hasShared) rows.push({ platform: null, workers: snapshot.workers.filter(w => !w.platform), findings: [], score: null });
  return rows.map(row => {
    const ws = row.workers;
    let tone = 'muted', word = 'Nothing recorded yet';
    if (ws.length) {
      if (ws.some(w => w.status === 'failed' || w.result_status === 'failed' || w.result_status === 'blocked')) { tone = 'bad'; word = ws.some(w => w.result_status === 'blocked') ? 'Blocked' : 'Failed'; }
      else if (ws.some(w => w.missing_inputs.length || w.result_status === 'needs_input')) { tone = 'warn'; word = 'Waiting for your input'; }
      else if (ws.some(w => w.status === 'running' || w.status === 'pending')) { tone = 'info'; word = ws.some(w => w.status === 'running') ? 'Working' : 'Queued'; }
      else { tone = 'ok'; word = 'Done'; }
    }
    return { ...row, tone, word, done: ws.filter(w => w.status === 'completed').length };
  });
}

// Scores are shown only when the core says a profile is enabled and gave a number.
// A disabled profile never shows a number, whatever the wire carried.
export function scoreLine(entry) {
  if (!entry || entry.profile_status === 'disabled' || entry.health_score === null) return { shown: false, text: 'Not scored' };
  return { shown: true, text: `${entry.health_score}/100`, coverage: entry.evidence_coverage === null ? null : `${entry.evidence_coverage}% evidence` };
}
export const allScoresOff = snapshot => snapshot.scoring.length > 0 && snapshot.scoring.every(s => !scoreLine(s).shown);
export const scoringStatus = entry => say('scoring', entry.status);

// Result counts for a list of findings, in the order the person reads them.
export function resultCounts(findings) {
  const n = status => findings.filter(f => f.finding.status === status).length;
  return { pass: n('pass'), fail: n('fail'), unknown: n('unknown'), na: n('not_applicable') };
}
export const resultParts = r => [{ n: r.pass, label: 'pass', tone: 'ok' }, { n: r.fail, label: 'fail', tone: 'bad' }, { n: r.unknown, label: 'unknown', tone: 'warn' }, { n: r.na, label: 'n/a', tone: 'muted' }];
const RANK = { fail: 0, unknown: 1, pass: 2, not_applicable: 3 };
const SEVERITY = { critical: 0, high: 1, medium: 2, informational: 3 };
// Failed checks first, then unknown ones, worst severity first, with out-of-date support as a tie-break.
export function byAttention(findings) {
  return findings.map((item, index) => ({ item, index })).sort((a, b) => (RANK[a.item.finding.status] - RANK[b.item.finding.status])
    || ((SEVERITY[a.item.severity] ?? 9) - (SEVERITY[b.item.severity] ?? 9))
    || ((a.item.evidence_status === 'current') - (b.item.evidence_status === 'current')) || a.index - b.index);
}
export const statusTone = status => ({ pass: 'ok', fail: 'bad', unknown: 'warn' }[status] || 'muted');
