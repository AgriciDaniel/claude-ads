// Hook-level and rendering tests for the first-run message, turn-end polling, hotkey labels, label
// sanitising, control keys, path rules, narrow tables and plain wording.
import { expect, mock, test } from 'claude-code/testing';
import { drawPane, drawBand } from '../hooks/views.mjs';
import { makeKit } from '../hooks/kit.mjs';
import { emptyView, createController } from '../hooks/controller.mjs';
import { absolutePath, binding } from '../hooks/launcher.mjs';
import { MESSAGES } from '../hooks/lexicon.mjs';
import { oneLine, snapshotWire } from '../hooks/wire.mjs';
import { doctor, snapshot, H } from './fixtures.mjs';
import { fakeUi, renderText } from './render-text.mjs';

const CONFIG = { coreRoot: '/synthetic/core', pythonExecutable: '/synthetic/python', runsRoot: '/synthetic/runs' };
const PANE = { plugin: 'ads-cockpit', component: 'Pane', requestId: 'ads-cockpit', viewport: { columns: 100, rows: 30 }, props: { title: 'Claude Ads Cockpit', isFocused: true, bodyColumns: 60, placement: 'inline', scroll: { offset: 0, bodyRows: 10 }, view: {} } } as const;
const BAND = { plugin: 'ads-cockpit', component: 'AbovePrompt', requestId: 'band', viewport: { columns: 100, rows: 30 }, props: { hasSurvey: false, isWorking: false, maxRows: 5, bodyColumns: 60, scroll: { offset: 0, bodyRows: 5 }, view: {} } } as const;
const TURN = { answer: '', durationMs: 5, isAborted: false, turnId: 'turn-1', reason: 'answer' } as const;
const noControls = { chooser: () => {}, select: () => {}, refresh: () => {}, hide: () => {}, demo: () => {}, step: () => {}, reset: () => {}, tab: () => {}, baseline: () => {}, action: () => {}, navigate: () => {}, workbench: () => {}, details: () => {} };
const TABS = ['Run', 'Evidence', 'Inputs', 'Compare', 'Reports'];
const walk = node => (!node ? [] : [node, ...(node.children || []).flatMap(child => (typeof child === 'object' ? walk(child) : []))]);
const view = (tab, value = snapshot(), extra = {}) => ({ ...emptyView(), visible: true, selected: 'demo-run', tab, snapshot: value, ...extra });
const text = (state, width = 72, ui = fakeUi()) => renderText(drawPane(ui, state, noControls, width), width + 4);
const buttons = (state, width = 72) => walk(drawPane(fakeUi(), state, noControls, width)).filter(n => n?.type === 'Button');
const allText = node => walk(node).flatMap(n => (typeof n === 'object' ? (n.children ?? []).filter(c => typeof c === 'string') : []));

// A host rig: the process stub answers the core's commands from fixtures and counts them. The stubs
// read the mutable `world`, so one test can change what the host says part way through.
function rig($, on, { status = 'running', panes = true, hold = null } = {}) {
  const log = { processes: [] as string[], opens: 0, closes: [] as string[], turns: 0 };
  const world = { status, panes, hold, failure: '' };
  on('session.surfaces', () => ({ value: ['terminal'] }));
  on('ui.open', () => { log.opens++; return { value: { isPlaced: true } }; });
  on('ui.close', (_$, e) => { log.closes.push(e.id); return { value: undefined }; });
  on('ui.render', () => ({ type: 'Text', props: {}, children: ['other band'] }));
  on('turn.complete', () => { log.turns++; return { text: '' }; });
  on('ui.panes', () => ({ value: world.panes === 'background' ? [{ id: 'ads-cockpit', title: 't', isShown: false, isFocused: false, isPlaced: true }] : world.panes ? [{ id: 'ads-cockpit', title: 'Claude Ads Cockpit', isShown: true, isFocused: false, isPlaced: true }] : [] }));
  on('process.run', async (_$, e) => {
    const command = e.argv[7];
    log.processes.push(command);
    if (world.failure) throw new Error(world.failure);
    if (world.hold && world.hold.active && command === 'snapshot') await world.hold.promise;
    const body = command === 'doctor' ? doctor : snapshot('demo-run', world.status);
    return { value: { exitCode: 0, stdout: JSON.stringify(body), stderr: '', isStdoutTruncated: false, isStderrTruncated: false } };
  });
  return { log, world };
}
const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return { promise, resolve, active: true }; };

