import blogCopyCatalog from "../data/i18n-blog-copy.json";
import { DEFAULT_LOCALE, type ComLocale } from "../config/i18n";

type BlogFieldKey = "title" | "description" | "cta_line";

type BlogFieldMap = Record<BlogFieldKey, string>;

type BlogLocaleFieldMap = Partial<BlogFieldMap>;

type BlogSlugCopy = {
  en: BlogFieldMap;
  locales?: Partial<Record<Exclude<ComLocale, typeof DEFAULT_LOCALE>, BlogLocaleFieldMap>>;
};

type BlogCopyCatalog = {
  slugs: Record<string, BlogSlugCopy>;
};

type ResolveBlogCopyDefaults = {
  title: string;
  description: string;
  ctaLine: string;
};

export type BlogCopyResolution = {
  title: string;
  description: string;
  ctaLine: string;
  fallbackFields: BlogFieldKey[];
  fallbackRatio: number;
  isLocalized: boolean;
};

const REQUIRED_FIELDS: BlogFieldKey[] = ["title", "description", "cta_line"];
const parsedCatalog = blogCopyCatalog as BlogCopyCatalog;

function normalize(value: unknown, fallback: string): string {
  if (typeof value !== "string") {
    return fallback;
  }
  const trimmed = value.trim();
  return trimmed.length ? trimmed : fallback;
}

function resolveEnglishFallback(
  slugEntry: BlogSlugCopy | undefined,
  defaults: ResolveBlogCopyDefaults,
): BlogFieldMap {
  return {
    title: normalize(slugEntry?.en?.title, defaults.title),
    description: normalize(slugEntry?.en?.description, defaults.description),
    cta_line: normalize(slugEntry?.en?.cta_line, defaults.ctaLine),
  };
}

export function resolveBlogCopy(
  slug: string,
  locale: ComLocale,
  defaults: ResolveBlogCopyDefaults,
): BlogCopyResolution {
  const slugKey = String(slug || "").trim();
  const slugEntry = parsedCatalog?.slugs?.[slugKey];
  const englishFallback = resolveEnglishFallback(slugEntry, defaults);

  if (locale === DEFAULT_LOCALE) {
    return {
      title: englishFallback.title,
      description: englishFallback.description,
      ctaLine: englishFallback.cta_line,
      fallbackFields: [],
      fallbackRatio: 0,
      isLocalized: true,
    };
  }

  const localeFields =
    slugEntry?.locales?.[locale as Exclude<ComLocale, typeof DEFAULT_LOCALE>] || {};

  const resolved: BlogFieldMap = {
    title: englishFallback.title,
    description: englishFallback.description,
    cta_line: englishFallback.cta_line,
  };
  const fallbackFields: BlogFieldKey[] = [];

  for (const fieldName of REQUIRED_FIELDS) {
    const localized = localeFields[fieldName];
    const hasLocalizedValue = typeof localized === "string" && localized.trim().length > 0;
    if (hasLocalizedValue) {
      resolved[fieldName] = localized.trim();
      continue;
    }
    fallbackFields.push(fieldName);
  }

  return {
    title: resolved.title,
    description: resolved.description,
    ctaLine: resolved.cta_line,
    fallbackFields,
    fallbackRatio: fallbackFields.length / REQUIRED_FIELDS.length,
    isLocalized: fallbackFields.length === 0,
  };
}
