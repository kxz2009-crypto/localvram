import { type ComLocale, buildLocalePath } from "../config/i18n";

export function withLocale(locale: ComLocale, path: string): string {
  return buildLocalePath(locale, path);
}

