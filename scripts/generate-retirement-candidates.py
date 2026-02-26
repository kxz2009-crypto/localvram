#!/usr/bin/env python3
import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_FILE = "src/data/benchmark-results.json"
DEFAULT_WEEKLY_TARGET_PLAN_FILE = "src/data/weekly-target-plan.json"
DEFAULT_RETIRED_POLICY_FILE = "src/data/retired-models.json"
DEFAULT_OUTPUT_FILE = "src/data/retirement-candidates.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_path(raw: str) -> Path:
    path = Path(str(raw or "").strip())
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    return path


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def model_family(tag_or_family: str) -> str:
    raw = str(tag_or_family or "").strip().lower()
    if not raw:
        return ""
    return raw.split(":", 1)[0].strip()


def is_variant(value: str, base: str) -> bool:
    if value == base:
        return True
    if not value.startswith(base):
        return False
    if len(value) == len(base):
        return True
    return value[len(base)] in {"-", "_", ".", ":"}


def parse_csv_refs(raw: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for chunk in str(raw or "").split(","):
        part = chunk.strip().lower()
        if not part:
            continue
        if "=" in part:
            part = part.rsplit("=", 1)[0].strip()
        if not part or part in seen:
            continue
        seen.add(part)
        out.append(part)
    return out


def parse_json_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        source = ",".join(str(x) for x in value)
    else:
        source = str(value or "")
    return parse_csv_refs(source)


def matches_plan(tag: str, plan_refs: list[str]) -> bool:
    value = str(tag or "").strip().lower()
    if not value:
        return False
    fam = model_family(value)
    for ref in plan_refs:
        if ":" in ref:
            if is_variant(value, ref):
                return True
        elif fam == ref:
            return True
    return False


@dataclass
class TagObservation:
    tag: str
    family: str
    first_seen_at: str = ""
    last_seen_at: str = ""
    last_seen_run_index: int = 9999
    seen_targets_count: int = 0
    seen_results_count: int = 0
    seen_ok_count: int = 0
    last_success_at: str = ""

    def touch(self, updated_at: str, run_index: int, source: str, status: str = "") -> None:
        ts = str(updated_at or "")
        if not self.first_seen_at:
            self.first_seen_at = ts
        self.last_seen_at = ts
        if run_index < self.last_seen_run_index:
            self.last_seen_run_index = run_index
        if source == "targets":
            self.seen_targets_count += 1
        if source == "results":
            self.seen_results_count += 1
            if str(status).strip().lower() == "ok":
                self.seen_ok_count += 1
                self.last_success_at = ts


def get_or_create(obs: dict[str, TagObservation], tag: str) -> TagObservation:
    key = str(tag or "").strip().lower()
    if not key:
        key = "unknown"
    current = obs.get(key)
    if current is None:
        current = TagObservation(tag=key, family=model_family(key))
        obs[key] = current
    return current


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate stale model retirement candidates from benchmark history.")
    parser.add_argument("--results-file", default=DEFAULT_RESULTS_FILE)
    parser.add_argument("--weekly-target-plan-file", default=DEFAULT_WEEKLY_TARGET_PLAN_FILE)
    parser.add_argument("--retired-policy-file", default=DEFAULT_RETIRED_POLICY_FILE)
    parser.add_argument("--output-file", default=DEFAULT_OUTPUT_FILE)
    parser.add_argument("--stale-run-threshold", type=int, default=3, help="Candidate must be absent for N recent runs.")
    parser.add_argument("--max-candidates", type=int, default=50)
    args = parser.parse_args()

    results_path = resolve_path(args.results_file)
    weekly_plan_path = resolve_path(args.weekly_target_plan_file)
    retired_policy_path = resolve_path(args.retired_policy_file)
    out_path = resolve_path(args.output_file)

    results = load_json(results_path, {})
    weekly_plan = load_json(weekly_plan_path, {})
    retired_policy = load_json(retired_policy_path, {})

    history = results.get("history", [])
    latest = results.get("latest", {})
    if not isinstance(history, list):
        history = []
    if not isinstance(latest, dict):
        latest = {}

    latest_targets = {str(x.get("model", "")).strip().lower() for x in (latest.get("targets") or []) if isinstance(x, dict)}
    latest_results = {str(x.get("canonical_model") or x.get("model", "")).strip().lower() for x in (latest.get("results") or []) if isinstance(x, dict)}
    latest_run_updated_at = str(latest.get("updated_at", ""))

    plan_refs = parse_csv_refs(weekly_plan.get("resolved_targets_csv", ""))
    retired_families = set(model_family(x) for x in parse_json_str_list(retired_policy.get("retired_families", [])) if model_family(x))
    retired_tags = set(parse_json_str_list(retired_policy.get("retired_tags", [])))

    observations: dict[str, TagObservation] = {}
    for run_index, run in enumerate(history):
        if not isinstance(run, dict):
            continue
        updated_at = str(run.get("updated_at", ""))

        for row in run.get("targets", []) or []:
            if not isinstance(row, dict):
                continue
            tag = str(row.get("model", "")).strip().lower()
            if not tag:
                continue
            get_or_create(observations, tag).touch(updated_at, run_index, source="targets")

        for row in run.get("results", []) or []:
            if not isinstance(row, dict):
                continue
            tag = str(row.get("canonical_model") or row.get("model", "")).strip().lower()
            if not tag:
                continue
            status = str(row.get("status", "")).strip().lower()
            get_or_create(observations, tag).touch(updated_at, run_index, source="results", status=status)

    stale_threshold = max(1, int(args.stale_run_threshold))
    max_candidates = max(1, int(args.max_candidates))
    candidates: list[dict[str, Any]] = []

    for tag, item in sorted(observations.items(), key=lambda kv: (kv[1].last_seen_run_index, kv[0])):
        if not tag or ":" not in tag:
            continue
        if tag in retired_tags:
            continue
        if item.family in retired_families:
            continue

        in_plan = matches_plan(tag, plan_refs)
        in_latest_targets = tag in latest_targets or item.family in latest_targets
        in_latest_results = tag in latest_results
        stale = item.last_seen_run_index >= stale_threshold
        if in_plan or in_latest_targets or in_latest_results or not stale:
            continue

        reasons = [
            f"absent_in_recent_runs>={stale_threshold}",
            "not_in_current_weekly_plan",
            "not_in_latest_targets_or_results",
        ]
        candidates.append(
            {
                "model": tag,
                "family": item.family,
                "last_seen_at": item.last_seen_at,
                "last_seen_run_index": item.last_seen_run_index,
                "last_success_at": item.last_success_at,
                "seen_ok_count": item.seen_ok_count,
                "seen_targets_count": item.seen_targets_count,
                "seen_results_count": item.seen_results_count,
                "reasons": reasons,
            }
        )

    candidates = candidates[:max_candidates]
    payload = {
        "generated_at": utc_now_iso(),
        "results_file": str(results_path),
        "weekly_target_plan_file": str(weekly_plan_path),
        "retired_policy_file": str(retired_policy_path),
        "latest_run_updated_at": latest_run_updated_at,
        "history_run_count": len(history),
        "stale_run_threshold": stale_threshold,
        "max_candidates": max_candidates,
        "current_plan_refs": plan_refs,
        "retired_families": sorted(retired_families),
        "retired_tags": sorted(retired_tags),
        "observed_tag_count": len(observations),
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    write_json(out_path, payload)

    print(f"candidate_count={len(candidates)}")
    print(f"observed_tag_count={len(observations)}")
    print(f"stale_run_threshold={stale_threshold}")
    print(f"retirement_candidates_out={out_path}")


if __name__ == "__main__":
    main()
