// One source for what the person reads. Raw wire values never reach the screen.
import { toneOf } from './theme.mjs';
const w = (word, tone) => Object.freeze({ word, tone });
export const LEXICON = Object.freeze({
  workflow: { pending: w('Queued', 'muted'), running: w('Running', 'info'), completed: w('Finished', 'ok'), blocked: w('Blocked', 'bad'), failed: w('Failed', 'bad'), unknown: w('Unknown', 'muted') },
  completeness: { complete: w('Complete', 'ok'), partial: w('Partial', 'warn'), failed: w('Failed', 'bad') },
  worker: { pending: w('Queued', 'muted'), running: w('Working', 'info'), completed: w('Done', 'ok'), failed: w('Failed', 'bad'), skipped: w('Skipped', 'muted') },
  result: { ok: w('Result recorded', 'ok'), needs_input: w('Waiting for your input', 'warn'), blocked: w('Blocked', 'bad'), failed: w('Failed', 'bad'), none: w('No result yet', 'muted') },
  finding: { pass: w('Pass', 'ok'), fail: w('Fail', 'bad'), unknown: w('Not enough data', 'unclear'), not_applicable: w('Not applicable', 'muted') },
  severity: { critical: w('Critical', 'bad'), high: w('High', 'bad'), medium: w('Medium', 'warn'), informational: w('Info', 'muted') },
  confidence: { high: w('High', 'ok'), medium: w('Medium', 'warn'), low: w('Low', 'warn'), none: w('None', 'muted') },
  support: { current: w('Up to date', 'ok'), stale: w('Out of date', 'warn'), demoted: w('Less certain', 'warn'), missing: w('No support', 'bad'), contested: w('Sources disagree', 'warn'), provisional: w('Not final', 'warn') },
  input: { unchecked: w('Not checked yet', 'muted'), valid: w('Valid structure', 'ok'), invalid: w('Invalid', 'bad'), missing: w('File missing', 'bad') },
  outcome: { succeeded: w('Succeeded', 'ok'), failed: w('Failed', 'bad'), blocked: w('Blocked', 'warn') },
  change: { new_failure: w('New failure', 'bad'), new_finding: w('New finding', 'info'), newly_unknown: w('Now unknown', 'warn'), not_retested: w('Not retested', 'muted'), status_changed: w('Changed', 'info'), unchanged: w('Unchanged', 'muted') },
  scoring: { normal: w('Scored', 'ok'), provisional: w('Early estimate', 'warn'), insufficient_evidence: w('Not enough evidence to score', 'muted') },
  operation: { 'validate-input': w('Input check', 'muted'), 'validate-run': w('Run check', 'muted'), 'render-report': w('Report', 'muted') },
  privacy: { public: w('Public', 'muted'), internal: w('Internal', 'muted'), confidential: w('Confidential', 'warn'), restricted: w('Restricted', 'warn') },
});
// Fixed messages that may reach the screen from outside the controller. Each is a constant with no
// path, stderr or account data in it, so it can be shown as written. Anything else collapses to
// MESSAGES.unavailable. Terms used on screen: checks, steps, platform and engine (the local Claude Ads core).
export const MESSAGES = Object.freeze({
  setup: 'Not set up yet. Set the ads-cockpit options coreRoot and pythonExecutable to full paths (run: claude plugin configure ads-cockpit), then open the cockpit again.',
  runs: 'No runs folder is set. Set the ads-cockpit option runsRoot (run: claude plugin configure ads-cockpit), or try the practice demo.',
  unavailable: 'Local request unavailable. Run doctor or refresh the selected run.',
  didNotFinish: 'The local engine did not finish. Check coreRoot and pythonExecutable, then retry.',
  refused: 'The local engine refused the request. Run doctor or refresh the selected run.',
  incompatible: 'The local engine returned an incompatible response.',
  badId: 'Select a valid registered run or input ID.',
  bandSetup: 'Claude Ads Cockpit: not set up yet. Set coreRoot and pythonExecutable.',
  bandUnavailable: 'Claude Ads Cockpit: local request unavailable.',
});
const NAMES = { google: 'Google Ads', meta: 'Meta Ads', youtube: 'YouTube Ads', linkedin: 'LinkedIn Ads', tiktok: 'TikTok Ads', microsoft: 'Microsoft Ads', apple: 'Apple Ads', amazon: 'Amazon Ads', reddit: 'Reddit Ads', pinterest: 'Pinterest Ads', snapchat: 'Snapchat Ads', x: 'X Ads' };
export const humanize = value => String(value ?? '').replace(/[_-]+/g, ' ').trim().replace(/^./, c => c.toUpperCase());
export function say(group, value) {
  const entry = LEXICON[group]?.[value ?? 'none'];
  return entry || Object.freeze({ word: humanize(value) || 'Unknown', tone: 'muted' });
}
export const toneFor = (group, value) => toneOf(say(group, value).tone);
export const platformName = platform => (platform ? NAMES[platform] || humanize(platform) : 'Shared');
export const shortHash = hash => String(hash ?? '').slice(0, 8);
export function bytes(n) {
  if (!Number.isFinite(n)) return '';
  if (n < 1024) return `${n} B`;
  if (n < 1048576) return `${(n / 1024).toFixed(n < 10240 ? 1 : 0)} KB`;
  return `${(n / 1048576).toFixed(1)} MB`;
}
// Timestamps are shown in UTC so a screenshot means the same thing everywhere.
export function when(iso) {
  const s = String(iso ?? '');
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(s) ? `${s.slice(0, 10)} ${s.slice(11, 16)} UTC` : s || 'unknown';
}
export const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
