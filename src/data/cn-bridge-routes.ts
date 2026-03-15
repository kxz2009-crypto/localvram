import {
  GUIDE_ROUTE_ITEMS,
  STATUS_ROUTE_ITEMS,
  TOOL_ROUTE_ITEMS,
  type RouteManifestItem,
} from "./i18n-route-manifest";

export type CnBridgeRoute = {
  path: string;
  enPath: string;
  title: string;
  description: string;
};

function toCnPath(enPath: string): string {
  const normalized = String(enPath || "").trim();
  if (!normalized) {
    return "/";
  }
  if (normalized === "/en" || normalized === "/en/") {
    return "/";
  }
  if (normalized.startsWith("/en/")) {
    return normalized.slice(3);
  }
  return normalized;
}

function routeFromManifest(
  item: RouteManifestItem,
  copyBySlug: Record<string, { title: string; description: string }>,
): CnBridgeRoute {
  const copy = copyBySlug[item.slug] || {
    title: item.title,
    description: "该页面的中文完整版正在校对中，可先查看英文原页。",
  };
  return {
    path: toCnPath(item.enPath),
    enPath: item.enPath,
    title: copy.title,
    description: copy.description,
  };
}

const TOOL_COPY: Record<string, { title: string; description: string }> = {
  "vram-calculator": {
    title: "显存计算器",
    description: "按模型规模和运行配置估算显存需求，快速判断本地是否可跑。",
  },
  "quantization-blind-test": {
    title: "量化盲测工具",
    description: "对比不同量化等级的质量差异，避免只看速度不看效果。",
  },
  "roi-calculator": {
    title: "ROI 成本计算器",
    description: "对比本地部署与云端租用的总成本，辅助做出投入决策。",
  },
};

const GUIDE_COPY: Record<string, { title: string; description: string }> = {
  "best-coding-models": {
    title: "编程模型推荐",
    description: "用于代码生成、重构与调试的实用模型选择建议。",
  },
  "best-rag-models": {
    title: "RAG 模型推荐",
    description: "面向检索增强场景的质量、延迟和显存平衡方案。",
  },
  "local-llm-cost-vs-cloud": {
    title: "本地成本 vs 云端成本",
    description: "按统一口径评估本地部署与云推理的成本差异。",
  },
  "ollama-local-cluster-network": {
    title: "本地集群网络指南",
    description: "从单机到多机的网络规划与稳定性检查要点。",
  },
  "ollama-vs-vllm-vram": {
    title: "Ollama vs vLLM 显存对比",
    description: "对比两类运行后端在显存规划和部署复杂度上的差异。",
  },
};

const STATUS_COPY: Record<string, { title: string; description: string }> = {
  "content-publish": {
    title: "内容发布状态",
    description: "追踪内容发布节奏、待发布队列和近期更新时间。",
  },
  "conversion-funnel": {
    title: "转化漏斗状态",
    description: "查看高意图页面到转化动作的关键链路表现。",
  },
  "data-freshness": {
    title: "数据新鲜度状态",
    description: "核对模型基准、目录数据和流水线快照是否最新。",
  },
  "pipeline-status": {
    title: "流水线状态",
    description: "汇总自动化任务健康度、失败告警和恢复情况。",
  },
  "runner-health": {
    title: "Runner 健康状态",
    description: "跟踪执行节点在线状态、负载和可用性。",
  },
  "submission-review": {
    title: "提交审核状态",
    description: "查看提交审核队列、通过率和处理进度。",
  },
};