// 1. First run: an unconfigured install tells the person what to set, in plain words, without paths.
test('controller shows the setup message instead of a generic failure', async () => {
  const fail = message => createController({ after: () => ({ cancel() {} }), publish: async () => {}, call: async () => { throw new Error(message); } });
  for (const open of ['chooser', 'demo', 'select', 'doctor'] as const) {
    const c = fail(MESSAGES.setup);
    if (open === 'select') await c.select('demo-run'); else await c[open]();
    expect(c.view().error).toBe(MESSAGES.setup);
  }
  expect(MESSAGES.setup).toMatch(/coreRoot/); expect(MESSAGES.setup).toMatch(/pythonExecutable/); expect(MESSAGES.setup).toMatch(/claude plugin configure ads-cockpit/);
  expect(MESSAGES.setup).not.toMatch(/[\\/]/);
  const runs = fail(MESSAGES.runs); await runs.select('demo-run'); expect(runs.view().error).toBe(MESSAGES.runs); expect(MESSAGES.runs).toMatch(/runsRoot/);
});
test('only fixed messages are shown; raw errors, paths and stderr collapse to the generic line', async () => {
  for (const raw of ['/private/client secret=1', 'Traceback: /srv/app/core.py line 3', 'EACCES: /var/data/python']) {
    const c = createController({ after: () => ({ cancel() {} }), publish: async () => {}, call: async () => { throw new Error(raw); } });
    await c.chooser(); expect(c.view().error).toBe(MESSAGES.unavailable);
  }
  for (const fixed of [MESSAGES.didNotFinish, MESSAGES.refused, MESSAGES.incompatible, MESSAGES.badId]) {
    const c = createController({ after: () => ({ cancel() {} }), publish: async () => {}, call: async () => { throw new Error(fixed); } });
    await c.chooser(); expect(c.view().error).toBe(fixed);
  }
});
test('an unconfigured install shows the setup message in the chooser, demo, band and doctor', async ($, on) => {
  rig($, on);
  const reply = await $.command.run({ command: 'ads-cockpit', args: '' });
  expect(reply).toEqual({});
  let pane = await $.ui.mount({ ...PANE, surface: 'terminal' });
  expect(await pane.find({ type: 'Text', text: MESSAGES.setup })).toBeDefined();
  await pane.unmount();
  await $.command.run({ command: 'ads-cockpit', args: 'demo' });
  pane = await $.ui.mount({ ...PANE, surface: 'terminal' });
  expect(await pane.find({ type: 'Text', text: MESSAGES.setup })).toBeDefined();
  expect(await pane.find({ key: 'demo' })).toBeDefined();
  await pane.unmount();
  const band = await $.ui.mount({ ...BAND, surface: 'terminal' });
  expect(await band.find({ type: 'Text', text: MESSAGES.bandSetup })).toBeDefined();
  await band.unmount();
  const doctorReply = await $.command.run({ command: 'ads-cockpit', args: 'doctor' });
  expect(doctorReply.text).toContain('unavailable'); expect(doctorReply.text).toContain(MESSAGES.setup);
});
test('a failing interpreter shows a fixed message and never its path or stderr', { options: CONFIG }, async ($, on) => {
  const { world } = rig($, on);
  world.failure = 'spawn /synthetic/secret/python ENOENT';
  await $.command.run({ command: 'ads-cockpit', args: '' });
  const pane = await $.ui.mount({ ...PANE, surface: 'terminal' });
  expect(await pane.find({ type: 'Text', text: MESSAGES.didNotFinish })).toBeDefined();
  expect(await pane.find({ type: 'Text', text: /secret/ })).toBe(undefined);
  await pane.unmount();
});

