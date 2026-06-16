#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATUS_FILE = ROOT / "src" / "data" / "status.json"
DEFAULT_CONTENT_PUBLISH_FILE = ROOT / "src" / "data" / "content-publish-log.json"
DEFAULT_DAILY_UPDATES_FILE = ROOT / "src" / "data" / "daily-updates.json"
LOGGER = configure_logging("check-site-update-health")


def parse_iso_utc(value: str) -> dt.datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if len(raw) == 10:
        try:
            return dt.datetime.fromisoformat(raw).replace(tzinfo=dt.timezone.utc)
        except ValueError:
            return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def age_hours(now_utc: dt.datetime, parsed: dt.datetime | None) -> float:
    if parsed is None:
        return -1.0
    return round((now_utc - parsed).total_seconds() / 3600.0, 2)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def resolve_path(path: Path | str, root_dir: Path) -> Path:
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = root_dir / resolved
    return resolved


def check_site_update_health(
    *,
    now_utc: dt.datetime,
    status_file: Path,
    content_publish_file: Path,
    daily_updates_file: Path,
    root_dir: Path = ROOT,
    max_home_sync_age_hours: int = 192,
    max_daily_publish_age_hours: int = 48,
    max_daily_update_date_age_days: int = 2,
) -> dict[str, Any]:
    errors: list[str] = []

    status_payload = load_json(status_file) if status_file.exists() else {}
    publish_payload = load_json(content_publish_file) if content_publish_file.exists() else {}
    updates_payload = load_json(daily_updates_file) if daily_updates_file.exists() else {}

    if not status_file.exists():
        errors.append(f"missing_status_file={status_file}")
    if not content_publish_file.exists():
        errors.append(f"missing_content_publish_file={content_publish_file}")
    if not daily_updates_file.exists():
        errors.append(f"missing_daily_updates_file={daily_updates_file}")

    home_sync_raw = str(status_payload.get("last_hardware_sync") or status_payload.get("last_verified") or "").strip()
    home_sync_at = parse_iso_utc(home_sync_raw)
    home_sync_age_h = age_hours(now_utc, home_sync_at)
    if home_sync_at is None:
        errors.append("invalid_home_sync")
    elif home_sync_age_h > max(0, int(max_home_sync_age_hours)):
        errors.append(f"home_sync_stale(age_hours={home_sync_age_h}, max_hours={int(max_home_sync_age_hours)})")

    publish_updated_raw = str(publish_payload.get("updated_at") or "").strip()
    publish_updated_at = parse_iso_utc(publish_updated_raw)
    publish_age_h = age_hours(now_utc, publish_updated_at)
    if publish_updated_at is None:
        errors.append("invalid_daily_publish_updated_at")
    elif publish_age_h > max(0, int(max_daily_publish_age_hours)):
        errors.append(f"daily_publish_stale(age_hours={publish_age_h}, max_hours={int(max_daily_publish_age_hours)})")

    last_run = publish_payload.get("last_run") if isinstance(publish_payload.get("last_run"), dict) else {}
    queue_date = str(last_run.get("queue_date") or "").strip()
    published = last_run.get("published") if isinstance(last_run.get("published"), list) else []
    try:
        published_count = int(last_run.get("published_count", 0) or 0)
    except (TypeError, ValueError):
        published_count = 0
    if published_count <= 0:
        errors.append(f"daily_publish_zero_published(queue_date={queue_date or 'unknown'})")

    latest_slug = ""
    latest_out_file = ""
    if published:
        first = published[0] if isinstance(published[0], dict) else {}
        latest_slug = str(first.get("slug") or "").strip()
        latest_out_file = str(first.get("out_file") or "").strip()
        if latest_out_file and not resolve_path(latest_out_file, root_dir).exists():
            errors.append(f"daily_publish_missing_blog_file(slug={latest_slug or 'unknown'})")

    updates_items = updates_payload.get("items") if isinstance(updates_payload.get("items"), list) else []
    latest_update_date = ""
    latest_update_slugs: set[str] = set()
    if updates_items:
        latest_update = updates_items[0] if isinstance(updates_items[0], dict) else {}
        latest_update_date = str(latest_update.get("date") or "").strip()
        for item in latest_update.get("published_posts") or []:
            if isinstance(item, dict) and str(item.get("slug") or "").strip():
                latest_update_slugs.add(str(item.get("slug")).strip())
    else:
        errors.append("daily_updates_empty")

    latest_update_at = parse_iso_utc(latest_update_date)
    latest_update_age_days = -1
    if latest_update_at is None:
        errors.append("invalid_daily_update_date")
    else:
        latest_update_age_days = (now_utc.date() - latest_update_at.date()).days
        if latest_update_age_days > max(0, int(max_daily_update_date_age_days)):
            errors.append(
                f"daily_update_date_stale(age_days={latest_update_age_days}, max_days={int(max_daily_update_date_age_days)})"
            )

    if latest_slug and latest_update_slugs and latest_slug not in latest_update_slugs:
        errors.append(f"daily_publish_not_in_update_feed(slug={latest_slug})")

    report = {
        "checked_at": now_utc.isoformat().replace("+00:00", "Z"),
        "inputs": {
            "status_file": str(status_file),
            "content_publish_file": str(content_publish_file),
            "daily_updates_file": str(daily_updates_file),
            "max_home_sync_age_hours": int(max_home_sync_age_hours),
            "max_daily_publish_age_hours": int(max_daily_publish_age_hours),
            "max_daily_update_date_age_days": int(max_daily_update_date_age_days),
        },
        "home_sync": {
            "last_sync": home_sync_raw,
            "age_hours": home_sync_age_h,
        },
        "daily_publish": {
            "updated_at": publish_updated_raw,
            "age_hours": publish_age_h,
            "queue_date": queue_date,
            "published_count": published_count,
            "latest_slug": latest_slug,
        },
        "daily_updates": {
            "latest_date": latest_update_date,
            "latest_date_age_days": latest_update_age_days,
            "latest_published_slugs": sorted(latest_update_slugs),
        },
        "result": "ok" if not errors else "failed",
        "errors": errors,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Check homepage sync and daily blog update freshness.")
    parser.add_argument("--status-file", default=str(DEFAULT_STATUS_FILE))
    parser.add_argument("--content-publish-file", default=str(DEFAULT_CONTENT_PUBLISH_FILE))
    parser.add_argument("--daily-updates-file", default=str(DEFAULT_DAILY_UPDATES_FILE))
    parser.add_argument("--max-home-sync-age-hours", type=int, default=192)
    parser.add_argument("--max-daily-publish-age-hours", type=int, default=48)
    parser.add_argument("--max-daily-update-date-age-days", type=int, default=2)
    parser.add_argument("--report-file", default="")
    args = parser.parse_args()

    report = check_site_update_health(
        now_utc=dt.datetime.now(dt.timezone.utc),
        status_file=resolve_path(args.status_file, ROOT),
        content_publish_file=resolve_path(args.content_publish_file, ROOT),
        daily_updates_file=resolve_path(args.daily_updates_file, ROOT),
        root_dir=ROOT,
        max_home_sync_age_hours=args.max_home_sync_age_hours,
        max_daily_publish_age_hours=args.max_daily_publish_age_hours,
        max_daily_update_date_age_days=args.max_daily_update_date_age_days,
    )

    if args.report_file:
        report_path = resolve_path(args.report_file, ROOT)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        LOGGER.info("report_file=%s", report_path)

    LOGGER.info("home_sync_last=%s age_hours=%s", report["home_sync"]["last_sync"] or "unknown", report["home_sync"]["age_hours"])
    LOGGER.info(
        "daily_publish_updated_at=%s age_hours=%s published_count=%s",
        report["daily_publish"]["updated_at"] or "unknown",
        report["daily_publish"]["age_hours"],
        report["daily_publish"]["published_count"],
    )
    LOGGER.info("daily_updates_latest_date=%s", report["daily_updates"]["latest_date"] or "unknown")
    if report["errors"]:
        LOGGER.error("site_update_health=failed errors=%s", ",".join(report["errors"]))
        return 1
    LOGGER.info("site_update_health=ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
