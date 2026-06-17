type CatalogModel = {
  id?: string;
  name?: string;
  slug?: string;
  ollama_tag?: string;
  quantization?: string;
  updated_at?: string;
};

type BenchmarkRow = {
  status?: string;
  tokens_per_second?: number;
  test_time?: string;
};

export type FeaturedTestModel = CatalogModel & {
  featured_tag: string;
  featured_label: string;
  featured_path: string;
  measured_tokens_per_second: number | null;
  measured_at: string;
};

const FEATURED_TAGS = [
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

function tagPriority(tag: string): number {
  const index = FEATURED_TAGS.indexOf(tag as (typeof FEATURED_TAGS)[number]);
  return index === -1 ? FEATURED_TAGS.length + 1 : index;
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

export function getFeaturedTestModels(
  catalogItems: unknown,
  benchmarkMapRaw: unknown,
): FeaturedTestModel[] {
  const items = Array.isArray(catalogItems) ? (catalogItems as CatalogModel[]) : [];
  const benchmarkMap = (
    benchmarkMapRaw && typeof benchmarkMapRaw === "object" ? benchmarkMapRaw : {}
  ) as Record<string, BenchmarkRow>;

  return [...items]
    .filter((item) => {
      const tag = String(item?.ollama_tag || "").trim();
      return tag && tagPriority(tag) <= FEATURED_TAGS.length;
    })
    .sort((a, b) => {
      const aTag = String(a?.ollama_tag || "");
      const bTag = String(b?.ollama_tag || "");
      const byTag = tagPriority(aTag) - tagPriority(bTag);
      if (byTag !== 0) {
        return byTag;
      }

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
    })
    .map((item) => {
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
    });
}

export function getFeaturedTestModel(
  catalogItems: unknown,
  benchmarkMapRaw: unknown,
): FeaturedTestModel | null {
  return getFeaturedTestModels(catalogItems, benchmarkMapRaw)[0] || null;
}
