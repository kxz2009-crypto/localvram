#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "src" / "data" / "search-console-keywords.json"
DEFAULT_LOCALES = "en,es,pt,fr,de,ru,ja,ko,ar,hi,id"
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
LOCALE_PATTERN = re.compile(r"^[a-z]{2}$")


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_locales(raw: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for chunk in str(raw or "").split(","):
        locale = chunk.strip().lower()
        if not locale or locale in seen:
            continue
        if not LOCALE_PATTERN.fullmatch(locale):
            continue
        seen.add(locale)
        out.append(locale)
    return out


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_landing(page: str) -> str:
    value = str(page or "").strip()
    if not value:
        return "/"
    if value.startswith("/"):
        path = value
    else:
        parsed = urlsplit(value)
        path = parsed.path or "/"
    return path if path.startswith("/") else f"/{path}"


def extract_locale_from_landing(landing: str) -> str:
    m = re.match(r"^/([a-z]{2})(/|$)", landing)
    if not m:
        return ""
    return m.group(1).lower()


def build_service(credentials_json: str):
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise RuntimeError(
            "missing google api dependencies; install google-api-python-client and google-auth"
        ) from exc

    info = json.loads(credentials_json)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def query_locale_rows(
    service,
    site_url: str,
    locale: str,
    start_date: str,
    end_date: str,
    row_limit: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start_row = 0
    page_row_limit = min(max(1, row_limit), 25000)
    while len(rows) < row_limit:
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": ["query", "page"],
            "rowLimit": min(page_row_limit, row_limit - len(rows)),
            "startRow": start_row,
            "dimensionFilterGroups": [
                {
                    "groupType": "and",
                    "filters": [
                        {
                            "dimension": "page",
                            "operator": "contains",
                            "expression": f"/{locale}/",
                        }
                    ],
                }
            ],
        }
        response = (
            service.searchanalytics()
            .query(siteUrl=site_url, body=body)
            .execute()
        )
        batch = response.get("rows", []) if isinstance(response, dict) else []
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < body["rowLimit"]:
            break
        start_row += len(batch)
    return rows[:row_limit]


def convert_rows(locale: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converted: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        keys = row.get("keys", [])
        if not isinstance(keys, list) or len(keys) < 2:
            continue
        query = str(keys[0] or "").strip()
        landing = normalize_landing(str(keys[1] or ""))
        if not query or not landing:
            continue
        row_locale = extract_locale_from_landing(landing)
        if row_locale != locale:
            continue
        clicks = float(row.get("clicks", 0.0) or 0.0)
        impressions = float(row.get("impressions", 0.0) or 0.0)
        ctr = float(row.get("ctr", 0.0) or 0.0)
        position = float(row.get("position", 0.0) or 0.0)
        key = (query, landing)
        if key not in converted:
            converted[key] = {
                "keyword": query,
                "query": query,
                "clicks": clicks,
                "impressions": impressions,
                "ctr": ctr,
                "position": position,
                "landing": landing,
                "locale": locale,
            }
            continue
        # Search Console may return duplicated buckets across pagination, merge them.
        existing = converted[key]
        existing["clicks"] = float(existing["clicks"]) + clicks
        existing["impressions"] = float(existing["impressions"]) + impressions
        total_impressions = float(existing["impressions"]) or 0.0
        if total_impressions > 0:
            existing["ctr"] = float(existing["clicks"]) / total_impressions
            existing["position"] = (
                (float(existing["position"]) * max(total_impressions - impressions, 0.0)) + (position * impressions)
            ) / total_impressions

    items = list(converted.values())
    items.sort(key=lambda item: (item["locale"], -float(item["impressions"]), -float(item["clicks"]), item["query"]))
    for item in items:
        item["clicks"] = int(round(float(item["clicks"])))
        item["impressions"] = int(round(float(item["impressions"])))
        item["ctr"] = round(float(item["ctr"]), 4)
        item["position"] = round(float(item["position"]), 2)
    return items


def merge_items(existing_items: list[dict[str, Any]], fresh_items: list[dict[str, Any]], target_locales: set[str]) -> list[dict[str, Any]]:
    keep = []
    for item in existing_items:
        if not isinstance(item, dict):
            continue
        landing = str(item.get("landing", "")).strip()
        locale = extract_locale_from_landing(landing)
        if locale and locale in target_locales:
            continue
        keep.append(item)
    merged = keep + fresh_items
    merged.sort(
        key=lambda item: (
            extract_locale_from_landing(str(item.get("landing", ""))),
            -float(item.get("impressions", 0.0) or 0.0),
            -float(item.get("clicks", 0.0) or 0.0),
            str(item.get("query", "")),
        )
    )
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Search Console query/page rows into search-console-keywords.json")
    parser.add_argument("--site-url", default="", help="Search Console property, e.g. sc-domain:localvram.com")
    parser.add_argument("--credentials-json", default="", help="Service account JSON string")
    parser.add_argument("--locales", default=DEFAULT_LOCALES, help="Comma-separated locale prefixes")
    parser.add_argument("--days", type=int, default=28, help="Lookback window in days (inclusive)")
    parser.add_argument("--row-limit", type=int, default=200, help="Max rows per locale")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output JSON file")
    args = parser.parse_args()

    site_url = str(args.site_url or "").strip()
    credentials_json = str(args.credentials_json or "").strip()
    if not site_url:
        raise SystemExit("missing --site-url")
    if not credentials_json:
        raise SystemExit("missing --credentials-json")

    locales = parse_locales(args.locales)
    if not locales:
        raise SystemExit("no valid locales configured")

    days = max(1, int(args.days))
    today = dt.date.today()
    start_date = (today - dt.timedelta(days=days - 1)).isoformat()
    end_date = today.isoformat()

    service = build_service(credentials_json)
    fetched: list[dict[str, Any]] = []
    for locale in locales:
        rows = query_locale_rows(
            service=service,
            site_url=site_url,
            locale=locale,
            start_date=start_date,
            end_date=end_date,
            row_limit=max(1, int(args.row_limit)),
        )
        items = convert_rows(locale, rows)
        fetched.extend(items)
        print(f"gsc_locale={locale} rows={len(rows)} items={len(items)}")

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = (ROOT / output_path).resolve()

    existing = read_json(output_path, {"items": []})
    existing_items = existing.get("items", []) if isinstance(existing, dict) else []
    merged_items = merge_items(existing_items, fetched, set(locales))

    payload = {
        "updated_at": utc_now_iso(),
        "source": "google-search-console-api",
        "site_url": site_url,
        "window": {
            "start_date": start_date,
            "end_date": end_date,
            "days": days,
        },
        "locales": locales,
        "items": merged_items,
    }
    write_json(output_path, payload)
    print(f"search_console_items={len(merged_items)}")
    print(f"search_console_file={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
