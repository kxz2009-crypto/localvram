import {
  DEFAULT_LOCALE,
  HREFLANG_ROLLOUT_LOCALES,
  buildLocalePath,
  normalizePath,
  stripLocalePrefix,
} from "../config/i18n";

const EN_SITE_ORIGIN = "https://localvram.com";
const CN_SITE_ORIGIN = "https://localvram.cn";
const SHARED_COM_PATHS = new Set<string>(["/legal/"]);

function toCnPath(path: string): string {
  const tail = stripLocalePrefix(path);
  return normalizePath(tail);
}

function toComEnPathFromCnPath(path: string): string {
  const normalized = normalizePath(path);
  if (normalized === "/") {
    return "/en/";
  }
  if (SHARED_COM_PATHS.has(normalized)) {
    return normalized;
  }
  return normalizePath(`/en${normalized}`);
}

export function buildLocaleAlternates(path: string) {
  const alternates = HREFLANG_ROLLOUT_LOCALES.map((locale) => {
    const href = new URL(buildLocalePath(locale, path), EN_SITE_ORIGIN).toString();
    return { hrefLang: locale, href };
  });
  alternates.push({
    hrefLang: "zh-CN",
    href: new URL(toCnPath(path), CN_SITE_ORIGIN).toString(),
  });
  const enHref = alternates.find((item) => item.hrefLang === DEFAULT_LOCALE)?.href || new URL("/en/", EN_SITE_ORIGIN).toString();
  alternates.push({
    hrefLang: "x-default",
    href: enHref
  });
  return alternates;
}

export function buildCnAlternates(path: string) {
  const cnPath = normalizePath(path);
  const cnHref = new URL(cnPath, CN_SITE_ORIGIN).toString();
  const enHref = new URL(toComEnPathFromCnPath(cnPath), EN_SITE_ORIGIN).toString();
  return [
    { hrefLang: "zh-CN", href: cnHref },
    { hrefLang: DEFAULT_LOCALE, href: enHref },
    { hrefLang: "x-default", href: enHref },
  ];
}

export const ROOT_ALTERNATES = buildLocaleAlternates("/en/");
