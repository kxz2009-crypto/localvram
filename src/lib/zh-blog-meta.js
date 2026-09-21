const ZH_INTENT_LABELS = {
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

const GENERIC_ZH_PLACEHOLDER_HEADINGS = new Set(["为什么现在这个话题"]);

export function getZhIntentLabel(intent) {
  const key = String(intent || "").trim().toLowerCase();
  return ZH_INTENT_LABELS[key] || (intent ? String(intent) : "通用");
}

export function extractFirstHeading(markdown) {
  const match = String(markdown || "").match(/^\s*#{1,6}\s+(.+)$/m);
  return match?.[1]?.trim() || null;
}

export function resolveZhBlogTitle(markdown, fallbackTitle) {
  // Section headings such as “快速结论” are not article titles.
  const clean = String(markdown || '').replace(/<!--[\s\S]*?-->/g, '');
  const title = clean.match(/^#\s+(.+)$/m)?.[1]?.trim();
  if (title && !['快速结论','今日精选','为什么现在这个话题'].includes(title)) return title;
  const fallback = String(fallbackTitle || '').trim();
  const pick = fallback.match(/^Today's Local LLM Pick: (.+) on RTX 3090 \(\d{4}\)$/);
  return pick ? `${pick[1]}：RTX 3090 历史测速与使用边界` : fallback;
}

export function extractFirstParagraph(markdown) {
  const lines = String(markdown || "").replace(/<!--[\s\S]*?-->/g, "").split(/\r?\n/);
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

