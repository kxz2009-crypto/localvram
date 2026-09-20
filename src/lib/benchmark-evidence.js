/** Match a measured run to an exact model file, never just a mutable family tag.
 * Legacy rows without identity remain available in the tag benchmark archive.
 * This verifies the reported run only, not VRAM fit or answer quality.
 */
export function getProfileBenchmark(profile, benchmarkMap = {}) {
  if (!profile) return null;
  const row = benchmarkMap[profile.ollama_tag];
  if (!row || row.status !== 'ok' || !Number.isFinite(row.tokens_per_second) || row.tokens_per_second <= 0) return null;
  const digest = String(profile.model_digest || '').trim();
  const quantization = String(profile.quantization || '').trim().toUpperCase();
  if (!/^sha256:[a-f0-9]{64}$/i.test(digest) || digest !== row.model_digest) return null;
  if (!quantization || quantization !== String(row.quantization || '').trim().toUpperCase()) return null;
  if (!Number.isInteger(row.num_ctx) || row.num_ctx <= 0 || !row.gpu_model || !Number.isFinite(Date.parse(row.test_time || ""))) return null;
  // The profile views currently label this measurement as RTX 3090 performance.
  if (!/\bRTX 3090\b/i.test(row.gpu_model)) return null;
  return row;
}
