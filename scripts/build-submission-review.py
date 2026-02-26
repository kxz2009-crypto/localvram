#!/usr/bin/env python3
import argparse
import datetime as dt
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORTS_FILE = ROOT / "src" / "data" / "community-reports.json"
DEFAULT_OUTPUT_FILE = ROOT / "src" / "data" / "submission-review.json"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Build community submission review queue snapshot.")
    parser.add_argument("--reports-file", default=str(DEFAULT_REPORTS_FILE))
    parser.add_argument("--output-file", default=str(DEFAULT_OUTPUT_FILE))
    parser.add_argument("--stale-days", type=int, default=7)
    parser.add_argument("--max-pending-sample", type=int, default=50)
    args = parser.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    stale_days = max(1, int(args.stale_days))
    stale_before = now - dt.timedelta(days=stale_days)
    max_pending_sample = max(1, int(args.max_pending_sample))

    reports_path = Path(args.reports_file)
    out_path = Path(args.output_file)

    payload = load_json(reports_path, {"reports": []})
    rows = payload.get("reports", []) if isinstance(payload, dict) else []
    rows = [row for row in rows if isinstance(row, dict)]

    status_counter: Counter[str] = Counter()
    bucket_counter: Counter[str] = Counter()
    risk_counter: Counter[str] = Counter()
    submitter_counter: Counter[str] = Counter()
    model_counter: Counter[str] = Counter()

    pending_rows: list[dict[str, Any]] = []
    stale_pending_count = 0
    high_risk_count = 0

    for row in rows:
        status = str(row.get("status", "")).strip() or "unknown"
        bucket = str(row.get("queue_bucket", "")).strip() or "unknown"
        status_counter[status] += 1
        bucket_counter[bucket] += 1

        submitter = str(row.get("submitter_id", "")).strip() or "anonymous"
        submitter_counter[submitter] += 1

        model_id = str(row.get("model_id", "")).strip() or "unknown"
        model_counter[model_id] += 1

        flags = row.get("risk_flags", [])
        if isinstance(flags, list):
            if len(flags) > 0:
                high_risk_count += 1
            for flag in flags:
                text = str(flag).strip()
                if text:
                    risk_counter[text] += 1

        if status.startswith("pending"):
            submitted_at_raw = str(row.get("submitted_at", "")).strip()
            submitted_at = parse_iso_utc(submitted_at_raw)
            age_days = None
            if submitted_at is not None:
                age_days = max(0, int((now - submitted_at).total_seconds() // 86400))
                if submitted_at < stale_before:
                    stale_pending_count += 1
            pending_rows.append(
                {
                    "submission_id": str(row.get("submission_id", "")).strip(),
                    "submitted_at": submitted_at_raw,
                    "age_days": age_days,
                    "model_id": model_id,
                    "hardware": str(row.get("hardware", "")).strip(),
                    "submitter_id": submitter,
                    "precheck_score": row.get("precheck_score"),
                    "status": status,
                    "risk_flags": flags if isinstance(flags, list) else [],
                    "issue_url": str(row.get("issue_url", "")).strip(),
                }
            )

    pending_rows.sort(key=lambda x: ((x.get("age_days") is None), -(x.get("age_days") or 0), str(x.get("submitted_at", ""))))
    pending_rows = pending_rows[:max_pending_sample]

    out = {
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "source": str(reports_path.relative_to(ROOT)).replace("\\", "/") if reports_path.exists() else str(reports_path),
        "stale_days_threshold": stale_days,
        "summary": {
            "total_reports": len(rows),
            "pending_reports": int(sum(count for key, count in status_counter.items() if key.startswith("pending"))),
            "stale_pending_reports": stale_pending_count,
            "high_risk_reports": high_risk_count,
            "status_counts": dict(status_counter),
            "queue_bucket_counts": dict(bucket_counter),
        },
        "risk_breakdown": [{"risk_flag": flag, "count": int(count)} for flag, count in risk_counter.most_common()],
        "top_submitters": [{"submitter_id": sid, "reports": int(count)} for sid, count in submitter_counter.most_common(20)],
        "top_models": [{"model_id": model, "reports": int(count)} for model, count in model_counter.most_common(20)],
        "pending_review_sample": pending_rows,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"submission_review_out={out_path}")
    print(
        "submission_review_summary="
        f"total={out['summary']['total_reports']},pending={out['summary']['pending_reports']},"
        f"stale_pending={out['summary']['stale_pending_reports']},high_risk={out['summary']['high_risk_reports']}"
    )


if __name__ == "__main__":
    main()
