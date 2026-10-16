import { MESSAGES } from './lexicon.mjs';
import { doctorWire, snapshotWire, receiptWire, demoWire, preparedDemoWire, TABS } from './wire.mjs';
export function emptyView() {
  return { visible: false, selected: null, tab: 'Run', snapshot: null, doctor: null, receipt: null, error: null, busy: false, demo: null, baseline: '', context: null, details: false, page: 0, filter: 'all' };
}
// IDs and relative paths may contain punctuation. Match the complete literal
// reference bounded by characters outside either token alphabet, never a word fragment.
function hasLiteralReference(text, reference) {
  const tokenCharacter = value => value !== undefined && /[\p{L}\p{N}\p{M}_./\\%-]/u.test(value);
  let offset = 0;
  while (offset < text.length) {
    const index = text.indexOf(reference, offset);
    if (index === -1) return false;
    const end = index + reference.length;
    if (!tokenCharacter(text[index - 1]) && !tokenCharacter(text[end])) return true;
    offset = end;
  }
  return false;
}
const SHOWN = new Set([MESSAGES.setup, MESSAGES.runs, MESSAGES.didNotFinish, MESSAGES.refused, MESSAGES.incompatible, MESSAGES.badId]);
// Original controller. Every dependent effect rechecks its captured generation.
export function createController(adapter) {
  let state = emptyView();
  let epoch = 0;
  let timer = null;
  let refreshBusy = false;
  let actionBusy = false;
  let pendingWork = false;
  let publishQueue = Promise.resolve();
  const publish = () => {
    const view = JSON.parse(JSON.stringify(state));
    publishQueue = publishQueue.then(() => adapter.publish(view));
    return publishQueue;
  };
  const stop = () => { if (timer) timer.cancel(); timer = null; };
  const roots = () => state.demo ? { runsRoot: state.demo.runsRoot, policyRoot: state.demo.policyRoot } : {};
  const generation = ticket => epoch === ticket && state.visible;
  const selection = (ticket, runId, baseline) => generation(ticket) && state.selected === runId && state.baseline === baseline;
  // Polling runs only while the pane is drawn. An undrawn, closed or backgrounded pane costs no process.
  // If the adapter cannot say, the answer is "not drawn": the safe side is to start nothing.
  const drawn = async () => {
    if (typeof adapter.isDrawn !== 'function') return true;
    try { return (await adapter.isDrawn()) === true; } catch { return false; }
  };
  // The timer callback never rejects: a failure ends this tick, and the next one is armed by the tick itself.
  const tick = async () => {
    timer = null;
    if (!(await drawn())) { schedule(); return; }
    await refresh();
  };
  const schedule = () => {
    stop();
    if (state.visible && state.selected && pendingWork) timer = adapter.after(5000, () => tick().catch(() => { schedule(); }));
  };
  // Only fixed, path-free messages reach the screen. A raw error (a path, stderr, account data) never does.
  const diagnose = error => (typeof error?.message === 'string' && (error.message.startsWith('Engine response') || SHOWN.has(error.message)) ? error.message : MESSAGES.unavailable);
  async function probe(request = roots()) {
    const value = doctorWire(await adapter.call('doctor', request));
    if (value.status !== 'ok') throw new Error('Engine response is blocked. Check policy and the configured engine.');
    return value;
  }
  async function load(ticket, runId, baseline, boundRoots) {
    const matches = () => selection(ticket, runId, baseline);
    if (!matches()) return null;
    const doctor = await probe(boundRoots);
    if (!matches()) return null;
    // A plain snapshot anchors the comparison's current run and policy subject.
    const anchor = snapshotWire(await adapter.call('snapshot', { ...boundRoots, runId }));
    if (!matches()) return null;
    if (anchor.run_id !== runId || anchor.comparison !== null) throw new Error('Engine response has a mismatched selection.');
    if (!baseline) return { doctor, snapshot: anchor };
    const compared = snapshotWire(await adapter.call('compare', { ...boundRoots, runId, baselineId: baseline }));
    if (!matches()) return null;
    if (compared.run_id !== runId || compared.comparison?.baseline_run_id !== baseline
        || compared.fingerprint !== anchor.fingerprint || compared.policy_fingerprint !== anchor.policy_fingerprint) {
      throw new Error('Engine response has a mismatched comparison subject.');
    }
    return { doctor, snapshot: compared };
  }
  async function chooser() {
    stop(); pendingWork = false; const ticket = ++epoch;
    state = { ...emptyView(), visible: true, busy: true };
    await publish();
    if (!generation(ticket)) return;
    try {
      const doctor = await probe({});
      if (generation(ticket)) state = { ...state, doctor, busy: false };
    } catch (e) { if (generation(ticket)) state = { ...state, error: diagnose(e), busy: false }; }
    if (generation(ticket)) await publish();
  }
  async function select(runId, tab = 'Run', baseline = '', retainTicket = null) {
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(runId) || (baseline && (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(baseline) || baseline === runId))) return;
    if (retainTicket !== null && !generation(retainTicket)) return;
    stop(); pendingWork = false; const ticket = retainTicket === null ? ++epoch : retainTicket; const boundRoots = roots();
    state = { ...state, visible: true, selected: runId, tab, baseline, context: null, snapshot: null, receipt: null, error: null, busy: true, page: 0, filter: 'all' };
    await publish();
    if (!selection(ticket,runId,baseline)) return;
    try {
      const loaded = await load(ticket, runId, baseline, boundRoots);
      if (loaded && selection(ticket,runId,baseline)) {
        pendingWork = ['pending','running'].includes(loaded.snapshot.workflow_status);
        state = { ...state, ...loaded, busy: false };
      }
    } catch (e) { if (selection(ticket,runId,baseline)) state = { ...state, error: diagnose(e), busy: false }; }
    if (selection(ticket,runId,baseline)) { await publish(); if (selection(ticket,runId,baseline)) schedule(); }
  }
  async function refresh() {
    if (!state.visible || !state.selected || refreshBusy || actionBusy) { schedule(); return; }
    refreshBusy = true; const ticket = epoch; const runId = state.selected; const boundRoots = roots(); const baseline = state.baseline;
    try {
      const loaded = await load(ticket, runId, baseline, boundRoots);
      if (loaded && selection(ticket,runId,baseline)) {
        pendingWork = ['pending','running'].includes(loaded.snapshot.workflow_status);
        state = { ...state, ...loaded, context: loaded.snapshot.fingerprint === state.snapshot?.fingerprint ? state.context : null, error: null };
      }
    } catch (e) { if (selection(ticket,runId,baseline)) state = { ...state, snapshot: null, error: diagnose(e) }; }
    finally {
      refreshBusy = false;
      if (selection(ticket,runId,baseline)) { await publish(); if (selection(ticket,runId,baseline)) schedule(); }
    }
  }
  // For a turn end: refresh only a visible run that is still queued or running, and only while drawn.
  async function refreshIfPending() {
    if (!state.visible || !state.selected || !pendingWork || !(await drawn())) return;
    await refresh();
  }
  async function action(operation, inputId = null, format = 'markdown', subject) {
    if (!subject || subject.runId !== state.selected || subject.fingerprint !== state.snapshot?.fingerprint || subject.policyFingerprint !== state.snapshot?.policy_fingerprint) return;
    if (actionBusy || refreshBusy || state.busy || state.error || !state.visible || !state.selected || !state.snapshot || !state.snapshot.permitted_actions.includes(operation)) return;
    if (operation === 'validate-input' && !state.snapshot.inputs.some(input => input.id === inputId)) return;
    const runId = state.selected, baseline = state.baseline, fingerprint = state.snapshot.fingerprint, policyFingerprint = state.snapshot.policy_fingerprint;
    const ticket = epoch, boundRoots = roots(); const matches = () => selection(ticket,runId,baseline) && state.snapshot?.fingerprint === fingerprint && state.snapshot?.policy_fingerprint === policyFingerprint;
    let actionFailure = null;
    actionBusy = true; stop(); state = { ...state, busy: true, error: null, receipt: null }; await publish();
    try {
      if (!matches()) return;
      await probe(boundRoots);
      if (!matches()) return;
      const receipt = receiptWire(await adapter.call('action', { ...boundRoots, runId, operation, fingerprint, format, ...(inputId ? { inputId } : {}) }));
      if (!matches()) return;
      if (receipt.run_id !== runId || receipt.operation !== operation || receipt.input_fingerprint !== fingerprint || receipt.policy_fingerprint !== policyFingerprint) throw new Error('Engine response has a mismatched receipt.');
      state = { ...state, receipt };
    } catch (e) { if (selection(ticket,runId,baseline)) { actionFailure = diagnose(e); state = { ...state, error: actionFailure }; } }
    finally {
      actionBusy = false;
      if (selection(ticket,runId,baseline)) {
        state = { ...state, busy: false }; await publish();
        if (selection(ticket,runId,baseline)) await refresh();
        if (actionFailure && selection(ticket,runId,baseline)) { state = { ...state, error: actionFailure }; await publish(); }
      }
    }
  }
  async function demo() {
    stop(); pendingWork = false; const ticket = ++epoch;
    state = { ...emptyView(), visible: true, busy: true }; await publish();
    if (!generation(ticket)) return;
    try {
      await probe({});
      if (!generation(ticket)) return;
      const destination = preparedDemoWire(await adapter.call('prepare-demo', {}), adapter.protectedRoots || []);
      if (!generation(ticket)) return;
      const setup = demoWire(await adapter.call('demo', { runsRoot: destination.runs_root, policyRoot: destination.policy_root }));
      if (!generation(ticket)) return;
      if (setup.runs_root !== destination.runs_root || setup.policy_root !== destination.policy_root) throw new Error('Engine response has a mismatched demo destination.');
      const demo = { runsRoot: setup.runs_root, policyRoot: setup.policy_root, steps: setup.steps, index: 0 };
      state = { ...state, demo, busy: false };
      const first = demo.steps[0];
      await select(first.run_id, first.tab, first.baseline_id || '', ticket);
    } catch (e) { if (generation(ticket)) { state = { ...state, busy: false, error: diagnose(e) }; await publish(); } }
  }
  async function step(delta) {
    if (!state.demo || state.busy || actionBusy) return;
    const index = Math.max(0, Math.min(state.demo.steps.length - 1, state.demo.index + delta));
    state = { ...state, demo: { ...state.demo, index } };
    const item = state.demo.steps[index]; await select(item.run_id, item.tab, item.baseline_id || '');
  }
  async function hide() { stop(); pendingWork = false; epoch++; state = emptyView(); await publish(); }
  async function tab(value) { if (state.visible && TABS.includes(value)) { state = { ...state, tab: value, page: 0 }; await publish(); } }
  async function details() { if (state.visible && state.selected) { state = { ...state, details: !state.details, page: 0 }; await publish(); } }
  // Paging and filtering only change what is drawn from the cached snapshot. No process runs.
  async function page(delta) { if (state.visible && (delta === 1 || delta === -1)) { state = { ...state, page: Math.max(0, state.page + delta) }; await publish(); } }
  // Leave a opened check or input and return to the list. No process runs.
  async function clearContext() { if (state.visible && state.selected && state.context) { state = { ...state, context: null, page: 0 }; await publish(); } }
  async function filter() { if (state.visible && state.selected) { const order = ['all', 'fail', 'unknown', 'pass']; state = { ...state, filter: order[(order.indexOf(state.filter) + 1) % order.length], page: 0 }; await publish(); } }
  async function navigate(tab, target, runId, fingerprint) {
    // Cached navigation is bound to the rendered run and its exact input subject.
    if (!state.visible || state.selected !== runId || !state.snapshot || state.snapshot.fingerprint !== fingerprint) return;
    let context;
    if (tab === 'Inputs') {
      const worker = state.snapshot.workers.find(item => item.id === target?.workerId);
      if (!worker || !worker.missing_inputs.includes(target.missingInput)) return;
      const textMatches = state.snapshot.inputs.filter(input => hasLiteralReference(target.missingInput,input.id) || hasLiteralReference(target.missingInput,input.path));
      const related = textMatches.length ? textMatches : state.snapshot.inputs.filter(input => worker.platform && input.platform === worker.platform);
      context = { kind: 'inputs', workerId: worker.id, missingInput: target.missingInput, inputIds: related.map(input => input.id), match: textMatches.length ? 'text' : related.length ? 'platform' : 'none' };
    } else if (tab === 'Evidence') {
      const finding = state.snapshot.findings.find(item => item.platform === target?.platform && item.finding.control_id === target.controlId);
      if (!finding) return;
      context = { kind: 'finding', platform: finding.platform, controlId: finding.finding.control_id };
    } else return;
    state = { ...state, tab, context, page: 0 }; await publish();
  }
  async function baseline(value) {
    if (state.visible && state.selected && /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(value) && value !== state.selected) await select(state.selected, 'Compare', value);
  }
  async function doctor() {
    const ticket = epoch;
    try { const result = doctorWire(await adapter.call('doctor', roots())); if (epoch === ticket) { state = { ...state, doctor: result, error: result.status === 'ok' ? null : 'Engine policy is blocked.' }; await publish(); } return result.status; }
    catch (e) { if (epoch === ticket) { state = { ...state, error: diagnose(e) }; await publish(); } return 'unavailable'; }
  }
  return { chooser, select, open: runId => { state = emptyView(); return select(runId); }, version: () => epoch, refresh, refreshIfPending, action, demo, step, hide, tab, details, page, filter, clearContext, navigate, baseline, doctor, reset: () => state.demo ? step(-state.demo.index) : chooser(), view: () => state, dispose: hide };
}
