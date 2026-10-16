import { expect, test } from 'claude-code/testing';
import { drawPane, drawBand } from '../hooks/views.mjs';
import { emptyView, createController } from '../hooks/controller.mjs';
import { snapshot, doctor, receipt } from './fixtures.mjs';
import { fakeUi, renderText } from './render-text.mjs';
import { LEXICON } from '../hooks/lexicon.mjs';

const PANE = { plugin:'ads-cockpit',component:'Pane',requestId:'ads-cockpit',viewport:{columns:100,rows:30},props:{title:'Claude Ads Cockpit',isFocused:true,bodyColumns:60,placement:'inline',scroll:{offset:0,bodyRows:10},view:{}} } as const;
const BAND = { plugin:'ads-cockpit',component:'AbovePrompt',requestId:'band',viewport:{columns:100,rows:30},props:{hasSurvey:false,isWorking:false,maxRows:5,bodyColumns:60,scroll:{offset:0,bodyRows:5},view:{}} } as const;
const noControls = {chooser:()=>{},select:()=>{},refresh:()=>{},hide:()=>{},demo:()=>{},step:()=>{},reset:()=>{},tab:()=>{},baseline:()=>{},action:()=>{},navigate:()=>{},workbench:()=>{},details:()=>{}};
const TABS = ['Run','Evidence','Inputs','Compare','Reports'];
const walk = node => !node ? [] : [node, ...(node.children || []).flatMap(child => typeof child === 'object' ? walk(child) : [])];
const text = (state, width = 72, controls = noControls, ui = fakeUi()) => renderText(drawPane(ui, state, controls, width), width + 4);
const view = (tab, value = snapshot(), extra = {}) => ({ ...emptyView(), visible: true, selected: 'demo-run', tab, snapshot: value, ...extra });

for (const surface of ['terminal','desktop'] as const) {
  for (const tab of TABS) for (const width of [34, 72, 160]) {
    test(`${surface} width ${width} ${tab} screen passes the host validator and exposes its controls`, async ($, on) => {
      const state = view(tab);
      on('ui.render', ($, e) => drawPane($.ui.resolve(e), state, noControls, e.props.bodyColumns));
      const ui = await $.ui.mount({ ...PANE, surface, viewport: { columns: width + 4, rows: 40 }, props: { ...PANE.props, bodyColumns: width } });
      expect(await ui.find({ key: `tab-${tab.toLowerCase()}` })).toBeDefined();
      if (tab === 'Run') expect(await ui.find({ key: 'verdict-action' })).toBeDefined();
      if (tab === 'Evidence') expect(await ui.find({ key: 'finding-open-0' })).toBeDefined();
      if (tab === 'Inputs') expect(await ui.find({ key: 'validate-input-input-demo' })).toBeDefined();
      if (tab === 'Compare') expect(await ui.find({ key: 'compare-empty' })).toBeDefined();
      if (tab === 'Reports') for (const format of ['markdown', 'html', 'pdf']) expect(await ui.find({ key: `render-${format}` })).toBeDefined();
      await ui.unmount();
    });
  }
  test(`${surface} chooser, demo strip and error card pass the host validator`, async ($, on) => {
    const demo = { runsRoot: '/x', policyRoot: '/y', index: 0, steps: [{ run_id: 'a', title: 'First', tab: 'Run', baseline_id: null }, { run_id: 'b', title: 'Second', tab: 'Inputs', baseline_id: null }] };
    const states = [{ ...emptyView(), visible: true, doctor }, view('Run', snapshot(), { demo, error: 'Local request unavailable.', busy: true }), { ...emptyView(), visible: true, selected: 'demo-run', tab: 'Inputs' }];
    let state = states[0];
    on('ui.render', ($, e) => drawPane($.ui.resolve(e), state, noControls, e.props.bodyColumns));
    for (state of states) {
      const ui = await $.ui.mount({ ...PANE, surface });
      expect(await ui.find({ key: 'hide' })).toBeDefined();
      await ui.unmount();
    }
  });
}
test('narrow terminal keeps keyboard hotkeys', async ($, on) => {
  const state = view('Run');
  on('ui.render', ($, e) => drawPane($.ui.resolve(e), state, noControls, e.props.bodyColumns));
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal', viewport: { columns: 38, rows: 20 }, props: { ...PANE.props, bodyColumns: 34 } });
  expect((await ui.find({ key: 'tab-run' })).props.hotkey).toBe('1'); expect((await ui.find({ key: 'hide' })).props.hotkey).toBe('h'); expect((await ui.find({ key: 'details' })).props.hotkey).toBe('d');
  await ui.unmount();
});

