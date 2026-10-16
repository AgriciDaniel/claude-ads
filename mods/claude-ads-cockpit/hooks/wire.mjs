import { absolutePath } from './launcher.mjs';
// Fail closed at the display boundary. The core owns canonical validation.
const SHA = /^[a-f0-9]{64}$/;
const ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
const PLATFORMS = ['google','meta','youtube','linkedin','tiktok','microsoft','apple','amazon','reddit','pinterest','snapchat','x'];
const EVIDENCE = ['current','stale','demoted','missing','contested','provisional'];
const OPS = ['validate-input', 'validate-run', 'render-report'];
export const TABS = ['Run', 'Evidence', 'Inputs', 'Compare', 'Reports'];
export function safeText(value) {
  return String(value ?? '').replace(/[\x00-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]/g, ' ').slice(0, 8000);
}
// One bounded line for a control label: control characters (tab, newline) and runs of spaces collapse.
export function oneLine(value, max = 160) {
  const text = safeText(value).replace(/\s+/g, ' ').trim();
  return text.length <= max ? text : `${text.slice(0, Math.max(1, max - 1))}…`;
}
function fail() { throw new Error('Engine response does not match cockpit interface 1.0.0.'); }
function object(x, keys) {
  if (!x || typeof x !== 'object' || Array.isArray(x) || Object.keys(x).length !== keys.length || keys.some(k => !Object.hasOwn(x, k))) fail();
}
function optionalObject(x, required, optional) {
  if (!x || typeof x !== 'object' || Array.isArray(x) || required.some(k => !Object.hasOwn(x,k)) || Object.keys(x).some(k => !required.includes(k) && !optional.includes(k))) fail();
}
function list(x) { if (!Array.isArray(x) || x.length > 1000) fail(); }
function str(x) { if (typeof x !== 'string' || x.length > 8192 || /[\x00-\x08\x0b-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]/.test(x)) fail(); }
function strings(x) { list(x); x.forEach(str); }
function choice(x, values) { if (!values.includes(x)) fail(); }
function rows(x, keys, check) { list(x); for (const row of x) { object(row, keys); check(row); } }
function relative(x) { str(x); if (!x || x.startsWith('/') || /[\\:]/.test(x) || x.split('/').some(v => !v || v === '.' || v === '..')) fail(); }
function timestamp(x) { str(x); if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(x) || !Number.isFinite(Date.parse(x))) fail(); }
function hash(x) { if (!SHA.test(x || '')) fail(); }
export function doctorWire(x) {
  object(x, ['interface_version', 'status', 'core_version', 'profiles', 'runs', 'diagnostics']);
  if (x.interface_version !== '1.0.0') fail();
  choice(x.status, ['ok', 'blocked']); str(x.core_version); strings(x.diagnostics);
  rows(x.profiles, ['platform', 'status', 'disabled_reason'], r => { str(r.platform); str(r.status); if (r.disabled_reason !== null) str(r.disabled_reason); });
  rows(x.runs, ['id', 'status'], r => { if (!ID.test(r.id)) fail(); str(r.status); });
  return x;
}
export function snapshotWire(x) {
  object(x, ['schema_version','artifact_type','run_id','evaluated_at','fingerprint','policy_fingerprint','privacy_class','phase','completeness','workflow_status','workers','accounts','findings','claims','sources','inputs','artifacts','scoring','permitted_actions','limitations','comparison','receipts']);
  if (x.schema_version !== '1.0.0' || x.artifact_type !== 'cockpit-snapshot' || !ID.test(x.run_id)) fail();
  timestamp(x.evaluated_at); hash(x.fingerprint); hash(x.policy_fingerprint); choice(x.privacy_class,['public','internal','confidential','restricted']); if (x.phase !== null) str(x.phase);
  choice(x.completeness, ['complete','partial','failed']); choice(x.workflow_status, ['pending','running','completed','blocked','failed','unknown']);
  rows(x.workers, ['id','platform','status','result_status','missing_inputs','contradictions','stale_sources','recovery_hints'], r => { if (!ID.test(r.id)) fail(); if (r.platform !== null) choice(r.platform,PLATFORMS); choice(r.status,['pending','running','completed','failed','skipped']); choice(r.result_status, ['ok','needs_input','blocked','failed',null]); ['missing_inputs','contradictions','stale_sources','recovery_hints'].forEach(k => strings(r[k])); });
  rows(x.accounts, ['platform','account_key','window','currency'], r => { choice(r.platform,PLATFORMS); hash(r.account_key); object(r.window,['start','end']); str(r.window.start); str(r.window.end); if (r.window.start > r.window.end) fail(); if (!/^[A-Z]{3}$/.test(r.currency)) fail(); });
  rows(x.findings, ['platform','account_key','finding','control_title','severity','claim_ids','source_ids','evidence_status'], r => {
    str(r.control_title); if (r.control_title.length > 200) fail();
    choice(r.platform,PLATFORMS); if (r.account_key !== null) hash(r.account_key); optionalObject(r.finding,['schema_version','control_id','status','evidence','confidence','observation','diagnosis','recommendation'],['source_classification','score_contribution']); if (r.finding.schema_version !== '1.0.0') fail(); list(r.finding.evidence); if (r.finding.evidence.some(e => !e || typeof e !== 'object' || Array.isArray(e))) fail();
    ['control_id','status','confidence','observation','diagnosis','recommendation'].forEach(k => str(r.finding[k]));
    choice(r.finding.status, ['pass','fail','unknown','not_applicable']); choice(r.finding.confidence,['high','medium','low','none']); if (['pass','fail'].includes(r.finding.status) && !r.finding.evidence.length) fail(); if ('source_classification' in r.finding) choice(r.finding.source_classification,['evidence_based','practitioner','contested','folklore']); if ('score_contribution' in r.finding && r.finding.score_contribution !== null && !Number.isFinite(r.finding.score_contribution)) fail();
    strings(r.claim_ids); strings(r.source_ids); choice(r.evidence_status,['current','stale','demoted','missing','contested','provisional']);
    choice(r.severity,['critical','high','medium','informational']);
  });
  rows(x.claims, ['id','statement','verdict','classification','last_verified','refresh_due','effective_status','source_ids','control_ids'], r => { ['id','statement','verdict','classification','effective_status'].forEach(k => str(r[k])); for (const k of ['last_verified','refresh_due']) if (r[k] !== null) str(r[k]); strings(r.source_ids); strings(r.control_ids); });
  rows(x.sources, ['id','title','locator','retrieved_at','refresh_due','confidence','status','claim_ids','control_ids'], r => { ['id','title','confidence','status'].forEach(k => str(r[k])); for (const k of ['retrieved_at','refresh_due']) if (r[k] !== null) str(r[k]); if (r.locator !== null) { str(r.locator); if (!/^https?:\/\//.test(r.locator)) fail(); } strings(r.claim_ids); strings(r.control_ids); });
  rows(x.inputs, ['id','path','kind','contract','platform','sha256','validation','details'], r => { if (!ID.test(r.id)) fail(); relative(r.path); choice(r.kind,['json','csv']); if (r.contract !== null) str(r.contract); if (r.platform !== null) choice(r.platform,PLATFORMS); hash(r.sha256); choice(r.validation,['unchecked','valid','invalid','missing']); strings(r.details); });
  rows(x.artifacts, ['path','kind','sha256','size'], r => { relative(r.path); str(r.kind); hash(r.sha256); if (!Number.isSafeInteger(r.size) || r.size < 0) fail(); });
  rows(x.scoring, ['platform','health_score','evidence_coverage','status','profile_status'], r => { choice(r.platform,PLATFORMS); choice(r.status,['normal','provisional','insufficient_evidence']); choice(r.profile_status,['enabled','disabled']); for (const key of ['health_score','evidence_coverage']) if (r[key] !== null && (typeof r[key] !== 'number' || !Number.isFinite(r[key]) || r[key] < 0 || r[key] > 100)) fail(); if (r.evidence_coverage === null || (r.profile_status === 'disabled' && (r.health_score !== null || r.evidence_coverage !== 0))) fail(); });
  rows(x.receipts,['path','sha256','size','receipt'], r => { relative(r.path); hash(r.sha256); if (!Number.isSafeInteger(r.size) || r.size < 0) fail(); receiptWire(r.receipt); if (r.receipt.run_id !== x.run_id || r.path !== `cockpit/receipts/${r.receipt.action_id}.json`) fail(); });
  strings(x.permitted_actions); if (x.permitted_actions.some(v => !OPS.includes(v))) fail(); strings(x.limitations);
  if (x.comparison !== null) {
    object(x.comparison,['baseline_run_id','comparable','differences','findings']); str(x.comparison.baseline_run_id); if (typeof x.comparison.comparable !== 'boolean') fail(); strings(x.comparison.differences);
    rows(x.comparison.findings,['platform','control_id','change','baseline_status','current_status'], r => { choice(r.platform,PLATFORMS); str(r.control_id); choice(r.change,['new_failure','new_finding','newly_unknown','not_retested','status_changed','unchanged']); for (const k of ['baseline_status','current_status']) choice(r[k],['pass','fail','unknown','not_applicable',null]); });
  }
  return x;
}
export function receiptWire(x) {
  object(x,['schema_version','artifact_type','action_id','run_id','operation','started_at','finished_at','outcome','input_fingerprint','policy_fingerprint','outputs','diagnostics']);
  if (x.schema_version !== '1.0.0' || x.artifact_type !== 'cockpit-action-receipt' || !ID.test(x.run_id)) fail();
  if (!ID.test(x.action_id)) fail(); timestamp(x.started_at); timestamp(x.finished_at); if (Date.parse(x.finished_at) < Date.parse(x.started_at)) fail(); choice(x.operation,OPS); choice(x.outcome,['succeeded','failed','blocked']); hash(x.input_fingerprint); hash(x.policy_fingerprint); strings(x.diagnostics);
  rows(x.outputs,['path','sha256','size'], r => { relative(r.path); hash(r.sha256); if (!Number.isSafeInteger(r.size) || r.size < 0) fail(); }); return x;
}
export function demoWire(x) {
  object(x,['interface_version','runs_root','policy_root','steps']);
  if (x.interface_version !== '1.0.0') fail(); str(x.runs_root); str(x.policy_root);
  rows(x.steps,['run_id','title','baseline_id','tab'], r => { if (!ID.test(r.run_id)) fail(); str(r.title); if (r.baseline_id !== null && !ID.test(r.baseline_id)) fail(); choice(r.tab,TABS); });
  if (!x.steps.length) fail(); return x;
}

export function preparedDemoWire(x, protectedRoots = []) {
  object(x,['interface_version','runs_root','policy_root']);
  if (x.interface_version !== '1.0.0' || !absolutePath(x.runs_root) || !absolutePath(x.policy_root)) fail();
  const normalize = value => value.replaceAll('\\','/').replace(/\/$/,'').toLowerCase();
  const root = normalize(x.runs_root), policy = normalize(x.policy_root);
  if (!/\/claude-ads-demo-[a-z0-9_-]+\/runs$/.test(root) || policy !== root + '/_policy') fail();
  for (const protectedRoot of protectedRoots) {
    const real = normalize(protectedRoot);
    if (root === real || root.startsWith(real + '/') || real.startsWith(root + '/')) fail();
  }
  return x;
}
