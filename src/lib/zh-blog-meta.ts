const ZH_INTENT_LABELS: Record<string, string> = {
  benchmark: "基准测试",
  errors: "错误排查",
  guide: "实践指南",
  hardware: "硬件决策",
  matrix: "兼容矩阵",
  models: "模型对比",
  tools: "工具实践",
  updates: "更新速递",
  status: "运行状态",
  affiliate: "方案推荐",
};

export function getZhIntentLabel(intent: string): string {
  const key = String(intent || "").trim().toLowerCase();
  return ZH_INTENT_LABELS[key] || (intent ? String(intent) : "通用");
}

export function extractFirstHeading(markdown: string): string | null {
  const match = String(markdown || "").match(/^\s*#{1,6}\s+(.+)$/m);
  return match?.[1]?.trim() || null;
}

export function extractFirstParagraph(markdown: string): string | null {
  const lines = String(markdown || "").split(/\r?\n/);
  for (const line of lines) {
    const text = line.trim();
    if (!text || text.startsWith("#") || text.startsWith("```") || text.startsWith("<!--")) {
      continue;
    }
    if (text.startsWith("- ") || text.startsWith("* ") || /^\d+[.)]\s/.test(text)) {
      continue;
    }
    return text.replace(/^>\s*/, "").trim() || null;
  }
  return null;
}

