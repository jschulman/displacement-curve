// Renders the composite displacement index to a static PNG for GitHub Pages
// (social / OG preview + no-JS fallback). Dark-themed to match the dashboard.
//
//   node tools/render_chart.mjs [inputJson] [outputPng]
//
// Defaults: data/composite/displacement_index.json -> docs/displacement-index.png
// Colors are validated with the dataviz palette method (line #3987e5 vs event
// emphasis #d03b3b: CVD ΔE 25.7, contrast >=3:1 on the dark surface).
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import * as vega from 'vega';
import * as vegaLiteNs from 'vega-lite';
const vegaLite = vegaLiteNs.default ?? vegaLiteNs;
import { Resvg } from '@resvg/resvg-js';

const IN = process.argv[2] ?? 'data/composite/displacement_index.json';
const OUT = process.argv[3] ?? 'docs/displacement-index.png';

const full = JSON.parse(readFileSync(IN, 'utf8'));
const rows = full.monthly.map((m) => ({ date: m.date + '-01', score: m.score }));

// merge same-month layoff events into one emphasized marker
const seen = new Map();
for (const e of full.events ?? []) {
  const d = e.date + '-01';
  const key = d + '|' + e.type;
  if (e.type === 'layoff' && seen.has(d + '|layoff')) { seen.get(d + '|layoff').label = 'AI-cited layoffs'; continue; }
  seen.set(key, { date: d, label: e.label, emphasis: e.type === 'layoff', ylab: 48 });
}
const events = [...seen.values()];
const evMuted = events.filter((e) => !e.emphasis);
const evEmph = events.filter((e) => e.emphasis);

// dark-theme, dataviz-validated palette
const C = {
  line: '#3987e5', bandLow: 'rgba(210,170,90,0.10)', bandHigh: 'rgba(57,135,229,0.12)',
  evMuted: '#6e7681', evEmph: '#d03b3b',
  ink: '#e6edf3', ink2: '#9da7b3', muted: '#7d8590', grid: 'rgba(110,118,129,0.28)', surface: '#0d1117',
};
const bands = [
  // ly = label y-position, placed in open space inside each band so the zone
  // labels clear the event labels that bottom out along the top edge.
  { y0: 0, y1: 25, ly: 22, label: 'Pre-disruption · 0–25', fill: C.bandLow },
  { y0: 25, y1: 50, ly: 37, label: 'Productivity · 26–50', fill: C.bandHigh },
];
const Y = { field: 'score', type: 'quantitative', scale: { domain: [0, 50] },
  axis: { title: 'Composite score', titleColor: C.ink2, values: [0, 10, 20, 30, 40, 50], grid: true, gridColor: C.grid, tickColor: C.grid, labelColor: C.muted } };
const X = { field: 'date', type: 'temporal', axis: { title: null, format: '%b %Y', labelColor: C.muted, tickColor: C.grid, grid: false } };
const evText = (color, extra = {}) => ({ type: 'text', angle: 270, align: 'left', baseline: 'middle', dx: 5, dy: -3, font: 'sans-serif', fontSize: 11, color, ...extra });

const spec = {
  $schema: 'https://vega.github.io/schema/vega-lite/v6.json',
  width: 900, height: 470, background: C.surface,
  title: { text: 'AI Displacement Index — Composite Score',
    subtitle: 'source: displacement-curve · composite of 6 weighted signals',
    anchor: 'start', font: 'sans-serif', fontSize: 21, subtitleFontSize: 12.5, color: C.ink, subtitleColor: C.ink2, offset: 14 },
  layer: [
    { data: { values: bands }, mark: { type: 'rect' },
      encoding: { y: { field: 'y0', type: 'quantitative', scale: { domain: [0, 50] } }, y2: { field: 'y1' }, color: { field: 'fill', type: 'nominal', scale: null, legend: null } } },
    { data: { values: bands }, mark: { type: 'text', align: 'left', baseline: 'middle', dx: 8, font: 'sans-serif', fontSize: 12, fontWeight: 600, color: C.muted },
      encoding: { y: { field: 'ly', type: 'quantitative' }, x: { value: 4 }, text: { field: 'label' } } },
    { data: { values: evMuted }, mark: { type: 'rule', strokeDash: [3, 3], color: C.evMuted, strokeWidth: 1 }, encoding: { x: X } },
    { data: { values: evEmph }, mark: { type: 'rule', strokeDash: [4, 2], color: C.evEmph, strokeWidth: 2 }, encoding: { x: X } },
    { data: { values: rows }, mark: { type: 'line', color: C.line, strokeWidth: 2.5, interpolate: 'monotone' }, encoding: { x: X, y: Y } },
    { data: { values: evMuted }, mark: evText(C.ink2), encoding: { x: X, y: { field: 'ylab', type: 'quantitative' }, text: { field: 'label' } } },
    { data: { values: evEmph }, mark: evText(C.evEmph, { fontWeight: 700 }), encoding: { x: X, y: { field: 'ylab', type: 'quantitative' }, text: { field: 'label' } } },
  ],
  config: { view: { stroke: null }, axis: { domainColor: C.grid, labelFont: 'sans-serif', titleFont: 'sans-serif', labelFontSize: 11 } },
};

const vg = vegaLite.compile(spec).spec;
const view = new vega.View(vega.parse(vg), { renderer: 'none' }).initialize();
const svg = await view.toSVG();
const png = new Resvg(svg, { fitTo: { mode: 'width', value: 1832 }, font: { loadSystemFonts: true } }).render().asPng();
mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, png);
console.log(`rendered ${OUT} (${png.length} bytes) from ${IN} · ${rows.length} points, ${events.length} events`);