// Pure, text-level guarantees over every screen, width and mode.
const COMBOS = [] as Array<[string, number, boolean]>;
for (const tab of TABS) for (const width of [34, 54, 72, 100, 160]) for (const details of [false, true]) COMBOS.push([tab, width, details]);
function fullSnapshot() {
  const s = snapshot();
  s.workers.push({ ...s.workers[0], id: 'worker-meta', platform: 'meta', status: 'failed', result_status: 'failed', missing_inputs: [], contradictions: ['A conflict'], stale_sources: [] });
  s.comparison = { baseline_run_id: 'older-run', comparable: false, differences: ['Window differs'], findings: [{ platform: 'google', control_id: 'G-DEMO', change: 'new_failure', baseline_status: null, current_status: 'fail' }] };
  s.receipts = [{ path: 'cockpit/receipts/historical.json', sha256: 'b'.repeat(64), size: 900, receipt: { schema_version: '1.0.0', artifact_type: 'cockpit-action-receipt', action_id: 'historical', run_id: 'demo-run', operation: 'render-report', started_at: '2026-10-07T00:00:00Z', finished_at: '2026-10-07T00:00:01Z', outcome: 'blocked', input_fingerprint: 'c'.repeat(64), policy_fingerprint: 'd'.repeat(64), outputs: [], diagnostics: ['Optional PDF renderer unavailable'] } }];
  return s;
}
function bigSnapshot() {
  const s = fullSnapshot();
  const platforms = ['google', 'meta', 'linkedin', 'tiktok'], statuses = ['pass', 'fail', 'unknown', 'pass', 'not_applicable'];
  s.findings = platforms.flatMap((platform, p) => Array.from({ length: 7 }, (_, i) => ({ platform, account_key: null, control_title: `Synthetic check title number ${p * 7 + i} with a rather long descriptive name`, severity: ['critical', 'high', 'medium', 'informational'][i % 4], claim_ids: [], source_ids: [], evidence_status: i % 3 ? 'current' : 'stale', finding: { schema_version: '1.0.0', control_id: `${platform[0].toUpperCase()}${i + 1}`, status: statuses[(i + p) % 5], evidence: statuses[(i + p) % 5] === 'pass' || statuses[(i + p) % 5] === 'fail' ? [{ kind: 'synthetic' }] : [], confidence: 'high', observation: 'Synthetic observation', diagnosis: 'Synthetic diagnosis', recommendation: 'Synthetic recommendation' } })));
  return s;
}
test('a large audit is paged: one screenful at a time, every check reachable, nothing wider than the pane', () => {
  for (const width of [34, 54, 72, 100, 160]) for (const tab of ['Run', 'Evidence']) {
    const r = text(view(tab, bigSnapshot()), width);
    expect(r.tooWide).toEqual([]);
  }
  const first = text(view('Evidence', bigSnapshot()), 100).text;
  expect(first).toMatch(/Showing all 28/); expect(first).toMatch(/page 1 of \d+/);
  const seen = new Set<string>();
  const pages = Number(first.match(/page 1 of (\d+)/)?.[1]);
  for (let page = 0; page < pages; page++) {
    const keys = walk(drawPane(fakeUi(), view('Evidence', bigSnapshot(), { page }), noControls, 100)).filter(n => n?.type === 'Button').map(n => n.props.key);
    for (const key of keys.filter(k => k.startsWith('finding-open-'))) seen.add(key);
  }
  expect(seen.size).toBe(28);
  const overview = text(view('Run', bigSnapshot()), 100).text;
  expect(overview).toContain('Fix first'); expect(overview).toMatch(/See all 28 checks/); expect(overview).toMatch(/█████/);
});
test('an opened finding in a large audit shows its full card', () => {
  const shown = text(view('Evidence', bigSnapshot(), { context: { kind: 'finding', platform: 'meta', controlId: 'M1' } }), 100).text;
  expect(shown).toContain('Synthetic diagnosis'); expect(shown).toContain('What to do');
});
// The pane is drawn to the rows the host gives it, so it never needs to scroll.
const ROW_SIZES = [[54, 14], [60, 16], [72, 20], [84, 24], [100, 30], [120, 40]] as Array<[number, number]>;
const demoState = { runsRoot: '/x', policyRoot: '/y', index: 2, steps: Array.from({ length: 8 }, (_, i) => ({ run_id: 'a', title: `Step title ${i + 1} that is long enough to need cutting at a narrow width`, tab: 'Run', baseline_id: null })) };
const ROW_MODES = { plain: {}, details: { details: true }, demo: { demo: demoState }, busy: { busy: true }, error: { error: 'Local request unavailable. Run doctor or refresh the selected run.' }, page2: { page: 1 }, filter: { filter: 'fail' } } as Record<string, object>;
test('every screen fits the rows it is given, in every mode and at every size', () => {
  const lines = (state, width, rows) => renderText(drawPane(fakeUi(), state, noControls, width, true, rows), width + 4);
  for (const [width, rows] of ROW_SIZES) for (const value of [snapshot(), fullSnapshot(), bigSnapshot()]) for (const tab of TABS) for (const [mode, extra] of Object.entries(ROW_MODES)) {
    const r = lines(view(tab, value, extra), width, rows);
    expect({ tab, mode, width, rows, tooTall: r.lines.length > rows, tooWide: r.tooWide.length }).toEqual({ tab, mode, width, rows, tooTall: false, tooWide: 0 });
  }
  // The chooser and an opened check obey the same rule.
  for (const [width, rows] of ROW_SIZES) {
    expect(lines({ ...emptyView(), visible: true, doctor }, width, rows).lines.length).toBeLessThanOrEqual(rows);
    const opened = view('Evidence', bigSnapshot(), { context: { kind: 'finding', platform: 'meta', controlId: 'M1' } });
    expect(lines(opened, width, rows).lines.length).toBeLessThanOrEqual(rows);
    expect(lines({ ...opened, details: true }, width, rows).lines.length).toBeLessThanOrEqual(rows);
  }
});
test('a taller pane shows more of the same screen, never a different one', () => {
  const short = text(view('Run', bigSnapshot()), 100).lines.length;
  const tall = renderText(drawPane(fakeUi(), view('Run', bigSnapshot()), noControls, 100, true, 48), 104).lines.length;
  expect(tall).toBeGreaterThanOrEqual(short);
  const small = renderText(drawPane(fakeUi(), view('Run', bigSnapshot()), noControls, 100, true, 16), 104).text;
  expect(small).toContain('Fix first'); expect(small).toContain('2: Checks 28');
  const medium = renderText(drawPane(fakeUi(), view('Run', bigSnapshot()), noControls, 100, true, 24), 104).text;
  expect(medium).toContain('See all 28 checks');
});
test('no screen overflows its width at any size, in any mode', () => {
  for (const [tab, width, details] of COMBOS) for (const value of [snapshot(), fullSnapshot()]) {
    const r = text(view(tab, value, { details }), width);
    expect(r.tooWide).toEqual([]);
  }
});
test('raw wire words never reach the screen', () => {
  const raw = /needs_input|insufficient_evidence|not_applicable|new_failure|new_finding|newly_unknown|status_changed|not_retested|evidence_status|profile_status|profile disabled|result needs|validate-run|render-report|informational/;
  for (const [tab, width, details] of COMBOS) for (const value of [snapshot(), fullSnapshot()]) expect(text(view(tab, value, { details }), width).text).not.toMatch(raw);
});
test('every wire status has a plain-language entry', () => {
  const enums = { workflow: ['pending','running','completed','blocked','failed','unknown'], completeness: ['complete','partial','failed'], worker: ['pending','running','completed','failed','skipped'], result: ['ok','needs_input','blocked','failed','none'], finding: ['pass','fail','unknown','not_applicable'], severity: ['critical','high','medium','informational'], confidence: ['high','medium','low','none'], support: ['current','stale','demoted','missing','contested','provisional'], input: ['unchecked','valid','invalid','missing'], outcome: ['succeeded','failed','blocked'], change: ['new_failure','new_finding','newly_unknown','not_retested','status_changed','unchanged'], scoring: ['normal','provisional','insufficient_evidence'], operation: ['validate-input','validate-run','render-report'], privacy: ['public','internal','confidential','restricted'] };
  for (const [group, values] of Object.entries(enums)) for (const value of values) expect(LEXICON[group][value]).toBeDefined();
});
test('every element prop is on the allowlist, with theme colors only and no undefined values', () => {
  const allowed = { Box: ['key','children','flexDirection','flexWrap','columnGap','rowGap','width','marginTop','marginLeft','paddingX','borderStyle','borderColor','borderDimColor','justifyContent'], Text: ['children','color','bold','dimColor','wrap','inverse'], Button: ['key','label','hotkey','plain','variant','onPress'], Input: ['key','label','value','placeholder','submitLabel','onSubmit'], Svg: ['source','alt','width','height'] };
  const colors = ['success','warning','error','suggestion','claude'];
  const ui = fakeUi({ Svg: props => ({ type: 'Svg', props }) });
  for (const [tab, width, details] of COMBOS) {
    const state = view(tab, fullSnapshot(), { details, context: { kind: 'finding', platform: 'google', controlId: 'G-DEMO' } });
    for (const node of walk(drawPane(ui, state, noControls, width))) {
      if (typeof node !== 'object') continue;
      for (const [name, value] of Object.entries(node.props)) {
        expect(allowed[node.type]).toContain(name); expect(value).not.toBe(undefined);
        if (name === 'color' || name === 'borderColor') expect(colors).toContain(value);
        if (name === 'borderStyle') expect(value).toBe('round');
        if (name === 'hotkey') expect(value).toMatch(/^[0-9a-z]$/);
      }
      if (node.type === 'Svg') { expect(node.props.source.length).toBeLessThan(131072); expect(node.props.source).not.toMatch(/<script|onload|href/i); expect(node.props.alt.length).toBeGreaterThan(0); }
    }
  }
});
test('control keys are unique within every screen', () => {
  for (const [tab, width] of COMBOS.map(([t, w]) => [t, w] as [string, number])) {
    const keys = walk(drawPane(fakeUi(), view(tab, fullSnapshot()), noControls, width)).filter(n => n?.type === 'Button' || n?.type === 'Input').map(n => n.props.key);
    expect(new Set(keys).size).toBe(keys.length);
  }
});

