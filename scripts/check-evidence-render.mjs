import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
import { getProfileBenchmark } from '../src/lib/benchmark-evidence.js';
const catalog = JSON.parse(readFileSync('src/data/model-catalog.json','utf8'));
const benchmarks = JSON.parse(readFileSync('src/data/benchmark-results.json','utf8')).models;
let checked = 0;
for (const profile of catalog.items) {
  if (getProfileBenchmark(profile, benchmarks)) continue;
  const html = readFileSync(`dist/en/models/${profile.id}/index.html`,'utf8');
  assert.ok(!html.includes('Verified by Real Hardware'),`${profile.id}: unproven profile displays a verified badge`);
  checked++;
}
for (const locale of ['en','de','ko']) {
  const html=readFileSync(`dist/${locale}/status/conversion-funnel/index.html`,'utf8');
  assert.ok(html.includes('N/A — no session attribution'),`${locale}: missing unavailable conversion state`);
  assert.ok(!html.includes('29000%'),`${locale}: invalid rate remains`);
}
const tagArchive=readFileSync('dist/en/hardware/verified-3090/index.html','utf8');
const hasUnlinkedTag = Object.entries(benchmarks).some(([tag,row]) => row.status === 'ok' && !catalog.items.some(profile => profile.ollama_tag === tag && getProfileBenchmark(profile, benchmarks)));
if (hasUnlinkedTag) assert.ok(tagArchive.includes('tag-level reference; exact profile unverified'),'Legacy tag evidence must remain accessible with its limitation');
console.log(`Rendered evidence checks passed: ${checked} unproven profiles; conversion pages and legacy archive checked.`);
