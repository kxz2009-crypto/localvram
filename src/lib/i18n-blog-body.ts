import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { DEFAULT_LOCALE, type ComLocale } from "../config/i18n";

export type BlogBodyResolution = {
  markdown: string;
  isLocalized: boolean;
  sourcePath: string | null;
};

function resolveLocalizedBodyPath(locale: Exclude<ComLocale, typeof DEFAULT_LOCALE>, slug: string): string {
  return path.join(process.cwd(), "src", "content", "blog-i18n", locale, `${slug}.md`);
}

export function resolveBlogBody(
  slug: string,
  locale: ComLocale,
  fallbackMarkdown: string,
): BlogBodyResolution {
  if (locale === DEFAULT_LOCALE) {
    return {
      markdown: fallbackMarkdown,
      isLocalized: true,
      sourcePath: null,
    };
  }

  const localizedPath = resolveLocalizedBodyPath(locale, slug);
  if (!existsSync(localizedPath)) {
    return {
      markdown: fallbackMarkdown,
      isLocalized: false,
      sourcePath: null,
    };
  }

  const localizedMarkdown = readFileSync(localizedPath, "utf-8").trim();
  if (!localizedMarkdown) {
    return {
      markdown: fallbackMarkdown,
      isLocalized: false,
      sourcePath: localizedPath,
    };
  }

  return {
    markdown: localizedMarkdown,
    isLocalized: true,
    sourcePath: localizedPath,
  };
}