for (const surface of ['terminal', 'desktop'] as const) {
  test(`${surface} disabled profile withholds spoofed health and coverage`, async ($, on) => {
    const value = snapshot(); value.scoring[0].health_score = 97; value.scoring[0].evidence_coverage = 100;
    for (const tab of TABS) { const shown = text(view(tab, value), 72).text; expect(shown).not.toContain('97'); }
    expect(text(view('Run', value), 72).text).toContain('Scoring is off');
    const state = view('Run', value);
    on('ui.render', ($, e) => drawPane($.ui.resolve(e), state, noControls, e.props.bodyColumns));
    const ui = await $.ui.mount({ ...PANE, surface }); expect(await ui.find({ key: 'verdict-action' })).toBeDefined(); await ui.unmount();
  });
}
test('enabled profile shows a score and coverage only when the core supplied them', () => {
  const value = snapshot(); value.scoring[0] = { platform: 'google', health_score: 83, evidence_coverage: 64, status: 'normal', profile_status: 'enabled' };
  expect(text(view('Run', value), 72).text).toMatch(/83\/100/);
});
test('Reports rediscover retained failure receipts with plain wording', () => {
  const shown = text(view('Reports', fullSnapshot()), 72).text;
  expect(shown).toContain('Report'); expect(shown).toContain('Blocked'); expect(shown).toContain('Optional PDF renderer unavailable');
  expect(text(view('Reports', fullSnapshot(), { details: true }), 72).text).toMatch(/input cccccccc, policy dddddddd/);
});
test('verdict states say what to do next', () => {
  const s = snapshot();
  expect(text(view('Run', s), 72).text).toMatch(/Waiting for you[\s\S]*Search terms missing/);
  s.workers[0].missing_inputs = []; s.workers[0].result_status = 'ok';
  expect(text(view('Run', s), 72).text).toMatch(/Finished|Running/);
  s.workflow_status = 'failed'; expect(text(view('Run', s), 72).text).toMatch(/Partly done/);
  s.completeness = 'failed'; expect(text(view('Run', s), 72).text).toMatch(/The run failed/);
});
test('the selected input and finding are listed first and a text match is never called a link', () => {
  const value = snapshot(); value.inputs.unshift({ ...value.inputs[0], id: 'other', path: 'inputs/other.json' }); value.findings.unshift({ ...value.findings[0], platform: 'meta' });
  let shown = text(view('Inputs', value, { context: { kind: 'inputs', workerId: 'worker-google', missingInput: 'Search terms missing', inputIds: ['input-demo'], match: 'platform' } })).text;
  expect(shown.indexOf('input-demo')).toBeLessThan(shown.indexOf('other'));
  shown = text(view('Inputs', value, { context: { kind: 'inputs', workerId: 'worker-google', missingInput: 'Provide input-demo', inputIds: ['input-demo'], match: 'text' } })).text;
  expect(shown.replace(/[│\n]+/g, ' ').replace(/\s+/g, ' ')).toContain('A text match is not a recorded link.'); expect(shown).not.toMatch(/linked to/i);
  // An opened check is shown on its own, with a way back to the whole list.
  const open = { context: { kind: 'finding', platform: 'google', controlId: 'G-DEMO' } };
  shown = text(view('Evidence', value, open)).text;
  expect(shown).toContain('Google Ads · G-DEMO'); expect(shown).not.toContain('Meta Ads · G-DEMO'); expect(shown).toContain('Back to all checks');
  shown = text(view('Evidence', value)).text;
  expect(shown).toMatch(/Google Ads: .*G-DEMO/); expect(shown).toMatch(/Meta Ads: .*G-DEMO/);
});
test('demo strip shows the step, hides unusable Back and keeps the data disclosure', () => {
  const steps = Array.from({ length: 7 }, (_, i) => ({ run_id: 'demo-run', title: `Step title ${i + 1}`, tab: 'Run', baseline_id: null }));
  const first = walk(drawPane(fakeUi(), view('Run', snapshot(), { demo: { runsRoot: '/x', policyRoot: '/y', index: 0, steps } }), noControls, 72));
  expect(first.some(n => n?.props?.key === 'demo-back')).toBe(false); expect(first.some(n => n?.props?.key === 'demo-next')).toBe(true);
  const shown = text(view('Run', snapshot(), { demo: { runsRoot: '/x', policyRoot: '/y', index: 6, steps } })).text;
  expect(shown).toMatch(/Step 7 of 7/); expect(shown).toContain('Made-up data'); expect(walk(drawPane(fakeUi(), view('Run', snapshot(), { demo: { runsRoot: '/x', policyRoot: '/y', index: 6, steps } }), noControls, 72)).some(n => n?.props?.key === 'demo-next')).toBe(false);
});