// 2. Hooks: turn end, timers, session start, pane close.
test('turn.complete spawns nothing for a finished run', { options: CONFIG }, async ($, on) => {
  const { log } = rig($, on, { status: 'completed' });
  await $.command.run({ command: 'ads-cockpit', args: 'open demo-run' });
  const before = log.processes.length;
  expect(before).toBe(2);
  await $.turn.complete(TURN);
  await $.turn.complete(TURN);
  expect(log.turns).toBe(2);
  expect(log.processes.length).toBe(before);
});
test('turn.complete spawns nothing when no run is open', { options: CONFIG }, async ($, on) => {
  const { log } = rig($, on);
  await $.turn.complete(TURN);
  await $.command.run({ command: 'ads-cockpit', args: '' });
  await $.turn.complete(TURN);
  expect(log.processes.every(command => command === 'doctor')).toBe(true);
  expect(log.processes.length).toBe(1);
});
test('turn.complete refreshes a pending run in the background and never waits on it', { options: CONFIG }, async ($, on) => {
  const hold = deferred(); hold.active = false;
  const { log } = rig($, on, { status: 'running', hold });
  mock.clock(on);
  await $.command.run({ command: 'ads-cockpit', args: 'open demo-run' });
  const before = log.processes.length;
  hold.active = true;
  // The refresh is stuck inside the core call, and the turn still ends.
  const result = await $.turn.complete(TURN);
  expect(result).toBeDefined(); expect(log.turns).toBe(1);
  expect(log.processes.length).toBeGreaterThan(before);
  hold.active = false; hold.resolve();
});
test('polling pauses while the pane is not drawn and resumes when it is', { options: CONFIG }, async ($, on) => {
  const { log, world } = rig($, on, { status: 'running' });
  const clock = mock.clock(on);
  await $.command.run({ command: 'ads-cockpit', args: 'open demo-run' });
  let count = log.processes.length;
  await clock.advance(5000);
  expect(log.processes.length).toBeGreaterThan(count);
  count = log.processes.length;
  world.panes = false;
  await clock.advance(5000); await clock.advance(5000);
  expect(log.processes.length).toBe(count);
  await $.turn.complete(TURN);
  expect(log.processes.length).toBe(count);
  world.panes = true;
  await clock.advance(5000);
  expect(log.processes.length).toBeGreaterThan(count);
});
test('a pane that is placed but a background tab is not polled', { options: CONFIG }, async ($, on) => {
  const { log } = rig($, on, { status: 'running', panes: 'background' });
  const clock = mock.clock(on);
  await $.command.run({ command: 'ads-cockpit', args: 'open demo-run' });
  const count = log.processes.length;
  await clock.advance(5000);
  expect(log.processes.length).toBe(count);
});
test('a failing poll ends quietly and the next one is armed', { options: CONFIG }, async ($, on) => {
  const { log, world } = rig($, on, { status: 'running' });
  const clock = mock.clock(on);
  await $.command.run({ command: 'ads-cockpit', args: 'open demo-run' });
  world.failure = 'boom /synthetic/secret';
  await clock.advance(5000);
  const band = await $.ui.mount({ ...BAND, surface: 'terminal' });
  expect(await band.find({ type: 'Text', text: MESSAGES.bandUnavailable })).toBeDefined();
  await band.unmount();
  world.failure = '';
  const count = log.processes.length;
  await clock.advance(5000);
  expect(log.processes.length).toBeGreaterThan(count);
});
test('session.start survives a command name clash and still reaches the rest of the chain', { options: CONFIG }, async ($, on) => {
  let reached = false; const logged = [] as string[];
  on('command.register', () => ({ deny: 'name already taken' }));
  on('ui.log', (_$, e) => { logged.push(e.text); return { value: undefined }; });
  on('session.start', (_$, e) => { reached = true; return { cwd: e.cwd }; });
  rig($, on);
  const started = await $.session.start({ surface: 'terminal', isInteractive: true, cwd: '/synthetic/session' });
  expect(reached).toBe(true); expect(started).toEqual({ cwd: '/synthetic/session' });
  // The catch ran inside the hook: the clash is noted in the debug log, and the hook was not skipped.
  expect(logged.some(line => line.includes('could not be registered'))).toBe(true);
});
test('closing the pane hides the cockpit, clears the band and stops polling', { options: CONFIG }, async ($, on) => {
  const { log } = rig($, on, { status: 'running' });
  const clock = mock.clock(on);
  await $.command.run({ command: 'ads-cockpit', args: 'open demo-run' });
  const pane = await $.ui.mount({ ...PANE, surface: 'terminal' });
  let band = await $.ui.mount({ ...BAND, surface: 'terminal' });
  expect(await band.find({ key: 'open-workbench' })).toBeDefined();
  // The Hide button closes the pane through the host, which raises ui.close for the module's hook.
  await pane.press({ key: 'hide' });
  expect(log.closes).toEqual(['ads-cockpit']);
  expect(await band.find({ key: 'open-workbench' })).toBe(undefined);
  await band.unmount(); await pane.unmount();
  const count = log.processes.length;
  await clock.advance(5000); await clock.advance(5000);
  await $.turn.complete(TURN);
  expect(log.processes.length).toBe(count);
  band = await $.ui.mount({ ...BAND, surface: 'terminal' });
  expect(await band.find({ type: 'Text', text: 'other band' })).toBeDefined();
  await band.unmount();
});

