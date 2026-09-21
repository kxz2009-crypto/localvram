import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
const root=process.argv.includes('--cn') ? 'dist-cn' : 'dist';
for(const locale of root==='dist-cn' ? [''] : ['en/','zh/']) {
 const home=readFileSync(`${root}/${locale}index.html`,'utf8');
 const updates=readFileSync(`${root}/${locale}updates/index.html`,'utf8');
 assert.ok(home.includes('data-daily-articles') && updates.includes('data-daily-articles'));
 assert.ok(updates.includes('qwen38-27b-cost-from-measured-workload'));
 const index=readFileSync(`${root}/${locale}blog/index.html`,'utf8');
 assert.ok(!/<a[^>]+>快速结论<\/a>/.test(index),'Generic body section leaked into article titles');
 const post=readFileSync(`${root}/${locale}blog/qwen38-27b-cost-from-measured-workload/index.html`,'utf8');
 assert.ok(post.includes('3.6 million') || post.includes('360 万'));
 assert.ok(post.includes('roi-calculator/?model=qwen3.8%3A27b'));
}
console.log(`Daily blog render checks passed: ${root}`);