test('actual host command shows a bounded configuration error and hide clears state', async ($, on) => {
  on('session.surfaces',()=>({value:['terminal']}));on('ui.open',()=>({value:{isPlaced:true}}));on('ui.close',()=>({value:undefined}));on('ui.render',()=>({type:'Text',props:{},children:['other']}));
  const reply=await $.command.run({command:'ads-cockpit',args:''});expect(reply).toEqual({});
  const ui=await $.ui.mount({...PANE,surface:'terminal'});expect(await ui.find({key:'error'})).toBeDefined();
  await ui.press({key:'hide'});expect(await ui.find({type:'Text',text:'other'})).toBeDefined();await ui.unmount();
});
test('band preserves other mods and yields to survey', async ($, on) => {
  on('session.surfaces',()=>({value:['terminal']}));on('ui.open',()=>({value:{isPlaced:true}}));on('ui.render',()=>({type:'Text',props:{},children:['other band']}));
  await $.command.run({command:'ads-cockpit',args:''});
  const band=await $.ui.mount({...BAND,surface:'terminal'});expect(await band.find({type:'Text',text:'other band'})).toBeDefined();expect(await band.find({type:'Text',text:'Claude Ads Cockpit: not set up yet. Set coreRoot and pythonExecutable.'})).toBeDefined();await band.unmount();
  const survey=await $.ui.mount({...BAND,surface:'terminal',props:{...BAND.props,hasSurvey:true}});expect(await survey.find({type:'Text',text:'other band'})).toBeDefined();expect(await survey.find({key:'open-workbench'})).toBe(undefined);await survey.unmount();
});
test('clear resets session data and closes pane without core calls', async ($, on) => {
  on('session.surfaces',()=>({value:['terminal']}));on('ui.open',()=>({value:{isPlaced:true}}));on('ui.close',()=>({value:undefined}));on('classic.SessionStart',()=>({}));on('ui.render',()=>({type:'Text',props:{},children:['cleared']}));
  await $.command.run({command:'ads-cockpit',args:''});await $.classic.SessionStart({source:'clear'});const ui=await $.ui.mount({...PANE,surface:'terminal'});expect(await ui.find({type:'Text',text:'cleared'})).toBeDefined();await ui.unmount();
});
test('nonvisual command emits safe status and clears data', async ($, on) => {
  on('session.surfaces',()=>({value:[]}));on('ui.render',()=>({type:'Text',props:{},children:['cleared']}));
  const reply=await $.command.run({command:'ads-cockpit',args:''});expect(reply.text).toBe('Claude Ads Cockpit local request finished. Visual cockpit requires terminal or Desktop; session data cleared.');const ui=await $.ui.mount({...PANE,surface:'terminal'});expect(await ui.find({type:'Text',text:'cleared'})).toBeDefined();await ui.unmount();
});
for(const reason of ['hide','clear','reload'])test(`actual command cannot reopen after ${reason} while surfaces are delayed`,async($,on)=>{
  let enter,release;const entered=new Promise(resolve=>enter=resolve),surfaces=new Promise(resolve=>release=resolve);let opens=0;
  on('session.surfaces',async()=>{enter();return {value:await surfaces};});on('ui.open',()=>{opens++;return {value:{isPlaced:true}};});on('ui.close',()=>({value:undefined}));on('classic.SessionStart',()=>({}));on('session.start',($,e)=>({cwd:e.cwd}));on('command.register',()=>({value:undefined}));
  const pending=$.command.run({command:'ads-cockpit',args:''});await entered;
  if(reason==='hide')await $.command.run({command:'ads-cockpit',args:'hide'});
  else if(reason==='clear')await $.classic.SessionStart({source:'clear'});
  else await $.session.start({cwd:'/synthetic/session'});
  release(['terminal']);await pending;expect(opens).toBe(0);
});
test('actual workbench callback opens only on user press and does not revive hidden session',async($,on)=>{
  let opens=0;on('session.surfaces',()=>({value:['terminal']}));on('ui.open',()=>{opens++;return {value:{isPlaced:true}};});on('ui.close',()=>({value:undefined}));on('ui.render',()=>({type:'Text',props:{},children:['other']}));
  await $.command.run({command:'ads-cockpit',args:''});expect(opens).toBe(1);const band=await $.ui.mount({...BAND,surface:'terminal'});expect(opens).toBe(1);await band.press({key:'open-workbench'});expect(opens).toBe(2);await $.command.run({command:'ads-cockpit',args:'hide'});expect(await band.find({key:'open-workbench'})).toBe(undefined);expect(opens).toBe(2);await band.unmount();
});

