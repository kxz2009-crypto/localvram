import type { RouteManifestItem } from "../data/i18n-route-manifest";

type LocalizedRouteItem = {
  title: string;
  description: string;
};

type RouteCopyKeyMap = {
  titleKey?: string;
  descriptionKey?: string;
};

const ROUTE_COPY_KEYS: Record<string, RouteCopyKeyMap> = {
  "/en/guides/best-coding-models/": { titleKey: "cta_best_coding" },
  "/en/guides/best-rag-models/": { titleKey: "cta_best_rag" },
  "/en/guides/local-llm-cost-vs-cloud/": {
    titleKey: "card_run_rent_title",
    descriptionKey: "card_run_rent_desc",
  },
  "/en/guides/ollama-local-cluster-network/": {
    titleKey: "card_cluster_title",
    descriptionKey: "card_cluster_desc",
  },
  "/en/guides/ollama-vs-vllm-vram/": {
    titleKey: "card_backend_title",
    descriptionKey: "card_backend_desc",
  },
  "/en/status/content-publish/": { titleKey: "cta_content_publish" },
  "/en/status/conversion-funnel/": { titleKey: "cta_conversion_funnel" },
  "/en/status/data-freshness/": { titleKey: "cta_data_freshness" },
  "/en/status/pipeline-status/": { titleKey: "cta_pipeline_status" },
  "/en/status/runner-health/": { titleKey: "cta_runner_health" },
  "/en/status/submission-review/": { titleKey: "cta_submission_review" },
  "/en/tools/quantization-blind-test/": { titleKey: "cta_quant_test" },
  "/en/tools/roi-calculator/": {
    titleKey: "card_run_rent_title",
    descriptionKey: "card_run_rent_desc",
  },
  "/en/tools/vram-calculator/": { titleKey: "cta_start_vram" },
};

export function localizeRouteItem(
  item: RouteManifestItem,
  homeFields: Record<string, string>,
  fallbackDescription = "",
): LocalizedRouteItem {
  const keys = ROUTE_COPY_KEYS[item.enPath] || {};
  const title = keys.titleKey ? homeFields[keys.titleKey] : "";
  const description = keys.descriptionKey ? homeFields[keys.descriptionKey] : "";
  return {
    title: String(title || item.title || "").trim(),
    description: String(description || fallbackDescription || homeFields.hero_intro || item.description || "").trim(),
  };
}
