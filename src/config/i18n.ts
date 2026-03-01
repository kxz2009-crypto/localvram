export const DEFAULT_LOCALE = "en" as const;

export const STANDARD_I18N_LOCALES = [
  "es",
  "pt",
  "fr",
  "de",
  "ru",
  "ja",
  "ko",
  "ar",
  "hi",
  "id"
] as const;

export const COM_LOCALES = [DEFAULT_LOCALE, ...STANDARD_I18N_LOCALES] as const;
export type ComLocale = (typeof COM_LOCALES)[number];
export const HREFLANG_ROLLOUT_LOCALES: readonly ComLocale[] = [DEFAULT_LOCALE];

const COM_LOCALE_SET = new Set<string>(COM_LOCALES);
const RTL_LOCALE_SET = new Set<string>(["ar"]);

export const OG_LOCALE_BY_LANG: Record<ComLocale, string> = {
  en: "en_US",
  es: "es_ES",
  pt: "pt_BR",
  fr: "fr_FR",
  de: "de_DE",
  ru: "ru_RU",
  ja: "ja_JP",
  ko: "ko_KR",
  ar: "ar_SA",
  hi: "hi_IN",
  id: "id_ID"
};

export function isComLocale(value: string): value is ComLocale {
  return COM_LOCALE_SET.has(String(value || "").toLowerCase());
}

export function isRtlLocale(locale: ComLocale): boolean {
  return RTL_LOCALE_SET.has(locale);
}

export function normalizePath(path: string): string {
  const cleaned = String(path || "/").trim();
  const withLeading = cleaned.startsWith("/") ? cleaned : `/${cleaned}`;
  return withLeading.endsWith("/") ? withLeading : `${withLeading}/`;
}

export function stripLocalePrefix(path: string): string {
  const normalized = normalizePath(path);
  const match = normalized.match(/^\/([a-z]{2})(?=\/|$)/);
  if (!match) {
    return normalized;
  }
  const localeCandidate = match[1];
  if (!isComLocale(localeCandidate)) {
    return normalized;
  }
  const tail = normalized.slice(match[0].length);
  return tail || "/";
}

export function buildLocalePath(locale: ComLocale, path: string): string {
  const tail = stripLocalePrefix(path);
  const suffix = tail.startsWith("/") ? tail : `/${tail}`;
  return normalizePath(`/${locale}${suffix}`);
}

export function isLocalizedComPath(path: string): boolean {
  const normalized = normalizePath(path);
  const match = normalized.match(/^\/([a-z]{2})(?=\/|$)/);
  return Boolean(match && isComLocale(match[1]));
}