test('navigation callbacks carry the exact cached subject and render has no effects', () => {
  const actions = []; const controls = { ...noControls, navigate: (...args) => actions.push(args), tab: value => actions.push(['tab', value]), workbench: id => actions.push(['open', id]) };
  const value = snapshot(); value.findings.unshift({ ...value.findings[0], platform: 'meta' });
  const state = view('Run', value);
  const tree = walk(drawPane(fakeUi(), state, controls, 72)); expect(actions).toEqual([]);
  tree.find(n => n?.props?.key === 'verdict-action').props.onPress(); tree.find(n => n?.props?.key === 'finding-evidence-1').props.onPress();
  expect(actions).toEqual([['Inputs', { workerId: 'worker-google', missingInput: 'Search terms missing' }, 'demo-run', value.fingerprint], ['Evidence', { platform: 'google', controlId: 'G-DEMO' }, 'demo-run', value.fingerprint]]);
  const band = walk(drawBand(fakeUi(), state, null, controls, 72)); expect(actions.length).toBe(2); band.find(n => n?.props?.key === 'open-workbench').props.onPress(); expect(actions[2]).toEqual(['open', 'demo-run']);
});
test('band reports an absent snapshot without inventing progress', () => {
  const shown = renderText(drawBand(fakeUi(), { ...emptyView(), visible: true, selected: 'demo-run' }, null, noControls, 80), 84).text;
  expect(shown).toContain('Choose a run or the practice demo.'); expect(shown).not.toMatch(/steps \d/);
  const full = renderText(drawBand(fakeUi(), view('Run'), null, noControls, 90), 94).text; expect(full).toMatch(/Waiting for you/); expect(full).toMatch(/1 missing/);
});
test('details toggle is a view-only control that hide resets', async () => {
  const published = []; const c = createController({ after: () => ({ cancel() {} }), publish: async v => published.push(v), call: async (command, request) => command === 'doctor' ? doctor : snapshot(request.runId) });
  await c.details(); expect(c.view().details).toBe(false);
  await c.select('demo-run'); await c.details(); expect(c.view().details).toBe(true); await c.details(); expect(c.view().details).toBe(false);
  await c.details(); await c.hide(); expect(c.view().details).toBe(false);
});

