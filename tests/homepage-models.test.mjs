import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { getHomepageModels } from '../src/lib/homepage-models.js';
const registry=JSON.parse(readFileSync('src/data/homepage-models.json','utf8'));
const now=Date.parse('2026-09-21T00:00:00Z');
test('curated exact tags remain available without catalog or watchlist entries',()=>{
 const rows=getHomepageModels(registry,{}, {},now);
 assert.deepEqual(rows.map(r=>r.tag),['qwen3.8:27b','gemma4:26b','qwen3.6:27b']);
 assert.equal(rows[0].command,'ollama run qwen3.8:27b');
 assert.equal(rows[0].review_due,false);
});
test('sample presence is historical and sample absence is unknown',()=>{
 const rows=getHomepageModels(registry,{updated_at:'2026-09-16',api:{tags:{sample:['gemma4:26b']}}},{},now);
 assert.equal(rows[0].inventory_status,'unknown');
 assert.equal(rows[1].inventory_status,'observed_in_snapshot');
 assert.equal(rows[1].inventory_date,'2026-09-16');
});
test('tag-only benchmark never proves a new featured configuration',()=>{
 const row=getHomepageModels(registry,{}, {'qwen3.8:27b':{status:'ok',tokens_per_second:99}},now)[0];
 assert.equal(row.benchmark_status,'pending_verification');assert.equal(row.measured_tokens_per_second,null);
});
test('outdated official checks are marked for review; unsafe and duplicate sources excluded',()=>{
 const items=[...registry.items,registry.items[0],{tag:'bad',source_url:'https://example.com/library/bad'}];
 const rows=getHomepageModels({...registry,items},{},{},now+40*86400000);
 assert.equal(rows.length,3);assert.ok(rows.every(r=>r.review_due));
});
