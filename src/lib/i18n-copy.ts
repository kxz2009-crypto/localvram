import copyCatalog from "../data/i18n-copy.json";
import { DEFAULT_LOCALE, STANDARD_I18N_LOCALES, type ComLocale } from "../config/i18n";

type FieldMap = Record<string, string>;

type CopyPage = {
  en: FieldMap;
  locales?: Partial<Record<Exclude<ComLocale, typeof DEFAULT_LOCALE>, Partial<FieldMap>>>;
};

type CopyCatalog = {
  fallback_noindex_threshold: number;
  required_locales?: string[];
  pages: Record<string, CopyPage>;
};

type CopyResolution = {
  fields: FieldMap;
  fallbackFields: string[];
  fallbackRatio: number;
};

const parsedCatalog = copyCatalog as CopyCatalog;
const fallbackThreshold = Number(parsedCatalog.fallback_noindex_threshold || 0.2);
const standardLocaleSet = new Set<string>(STANDARD_I18N_LOCALES);

function applyTemplate(value: string, vars: Record<string, string | number>): string {
  return value.replace(/\{([a-zA-Z0-9_]+)\}/g, (_, key: string) => {
    const nextValue = vars[key];
    return nextValue === undefined || nextValue === null ? "" : String(nextValue);
  });
}

export function resolvePageCopy(
  pageId: string,
  locale: ComLocale,
  vars: Record<string, string | number> = {},
): CopyResolution {
  const page = parsedCatalog.pages[pageId];
  if (!page || typeof page.en !== "object") {
    return {
      fields: {},
      fallbackFields: [],
      fallbackRatio: 0,
    };
  }

  const english = page.en;
  const localeFields =
    locale === DEFAULT_LOCALE ? {} : (page.locales?.[locale as Exclude<ComLocale, "en">] || {});

  const fields: FieldMap = {};
  const fallbackFields: string[] = [];
  const keys = Object.keys(english);

  for (const key of keys) {
    const sourceValue = english[key];
    const localizedValue = localeFields[key];
    const shouldFallback =
      locale !== DEFAULT_LOCALE &&
      (typeof localizedValue !== "string" || !localizedValue.trim().length);
    const raw = shouldFallback ? sourceValue : localizedValue;
    if (shouldFallback) {
      fallbackFields.push(key);
    }
    fields[key] = applyTemplate(String(raw || ""), vars);
  }

  const fallbackRatio = keys.length === 0 ? 0 : fallbackFields.length / keys.length;
  return { fields, fallbackFields, fallbackRatio };
}

export function shouldNoindexByFallback(locale: ComLocale, fallbackRatio: number): boolean {
  if (locale === DEFAULT_LOCALE) {
    return false;
  }
  return fallbackRatio > fallbackThreshold;
}

export function getCopyCoverageSummary(): {
  pageCount: number;
  configuredLocaleCount: number;
  threshold: number;
} {
  const requiredLocales = Array.isArray(parsedCatalog.required_locales)
    ? parsedCatalog.required_locales.filter((x) => standardLocaleSet.has(x))
    : [];
  return {
    pageCount: Object.keys(parsedCatalog.pages || {}).length,
    configuredLocaleCount: requiredLocales.length,
    threshold: fallbackThreshold,
  };
}