const MANUAL_ROUTES: CnBridgeRoute[] = [
  {
    path: "/about/methodology/",
    enPath: "/en/about/methodology/",
    title: "方法说明",
    description: "介绍 LocalVRAM 的测试方法、采样口径与结果解读方式。",
  },
  {
    path: "/affiliate/cloud-gpu/",
    enPath: "/en/affiliate/cloud-gpu/",
    title: "云 GPU 方案",
    description: "用于本地资源不足时的云端补充方案与成本参考。",
  },
  {
    path: "/affiliate/hardware-upgrade/",
    enPath: "/en/affiliate/hardware-upgrade/",
    title: "硬件升级建议",
    description: "在预算范围内提升本地推理稳定性和吞吐的升级路径。",
  },
  {
    path: "/benchmarks/",
    enPath: "/en/benchmarks/",
    title: "基准总览",
    description: "浏览本地推理基准的结构化入口和核心指标。",
  },
  {
    path: "/benchmarks/changelog/",
    enPath: "/en/benchmarks/changelog/",
    title: "基准变更日志",
    description: "查看版本迭代带来的基准变化与环境差异。",
  },
  {
    path: "/benchmarks/submit-result/",
    enPath: "/en/benchmarks/submit-result/",
    title: "提交基准结果",
    description: "提交你的本地基准记录并补充测试环境说明。",
  },
  {
    path: "/compare/qwen35-35b-q4-vs-llama31-70b-q4/",
    enPath: "/en/compare/qwen35-35b-q4-vs-llama31-70b-q4/",
    title: "模型对比页",
    description: "同场景下比较不同模型方案的延迟、质量与显存消耗。",
  },
  {
    path: "/errors/",
    enPath: "/en/errors/",
    title: "错误知识库",
    description: "收录常见本地推理报错和可执行排障路径。",
  },
  {
    path: "/errors/cuda-out-of-memory/",
    enPath: "/en/errors/cuda-out-of-memory/",
    title: "CUDA 显存不足排障",
    description: "针对 OOM 报错给出优先级明确的修复清单。",
  },
  {
    path: "/errors/rocm-not-detected/",
    enPath: "/en/errors/rocm-not-detected/",
    title: "ROCm 未检测到排障",
    description: "定位 ROCm 环境未识别的常见原因并提供修复步骤。",
  },
  {
    path: "/errors/metal-not-found/",
    enPath: "/en/errors/metal-not-found/",
    title: "Metal 运行时缺失排障",
    description: "解决 Apple 设备上 Metal 后端不可用的问题。",
  },
  {
    path: "/hardware/",
    enPath: "/en/hardware/",
    title: "硬件导航",
    description: "按显存等级和场景查看本地部署硬件建议。",
  },
  {
    path: "/hardware/verified-3090/",
    enPath: "/en/hardware/verified-3090/",
    title: "RTX 3090 验证页",
    description: "查看 3090 在持续负载与关键任务下的验证结果。",
  },
  {
    path: "/hardware/apple-silicon-llm-guide/",
    enPath: "/en/hardware/apple-silicon-llm-guide/",
    title: "Apple Silicon 指南",
    description: "M 系列设备的本地 LLM 运行边界和推荐配置。",
  },
  {
    path: "/matrix/",
    enPath: "/en/matrix/",
    title: "兼容矩阵",
    description: "按模型、量化和硬件组合查看兼容性结果。",
  },
  {
    path: "/models/",
    enPath: "/en/models/",
    title: "模型目录",
    description: "按参数规模、用途和资源要求筛选模型。",
  },
  {
    path: "/multimodal/",
    enPath: "/en/multimodal/",
    title: "多模态专题",
    description: "聚焦视觉与多模态推理的模型和部署建议。",
  },
  {
    path: "/updates/",
    enPath: "/en/updates/",
    title: "每日更新",
    description: "查看近期数据、模型和内容更新流水。",
  },
];

function uniqueByPath(items: CnBridgeRoute[]): CnBridgeRoute[] {
  const dedup = new Map<string, CnBridgeRoute>();
  for (const item of items) {
    dedup.set(item.path, item);
  }
  return Array.from(dedup.values()).sort((a, b) => a.path.localeCompare(b.path));
}

export const CN_BRIDGE_ROUTES: CnBridgeRoute[] = uniqueByPath([
  ...MANUAL_ROUTES,
  ...TOOL_ROUTE_ITEMS.map((item) => routeFromManifest(item, TOOL_COPY)),
  ...GUIDE_ROUTE_ITEMS.map((item) => routeFromManifest(item, GUIDE_COPY)),
  ...STATUS_ROUTE_ITEMS.map((item) => routeFromManifest(item, STATUS_COPY)),
]);
