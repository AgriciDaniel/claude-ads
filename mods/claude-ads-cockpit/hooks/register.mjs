import { atom, read, update } from 'claude-code';
import { binding, buildArgv } from './launcher.mjs';
import { MESSAGES } from './lexicon.mjs';
import { createController, emptyView } from './controller.mjs';
import { drawPane, drawBand } from './views.mjs';
const PANE = 'ads-cockpit';
const view = atom({ plugin: 'ads-cockpit', key: 'view' }, emptyView());
let controller = null;
async function invoke($, config, command, request = {}) {
  const argv = buildArgv(config, command, request);
  let result;
  try { result = await $.process.run(argv, { timeoutMs: 30000 }); }
  catch { throw new Error(MESSAGES.didNotFinish); }
  if (result.exitCode !== 0 || typeof result.stdout !== 'string' || result.stdout.length > 2000000) throw new Error(MESSAGES.refused);
  try { return JSON.parse(result.stdout); }
  catch { throw new Error(MESSAGES.incompatible); }
}
function getController($, options) {
    if (!controller) controller = createController({
      protectedRoots: [options?.coreRoot, options?.runsRoot].filter(value => typeof value === 'string' && value),
      call: (command, request) => invoke($, binding(options), command, request),
      publish: value => update($, view, () => value),
      // A timer callback has no caller to catch for it, so a failure ends here and never goes unhandled.
      after: (ms, fn) => $.clock.after(ms, () => { try { Promise.resolve(fn()).catch(() => {}); } catch { /* ends this tick only */ } }),
      // Drawn means placed and shown. Polling pauses while the pane is closed, undrawn or a background tab.
      isDrawn: async () => (await $.ui.panes()).some(pane => pane.id === PANE && pane.isPlaced && pane.isShown),
    });
    return controller;
}
async function openWorkbench($, c, runId) {
  if (controller !== c || !c.view().visible || c.view().selected !== runId) return;
  // Only a user callback opens the cached workbench; no core read is needed.
  await $.ui.open({id:PANE,title:'Claude Ads Cockpit',focus:true,columns:100,rows:40});
}
const controls = ($, c) => ({
    workbench: runId => openWorkbench($,c,runId),
    navigate: (tab,target,runId,fingerprint) => c.navigate(tab,target,runId,fingerprint),
    chooser: () => c.chooser(), select: id => c.select(id), refresh: () => c.refresh(),
    action: (operation, inputId, format, subject) => c.action(operation,inputId,format,subject), demo: () => c.demo(),
    step: delta => c.step(delta), reset: () => c.reset(), tab: value => c.tab(value), details: () => c.details(), baseline: value => c.baseline(value),
    page: delta => c.page(delta), filter: () => c.filter(), clearContext: () => c.clearContext(),
    hide: async () => { await c.hide(); await $.ui.close({ id: PANE }); },
  });
export function register(on, options) {
  on('session.start', async ($, e, next) => {
    if (controller) await controller.dispose();
    controller = null; await update($, view, () => emptyView());
    // A taken name must not skip the rest of this hook, so the registration is allowed to fail.
    try { await $.command.register({name:'ads-cockpit',description:'Open local Claude Ads cockpit or synthetic demo',argumentHint:'[open <id>|demo|hide|doctor]',immediate:true}); }
    catch { $.ui.log('ads-cockpit: the /ads-cockpit command could not be registered (name taken?). The pane and band still work.', { to: 'debug' }); }
    return next(e);
  }).catch(($, e, next) => next(e));
  on('classic.SessionStart', { source: ['clear','resume','fork'] }, async ($, e, next) => {
    if (controller) await controller.dispose(); controller = null;
    await update($, view, () => emptyView()); await $.ui.close({id:PANE});
    return next(e);
  }).catch(($, e, next) => next(e));
  on('session.end', async ($, e, next) => { if (controller) await controller.dispose(); controller = null; return next(e); });
  on('command.run', {command:'ads-cockpit'}, async ($, e) => {
    const c = getController($, options); const args = e.args.trim().split(/\s+/).filter(Boolean);
    if (args[0] === 'hide' && args.length === 1) { await controls($,c).hide(); return {text:'Claude Ads Cockpit hidden; session data cleared.'}; }
    if (args[0] === 'doctor' && args.length === 1) {
      const status = await c.doctor();
      // An unavailable engine says why in plain words; the message is a fixed string, never a path.
      return {text:`Claude Ads Cockpit local compatibility: ${status}.${status === 'unavailable' && c.view().error ? ` ${c.view().error}` : ''}`};
    }
    let pending;
    if (!args.length) pending = c.chooser();
    else if (args[0] === 'demo' && args.length === 1) pending = c.demo();
    else if (args[0] === 'open' && args.length === 2 && /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(args[1])) {
      // Explicit real-run entry exits demo before selecting any client data.
      pending = c.open(args[1]);
    } else return {text:'Use /ads-cockpit [open <id>|demo|hide|doctor].'};
    const ticket = c.version();
    await pending;
    if (controller !== c || c.version() !== ticket || !c.view().visible) return {};
    const surfaces = await $.session.surfaces();
    if (controller !== c || c.version() !== ticket || !c.view().visible) return {};
    if (!surfaces.some(surface => surface === 'terminal' || surface === 'desktop' || surface?.surface === 'terminal' || surface?.surface === 'desktop')) {
      await c.hide(); return {text:'Claude Ads Cockpit local request finished. Visual cockpit requires terminal or Desktop; session data cleared.'};
    }
    await $.ui.open({id:PANE,title:'Claude Ads Cockpit',focus:true,columns:100,rows:40});
    return {};
  });
  on('ui.close', {id:PANE}, async ($, e, next) => { if (controller) await controller.hide(); return next(e); }).catch(($, e, next) => next(e));
  // A turn end never waits on the core: a pending run is refreshed in the background, and only if it is drawn.
  on('turn.complete', async ($, e, next) => {
    if (controller) void controller.refreshIfPending().catch(() => {});
    return next(e);
  }).catch(($, e, next) => next(e));
  on('ui.render', {component:'Pane'}, async ($, e, next) => {
    if (e.requestId !== PANE) return next(e);
    const cached = await read($,view);
    if (!cached.visible) return next(e);
    const ui = $.ui.resolve(e);
    // Render reads session state only; controller effects run in user callbacks.
    // The host says how many rows the body may use; the pane is drawn to fit them, so it never needs to scroll.
    return drawPane(ui,cached,controls($,getController($, options)),e.props.bodyColumns,e.props.isFocused !== false,e.props.scroll?.bodyRows);
  });
  on('ui.render', {component:'AbovePrompt'}, async ($, e, next) => {
    const other = await next(e);
    if (e.props.hasSurvey) return other;
    const cached = await read($,view);
    if (!cached.visible) return other;
    return drawBand($.ui.resolve(e),cached,other,controls($,getController($, options)),e.props.bodyColumns);
  });
}
