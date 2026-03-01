import { DEFAULT_LOCALE, HREFLANG_ROLLOUT_LOCALES, buildLocalePath } from "../config/i18n";

const EN_SITE_ORIGIN = "https://localvram.com";

export function buildLocaleAlternates(path: string) {
  const alternates = HREFLANG_ROLLOUT_LOCALES.map((locale) => {
    const href = new URL(buildLocalePath(locale, path), EN_SITE_ORIGIN).toString();
    return { hrefLang: locale, href };
  });
  const enHref = alternates.find((item) => item.hrefLang === DEFAULT_LOCALE)?.href || new URL("/en/", EN_SITE_ORIGIN).toString();
  alternates.push({
    hrefLang: "x-default",
    href: enHref
  });
  return alternates;
}

export const ROOT_ALTERNATES = buildLocaleAlternates("/en/");
