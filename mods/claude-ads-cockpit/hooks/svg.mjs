// Desktop and VS Code only: small SVG graphics. Text and tracks use currentColor so they read on light
// and dark; status colors are fixed mid-tones. Only called when the surface's kit has Svg.
import { SVG_COLORS } from './theme.mjs';
import { safeText } from './wire.mjs';

const esc = value => safeText(value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const doc = (width, height, body) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" font-family="system-ui, sans-serif">${body}</svg>`;

// A ring for steps done of steps total, with the fraction in the middle.
export function runRing(Svg, c, tone = 'info') {
  const R = 34;
  const C = 2 * Math.PI * R;
  const fraction = c.workers > 0 ? Math.min(1, c.done / c.workers) : 0;
  const color = SVG_COLORS[tone] || SVG_COLORS.muted;
  const arc = fraction > 0 ? `<circle cx="48" cy="48" r="${R}" fill="none" stroke="${color}" stroke-width="9" stroke-linecap="round" stroke-dasharray="${(fraction * C).toFixed(1)} ${C.toFixed(1)}" transform="rotate(-90 48 48)"/>` : '';
  const body = `<circle cx="48" cy="48" r="${R}" fill="none" stroke="currentColor" stroke-opacity="0.16" stroke-width="9"/>${arc}<text x="48" y="53" text-anchor="middle" font-size="19" font-weight="600" fill="currentColor">${c.done}/${c.workers}</text><text x="48" y="68" text-anchor="middle" font-size="8" fill="currentColor" fill-opacity="0.6">steps done</text>`;
  return Svg({ source: doc(96, 96, body), alt: `${c.done} of ${c.workers} steps done`, width: 96, height: 96 });
}

// A donut of the audit: green passing, red needing work, grey not enough data. The middle says how much was judged.
export function coverageRing(Svg, cov) {
  const R = 34;
  const C = 2 * Math.PI * R;
  const total = cov.pass + cov.fail + cov.unknown;
  if (!total) return null;
  let offset = 0;
  const arc = (n, color) => {
    if (!n) return '';
    const length = (n / total) * C;
    const out = `<circle cx="48" cy="48" r="${R}" fill="none" stroke="${color}" stroke-width="10" stroke-dasharray="${Math.max(0, length - 1.5).toFixed(1)} ${(C - Math.max(0, length - 1.5)).toFixed(1)}" stroke-dashoffset="${(-offset).toFixed(1)}" transform="rotate(-90 48 48)"/>`;
    offset += length;
    return out;
  };
  const body = `${arc(cov.pass, SVG_COLORS.ok)}${arc(cov.fail, SVG_COLORS.bad)}${arc(cov.unknown, SVG_COLORS.muted)}<text x="48" y="53" text-anchor="middle" font-size="19" font-weight="600" fill="currentColor">${cov.percent}%</text><text x="48" y="68" text-anchor="middle" font-size="8" fill="currentColor" fill-opacity="0.6">judged</text>`;
  return Svg({ source: doc(96, 96, body), alt: `${cov.pass} passing, ${cov.fail} need work, ${cov.unknown} without enough data`, width: 96, height: 96 });
}

// One stacked bar: how much of the evidence is up to date, out of date or missing.
export function supportBar(Svg, current, old, missing) {
  const total = current + old + missing;
  if (!total) return null;
  const W = 240;
  let x = 0;
  const seg = (n, color) => { const w = (n / total) * W; const out = n ? `<rect x="${x.toFixed(1)}" y="0" width="${w.toFixed(1)}" height="10" rx="3" fill="${color}"/>` : ''; x += w; return out; };
  const body = `${seg(current, SVG_COLORS.ok)}${seg(old, SVG_COLORS.warn)}${seg(missing, SVG_COLORS.bad)}`;
  return Svg({ source: doc(W, 10, body), alt: `${current} up to date, ${old} out of date, ${missing} missing`, width: W, height: 10 });
}

// A strip of saved actions, newest on the right: green succeeded, red failed, amber blocked.
export function receiptStrip(Svg, outcomes) {
  if (!outcomes.length) return null;
  const items = outcomes.slice(-24);
  const body = items.map((o, i) => `<circle cx="${8 + i * 16}" cy="8" r="5" fill="${o === 'succeeded' ? SVG_COLORS.ok : o === 'failed' ? SVG_COLORS.bad : SVG_COLORS.warn}"/>`).join('');
  return Svg({ source: doc(8 + items.length * 16, 16, body), alt: `${items.length} saved actions: ${esc(items.join(', '))}`, width: 8 + items.length * 16, height: 16 });
}