const actionButtons=[['Inputs','validate-input-input-demo'],['Inputs','validate-run'],['Reports','validate-run'],['Reports','render-markdown'],['Reports','render-html'],['Reports','render-pdf']];
for(const [tab,key] of actionButtons)for(const transition of ['different run','changed fingerprint','changed policy'])test(`retained ${tab} ${key} callback rejects ${transition} before any core call`,async()=>{
  const calls=[];let fingerprint='a'.repeat(64),policyFingerprint='a'.repeat(64);
  const c=createController({after:()=>({cancel(){}}),publish:async()=>{},call:async(command,request)=>{
    calls.push({command,request});if(command==='doctor')return doctor;if(command==='action')return receipt(request.runId,request.operation);
    return {...snapshot(request.runId),fingerprint,policy_fingerprint:policyFingerprint};
  }});
  await c.select('old-run',tab);
  const tree=walk(drawPane(fakeUi(),c.view(),{...noControls,action:(...args)=>c.action(...args)},72));const retained=tree.find(node=>node?.props?.key===key).props.onPress;
  if(transition==='different run')await c.select('new-run',tab);else{if(transition==='changed fingerprint')fingerprint='b'.repeat(64);else policyFingerprint='c'.repeat(64);await c.refresh();}
  const before=calls.length;await retained();expect(calls.length).toBe(before);expect(c.view().receipt).toBe(null);
});
test('current action callbacks pass rendered run, input and policy subject for all validation and render controls',async()=>{
  for(const [tab,key]of actionButtons){const value=snapshot();value.policy_fingerprint='b'.repeat(64);const calls=[];const state=view(tab,value);
    const tree=walk(drawPane(fakeUi(),state,{...noControls,action:(...args)=>calls.push(args)},72));await tree.find(node=>node?.props?.key===key).props.onPress();
    expect(calls.length).toBe(1);expect(calls[0][3]).toEqual({runId:'demo-run',fingerprint:value.fingerprint,policyFingerprint:value.policy_fingerprint});
    expect(calls[0][0]).toBe(key.startsWith('render-')?'render-report':key==='validate-run'?'validate-run':'validate-input');
    expect(calls[0][1]).toBe(key==='validate-input-input-demo'?'input-demo':null);expect(calls[0][2]).toBe(key.startsWith('render-')?key.replace('render-',''):'markdown');
  }
});
test('while a request is in flight, actions are drawn as dim labels, not controls', () => {
  const tree = walk(drawPane(fakeUi(), view('Reports', snapshot(), { busy: true }), noControls, 72));
  for (const key of ['render-markdown', 'render-html', 'render-pdf', 'validate-run']) expect(tree.some(n => n?.props?.key === key)).toBe(false);
  expect(text(view('Reports', snapshot(), { busy: true })).text).toMatch(/Markdown/);
});