// 3. Hotkeys are named on framed buttons, where the terminal does not draw them.
test('framed buttons name their key and plain ones are left alone', () => {
  const run = buttons(view('Run'));
  expect(run.find(b => b.props.key === 'verdict-action').props.label).toMatch(/ \(g\)$/);
  expect(buttons(view('Reports')).map(b => [b.props.key, b.props.label])).toEqual(expect.arrayContaining([['render-markdown', 'Markdown (m)'], ['render-html', 'HTML (l)'], ['render-pdf', 'PDF (p)'], ['validate-run', 'Check run (k)']]));
  expect(buttons(view('Inputs')).find(b => b.props.key === 'validate-run').props.label).toBe('Check whole run (k)');
  expect(buttons({ ...emptyView(), visible: true, doctor }).find(b => b.props.key === 'demo').props.label).toBe('Start the practice demo (d)');
  const demo = { runsRoot: '/x', policyRoot: '/y', index: 0, steps: [{ run_id: 'a', title: 'First', tab: 'Run', baseline_id: null }, { run_id: 'b', title: 'Second', tab: 'Run', baseline_id: null }] };
  expect(buttons(view('Run', snapshot(), { demo })).find(b => b.props.key === 'demo-next').props.label).toBe('Next (n)');
  for (const b of buttons(view('Run'))) if (b.props.plain) expect(b.props.label).not.toMatch(/\(.\)$/);
  for (const tab of TABS) for (const b of buttons(view(tab))) if (b.props.hotkey && !b.props.plain) expect(b.props.label).toContain(`(${b.props.hotkey})`);
});
test('the coach lines name the keys they mention', () => {
  const steps = Array.from({ length: 8 }, (_, i) => ({ run_id: 'demo-run', title: `Step ${i + 1}`, tab: 'Run', baseline_id: null }));
  const line = index => text(view('Run', snapshot(), { demo: { runsRoot: '/x', policyRoot: '/y', index, steps } })).text.replace(/[│\n]+/g, ' ').replace(/\s+/g, ' ');
  expect(line(0)).toContain('Press Next (n)');
  expect(line(3)).toMatch(/Press the Check button beside it \(or k to check the whole run\)/);
});

// 4. Labels built from run data are one bounded line.
test('control titles with a tab or newline never reach a button label', () => {
  const s = snapshot();
  s.findings[0].control_title = 'First line\nsecond\tline\n\tthird';
  expect(() => snapshotWire(s)).not.toThrow();
  const many = Array.from({ length: 8 }, (_, i) => ({ ...s.findings[0], finding: { ...s.findings[0].finding, control_id: `G-${i}` } }));
  const big = { ...s, findings: many };
  for (const value of [s, big]) for (const tab of ['Run', 'Evidence']) for (const width of [34, 72, 160]) {
    for (const b of buttons(view(tab, value), width)) { expect(b.props.label).not.toMatch(/[\x00-\x1f\x7f-\x9f]/); expect(b.props.label.length).toBeLessThan(200); }
  }
  const labels = buttons(view('Run', s), 100).map(b => b.props.label).join('|');
  expect(labels).toContain('First line second line third');
  s.findings[0].control_title = 'x'.repeat(200);
  for (const b of buttons(view('Evidence', big), 160)) expect(b.props.label.length).toBeLessThan(200);
  expect(oneLine('a\n\tb   c')).toBe('a b c'); expect(oneLine('y'.repeat(500)).length).toBe(160);
});

