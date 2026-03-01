export type RouteManifestItem = {
  slug: string;
  title: string;
  description: string;
  enPath: string;
};

export const GUIDE_ROUTE_ITEMS: RouteManifestItem[] = [
  {
    slug: "best-coding-models",
    title: "Best Coding Models",
    description: "Model recommendations for code generation, refactoring, and debugging workflows.",
    enPath: "/en/guides/best-coding-models/",
  },
  {
    slug: "best-rag-models",
    title: "Best RAG Models",
    description: "RAG-focused model choices for retrieval quality, latency, and VRAM efficiency.",
    enPath: "/en/guides/best-rag-models/",
  },
  {
    slug: "local-llm-cost-vs-cloud",
    title: "Local LLM Cost vs Cloud",
    description: "Decision framework for local deployment versus cloud inference cost.",
    enPath: "/en/guides/local-llm-cost-vs-cloud/",
  },
  {
    slug: "ollama-local-cluster-network",
    title: "Ollama Local Cluster Network",
    description: "Operator checklist for local cluster planning and network setup.",
    enPath: "/en/guides/ollama-local-cluster-network/",
  },
  {
    slug: "ollama-vs-vllm-vram",
    title: "Ollama vs vLLM VRAM",
    description: "Runtime comparison guide for VRAM planning and backend selection.",
    enPath: "/en/guides/ollama-vs-vllm-vram/",
  },
];

export const STATUS_ROUTE_ITEMS: RouteManifestItem[] = [
  {
    slug: "content-publish",
    title: "Content Publish Status",
    description: "Publishing cadence, queue state, and content operations visibility.",
    enPath: "/en/status/content-publish/",
  },
  {
    slug: "conversion-funnel",
    title: "Conversion Funnel",
    description: "Search intent to conversion funnel tracking for decision pages and outbound clicks.",
    enPath: "/en/status/conversion-funnel/",
  },
  {
    slug: "data-freshness",
    title: "Data Freshness",
    description: "Freshness status for model benchmarks, catalog data, and update pipelines.",
    enPath: "/en/status/data-freshness/",
  },
  {
    slug: "pipeline-status",
    title: "Pipeline Status",
    description: "Workflow health, SLO snapshot, and operation guardrail status.",
    enPath: "/en/status/pipeline-status/",
  },
  {
    slug: "runner-health",
    title: "Runner Health",
    description: "Runner availability, load state, and benchmark execution reliability.",
    enPath: "/en/status/runner-health/",
  },
  {
    slug: "submission-review",
    title: "Submission Review",
    description: "Submission queue quality checks and review throughput monitoring.",
    enPath: "/en/status/submission-review/",
  },
];

export const TOOL_ROUTE_ITEMS: RouteManifestItem[] = [
  {
    slug: "quantization-blind-test",
    title: "Quantization Blind Test",
    description: "Blind test workflow for quantization quality and response utility.",
    enPath: "/en/tools/quantization-blind-test/",
  },
  {
    slug: "roi-calculator",
    title: "ROI Calculator",
    description: "Run-vs-rent ROI estimation for local and cloud deployment decisions.",
    enPath: "/en/tools/roi-calculator/",
  },
  {
    slug: "vram-calculator",
    title: "VRAM Calculator",
    description: "Estimate practical VRAM requirements by model class and runtime setup.",
    enPath: "/en/tools/vram-calculator/",
  },
];
