#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
KPI_FILE = ROOT / "docs" / "seo-ops" / "locale-kpi-tracker.csv"
SITEMAP_FILE = ROOT / "public" / "sitemap.xml"
SC_FILE = ROOT / "src" / "data" / "search-console-keywords.json"

KPI_FIELDS = [
    "date",
    "domain",
    "locale",
    "owner",
    "indexed_urls",
    "discovered_urls",
    "index_rate_pct",
    "impressions",
    "clicks",
    "ctr_pct",
    "avg_position",
    "notes",
    "next_action",
]
LOGGER = configure_logging("refresh-locale-kpi")


def load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        out: list[dict[str, str]] = []
        for row in reader:
            out.append({k: str(v or "").strip() for k, v in row.items()})
        return out


def save_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=KPI_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in KPI_FIELDS})


def _sitemap_loc_to_local_path(loc: str) -> Path | None:
    loc = str(loc or "").strip()
    if not loc:
        return None
    if loc.startswith("http://") or loc.startswith("https://"):
        parts = urlsplit(loc)
        if not parts.path:
            return None
        return ROOT / "public" / parts.path.lstrip("/")
    if loc.startswith("/"):
        return ROOT / "public" / loc.lstrip("/")
    return ROOT / "public" / loc


def parse_sitemap_locale_counts(path: Path, locales: set[str]) -> dict[str, int]:
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    counts = {locale: 0 for locale in locales}
    visited: set[Path] = set()

    def parse_file(file_path: Path) -> None:
        real = file_path.resolve()
        if real in visited or not file_path.exists():
            return
        visited.add(real)

        xml_text = file_path.read_text(encoding="utf-8")
        root = ET.fromstring(xml_text)
        root_name = root.tag.rsplit("}", 1)[-1]

        if root_name == "urlset":
            for node in root.findall("sm:url/sm:loc", ns):
                loc = (node.text or "").strip()
                m = re.match(r"^https?://[^/]+/([a-z]{2})(/|$)", loc)
                if not m:
                    continue
                locale = m.group(1)
                if locale in counts:
                    counts[locale] += 1
            return

        if root_name == "sitemapindex":
            for node in root.findall("sm:sitemap/sm:loc", ns):
                nested_path = _sitemap_loc_to_local_path(node.text or "")
                if nested_path is not None:
                    parse_file(nested_path)
            return

    parse_file(path)
    return counts


def parse_search_console(path: Path, locales: set[str]) -> dict[str, dict[str, float]]:
    if not path.exists():
        return {
            locale: {"impressions": 0.0, "clicks": 0.0, "weighted_pos_sum": 0.0, "indexed_urls": 0.0}
            for locale in locales
        }

    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    items = payload.get("items", []) if isinstance(payload, dict) else []
    stats: dict[str, dict[str, float]] = {
        locale: {"impressions": 0.0, "clicks": 0.0, "weighted_pos_sum": 0.0, "indexed_urls": 0.0} for locale in locales
    }
    indexed_landing_by_locale: dict[str, set[str]] = {locale: set() for locale in locales}
    for item in items:
        if not isinstance(item, dict):
            continue
        landing = str(item.get("landing", "")).strip()
        m = re.match(r"^/([a-z]{2})(/|$)", landing)
        if not m:
            continue
        locale = m.group(1)
        if locale not in stats:
            continue
        impressions = float(item.get("impressions", 0) or 0)
        clicks = float(item.get("clicks", 0) or 0)
        position = float(item.get("position", 0) or 0)
        stats[locale]["impressions"] += impressions
        stats[locale]["clicks"] += clicks
        stats[locale]["weighted_pos_sum"] += position * impressions
        if impressions > 0 and landing:
            indexed_landing_by_locale[locale].add(landing)

    for locale in locales:
        stats[locale]["indexed_urls"] = float(len(indexed_landing_by_locale[locale]))

    return stats


def latest_owner(rows: list[dict[str, str]], locale: str, domain: str) -> str:
    candidates = [r for r in rows if r.get("locale") == locale and r.get("domain") == domain]
    if not candidates:
        return f"seo-{locale}"
    candidates.sort(key=lambda r: r.get("date", ""), reverse=True)
    owner = candidates[0].get("owner", "").strip()
    return owner or f"seo-{locale}"