test('the kit itself sanitises any label it is given', () => {
  const kit = makeKit(fakeUi(), 60);
  expect(kit.button('k', 'a\nb\tc  d', undefined, () => {}).props.label).toBe('a b c d');
  expect(kit.button('k', 'x'.repeat(500), 'g', () => {}).props.label.length).toBeLessThan(170);
  expect(kit.button('k', 'Go', 'g', () => {}, { plain: true }).props.label).toBe('Go');
});

// 5. Control keys stay distinct whatever an input is called.
test('an input called "run" cannot collide with the whole-run check', () => {
  const s = snapshot();
  s.inputs = [{ ...s.inputs[0], id: 'run', path: 'inputs/run.json' }, { ...s.inputs[0], id: 'render-markdown', path: 'inputs/r.json' }];
  for (const tab of TABS) for (const width of [34, 72]) {
    const keys = walk(drawPane(fakeUi(), view(tab, s), noControls, width)).filter(n => n?.type === 'Button' || n?.type === 'Input').map(n => n.props.key);
    expect(new Set(keys).size).toBe(keys.length);
  }
  const keys = buttons(view('Inputs', s)).map(b => b.props.key);
  expect(keys).toContain('validate-input-run'); expect(keys).toContain('validate-run'); expect(keys).toContain('validate-input-render-markdown');
  const calls = [];
  const tree = walk(drawPane(fakeUi(), view('Inputs', s), { ...noControls, action: (...args) => calls.push(args) }, 72));
  tree.find(n => n?.props?.key === 'validate-input-run').props.onPress();
  expect(calls[0].slice(0, 3)).toEqual(['validate-input', 'run', 'markdown']);
});

// 6. A drive letter or UNC path is never an absolute path on POSIX.
test('absolute paths follow the platform', () => {
  for (const bad of ['C:/Python/python.exe', 'C:\\Python\\python.exe', '\\\\server\\share\\python', '//server/share/python', 'relative/python', 'python3', '', '/', '/a/../b', '/a/./b', '/bad\npath', '/back\\slash']) expect(absolutePath(bad, 'linux')).toBe(false);
  for (const good of ['/usr/bin/python3', '/opt/ads core/python']) expect(absolutePath(good, 'linux')).toBe(true);
  for (const good of ['C:/Python/python.exe', 'C:\\Python\\python.exe', '/rooted/path']) expect(absolutePath(good, 'win32')).toBe(true);
  for (const bad of ['relative\\python', 'python.exe', 'C:python.exe', 'C:\\a\\..\\b', '']) expect(absolutePath(bad, 'win32')).toBe(false);
  if (globalThis.process?.platform !== 'win32') {
    expect(() => binding({ ...CONFIG, pythonExecutable: 'C:/Python/python.exe' })).toThrow(MESSAGES.setup);
    expect(() => binding({ ...CONFIG, coreRoot: '\\\\server\\share\\core' })).toThrow(MESSAGES.setup);
  }
});

// 7. Tables never ask for more room than the pane has.
test('table columns fit the available width at every size', () => {
  const rows = walk;
  const s = snapshot(); s.workers.push({ ...s.workers[0], id: 'worker-meta', platform: 'meta', status: 'failed', result_status: 'failed', missing_inputs: [], contradictions: [], stale_sources: [] });
  s.comparison = { baseline_run_id: 'older-run', comparable: true, differences: [], findings: [{ platform: 'google', control_id: 'G-DEMO', change: 'new_failure', baseline_status: null, current_status: 'fail' }] };
  for (const width of [30, 34, 40, 54, 72, 160]) for (const tab of TABS) {
    for (const node of rows(drawPane(fakeUi(), view(tab, s), noControls, width))) {
      if (node?.type !== 'Box' || node.props.flexDirection !== 'row' || node.props.flexWrap === 'wrap') continue;
      const cells = (node.children || []).filter(c => typeof c === 'object');
      if (cells.length < 2 || !cells.every(c => c.type === 'Box' && typeof c.props.width === 'number')) continue;
      const total = cells.reduce((a, c) => a + c.props.width, 0) + (node.props.columnGap ?? 0) * (cells.length - 1);
      expect(total).toBeLessThanOrEqual(width);
    }
  }
});
test('every screen fits exactly 34 columns', () => {
  const s = snapshot(); s.workers.push({ ...s.workers[0], id: 'worker-meta', platform: 'meta', status: 'failed', result_status: 'failed', missing_inputs: [], contradictions: ['A conflict'], stale_sources: [] });
  for (const tab of TABS) for (const details of [false, true]) {
    const r = renderText(drawPane(fakeUi(), view(tab, s, { details }), noControls, 34), 34);
    expect(r.tooWide).toEqual([]);
  }
});

