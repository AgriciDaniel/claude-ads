// Usage: node tests/preview.mjs [tab] [width] [scenario]
// Draws the pane as plain text from synthetic fixtures. Approximate: no color, simplified Button chrome.
import { drawPane, drawBand } from '../hooks/views.mjs';
import { emptyView } from '../hooks/controller.mjs';
import { fakeUi, renderText } from './render-text.mjs';
import { snapshot, receipt } from './fixtures.mjs';

const H = 'a'.repeat(64);
export function scenario(name) {
  const s = snapshot('demo-needs-input', 'running');
  if (name === 'needs-input') {
    s.workers = [{ id: 'google-worker', platform: 'google', status: 'running', result_status: 'needs_input', missing_inputs: ['Supply keyword-evidence (keyword-evidence.json) with both positive and negative keywords'], contradictions: [], stale_sources: [], recovery_hints: ['Supply fixture file'] }];
    s.findings = [{ platform: 'google', account_key: null, finding: { schema_version: '1.0.0', control_id: 'G14', status: 'unknown', evidence: [], confidence: 'none', observation: 'No keyword evidence was supplied.', diagnosis: 'Keyword governance cannot be judged without positive and negative keywords.', recommendation: 'Supply keyword-evidence.json, then check the input.' }, severity: 'informational', claim_ids: ['claim-g14'], source_ids: ['source-g14'], evidence_status: 'current' }];
    s.claims = [{ ...s.claims[0], id: 'claim-g14', effective_status: 'current', control_ids: ['G14'], source_ids: ['source-g14'] }];
    s.sources = [{ ...s.sources[0], id: 'source-g14', status: 'current', claim_ids: ['claim-g14'], control_ids: ['G14'] }];
    s.inputs = [];
    s.limitations = ['Evidence freshness evaluates dated ledgers; no live verification was performed', 'Local checks do not establish advertising truth or release readiness', 'Some indexed inputs are invalid, missing or unchecked'];
  }
  if (name === 'done') {
    s.workflow_status = 'completed'; s.completeness = 'complete';
    s.workers[0] = { ...s.workers[0], status: 'completed', result_status: 'ok', missing_inputs: [], stale_sources: [] };
    s.claims[0].effective_status = 'current'; s.sources[0].status = 'current'; s.findings[0].evidence_status = 'current';
    s.receipts = [{ path: 'cockpit/receipts/action-demo.json', sha256: H, size: 42, receipt: { ...receipt('demo-needs-input', 'render-report'), action_id: 'action-demo', outputs: [{ path: 'cockpit/reports/r1/report.html', sha256: H, size: 18432 }], diagnostics: [] } }];
  }
  return s;
}
const controls = new Proxy({}, { get: () => () => {} });
export function draw(tab, width, name = 'needs-input', extra = {}) {
  const state = { ...emptyView(), visible: true, selected: 'demo-needs-input', tab, snapshot: scenario(name), ...extra };
  return renderText(drawPane(fakeUi(), state, controls, width), width + 4);
}
if (import.meta.url === `file://${process.argv[1]}`) {
  const [tab = 'Run', width = '72', name = 'needs-input'] = process.argv.slice(2);
  const demo = name === 'needs-input' ? { demo: { index: 0, steps: Array.from({ length: 7 }, (_, i) => ({ title: i === 0 ? 'Identify missing synthetic keyword evidence' : `Step ${i + 1}`, run_id: 'x', tab: 'Run', baseline_id: null })) } } : {};
  const r = draw(tab, Number(width), name, demo);
  console.log(r.text);
  if (r.tooWide.length) console.log('\nTOO WIDE:', r.tooWide.length);
}