def to_int_str(value: float) -> str:
    return str(int(round(value)))


def to_pct_str(value: float) -> str:
    if abs(value - int(value)) < 1e-9:
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def build_row(
    *,
    date_iso: str,
    locale: str,
    owner: str,
    indexed_urls: int,
    discovered_urls: int,
    impressions: float,
    clicks: float,
    weighted_pos_sum: float,
    due_date: str,
) -> dict[str, str]:
    index_rate = 0.0 if discovered_urls <= 0 else (indexed_urls / discovered_urls) * 100.0
    ctr = 0.0 if impressions <= 0 else (clicks / impressions) * 100.0
    avg_pos = 0.0 if impressions <= 0 else (weighted_pos_sum / impressions)
    return {
        "date": date_iso,
        "domain": "localvram.com",
        "locale": locale,
        "owner": owner,
        "indexed_urls": str(indexed_urls),
        "discovered_urls": str(discovered_urls),
        "index_rate_pct": to_pct_str(round(index_rate, 2)),
        "impressions": to_int_str(impressions),
        "clicks": to_int_str(clicks),
        "ctr_pct": to_pct_str(round(ctr, 2)),
        "avg_position": to_pct_str(round(avg_pos, 2)),
        "notes": "72h checkpoint started after wave1 publish",
        "next_action": f"GSC URL inspection + KPI refresh on {due_date}",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh locale KPI tracker rows for rollout locales.")
    parser.add_argument("--date", default="", help="ISO date, e.g. 2026-02-28. Defaults to today.")
    parser.add_argument("--locales", default="es,pt,ja", help="Comma-separated locales.")
    args = parser.parse_args()

    today = dt.date.today()
    date_iso = str(args.date).strip() or today.isoformat()
    run_date = dt.date.fromisoformat(date_iso)
    due_date = (run_date + dt.timedelta(days=3)).isoformat()

    locales = [x.strip().lower() for x in str(args.locales).split(",") if x.strip()]
    locale_set = set(locales)

    rows = load_rows(KPI_FILE)
    sitemap_counts = parse_sitemap_locale_counts(SITEMAP_FILE, locale_set)
    sc_stats = parse_search_console(SC_FILE, locale_set)

    # Upsert rows by (date, domain, locale)
    existing = [
        r
        for r in rows
        if not (r.get("date") == date_iso and r.get("domain") == "localvram.com" and r.get("locale", "").lower() in locale_set)
    ]

    new_rows: list[dict[str, str]] = []
    for locale in locales:
        owner = latest_owner(rows, locale, "localvram.com")
        s = sc_stats.get(locale, {"impressions": 0.0, "clicks": 0.0, "weighted_pos_sum": 0.0, "indexed_urls": 0.0})
        discovered_urls = int(sitemap_counts.get(locale, 0))
        indexed_urls = int(round(float(s.get("indexed_urls", 0.0) or 0.0)))
        if discovered_urls > 0:
            indexed_urls = max(0, min(discovered_urls, indexed_urls))
        row = build_row(
            date_iso=date_iso,
            locale=locale,
            owner=owner,
            indexed_urls=indexed_urls,
            discovered_urls=discovered_urls,
            impressions=float(s.get("impressions", 0.0)),
            clicks=float(s.get("clicks", 0.0)),
            weighted_pos_sum=float(s.get("weighted_pos_sum", 0.0)),
            due_date=due_date,
        )
        new_rows.append(row)

    merged = existing + new_rows
    merged.sort(key=lambda r: (r.get("date", ""), r.get("domain", ""), r.get("locale", "")))
    save_rows(KPI_FILE, merged)

    for row in new_rows:
        LOGGER.info(
            "kpi_row="
            f"{row['date']} {row['locale']} indexed={row['indexed_urls']} discovered={row['discovered_urls']} "
            f"impr={row['impressions']} clicks={row['clicks']} next={row['next_action']}"
        )
    LOGGER.info("kpi_file=%s", KPI_FILE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
