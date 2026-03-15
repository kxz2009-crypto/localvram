import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { DEFAULT_LOCALE, type ComLocale } from "../config/i18n";

export type BlogBodyResolution = {
  markdown: string;
  isLocalized: boolean;
  sourcePath: string | null;
  fallbackReason?: "missing_file" | "empty_content" | "stub_content";
  isStub?: boolean;
};

export type BlogBodyLocale = ComLocale | "zh";

function resolveLocalizedBodyPath(locale: Exclude<BlogBodyLocale, typeof DEFAULT_LOCALE>, slug: string): string {
  return path.join(process.cwd(), "src", "content", "blog-i18n", locale, `${slug}.md`);
}

const ROUTE_TOKEN_FIXUPS: Record<string, string> = {
  "/en/tools/vram-कैलकुलेटर/": "/en/tools/vram-calculator/",
  "/en/मॉडल/": "/en/models/",
  "/en/टूल्स/क्वांटिज़ेशन-ब्लाइंड-टेस्ट/": "/en/tools/quantization-blind-test/",
  "/en/संबद्ध/हार्डवेयर-अपग्रेड/": "/en/affiliate/hardware-upgrade/",
};

function stripLeadingComment(markdown: string): string {
  const trimmed = markdown.trimStart();
  if (!trimmed.startsWith("<!--")) {
    return trimmed;
  }
  const commentEnd = trimmed.indexOf("-->");
  if (commentEnd < 0) {
    return trimmed;
  }
  return trimmed.slice(commentEnd + 3).trimStart();
}

function stripFrontmatter(markdown: string): string {
  if (!markdown.startsWith("---")) {
    return markdown;
  }
  const matched = markdown.match(/^---\s*\r?\n[\s\S]*?\r?\n---\s*(\r?\n)?/);
  if (!matched) {
    return markdown;
  }
  return markdown.slice(matched[0].length).trimStart();
}

function normalizeKnownRouteTokens(markdown: string): string {
  let normalized = markdown;
  for (const [bad, good] of Object.entries(ROUTE_TOKEN_FIXUPS)) {
    normalized = normalized.split(bad).join(good);
    normalized = normalized.split(bad.slice(0, -1)).join(good.slice(0, -1));
  }
  return normalized;
}

function sanitizeLocalizedMarkdown(markdown: string): string {
  const withoutComment = stripLeadingComment(markdown);
  const withoutFrontmatter = stripFrontmatter(withoutComment);
  return normalizeKnownRouteTokens(withoutFrontmatter).trim();
}

const STUB_MARKERS = [
  "status: zh-stub",
  "pending full translation",
  "（中文整理中）",
  "## 英文摘要（原文引用）",
  "## 中文速览（待人工校对）",
];

function isStubMarkdown(markdown: string): boolean {
  const head = String(markdown || "").slice(0, 2400);
  return STUB_MARKERS.some((marker) => head.includes(marker));
}

export function resolveBlogBody(
  slug: string,
  locale: BlogBodyLocale,
  fallbackMarkdown: string,
): BlogBodyResolution {
  if (locale === DEFAULT_LOCALE) {
    return {
      markdown: fallbackMarkdown,
      isLocalized: true,
      sourcePath: null,
    };
  }

  const localizedPath = resolveLocalizedBodyPath(locale as Exclude<BlogBodyLocale, typeof DEFAULT_LOCALE>, slug);
  if (!existsSync(localizedPath)) {
    return {
      markdown: fallbackMarkdown,
      isLocalized: false,
      sourcePath: null,
      fallbackReason: "missing_file",
      isStub: false,
    };
  }

  const localizedMarkdown = readFileSync(localizedPath, "utf-8");
  if (isStubMarkdown(localizedMarkdown)) {
    return {
      markdown: fallbackMarkdown,
      isLocalized: false,
      sourcePath: localizedPath,
      fallbackReason: "stub_content",
      isStub: true,
    };
  }

  const sanitizedMarkdown = sanitizeLocalizedMarkdown(localizedMarkdown);
  if (!sanitizedMarkdown) {
    return {
      markdown: fallbackMarkdown,
      isLocalized: false,
      sourcePath: localizedPath,
      fallbackReason: "empty_content",
      isStub: false,
    };
  }

  return {
    markdown: `${sanitizedMarkdown}\n`,
    isLocalized: true,
    sourcePath: localizedPath,
    isStub: false,
  };
}
