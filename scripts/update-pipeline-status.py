#!/usr/bin/env python3
import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILE = ROOT / "src" / "data" / "pipeline-status.json"


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"updated_at": "", "workflows": {}, "history": []}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return {"updated_at": "", "workflows": {}, "history": []}
    if not isinstance(raw, dict):
        return {"updated_at": "", "workflows": {}, "history": []}
    if not isinstance(raw.get("workflows"), dict):
        raw["workflows"] = {}
    if not isinstance(raw.get("history"), list):
        raw["history"] = []
    return raw


def normalize_run_id(value: str) -> str:
    text = str(value or "").strip()
    return text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update src/data/pipeline-status.json")
    parser.add_argument("--workflow-key", required=True, help="Stable key (example: weekly_benchmark)")
    parser.add_argument("--workflow-name", default="", help="Display name")
    parser.add_argument("--run-id", required=True, help="GitHub Actions run id")
    parser.add_argument("--run-url", required=True, help="GitHub Actions run URL")
    parser.add_argument("--status", default="completed", help="Run status")
    parser.add_argument("--conclusion", default="unknown", help="Run conclusion")
    parser.add_argument("--event", default="", help="Run event")
    parser.add_argument("--head-sha", default="", help="Run head SHA")
    parser.add_argument("--failure-class", default="", help="Failure class code")
    parser.add_argument("--failure-detail", default="", help="Failure detail message")
    parser.add_argument("--updated-at", default="", help="UTC ISO timestamp")
    parser.add_argument("--history-limit", type=int, default=60, help="History retention entries")
    parser.add_argument("--file", default=str(DEFAULT_FILE), help="Output file path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_path = Path(args.file)
    if not out_path.is_absolute():
        out_path = (ROOT / out_path).resolve()

    now_iso = utc_now_iso()
    updated_at = str(args.updated_at).strip() or now_iso
    workflow_key = str(args.workflow_key).strip()
    workflow_name = str(args.workflow_name).strip() or workflow_key
    run_id = normalize_run_id(args.run_id)
    status = str(args.status).strip() or "completed"
    conclusion = str(args.conclusion).strip() or "unknown"

    failure_class = str(args.failure_class).strip()
    if not failure_class and conclusion == "success":
        failure_class = "none"
    failure_detail = str(args.failure_detail).strip()

    record = {
        "workflow_key": workflow_key,
        "workflow_name": workflow_name,
        "run_id": run_id,
        "run_url": str(args.run_url).strip(),
        "status": status,
        "conclusion": conclusion,
        "event": str(args.event).strip(),
        "head_sha": str(args.head_sha).strip(),
        "failure_class": failure_class,
        "failure_detail": failure_detail,
        "updated_at": updated_at,
    }

    payload = load_payload(out_path)
    payload["workflows"][workflow_key] = record
    payload["updated_at"] = now_iso

    history = payload.get("history", [])
    if not isinstance(history, list):
        history = []
    history = [
        row
        for row in history
        if not (
            isinstance(row, dict)
            and str(row.get("workflow_key", "")) == workflow_key
            and str(row.get("run_id", "")) == run_id
        )
    ]
    history.insert(0, record)
    history.sort(key=lambda row: str(row.get("updated_at", "")), reverse=True)
    payload["history"] = history[: max(1, int(args.history_limit))]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"updated pipeline status: {out_path}")


if __name__ == "__main__":
    main()
