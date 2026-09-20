import test from 'node:test';
import assert from 'node:assert/strict';
import { getProfileBenchmark } from '../src/lib/benchmark-evidence.js';
const profile = { ollama_tag: 'example:14b', quantization: 'Q4_K_M', model_digest: `sha256:${'a'.repeat(64)}` };
const run = { ...profile, status: 'ok', tokens_per_second: 42, num_ctx: 4096, gpu_model: 'NVIDIA GeForce RTX 3090', test_time: '2026-09-20T00:00:00Z' };
const map = { [profile.ollama_tag]: run };
test('accepts the exact file and quantization under the recorded run conditions', () => {
  assert.equal(getProfileBenchmark(profile, map), run);
});
test('never reuses one run across Q4, Q5, Q8 or FP16 profiles sharing the same tag', () => {
  for (const quantization of ['Q4', 'Q5', 'Q8', 'FP16']) assert.equal(getProfileBenchmark({ ...profile, quantization }, map), null);
});
test('legacy and changed model files fail closed even with a successful tag result', () => {
  assert.equal(getProfileBenchmark({ ollama_tag: profile.ollama_tag, quantization: 'Q4_K_M' }, map), null);
  assert.equal(getProfileBenchmark({ ...profile, model_digest: `sha256:${'b'.repeat(64)}` }, map), null);
  assert.equal(getProfileBenchmark(profile, { [profile.ollama_tag]: { status: 'ok', tokens_per_second: 42 } }), null);
});
test('rejects failed, non-finite, missing-condition and different-hardware measurements', () => {
  for (const change of [{status:'error'}, {tokens_per_second:NaN}, {tokens_per_second:Infinity}, {tokens_per_second:0}, {num_ctx:0}, {gpu_model:'NVIDIA RTX 4090'}, {test_time:''}]) {
    assert.equal(getProfileBenchmark(profile, { [profile.ollama_tag]: {...run, ...change} }), null);
  }
});
