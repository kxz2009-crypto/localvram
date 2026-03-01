const EN_SITE_ORIGIN = "https://localvram.com";

function normalizePath(path: string): string {
  const cleaned = String(path || "/").trim();
  const withLeading = cleaned.startsWith("/") ? cleaned : `/${cleaned}`;
  return withLeading.endsWith("/") ? withLeading : `${withLeading}/`;
}

function getEnTail(path: string): string {
  const normalized = normalizePath(path);
  const tail = normalized.replace(/^\/en(?=\/|$)/, "");
  return tail || "/";
}

export function buildLocaleAlternates(path: string) {
  const tail = getEnTail(path);
  const suffix = tail.startsWith("/") ? tail : `/${tail}`;
  const enHref = new URL(`/en${suffix}`, EN_SITE_ORIGIN).toString();
  const alternates = [{ hrefLang: "en", href: enHref }];
  alternates.push({
    hrefLang: "x-default",
    href: enHref
  });
  return alternates;
}

export const ROOT_ALTERNATES = buildLocaleAlternates("/en/");
