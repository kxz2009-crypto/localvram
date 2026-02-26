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
FAILURE_ACTIONS = {
    "artifact_download_failure": "Verify source_run_id resolution and artifact name consistency before download.",
    "artifact_download_rate_limited": "Increase rate_limit_delay_s and keep 5/10/20+ retry backoff for artifact API calls.",
    "source_run_discovery_failure": "Validate workflow_dispatch inputs and auto-resolve latest successful weekly run id.",
    "source_run_metadata_failure": "Check GH API token scope and run visibility; retry metadata fetch before download.",
    "source_run_not_publishable": "Only publish from completed+success Weekly Benchmark runs.",
    "publish_push_rate_limited": "Apply longer push backoff and avoid concurrent publish jobs.",
    "publish_push_failure": "Check repository write permission and remote health before retrying push.",
    "weekly_benchmark_failed": "Inspect runner diagnostics and preflight output for Ollama visibility/target coverage.",
    "ollama_not_visible": "Restart managed Ollama service and verify /api/tags availability on runner.",
    "model_missing": "Align weekly targets with locally installed model tags and retirement policy.",
}


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


def action_for_failure_class(failure_class: str) -> str:
    key = str(failure_class or "").strip() or "unknown_failure"
    return FAILURE_ACTIONS.get(key, "Review workflow logs and update runbook mitigation for this failure class.")


def failure_class_counter(rows: list[dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        if normalize_conclusion(row.get("conclusion", "")) == "success":
            continue
        failure_class = str(row.get("failure_class", "")).strip() or "unknown_failure"
        if failure_class == "none":
            failure_class = "unknown_failure"
        counter[failure_class] += 1
    return counter


def top_failure_class(rows: list[dict[str, Any]]) -> tuple[str, int]:
    counter = failure_class_counter(rows)
    if not counter:
        return ("none", 0)
    key, count = counter.most_common(1)[0]
    return (key, int(count))


def top_failures(rows: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    counter = failure_class_counter(rows)
    out: list[dict[str, Any]] = []
    for failure_class, count in counter.most_common(max(1, int(limit))):
        out.append(
            {
                "failure_class": failure_class,
                "count": int(count),
                "action": action_for_failure_class(failure_class),
            }
        )
    return out


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
    workflow_recommendations_28d: list[dict[str, Any]] = []

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
            top_failure_rows = top_failures(scoped, limit=3)
            fail_counter = failure_class_counter(scoped)
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
                "top_failure_action": action_for_failure_class(fail_key) if fail_key != "none" else "",
                "top_failures": top_failure_rows,
                "failure_class_counts": dict(sorted(fail_counter.items(), key=lambda x: x[0])),
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
        window_28 = windows.get("28", {})
        for row in window_28.get("top_failures", []) if isinstance(window_28, dict) else []:
            workflow_recommendations_28d.append(
                {
                    "workflow_key": key,
                    "workflow_name": str(latest.get("workflow_name", "")).strip() or workflow_display_name(key),
                    "failure_class": row.get("failure_class", ""),
                    "count": int(row.get("count", 0) or 0),
                    "action": row.get("action", ""),
                }
            )

    if not history_rows:
        pipeline_slo_met = False

    since_28 = reference_dt - dt.timedelta(days=28)
    global_28_rows: list[dict[str, Any]] = []
    for row in history_rows:
        workflow_key = str(row.get("workflow_key", "")).strip()
        if workflow_key not in workflow_keys:
            continue
        row_time = parse_iso_utc(str(row.get("updated_at", "")))
        if row_time is None:
            continue
        if row_time >= since_28:
            global_28_rows.append(row)
    global_28_top = top_failures(global_28_rows, limit=5)

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
        "failure_recommendations": {
            "window_days": 28,
            "window_start": iso_no_micros(since_28),
            "window_end": iso_no_micros(reference_dt),
            "global_top_failures": global_28_top,
            "workflows_28d": sorted(
                workflow_recommendations_28d,
                key=lambda x: (-(int(x.get("count", 0) or 0)), str(x.get("workflow_name", ""))),
            ),
        },
        "failure_action_catalog": FAILURE_ACTIONS,
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"built pipeline SLO snapshot: {output_file}")
    print(f"pipeline_slo_met={str(pipeline_slo_met).lower()}")


if __name__ == "__main__":
    main()
