import { getProfileBenchmark } from './benchmark-evidence.js';

/** Homepage selection is independent of the short-lived benchmark/content queue. */
export function getHomepageModels(registry, runner = {}, benchmarkMap = {}, now = Date.now()) {
  const snapshotTags = new Set((runner.api?.tags?.sample || []).map(tag => String(tag).toLowerCase()));
  const seen = new Set();
  return [...(registry.items || [])]
    .filter(item => {
      if (!item?.tag || seen.has(item.tag)) return false;
      try {
        const source = new URL(item.source_url);
        if (source.protocol !== 'https:' || source.hostname !== 'ollama.com' || decodeURIComponent(source.pathname) !== `/library/${item.tag}`) return false;
      } catch { return false; }
      seen.add(item.tag);
      return true;
    })
    .sort((a,b) => (a.priority ?? 999) - (b.priority ?? 999))
    .map(item => {
      const checked = Date.parse(item.source_checked_at || '');
      const reviewDue = !Number.isFinite(checked) || checked > now || now - checked > (registry.review_interval_days || 30) * 86400000;
      const measured = getProfileBenchmark({ ...item, ollama_tag:item.tag }, benchmarkMap);
      return {
        ...item,
        review_due: reviewDue,
        source_date: Number.isFinite(checked) ? new Date(checked).toISOString().slice(0,10) : '',
        // A missing tag in a sample says nothing about the full local inventory.
        inventory_status: snapshotTags.has(item.tag.toLowerCase()) ? 'observed_in_snapshot' : 'unknown',
        inventory_date: runner.updated_at || '',
        benchmark_status: measured ? 'measured' : 'pending_verification',
        measured_tokens_per_second: measured?.tokens_per_second ?? null,
        command: `ollama run ${item.tag}`,
      };
    });
}
