#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORTS_FILE = ROOT / "src" / "data" / "community-reports.json"
LOGGER = configure_logging("review-community-submissions")

PENDING_STATUSES = {"pending_manual_review", "pending_duplicate_review"}
VALID_ACTIONS = {"approve", "reject", "needs_info"}


def emit(message: str, *, level: str = "info", stderr: bool = False) -> None:
    if level == "error":
        LOGGER.error("%s", message)
    elif level == "warning":
        LOGGER.warning("%s", message)
    else:
        LOGGER.info("%s", message)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_ids(raw_ids: str) -> list[str]:
    out: list[str] = []
    for part in str(raw_ids or "").split(","):
        value = part.strip()
        if value and value not in out:
            out.append(value)
    return out


def action_to_status(action: str) -> str:
    if action == "approve":
        return "approved_manual"
    if action == "reject":
        return "rejected_manual"
    return "needs_info_manual"


def action_to_bucket(action: str) -> str:
    if action == "approve":
        return "approved"
    if action == "reject":
        return "rejected"
    return "needs_info"


def main() -> None:
    parser = argparse.ArgumentParser(description="Review queued community submissions and set final status.")
    parser.add_argument("--submission-ids", required=True, help="CSV submission ids, e.g. id1,id2")
    parser.add_argument("--action", required=True, choices=sorted(VALID_ACTIONS))
    parser.add_argument("--reviewer", default="ops")
    parser.add_argument("--notes", default="")
    parser.add_argument("--reports-file", default=str(DEFAULT_REPORTS_FILE))
    parser.add_argument("--allow-non-pending", action="store_true", help="Allow re-reviewing non-pending statuses.")
    parser.add_argument("--dry-run", action="store_true", help="Preview status updates without writing file.")
    args = parser.parse_args()

    submission_ids = normalize_ids(args.submission_ids)
    if not submission_ids:
        raise SystemExit("no submission ids provided")

    reports_path = Path(args.reports_file)
    payload = load_json(reports_path, {"version": "2026.02.26", "updated_at": "", "reports": []})
    reports = payload.get("reports", []) if isinstance(payload, dict) else []
    if not isinstance(reports, list):
        raise SystemExit("invalid reports payload: reports must be a list")

    action = str(args.action).strip().lower()
    now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    reviewer = str(args.reviewer).strip() or "ops"
    notes = str(args.notes).strip()
    if len(notes) > 800:
        notes = notes[:800]

    touched = 0
    skipped_missing: list[str] = []
    skipped_non_pending: list[str] = []
    applied_ids: list[str] = []

    index = {
        str(item.get("submission_id", "")).strip(): item
        for item in reports
        if isinstance(item, dict) and str(item.get("submission_id", "")).strip()
    }

    for submission_id in submission_ids:
        row = index.get(submission_id)
        if row is None:
            skipped_missing.append(submission_id)
            continue

        current_status = str(row.get("status", "")).strip()
        if not args.allow_non_pending and current_status not in PENDING_STATUSES:
            skipped_non_pending.append(submission_id)
            continue

        row["status"] = action_to_status(action)
        row["queue_bucket"] = action_to_bucket(action)
        row["reviewed_at"] = now
        row["reviewed_by"] = reviewer
        if notes:
            row["review_notes"] = notes
        touched += 1
        applied_ids.append(submission_id)

    if touched > 0 and not args.dry_run:
        payload["updated_at"] = now
        save_json(reports_path, payload)

    emit(f"action={action}")
    emit(f"requested={len(submission_ids)}")
    emit(f"updated={touched}")
    if applied_ids:
        emit(f"updated_ids={','.join(applied_ids)}")
    if skipped_missing:
        emit(f"skipped_missing={','.join(skipped_missing)}", level="warning")
    if skipped_non_pending:
        emit(f"skipped_non_pending={','.join(skipped_non_pending)}", level="warning")
    emit(f"dry_run={'true' if args.dry_run else 'false'}")


if __name__ == "__main__":
    main()
