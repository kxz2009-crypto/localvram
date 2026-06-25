type CatalogModel = {
  id?: string;
  name?: string;
  slug?: string;
  ollama_tag?: string;
  quantization?: string;
  updated_at?: string;
  data_status?: string;
  popularity?: string;
  top20_rank?: number | null;
  is_top20_curated?: boolean;
  category_label?: string;
};

type BenchmarkRow = {
  status?: string;
  tokens_per_second?: number;
  test_time?: string;
};

type WatchlistRow = {
  tag?: string;
  landing?: string;
  status?: string;
  benchmark_status?: {
    status?: string;
  };
  local_inventory_status?: {
    status?: string;
  };
};

export type FeaturedTestModel = CatalogModel & {
  featured_tag: string;
  featured_label: string;
  featured_path: string;
  measured_tokens_per_second: number | null;
  measured_at: string;
};

const FALLBACK_FEATURED_TAGS = [
  "qwen3-coder:30b",
  "qwen3.6:35b",
  "ministral-3:14b",
  "qwen3:8b",
  "gemma3:27b",
  "llama4:16x17b",
  "gpt-oss:20b",
  "mistral-small:22b",
] as const;

const QUANTIZATION_PRIORITY: Record<string, number> = {
  Q4: 0,
  Q5: 1,
  Q8: 2,
  FP16: 3,
  CLOUD: 4,
};

const NEW_MODEL_FAMILY_HINTS = [
  "qwen3-coder",
  "gpt-oss",
  "llama4",
  "qwen3.6",
  "qwen3.5",
  "qwen3",
  "ministral",
  "nemotron",
  "magistral",
  "glm-4",
  "translategemma",
] as const;

function fallbackTagPriority(tag: string): number {
  const index = FALLBACK_FEATURED_TAGS.indexOf(tag as (typeof FALLBACK_FEATURED_TAGS)[number]);
  return index === -1 ? FALLBACK_FEATURED_TAGS.length + 1 : index;
}

function quantizationPriority(value: string): number {
  return QUANTIZATION_PRIORITY[value.toUpperCase()] ?? 10;
}

function benchmarkFor(tag: string, benchmarkMap: Record<string, BenchmarkRow>): BenchmarkRow | null {
  const row = benchmarkMap[tag];
  if (!row || row.status !== "ok" || typeof row.tokens_per_second !== "number") {
    return null;
  }
  return row;
}

function toFeaturedModel(
  item: CatalogModel,
  benchmarkMap: Record<string, BenchmarkRow>,
): FeaturedTestModel {
  const tag = String(item.ollama_tag || "");
  const benchmark = benchmarkFor(tag, benchmarkMap);
  return {
    ...item,
    featured_tag: tag,
    featured_label: String(item.name || tag),
    featured_path: `/en/models/${item.slug || item.id || ""}/`,
    measured_tokens_per_second: benchmark?.tokens_per_second ?? null,
    measured_at: String(benchmark?.test_time || ""),
  };
}

function compareCatalogModelQuality(
  a: CatalogModel,
  b: CatalogModel,
  benchmarkMap: Record<string, BenchmarkRow>,
): number {
  const aTag = String(a?.ollama_tag || "");
  const bTag = String(b?.ollama_tag || "");
  const aMeasured = benchmarkFor(aTag, benchmarkMap) ? 0 : 1;
  const bMeasured = benchmarkFor(bTag, benchmarkMap) ? 0 : 1;
  if (aMeasured !== bMeasured) {
    return aMeasured - bMeasured;
  }

  const byQuantization =
    quantizationPriority(String(a?.quantization || "")) -
    quantizationPriority(String(b?.quantization || ""));
  if (byQuantization !== 0) {
    return byQuantization;
  }

  const aUpdated = Date.parse(String(a?.updated_at || "")) || 0;
  const bUpdated = Date.parse(String(b?.updated_at || "")) || 0;
  if (aUpdated !== bUpdated) {
    return bUpdated - aUpdated;
  }

  return String(a?.name || "").localeCompare(String(b?.name || ""));
}

function newModelFamilyScore(item: CatalogModel): number {
  const haystack = `${item.id || ""} ${item.name || ""} ${item.ollama_tag || ""}`.toLowerCase();
  const index = NEW_MODEL_FAMILY_HINTS.findIndex((hint) => haystack.includes(hint));
  return index === -1 ? NEW_MODEL_FAMILY_HINTS.length + 1 : index;
}

function popularityScore(item: CatalogModel): number {
  const rank = Number(item.top20_rank);
  if (Number.isFinite(rank) && rank > 0) {
    return rank;
  }
  if (item.is_top20_curated) {
    return 30;
  }
  return String(item.popularity || "").trim() ? 40 : 80;
}

function localAvailabilityScore(item: CatalogModel, benchmarkMap: Record<string, BenchmarkRow>): number {
  const tag = String(item?.ollama_tag || "");
  const status = String(item?.data_status || "").toLowerCase();
  if (status === "local_inventory" || status === "measured" || benchmarkFor(tag, benchmarkMap)) {
    return 0;
  }
  return 1;
}

