const EN_SITE_ORIGIN = "https://localvram.com";
const ZH_SITE_ORIGIN = (import.meta.env.PUBLIC_ZH_SITE_ORIGIN || EN_SITE_ORIGIN).replace(/\/$/, "");

const LOCALE_PREFIXES = ["en", "es", "pt", "fr", "de", "ru", "ja", "ko", "ar", "hi", "id", "zh"] as const;
type LocalePrefix = (typeof LOCALE_PREFIXES)[number];

const HREF_LANG_BY_LOCALE: Record<LocalePrefix, string> = {
  en: "en",
  es: "es",
  pt: "pt",
  fr: "fr",
  de: "de",
  ru: "ru",
  ja: "ja",
  ko: "ko",
  ar: "ar",
  hi: "hi",
  id: "id",
  zh: "zh-CN"
};

function normalizePath(path: string): string {
  const cleaned = String(path || "/").trim();
  const withLeading = cleaned.startsWith("/") ? cleaned : `/${cleaned}`;
  return withLeading.endsWith("/") ? withLeading : `${withLeading}/`;
}

function getLocaleTail(path: string): string {
  const normalized = normalizePath(path);
  const tail = normalized.replace(/^\/[a-z]{2}(?=\/|$)/, "");
  return tail || "/";
}

export function buildLocaleAlternates(path: string) {
  const tail = getLocaleTail(path);
  const suffix = tail.startsWith("/") ? tail : `/${tail}`;
  const alternates = LOCALE_PREFIXES.map((locale) => {
    const origin = locale === "zh" ? ZH_SITE_ORIGIN : EN_SITE_ORIGIN;
    const href = new URL(`/${locale}${suffix}`, origin).toString();
    return { hrefLang: HREF_LANG_BY_LOCALE[locale], href };
  });
  alternates.push({
    hrefLang: "x-default",
    href: new URL(`/en${suffix}`, EN_SITE_ORIGIN).toString()
  });
  return alternates;
}

export const ROOT_ALTERNATES = buildLocaleAlternates("/en/");
