import { expect, test } from 'claude-code/testing';
import { binding, buildArgv, PYTHON_LOADER } from '../hooks/launcher.mjs';
import { doctorWire, snapshotWire, receiptWire, demoWire } from '../hooks/wire.mjs';
import { createController } from '../hooks/controller.mjs';
import { doctor, snapshot, receipt, demo, H } from './fixtures.mjs';
function boundAction(c,operation,inputId = null,format = 'markdown') {
  const state=c.view();return c.action(operation,inputId,format,{runId:state.selected,fingerprint:state.snapshot?.fingerprint,policyFingerprint:state.snapshot?.policy_fingerprint});
}
const config = {coreRoot:'/synthetic/core',pythonExecutable:'/synthetic/python',runsRoot:'/synthetic/runs'};
function harness(overrides = {}) {
  const calls = [], published = [], timers = [];
  const adapter = {
    call: async (command, request) => { calls.push({command,request}); if (command === 'doctor') return doctor; if (command === 'prepare-demo') return {interface_version:demo.interface_version,runs_root:demo.runs_root,policy_root:demo.policy_root}; if (command === 'demo') return demo; if (command === 'action') return receipt(request.runId,request.operation); return snapshot(request.runId); },
    publish: async value => published.push(value),
    after: (ms, fn) => { const timer = { ms,fn,cancelled:false,cancel() { this.cancelled = true; } }; timers.push(timer); return timer; }, ...overrides,
  };
  return { c:createController(adapter),calls,published,timers };
}
test('launcher accepts only trusted absolute bindings', () => {
  expect(binding(config)).toEqual(config);
  for (const value of ['', 'python3', '../python', '/trusted/../python', '/bad\npath']) expect(() => binding({...config,pythonExecutable:value})).toThrow();
});
test('fixed argv isolates Python and excludes shell, PATH and model calls', () => {
  const argv = buildArgv(config,'action',{runId:'demo-run',operation:'validate-run',fingerprint:H});
  expect(argv.slice(0,4)).toEqual([config.pythonExecutable,'-I','-S','-c']);
  expect(argv[4]).toBe(PYTHON_LOADER);
  expect(argv.slice(6)).toEqual(['cockpit','action','--policy-root',config.coreRoot,'--runs-root',config.runsRoot,'--run-id','demo-run','--operation','validate-run','--expected-fingerprint',H]);
  expect(() => buildArgv(config,'shell')).toThrow();
  expect(() => buildArgv(config,'action',{runId:'demo-run',operation:'pause',fingerprint:H})).toThrow();
  expect(() => buildArgv(config,'action',{runId:'demo-run',operation:'validate-run'})).toThrow();
  expect(() => buildArgv(config,'snapshot',{runId:'; rm -rf'})).toThrow();
  expect(buildArgv(config,'prepare-demo').slice(6)).toEqual(['demo-prepare',config.runsRoot]);
  expect(buildArgv(config,'demo',{runsRoot:demo.runs_root,policyRoot:demo.policy_root}).slice(6)).toEqual(['demo-setup',demo.runs_root]);
});
test('wire envelopes reject versions, unknown fields and unsafe artifact paths', () => {
  expect(doctorWire(doctor)).toEqual(doctor); expect(snapshotWire(snapshot())).toEqual(snapshot()); expect(receiptWire(receipt())).toEqual(receipt()); expect(demoWire(demo)).toEqual(demo);
  expect(() => snapshotWire({...snapshot(),schema_version:'2.0.0'})).toThrow();
  expect(() => snapshotWire({...snapshot(),raw_account_id:'private'})).toThrow();
  expect(() => snapshotWire({...snapshot(),artifacts:[{path:'../escape',kind:'report',sha256:H,size:1}]})).toThrow();
  expect(() => receiptWire({...receipt(),input_fingerprint:''})).toThrow();
});
test('selection probes policy before data and schedules only visible pending work', async () => {
  const h = harness(); await h.c.select('demo-run');
  expect(h.calls.map(x => x.command)).toEqual(['doctor','snapshot']); expect(h.timers[0].ms).toBe(5000);
  await h.c.hide(); expect(h.timers[0].cancelled).toBe(true); expect(h.c.view().snapshot).toBe(null); expect(h.c.view().visible).toBe(false);
  const finished = harness({call:async (command,request) => command === 'doctor' ? doctor : snapshot(request.runId,'completed')});
  await finished.c.select('demo-run'); expect(finished.timers).toEqual([]);
});
test('stale async selection cannot replace the newer run', async () => {
  let release; const delayed = new Promise(resolve => release=resolve);
  const h = harness({call:async (command,request) => command === 'doctor' ? doctor : request.runId === 'old-run' ? delayed : snapshot(request.runId)});
  const old = h.c.select('old-run'); await Promise.resolve(); await Promise.resolve();
  await h.c.select('new-run'); release(snapshot('old-run')); await old;
  expect(h.c.view().selected).toBe('new-run'); expect(h.c.view().snapshot.run_id).toBe('new-run');
});
test('double action is serialized and carries exact fingerprint', async () => {
  let release, actionCalls=0; const delayed = new Promise(resolve => release=resolve);
  const h = harness({call:async (command,request) => { if (command === 'doctor') return doctor; if (command === 'action') { actionCalls++; expect(request.fingerprint).toBe(H); return delayed; } return snapshot(request.runId); }});
  await h.c.select('demo-run'); const first=boundAction(h.c,'validate-run'); const second=boundAction(h.c,'validate-run');
  for (let i=0;i<8;i++) await Promise.resolve(); release(receipt()); await Promise.all([first,second]);
  expect(actionCalls).toBe(1); expect(h.c.view().receipt.outcome).toBe('succeeded');
});
test('hide before action probe finishes prevents a stale write', async () => {
  let count=0,release,writes=0; const delayed = new Promise(resolve => release=resolve);
  const h=harness({call:async (command,request) => { if (command === 'doctor') { count++; return count === 2 ? delayed : doctor; } if (command==='action') { writes++; return receipt(); } return snapshot(request.runId); }});
  await h.c.select('demo-run'); const pending=boundAction(h.c,'validate-run'); for (let i=0;i<6;i++) await Promise.resolve(); await h.c.hide(); release(doctor); await pending; expect(writes).toBe(0); expect(h.c.view().snapshot).toBe(null);
});
test('refresh calls never overlap and hide cancels future polling', async () => {
  let release,count=0; const delayed = new Promise(resolve => release=resolve);
  const h=harness({call:async (command,request) => { if (command==='doctor') return doctor; count++; return count === 2 ? delayed : snapshot(request.runId); }});
  await h.c.select('demo-run'); const first=h.c.refresh(); for(let i=0;i<6;i++) await Promise.resolve(); await h.c.refresh(); expect(count).toBe(2);
  await h.c.hide(); release(snapshot()); await first; expect(h.c.view().snapshot).toBe(null); expect(h.timers.every(t=>t.cancelled)).toBe(true);
});
test('demo entry clears clients, routes actions to fixture roots and exits to chooser', async () => {
  const h=harness(); await h.c.select('client-run'); await h.c.demo();
  expect(h.published.some(x=>x.selected===null && x.snapshot===null && x.demo===null && x.busy)).toBe(true);
  await h.c.step(1); expect(h.c.view().tab).toBe('Reports'); await boundAction(h.c,'render-report');
  const call=h.calls.find(x=>x.command==='action'); expect(call.request.runsRoot).toBe(demo.runs_root); expect(call.request.policyRoot).toBe(demo.policy_root);
  await h.c.reset(); expect(h.c.view().demo.index).toBe(0); await h.c.chooser(); expect(h.c.view().demo).toBe(null); expect(h.c.view().selected).toBe(null); expect(h.c.view().snapshot).toBe(null);
});
test('timeout and incompatible responses clear trusted snapshot without raw errors', async () => {
  let shouldFail=false; const h=harness({call:async (command,request) => { if (shouldFail) throw new Error('/private/client secret=not-for-display'); return command==='doctor' ? doctor : snapshot(request.runId); }});
  await h.c.select('demo-run'); shouldFail=true; await h.c.refresh(); expect(h.c.view().snapshot).toBe(null); expect(h.c.view().error).toBe('Local request unavailable. Run doctor or refresh the selected run.');
});
function deferred() { let resolve; const promise=new Promise(done=>resolve=done); return {promise,resolve}; }
const invalidate = {
  hide:c=>c.hide(),
  clear:c=>c.dispose(),
  reload:c=>c.dispose(),
  chooser:c=>c.chooser(),
  selection:c=>c.select('new-run'),
};
for (const [reason, change] of Object.entries(invalidate)) {
  test(`delayed selection doctor cannot read after ${reason}`,async()=>{
    const entered=deferred(),released=deferred();const reads=[];let probes=0;
    const h=harness({call:async(command,request)=>{
      if(command==='doctor'){if(++probes===1){entered.resolve();return released.promise;}return doctor;}
      reads.push(request.runId);return snapshot(request.runId);
    }});
    const pending=h.c.select('old-run');await entered.promise;await change(h.c);released.resolve(doctor);await pending;
    expect(reads).toEqual(reason==='selection'?['new-run']:[]);
    expect(h.c.view().selected).toBe(reason==='selection'?'new-run':null);
  });
  test(`delayed refresh doctor cannot read after ${reason}`,async()=>{
    const entered=deferred(),released=deferred();const reads=[];let probes=0;
    const h=harness({call:async(command,request)=>{
      if(command==='doctor'){if(++probes===2){entered.resolve();return released.promise;}return doctor;}
      reads.push(request.runId);return snapshot(request.runId);
    }});
    await h.c.select('old-run');const pending=h.c.refresh();await entered.promise;await change(h.c);released.resolve(doctor);await pending;
    expect(reads).toEqual(reason==='selection'?['old-run','new-run']:['old-run']);
    expect(h.c.view().selected).toBe(reason==='selection'?'new-run':null);
  });
}
function compared(runId='demo-run',baseline='baseline-run') { return {...snapshot(runId),comparison:{baseline_run_id:baseline,comparable:true,differences:[],findings:[]}}; }
for(const [name,modify] of Object.entries({
  baseline:value=>({...value,comparison:{...value.comparison,baseline_run_id:'wrong-run'}}),
  run:value=>({...value,run_id:'wrong-run'}),
  fingerprint:value=>({...value,fingerprint:'b'.repeat(64)}),
  policy:value=>({...value,policy_fingerprint:'b'.repeat(64)}),
  absent:value=>({...value,comparison:null}),
})) test(`comparison rejects mismatched ${name} subject`,async()=>{
  const h=harness({call:async(command,request)=>command==='doctor'?doctor:command==='compare'?modify(compared(request.runId,request.baselineId)):snapshot(request.runId)});
  await h.c.select('demo-run','Compare','baseline-run');expect(h.c.view().snapshot).toBe(null);expect(h.c.view().error).toBe('Engine response has a mismatched comparison subject.');
});
test('comparison binds baseline and policy to the current snapshot before accepting',async()=>{
  const calls=[];const h=harness({call:async(command,request)=>{calls.push(command);return command==='doctor'?doctor:command==='compare'?compared(request.runId,request.baselineId):snapshot(request.runId);}});
  await h.c.select('demo-run','Compare','baseline-run');expect(calls).toEqual(['doctor','snapshot','compare']);expect(h.c.view().snapshot.comparison.baseline_run_id).toBe('baseline-run');
});
test('hide during comparison anchor read prevents dependent compare',async()=>{
  const entered=deferred(),released=deferred();let comparisons=0;
  const h=harness({call:async(command,request)=>{if(command==='doctor')return doctor;if(command==='compare'){comparisons++;return compared();}entered.resolve();return released.promise;}});
  const pending=h.c.select('demo-run','Compare','baseline-run');await entered.promise;await h.c.hide();released.resolve(snapshot());await pending;expect(comparisons).toBe(0);expect(h.c.view().snapshot).toBe(null);
});
test('transient polling error clears snapshot and retries pending work after five seconds',async()=>{
  let reads=0;const h=harness({call:async(command,request)=>{if(command==='doctor')return doctor;if(++reads===2)throw new Error('transient');return snapshot(request.runId);}});
  await h.c.select('demo-run');await h.c.refresh();expect(h.c.view().snapshot).toBe(null);expect(h.timers[h.timers.length-1].ms).toBe(5000);
  await h.timers[h.timers.length-1].fn();expect(reads).toBe(3);expect(h.c.view().error).toBe(null);expect(h.c.view().snapshot.run_id).toBe('demo-run');
});
test('wire refuses disabled health and coverage even when supplied as numeric scores',()=>{
  for(const change of [{health_score:97},{evidence_coverage:100},{evidence_coverage:null}])expect(()=>snapshotWire({...snapshot(),scoring:[{...snapshot().scoring[0],...change}]})).toThrow();
});
for(const phase of ['doctor','prepare-demo','demo'])test(`hide during ${phase} cannot continue demo setup`,async()=>{
  const entered=deferred(),released=deferred();const calls=[];
  const prepared={interface_version:demo.interface_version,runs_root:demo.runs_root,policy_root:demo.policy_root};
  const h=harness({call:async(command,request)=>{calls.push(command);if(command===phase){entered.resolve();return released.promise;}return command==='doctor'?doctor:command==='prepare-demo'?prepared:command==='demo'?demo:snapshot(request.runId);}});
  const pending=h.c.demo();await entered.promise;await h.c.hide();released.resolve(phase==='doctor'?doctor:phase==='prepare-demo'?prepared:demo);await pending;
  expect(calls).toEqual(['doctor','prepare-demo','demo'].slice(0,['doctor','prepare-demo','demo'].indexOf(phase)+1));expect(h.c.view().demo).toBe(null);
});
test('demo helper cannot replace bound isolated roots with client roots',async()=>{
  const prepared={interface_version:demo.interface_version,runs_root:demo.runs_root,policy_root:demo.policy_root};let snapshots=0;
  const h=harness({protectedRoots:['/synthetic/clients'],call:async(command,request)=>{
    if(command==='doctor')return doctor;if(command==='prepare-demo')return prepared;if(command==='demo')return {...demo,runs_root:'/synthetic/clients',policy_root:'/synthetic/clients/_policy'};snapshots++;return snapshot(request.runId);
  }});
  await h.c.demo();expect(h.c.view().demo).toBe(null);expect(h.c.view().error).toBe('Engine response has a mismatched demo destination.');expect(snapshots).toBe(0);
});
test('demo preparation refuses roots overlapping configured client roots before setup',async()=>{
  let setups=0;const h=harness({protectedRoots:[demo.runs_root],call:async(command)=>{if(command==='doctor')return doctor;if(command==='prepare-demo')return {interface_version:demo.interface_version,runs_root:demo.runs_root,policy_root:demo.policy_root};setups++;return demo;}});
  await h.c.demo();expect(setups).toBe(0);expect(h.c.view().demo).toBe(null);
});
for(const field of ['run_id','operation','input_fingerprint','policy_fingerprint'])test(`action rejects mismatched ${field} receipt`,async()=>{
  const h=harness({call:async(command,request)=>command==='doctor'?doctor:command==='action'?{...receipt(request.runId,request.operation),[field]:field==='operation'?'render-report':field.endsWith('fingerprint')?'b'.repeat(64):'wrong-run'}:snapshot(request.runId)});
  await h.c.select('demo-run');await boundAction(h.c,'validate-run');expect(h.c.view().receipt).toBe(null);
});
test('action refuses an input outside the currently indexed snapshot',async()=>{
  const h=harness();await h.c.select('demo-run');await boundAction(h.c,'validate-input','unknown-input');expect(h.calls.some(call=>call.command==='action')).toBe(false);
});
test('demo keeps its command generation while loading its first fixture',async()=>{
  const h=harness();const pending=h.c.demo();const ticket=h.c.version();await pending;expect(h.c.version()).toBe(ticket);expect(h.c.view().selected).toBe('demo-run');
});
test('real-run entry clears demo roots synchronously before any dependent read',async()=>{
  const h=harness();await h.c.demo();const before=h.calls.length;await h.c.open('client-run');expect(h.c.view().demo).toBe(null);for(const call of h.calls.slice(before))expect(call.request.runsRoot).toBe(undefined);
});
test('wire history rejects a receipt from another run or a substituted receipt path',()=>{
  const value=snapshot();value.receipts=[{path:'cockpit/receipts/action-demo.json',sha256:H,size:10,receipt:receipt()}];expect(snapshotWire(value)).toEqual(value);
  expect(()=>snapshotWire({...value,receipts:[{...value.receipts[0],receipt:receipt('wrong-run')}]})).toThrow();
  expect(()=>snapshotWire({...value,receipts:[{...value.receipts[0],path:'cockpit/receipts/other.json'}]})).toThrow();
});
test('Reports history survives hide and reselect through canonical snapshot projection',async()=>{
  const retained={path:'cockpit/receipts/action-demo.json',sha256:H,size:10,receipt:receipt()};
  const h=harness({call:async(command,request)=>command==='doctor'?doctor:{...snapshot(request.runId),receipts:[retained]}});
  await h.c.select('demo-run','Reports');await h.c.hide();await h.c.select('demo-run','Reports');expect(h.c.view().receipt).toBe(null);expect(h.c.view().snapshot.receipts[0]).toEqual(retained);
});
test('mismatched action receipt keeps a visible diagnostic after fresh snapshot',async()=>{
  const h=harness({call:async(command,request)=>command==='doctor'?doctor:command==='action'?{...receipt(),policy_fingerprint:'b'.repeat(64)}:snapshot(request.runId)});
  await h.c.select('demo-run');await boundAction(h.c,'validate-run');expect(h.c.view().error).toBe('Engine response has a mismatched receipt.');expect(h.c.view().receipt).toBe(null);
});
test('cached contextual navigation binds run/fingerprint and targets indexed input or finding without effects',async()=>{
  const value=snapshot();value.workers[0].missing_inputs=['Provide input-demo'];value.inputs.unshift({...value.inputs[0],id:'other-input',path:'inputs/other.json',platform:'meta'});
  const h=harness({call:async(command)=>command==='doctor'?doctor:value});await h.c.select('demo-run');const before=h.calls.length;
  await h.c.navigate('Inputs',{workerId:'worker-google',missingInput:'Provide input-demo'},'demo-run',H);
  expect(h.c.view().tab).toBe('Inputs');expect(h.c.view().context).toEqual({kind:'inputs',workerId:'worker-google',missingInput:'Provide input-demo',inputIds:['input-demo'],match:'text'});
  await h.c.navigate('Evidence',{platform:'google',controlId:'G-DEMO'},'demo-run',H);expect(h.c.view().context).toEqual({kind:'finding',platform:'google',controlId:'G-DEMO'});expect(h.calls.length).toBe(before);
  for(const [run,fingerprint,target] of [['other-run',H,{platform:'google',controlId:'G-DEMO'}],['demo-run','b'.repeat(64),{platform:'google',controlId:'G-DEMO'}],['demo-run',H,{platform:'google',controlId:'absent'}]]) {
    await h.c.navigate('Evidence',target,run,fingerprint);expect(h.c.view().context.controlId).toBe('G-DEMO');
  }
  await h.c.hide();await h.c.navigate('Evidence',{platform:'google',controlId:'G-DEMO'},'demo-run',H);expect(h.c.view().context).toBe(null);
});
test('missing input navigation distinguishes platform-related fallback from literal text references and clears on select',async()=>{
  const h=harness();await h.c.select('demo-run');await h.c.navigate('Inputs',{workerId:'worker-google',missingInput:'Search terms missing'},'demo-run',H);
  expect(h.c.view().context.match).toBe('platform');expect(h.c.view().context.inputIds).toEqual(['input-demo']);await h.c.select('another-run');expect(h.c.view().context).toBe(null);
});
test('refresh clears contextual selection when the input subject changes',async()=>{
  let value=snapshot();const h=harness({call:async(command)=>command==='doctor'?doctor:value});await h.c.select('demo-run');await h.c.navigate('Evidence',{platform:'google',controlId:'G-DEMO'},'demo-run',H);
  value={...snapshot(),fingerprint:'b'.repeat(64)};await h.c.refresh();expect(h.c.view().context).toBe(null);
});
for(const [id,path,request,match] of [
  ['a','inputs/a.json','Data missing','none'],
  ['input-demo','inputs/example.json','Provide input-demo-extra','none'],
  ['input-demo','inputs/example.json','Provide prefixinput-demo','none'],
  ['input-demo','inputs/example.json','Provide input-demo.json','none'],
  ['input-demo','inputs/example.json','Provide inputs/example.json.bak','none'],
  ['input-demo','inputs/example.json','Provide archive/inputs/example.json','none'],
  ['input-demo','inputs/example.json','Provide inputs/example.json/child','none'],
  ['input-demo','inputs/example.json','Provide input-demo','text'],
  ['a','inputs/a.json','Provide "a", please','text'],
  ['input-demo','inputs/example.json','Provide (inputs/example.json), please','text'],
  ['input-demo','inputs/example.json','inputs/example.json','text'],
  ['input-demo','inputs/example.json','Provide INPUT-DEMO','none'],
])test(`missing request ${request} uses bounded literal reference classification ${match}`,async()=>{
  const value=snapshot();value.inputs=[{...value.inputs[0],id,path,platform:'meta'}];value.workers[0].missing_inputs=[request];
  const h=harness({call:async(command)=>command==='doctor'?doctor:value});await h.c.select('demo-run');const calls=h.calls.length;
  await h.c.navigate('Inputs',{workerId:'worker-google',missingInput:request},'demo-run',H);
  expect(h.c.view().context.match).toBe(match);expect(h.c.view().context.inputIds).toEqual(match==='text'?[id]:[]);expect(h.calls.length).toBe(calls);
});
test('actions require an explicit rendered subject before even a doctor probe',async()=>{
  const h=harness();await h.c.select('demo-run');const before=h.calls.length;await h.c.action('validate-run');expect(h.calls.length).toBe(before);
});
