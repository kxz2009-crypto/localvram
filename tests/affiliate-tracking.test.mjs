import test from 'node:test';
import assert from 'node:assert/strict';
import { shouldTrackRequest, trackClick } from '../functions/_lib/affiliate.js';
import { onRequest } from '../functions/go/[provider].js';
const request = (method = 'GET', ua = 'Mozilla/5.0', extra = {}) => new Request('https://localvram.com/go/runpod', {method, headers:{'user-agent':ua,...extra}});
test('excludes HEAD, health checks, crawlers and prefetch from telemetry', () => {
  for (const r of [request('HEAD'),request('POST'),request('GET','Googlebot'),request('GET','curl/8.1'),request('GET','Mozilla/5.0',{'sec-purpose':'prefetch'})]) {
    assert.equal(shouldTrackRequest(r),false);
    trackClick({request:r,waitUntil:()=>assert.fail('excluded requests must not write telemetry')},{});
  }
  assert.equal(shouldTrackRequest(request()),true);
});
test('excluded checks still get a working affiliate redirect', async () => {
  const response = await onRequest({request:request('HEAD'),params:{provider:'runpod'},env:{},waitUntil:()=>assert.fail('HEAD tracked')});
  assert.equal(response.status,302);
  assert.equal(new URL(response.headers.get('location')).hostname,'runpod.io');
});