// 8. One plain set of terms.
function plainSnapshot() {
  const s = snapshot();
  s.workers.push({ ...s.workers[0], id: 'worker-meta', platform: 'meta', status: 'failed', result_status: 'failed', missing_inputs: [], contradictions: ['A conflict'], stale_sources: [] });
  s.findings = ['demoted', 'contested', 'provisional', 'stale', 'missing', 'current'].map((evidence_status, i) => ({ ...snapshot().findings[0], finding: { ...snapshot().findings[0].finding, control_id: `G-${i}` }, evidence_status }));
  s.scoring[0] = { platform: 'google', health_score: 50, evidence_coverage: 40, status: 'provisional', profile_status: 'enabled' };
  s.claims[0].effective_status = 'contested'; s.sources[0].status = 'demoted';
  return s;
}
test('screens use checks, steps, platform and engine, and keep jargon out of the default view', () => {
  const jargon = /\bworkers?\b|\bCore\b|Weakened|Provisional|Contested|[Ff]ingerprint/;
  const ui = fakeUi({ Svg: props => ({ type: 'Svg', props }) });
  for (const tab of TABS) for (const width of [34, 72, 160]) {
    const state = view(tab, plainSnapshot());
    expect(text(state, width).text).not.toMatch(jargon);
    expect(allText(drawPane(ui, state, noControls, width)).join('\n')).not.toMatch(jargon);
    for (const node of walk(drawPane(ui, state, noControls, width))) if (node?.type === 'Svg') { expect(node.props.alt).not.toMatch(/worker/i); expect(node.props.source).not.toMatch(/worker/i); }
  }
  expect(text({ ...emptyView(), visible: true, doctor }, 72).text).not.toMatch(jargon);
  expect(text({ ...emptyView(), visible: true, doctor }, 72).text).toContain('Engine 2.0.0');
  expect(text(view('Evidence', plainSnapshot()), 100).text).toMatch(/Less certain|Sources disagree|Not final/);
});
test('the fingerprint, where it appears in details, is explained in plain words', () => {
  const shown = text(view('Evidence', plainSnapshot(), { details: true }), 100).text.replace(/[│\n]+/g, ' ').replace(/\s+/g, ' ');
  expect(shown).toMatch(/fingerprint [a-f0-9]{8} \(a short code that changes whenever the run data changes\)/);
});
test('the tab for findings is called Checks', () => {
  expect(text(view('Run'), 100).text).toMatch(/Checks 1/); expect(text(view('Run'), 100).text).not.toMatch(/Findings/);
});

// The wire and the controller still agree on the 64-character hashes used above.
test('fixtures stay valid wire data', () => { expect(H).toHaveLength(64); expect(() => snapshotWire(plainSnapshot())).not.toThrow(); });

// A real audit is large: dozens of missing inputs, mostly without registered support. These tests use
// that shape so a long list never takes over the screen and a wrapped line never strands its glyph.
function largeAudit() {
  const s = snapshot('real-audit', 'completed') as any;
  const base = s.findings[0];
  s.findings = Array.from({ length: 30 }, (_, i) => ({ ...base, platform: 'google', control_title: `Check number ${i}`,
    evidence_status: i < 3 ? 'current' : 'missing', finding: { ...base.finding, control_id: `G${String(i).padStart(2, '0')}`, status: i % 3 === 0 ? 'fail' : 'unknown' } }));
  s.workers[0] = { ...s.workers[0], status: 'completed', result_status: 'ok',
    missing_inputs: Array.from({ length: 26 }, (_, i) => `Missing input number ${i} with a long description that is certain to wrap onto a second line on a narrow screen`),
    recovery_hints: Array.from({ length: 12 }, (_, i) => `Pull export number ${i}`), stale_sources: [], contradictions: [] };
  s.workflow_status = 'completed';
  return s;
}

