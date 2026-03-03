#!/usr/bin/env python3
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "data" / "community-reports.json"
LOGGER = configure_logging("score-user-submission")


def load_payload() -> dict[str, Any]:
    if not OUT.exists():
        return {"version": "2026.02.26", "updated_at": "", "reports": []}
    payload = json.loads(OUT.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        return {"version": "2026.02.26", "updated_at": "", "reports": []}
    reports = payload.get("reports", [])
    if not isinstance(reports, list):
        payload["reports"] = []
    return payload


def parse_iso_utc(value: str) -> dt.datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def normalize(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def main() -> None:
    parser = argparse.ArgumentParser(description="Queue community benchmark submission with basic anti-spam/risk checks.")
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--hardware", required=True)
    parser.add_argument("--score", type=float, default=0.85)
    parser.add_argument("--submitter-id", default="anonymous")
    parser.add_argument("--issue-url", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--max-submissions-per-day", type=int, default=3)
    parser.add_argument("--min-score", type=float, default=0.70)
    parser.add_argument("--dedupe-window-hours", type=int, default=48)
    args = parser.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    today = now.date().isoformat()
    payload = load_payload()
    reports = payload.get("reports", [])
    assert isinstance(reports, list)

    model_id = str(args.model_id).strip()
    hardware = str(args.hardware).strip()
    submitter_id = normalize(args.submitter_id) or "anonymous"
    issue_url = str(args.issue_url).strip()
    notes = str(args.notes).strip()
    precheck_score = round(max(0.0, min(1.0, float(args.score))), 3)

    risk_flags: list[str] = []
    if precheck_score < float(args.min_score):
        risk_flags.append("low_precheck_score")
    if not issue_url:
        risk_flags.append("missing_issue_url")
    if len(notes) > 600:
        notes = notes[:600]
        risk_flags.append("notes_truncated")

    today_submissions = 0
    duplicate_found = False
    dedupe_window = dt.timedelta(hours=max(1, int(args.dedupe_window_hours)))
    normalized_model = normalize(model_id)
    normalized_hw = normalize(hardware)

    for row in reports:
        if not isinstance(row, dict):
            continue
        row_submitter = normalize(row.get("submitter_id", ""))
        submitted_at = parse_iso_utc(str(row.get("submitted_at", "")))
        row_model = normalize(str(row.get("model_id", "")))
        row_hw = normalize(str(row.get("hardware", "")))

        if row_submitter == submitter_id and submitted_at is not None and submitted_at.date().isoformat() == today:
            today_submissions += 1

        if (
            row_submitter == submitter_id
            and row_model == normalized_model
            and row_hw == normalized_hw
            and submitted_at is not None
            and now - submitted_at <= dedupe_window
            and str(row.get("status", "")).startswith("pending")
        ):
            duplicate_found = True

    status = "pending_manual_review"
    queue_bucket = "manual_review"
    if today_submissions >= max(1, int(args.max_submissions_per_day)):
        status = "rejected_rate_limited"
        queue_bucket = "rejected"
        risk_flags.append("submitter_rate_limited")
    elif duplicate_found:
        status = "pending_duplicate_review"
        queue_bucket = "duplicate_review"
        risk_flags.append("duplicate_submission_window")

    fingerprint = f"{normalized_model}|{normalized_hw}|{submitter_id}|{now.isoformat()}"
    submission_id = hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()[:12]
    report = {
        "submission_id": submission_id,
        "submitted_at": now.isoformat().replace("+00:00", "Z"),
        "model_id": model_id,
        "hardware": hardware,
        "submitter_id": submitter_id,
        "issue_url": issue_url,
        "notes": notes,
        "precheck_score": precheck_score,
        "risk_flags": risk_flags,
        "status": status,
        "queue_bucket": queue_bucket,
    }

    reports.append(report)
    payload["reports"] = reports
    payload["updated_at"] = now.isoformat().replace("+00:00", "Z")
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    LOGGER.info("submission_id=%s", submission_id)
    LOGGER.info("status=%s", status)
    LOGGER.info("queue_bucket=%s", queue_bucket)
    LOGGER.info("risk_flags=%s", ",".join(risk_flags) if risk_flags else "none")
    LOGGER.info("submission scored and queued")


if __name__ == "__main__":
    main()
