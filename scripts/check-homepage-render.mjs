import { readFileSync, existsSync } from 'node:fs';
import assert from 'node:assert/strict';
const cn=process.argv.includes('--cn');
const root=cn ? 'dist-cn' : 'dist';
const locales=cn ? [''] : ['en/','de/','zh/'];
for (const locale of locales) {
 const html=readFileSync(`${root}/${locale}index.html`,'utf8');
 const tags=[...html.matchAll(/data-model-tag="([^"]+)"/g)].map(match=>match[1]);
 assert.deepEqual(tags,['qwen3.8:27b','gemma4:26b','qwen3.6:27b']);
 assert.ok(html.includes('ollama run qwen3.8:27b'));
 assert.ok(html.includes('https://ollama.com/library/qwen3.8:27b'));
 assert.ok(!html.includes('ollama-verified-pill.svg'));
 assert.ok(!html.includes('1-stündige Dauerlastläufe'),'Unsupported sustained-load claim remains');
 const roi=readFileSync(`${root}/${locale}tools/roi-calculator/index.html`,'utf8');
 assert.ok(roi.includes('data-roi-calculator') && roi.includes('name="cloudTimeRatio"'));
 assert.ok(roi.includes('name="mode"') && roi.includes('data-roi-payback'));
 const bundles=[...roi.matchAll(/src="(\/_astro\/[^\"]+\.js)"/g)].map(match=>match[1]);
 assert.ok(bundles.some(bundle=>existsSync(`${root}${bundle}`)) || [...roi.matchAll(/<script type="module">([\s\S]*?)<\/script>/g)].some(match=>match[1].includes('data-roi-calculator')),'Calculator module must be emitted inline or as a bundle');
 if(cn) assert.ok(roi.includes('本地与云端：按同一任务比较总成本'));
}
console.log(`Homepage + ROI rendered checks passed (${root}: ${locales.length} routes).`);