test('a long list of missing inputs is capped on the overview and keeps one way to the rest', () => {
  const state = view('Run', largeAudit());
  const shown = text(state, 72).text;
  const listed = shown.split('\n').map(l => l.replace(/[│╭╮╰╯─]/g, '').trim()).filter(l => l.startsWith('▲ Google Ads: Missing input number'));
  expect(listed.length).toBeGreaterThanOrEqual(1); expect(listed.length).toBeLessThanOrEqual(5);
  expect(shown).toContain('See all 26 on Inputs');
  expect(buttons(state).filter(b => String(b.props.label) === 'See all 26 on Inputs').length).toBe(1);
  expect(buttons(state).filter(b => String(b.props.label).includes('Missing input')).length).toBe(0);
});

test('a wrapped missing-input line keeps its glyph with its text', () => {
  const lines = text(view('Inputs', largeAudit()), 60).text.split('\n').map(l => l.replace(/[│╭╮╰╯─]/g, '').trim());
  expect(lines.filter(l => l === '▲').length).toBe(0);
  // The list is capped to the room; the rest is counted, not hidden.
  const listed = lines.filter(l => l.startsWith('▲ Google Ads: Missing input number')).length;
  expect(listed).toBeGreaterThanOrEqual(3); expect(listed).toBeLessThan(26);
  expect(lines.some(l => /^\+ \d+ more$/.test(l))).toBe(true);
});

test('when most checks have no registered support it is said once, not on every line', () => {
  const shown = text(view('Evidence', largeAudit()), 80).text;
  expect(shown).toContain('27 of 30 checks have no registered source support yet');
  expect(shown).not.toContain('· No support');
});

test('plain kind and value evidence reads as a sentence and other evidence stays as data', () => {
  const s = snapshot('evidence-run', 'completed') as any;
  s.findings[0].finding.evidence = [{ kind: 'input_field', value: 'keywords.json: 15 rows' }, { kind: 'x', rows: [1, 2] }];
  const shown = text(view('Evidence', s, { context: { kind: 'finding', platform: s.findings[0].platform, controlId: s.findings[0].finding.control_id }, details: true }), 80).text;
  expect(shown).toContain('evidence 1: input field: keywords.json: 15 rows');
  expect(shown).toContain('evidence 2: {"kind":"x","rows":[1,2]}');
});

// 5. Color: a tone on a line part must reach the Text, and the meters must carry it.
test('a tone on a line part reaches the drawn Text as a theme color', () => {
  const kit = makeKit(fakeUi(), 80, 24);
  const texts = tree => walk(tree).filter(n => n?.type === 'Text');
  const colored = texts(kit.line([{ text: 'good', tone: 'ok' }, { text: 'bad', tone: 'bad' }, { text: 'none', tone: 'unclear' }, { text: 'quiet', dim: true }], { gap: 1 }));
  expect(colored.map(n => n.props.color ?? (n.props.dimColor ? 'dim' : 'plain'))).toEqual(['success', 'error', 'dim', 'dim']);
  // A style that is set wins over the tone; a style left undefined never erases it.
  expect(texts(kit.line([{ text: 'x', tone: 'ok', bold: true, dim: undefined }], { gap: 1 }))[0].props).toMatchObject({ color: 'success', bold: true });
  const bars = texts(kit.line(kit.meterParts({ pass: 5, fail: 2, unknown: 3 }, 10), { gap: 0 }));
  expect(bars.map(n => [n.props.children[0][0], n.props.color ?? 'dim'])).toEqual([['█', 'success'], ['▓', 'error'], ['░', 'dim']]);
  // The overview's own meter and legend are colored too.
  const mixed = snapshot() as any;
  mixed.findings = ['pass', 'fail', 'unknown'].map((status, i) => ({ ...mixed.findings[0], finding: { ...mixed.findings[0].finding, status, control_id: `G-${i}` } }));
  const overview = texts(drawPane(fakeUi(), view('Run', mixed), noControls, 100, true, 34));
  expect(overview.some(n => n.props.color === 'success' && /█/.test(n.props.children[0]))).toBe(true);
  expect(overview.some(n => n.props.color === 'error' && /✗/.test(String(n.props.children[0])))).toBe(true);
});