function isFeaturedCandidate(item: CatalogModel): boolean {
  const tag = String(item?.ollama_tag || "").trim();
  const quantization = String(item?.quantization || "").toUpperCase();
  const category = String(item?.category_label || "").toLowerCase();
  return Boolean(tag) && quantization !== "CLOUD" && category !== "embedding";
}

function compareDynamicCatalogCandidate(
  a: CatalogModel,
  b: CatalogModel,
  benchmarkMap: Record<string, BenchmarkRow>,
): number {
  const byLocalAvailability =
    localAvailabilityScore(a, benchmarkMap) - localAvailabilityScore(b, benchmarkMap);
  if (byLocalAvailability !== 0) {
    return byLocalAvailability;
  }

  const byNewFamily = newModelFamilyScore(a) - newModelFamilyScore(b);
  if (byNewFamily !== 0) {
    return byNewFamily;
  }

  const aTag = String(a?.ollama_tag || "");
  const bTag = String(b?.ollama_tag || "");
  const aMeasured = benchmarkFor(aTag, benchmarkMap) ? 0 : 1;
  const bMeasured = benchmarkFor(bTag, benchmarkMap) ? 0 : 1;
  if (aMeasured !== bMeasured) {
    return aMeasured - bMeasured;
  }

  const byPopularity = popularityScore(a) - popularityScore(b);
  if (byPopularity !== 0) {
    return byPopularity;
  }

  return compareCatalogModelQuality(a, b, benchmarkMap);
}

function tagFromWatchlist(row: WatchlistRow): string {
  return String(row?.tag || "").trim();
}

function preferredTagsFromWatchlist(watchlistRaw: unknown): string[] {
  const rows = Array.isArray(watchlistRaw) ? (watchlistRaw as WatchlistRow[]) : [];
  const seen = new Set<string>();
  const tags: string[] = [];
  for (const row of rows) {
    const tag = tagFromWatchlist(row);
    if (!tag || seen.has(tag)) {
      continue;
    }
    seen.add(tag);
    tags.push(tag);
  }
  return tags;
}

function pushUniqueModel(target: CatalogModel[], item: CatalogModel, seen: Set<string>): void {
  const key = String(item.id || item.slug || item.ollama_tag || "");
  if (!key || seen.has(key)) {
    return;
  }
  seen.add(key);
  target.push(item);
}

export function getFeaturedTestModels(
  catalogItems: unknown,
  benchmarkMapRaw: unknown,
  watchlistRaw?: unknown,
): FeaturedTestModel[] {
  const items = Array.isArray(catalogItems) ? (catalogItems as CatalogModel[]) : [];
  const benchmarkMap = (
    benchmarkMapRaw && typeof benchmarkMapRaw === "object" ? benchmarkMapRaw : {}
  ) as Record<string, BenchmarkRow>;
  const selected: CatalogModel[] = [];
  const seen = new Set<string>();
  const preferredTags = preferredTagsFromWatchlist(watchlistRaw);

  for (const tag of preferredTags) {
    const bestMatch = items
      .filter((item) => String(item?.ollama_tag || "").trim() === tag)
      .sort((a, b) => compareCatalogModelQuality(a, b, benchmarkMap))[0];
    if (bestMatch) {
      pushUniqueModel(selected, bestMatch, seen);
    }
  }

  [...items]
    .filter(isFeaturedCandidate)
    .sort((a, b) => compareDynamicCatalogCandidate(a, b, benchmarkMap))
    .slice(0, 24)
    .forEach((item) => pushUniqueModel(selected, item, seen));

  [...items]
    .filter((item) => {
      const tag = String(item?.ollama_tag || "").trim();
      return tag && fallbackTagPriority(tag) <= FALLBACK_FEATURED_TAGS.length;
    })
    .sort((a, b) => {
      const aTag = String(a?.ollama_tag || "");
      const bTag = String(b?.ollama_tag || "");
      const byTag = fallbackTagPriority(aTag) - fallbackTagPriority(bTag);
      if (byTag !== 0) {
        return byTag;
      }
      return compareCatalogModelQuality(a, b, benchmarkMap);
    })
    .forEach((item) => pushUniqueModel(selected, item, seen));

  if (!selected.length) {
    [...items]
      .filter((item) => String(item?.ollama_tag || "").trim())
      .sort((a, b) => compareCatalogModelQuality(a, b, benchmarkMap))
      .forEach((item) => pushUniqueModel(selected, item, seen));
  }

  return selected.map((item) => toFeaturedModel(item, benchmarkMap));
}

export function getFeaturedTestModel(
  catalogItems: unknown,
  benchmarkMapRaw: unknown,
  watchlistRaw?: unknown,
): FeaturedTestModel | null {
  return getFeaturedTestModels(catalogItems, benchmarkMapRaw, watchlistRaw)[0] || null;
}
