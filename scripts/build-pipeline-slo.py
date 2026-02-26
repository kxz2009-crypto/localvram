#!/usr/bin/env python3
import argparse
import datetime as dt
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATUS_FILE = ROOT / "src" / "data" / "pipeline-status.json"
DEFAULT_OUT_FILE = ROOT / "src" / "data" / "pipeline-slo.json"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return default


def parse_iso_utc(value: str) -> dt.datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return dt.datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    except ValueError:
        return None


def iso_no_micros(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_conclusion(value: str) -> str:
    return str(value or "").strip().lower()


def safe_rate(success: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((float(success) / float(total)) * 100.0, 2)


def top_failure_class(rows: list[dict[str, Any]]) -> tuple[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        if normalize_conclusion(row.get("conclusion", "")) == "success":
            continue
        failure_class = str(row.get("failure_class", "")).strip() or "unknown_failure"
        if failure_class == "none":
            failure_class = "unknown_failure"
        counter[failure_class] += 1
    if not counter:
        return ("none", 0)
    key, count = counter.most_common(1)[0]
    return (key, int(count))


def compute_streak(rows_sorted_desc: list[dict[str, Any]]) -> int:
    streak = 0
    for row in rows_sorted_desc:
        if normalize_conclusion(row.get("conclusion", "")) != "success":
            break
        streak += 1
    return streak


def workflow_display_name(workflow_key: str) -> str:
    mapping = {
        "weekly_benchmark": "Weekly Benchmark",
        "publish_benchmark_artifact": "Publish Benchmark Artifact",
    }
    return mapping.get(workflow_key, workflow_key)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build pipeline SLO snapshot from pipeline-status history.")
    parser.add_argument("--status-file", default=str(DEFAULT_STATUS_FILE))
    parser.add_argument("--output-file", default=str(DEFAULT_OUT_FILE))
    parser.add_argument("--workflow-keys", default="weekly_benchmark,publish_benchmark_artifact")
    parser.add_argument("--target-success-rate", type=float, default=95.0)
    parser.add_argument("--window-days", default="7,28")
    parser.add_argument("--history-limit", type=int, default=120)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    status_file = Path(args.status_file)
    if not status_file.is_absolute():
        status_file = (ROOT / status_file).resolve()
    output_file = Path(args.output_file)
    if not output_file.is_absolute():
        output_file = (ROOT / output_file).resolve()

    target_success_rate = float(args.target_success_rate)
    workflow_keys = [x.strip() for x in str(args.workflow_keys).split(",") if x.strip()]
    if not workflow_keys:
        raise SystemExit("workflow-keys cannot be empty")

    window_days = [int(x.strip()) for x in str(args.window_days).split(",") if x.strip()]
    window_days = sorted(set([x for x in window_days if x > 0]))
    if not window_days:
        window_days = [7, 28]

    payload = load_json(status_file, {"updated_at": "", "workflows": {}, "history": []})
    history_raw = payload.get("history", [])
    if not isinstance(history_raw, list):
        history_raw = []

    history_rows: list[dict[str, Any]] = [row for row in history_raw if isinstance(row, dict)]
    history_rows = history_rows[: max(1, int(args.history_limit))]

    parsed_times = [
        parse_iso_utc(str(row.get("updated_at", "")))
        for row in history_rows
        if isinstance(row, dict)
    ]
    parsed_times = [x for x in parsed_times if x is not None]

    status_updated_at = parse_iso_utc(str(payload.get("updated_at", "")))
    if parsed_times:
        reference_dt = max(parsed_times)
    elif status_updated_at:
        reference_dt = status_updated_at
    else:
        reference_dt = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)

    rows_by_workflow: dict[str, list[dict[str, Any]]] = {}
    for key in workflow_keys:
        rows = [row for row in history_rows if str(row.get("workflow_key", "")).strip() == key]
        rows.sort(key=lambda row: str(row.get("updated_at", "")), reverse=True)
        rows_by_workflow[key] = rows

    workflow_stats: dict[str, Any] = {}
    pipeline_slo_met = True
    weekly_lines: list[str] = []

    for key in workflow_keys:
        rows = rows_by_workflow.get(key, [])
        latest = rows[0] if rows else {}
        last_success_at = next(
            (str(row.get("updated_at", "")) for row in rows if normalize_conclusion(row.get("conclusion", "")) == "success"),
            "",
        )
        last_failure_at = next(
            (str(row.get("updated_at", "")) for row in rows if normalize_conclusion(row.get("conclusion", "")) != "success"),
            "",
        )

        windows: dict[str, Any] = {}
        for days in window_days:
            since_dt = reference_dt - dt.timedelta(days=days)
            scoped = []
            for row in rows:
                row_time = parse_iso_utc(str(row.get("updated_at", "")))
                if row_time is None:
                    continue
                if row_time >= since_dt:
                    scoped.append(row)
            total = len(scoped)
            success = len([row for row in scoped if normalize_conclusion(row.get("conclusion", "")) == "success"])
            failure = total - success
            rate = safe_rate(success, total)
            slo_met = bool(total > 0 and rate >= target_success_rate)
            if days >= 28 and not slo_met:
                pipeline_slo_met = False
            fail_key, fail_count = top_failure_class(scoped)
            windows[str(days)] = {
                "window_days": days,
                "window_start": iso_no_micros(since_dt),
                "window_end": iso_no_micros(reference_dt),
                "total_runs": total,
                "success_runs": success,
                "failure_runs": failure,
                "success_rate": rate,
                "target_success_rate": target_success_rate,
                "slo_met": slo_met,
                "top_failure_class": fail_key,
                "top_failure_count": fail_count,
            }

        default_window = windows.get("7") or windows.get("28") or next(iter(windows.values()))
        weekly_lines.append(
            f"{workflow_display_name(key)}: {default_window['success_runs']}/{default_window['total_runs']} "
            f"({default_window['success_rate']}%), top failure={default_window['top_failure_class']}"
        )

        workflow_stats[key] = {
            "workflow_key": key,
            "workflow_name": str(latest.get("workflow_name", "")).strip() or workflow_display_name(key),
            "latest_conclusion": str(latest.get("conclusion", "unknown")).strip() or "unknown",
            "latest_updated_at": str(latest.get("updated_at", "")).strip(),
            "latest_run_id": str(latest.get("run_id", "")).strip(),
            "latest_run_url": str(latest.get("run_url", "")).strip(),
            "current_success_streak": compute_streak(rows),
            "last_success_at": last_success_at,
            "last_failure_at": last_failure_at,
            "windows": windows,
        }

    if not history_rows:
        pipeline_slo_met = False

    report = {
        "version": "2026.02.26",
        "updated_at": iso_no_micros(reference_dt),
        "target_success_rate": target_success_rate,
        "reference_time": iso_no_micros(reference_dt),
        "pipeline_slo_met": pipeline_slo_met,
        "workflow_keys": workflow_keys,
        "workflows": workflow_stats,
        "weekly_report": {
            "window_days": 7,
            "window_start": iso_no_micros(reference_dt - dt.timedelta(days=7)),
            "window_end": iso_no_micros(reference_dt),
            "summary_lines": weekly_lines,
        },
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"built pipeline SLO snapshot: {output_file}")
    print(f"pipeline_slo_met={str(pipeline_slo_met).lower()}")


if __name__ == "__main__":
    main()
