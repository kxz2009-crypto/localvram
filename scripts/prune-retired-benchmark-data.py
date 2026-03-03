#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_FILE = "src/data/benchmark-results.json"
DEFAULT_RETIRED_POLICY_FILE = "src/data/retired-models.json"
DEFAULT_TAG_ALIASES_FILE = "src/data/benchmark-tag-aliases.json"
LOGGER = configure_logging("prune-retired-benchmark-data")


def emit(message: str, *, level: str = "info", stderr: bool = False) -> None:
    if level == "error":
        LOGGER.error("%s", message)
    elif level == "warning":
        LOGGER.warning("%s", message)
    else:
        LOGGER.info("%s", message)


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


def parse_json_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        source = ",".join(str(x) for x in value)
    else:
        source = str(value or "")
    out: list[str] = []
    seen: set[str] = set()
    for chunk in source.split(","):
        item = chunk.strip().lower()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


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


def load_retired_policy(path: Path) -> tuple[set[str], set[str]]:
    payload = load_json(path, {})
    retired_families = set(model_family(x) for x in parse_json_str_list(payload.get("retired_families", [])) if model_family(x))
    retired_tags = set(parse_json_str_list(payload.get("retired_tags", [])))
    return retired_families, retired_tags


def load_tag_aliases(path: Path) -> dict[str, str]:
    payload = load_json(path, {})
    aliases = payload.get("aliases", {}) if isinstance(payload, dict) else {}
    if not isinstance(aliases, dict):
        return {}
    out: dict[str, str] = {}
    for raw_tag, canonical_tag in aliases.items():
        raw = str(raw_tag).strip().lower()
        canonical = str(canonical_tag).strip().lower()
        if raw and canonical:
            out[raw] = canonical
    return out


def is_retired_model_ref(model_ref: str, retired_families: set[str], retired_tags: set[str], aliases: dict[str, str]) -> bool:
    raw = str(model_ref or "").strip().lower()
    if not raw:
        return False
    canonical = aliases.get(raw, raw)
    for candidate in (raw, canonical):
        if candidate in retired_tags:
            return True
        for retired_tag in retired_tags:
            if is_variant(candidate, retired_tag):
                return True
    family = model_family(canonical or raw)
    return family in retired_families


def prune_model_map(
    models: dict[str, Any], retired_families: set[str], retired_tags: set[str], aliases: dict[str, str]
) -> tuple[dict[str, Any], list[str]]:
    kept: dict[str, Any] = {}
    removed: list[str] = []
    for key, value in models.items():
        tag = str(key).strip().lower()
        if is_retired_model_ref(tag, retired_families, retired_tags, aliases):
            removed.append(tag)
            continue
        kept[tag] = value
    return kept, removed


def prune_targets_list(
    rows: list[Any], retired_families: set[str], retired_tags: set[str], aliases: dict[str, str]
) -> tuple[list[Any], int]:
    kept: list[Any] = []
    removed_count = 0
    for row in rows:
        if not isinstance(row, dict):
            kept.append(row)
            continue
        model = str(row.get("model", "")).strip().lower()
        if is_retired_model_ref(model, retired_families, retired_tags, aliases):
            removed_count += 1
            continue
        kept.append(row)
    return kept, removed_count


def prune_results_list(
    rows: list[Any], retired_families: set[str], retired_tags: set[str], aliases: dict[str, str]
) -> tuple[list[Any], int]:
    kept: list[Any] = []
    removed_count = 0
    for row in rows:
        if not isinstance(row, dict):
            kept.append(row)
            continue
        model = str(row.get("model", "")).strip().lower()
        canonical = str(row.get("canonical_model", "")).strip().lower()
        if is_retired_model_ref(model, retired_families, retired_tags, aliases) or is_retired_model_ref(
            canonical, retired_families, retired_tags, aliases
        ):
            removed_count += 1
            continue
        kept.append(row)
    return kept, removed_count


def prune_changed_models(
    rows: list[Any], retired_families: set[str], retired_tags: set[str], aliases: dict[str, str]
) -> tuple[list[Any], int]:
    kept: list[Any] = []
    removed_count = 0
    for row in rows:
        model = str(row).strip().lower()
        if model and is_retired_model_ref(model, retired_families, retired_tags, aliases):
            removed_count += 1
            continue
        kept.append(row)
    return kept, removed_count


def prune_run_payload(
    run_payload: dict[str, Any], retired_families: set[str], retired_tags: set[str], aliases: dict[str, str]
) -> dict[str, int]:
    stats = {
        "targets_removed": 0,
        "auto_backfill_removed": 0,
        "results_removed": 0,
        "changed_models_removed": 0,
    }
    targets = run_payload.get("targets")
    if isinstance(targets, list):
        kept, removed = prune_targets_list(targets, retired_families, retired_tags, aliases)
        run_payload["targets"] = kept
        stats["targets_removed"] = removed

    auto_backfill = run_payload.get("auto_backfill_targets")
    if isinstance(auto_backfill, list):
        kept, removed = prune_targets_list(auto_backfill, retired_families, retired_tags, aliases)
        run_payload["auto_backfill_targets"] = kept
        stats["auto_backfill_removed"] = removed

    results = run_payload.get("results")
    if isinstance(results, list):
        kept, removed = prune_results_list(results, retired_families, retired_tags, aliases)
        run_payload["results"] = kept
        stats["results_removed"] = removed

    changed_models = run_payload.get("changed_models")
    if isinstance(changed_models, list):
        kept, removed = prune_changed_models(changed_models, retired_families, retired_tags, aliases)
        run_payload["changed_models"] = kept
        stats["changed_models_removed"] = removed

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Prune retired models from benchmark result payloads.")
    parser.add_argument("--results-file", default=DEFAULT_RESULTS_FILE)
    parser.add_argument("--retired-policy-file", default=DEFAULT_RETIRED_POLICY_FILE)
    parser.add_argument("--tag-aliases-file", default=DEFAULT_TAG_ALIASES_FILE)
    parser.add_argument("--report-file", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    results_path = resolve_path(args.results_file)
    retired_policy_path = resolve_path(args.retired_policy_file)
    aliases_path = resolve_path(args.tag_aliases_file)

    payload = load_json(results_path, None)
    if not isinstance(payload, dict):
        emit(f"invalid benchmark results payload: {results_path}", level="error", stderr=True)
        raise SystemExit(f"invalid benchmark results payload: {results_path}")

    retired_families, retired_tags = load_retired_policy(retired_policy_path)
    aliases = load_tag_aliases(aliases_path)
    changed = False

    models_removed: list[str] = []
    models = payload.get("models")
    if isinstance(models, dict):
        pruned_models, models_removed = prune_model_map(models, retired_families, retired_tags, aliases)
        if len(pruned_models) != len(models):
            payload["models"] = pruned_models
            changed = True

    latest_stats = {"targets_removed": 0, "auto_backfill_removed": 0, "results_removed": 0, "changed_models_removed": 0}
    latest = payload.get("latest")
    if isinstance(latest, dict):
        latest_stats = prune_run_payload(latest, retired_families, retired_tags, aliases)
        if any(v > 0 for v in latest_stats.values()):
            changed = True

    history_stats = {"targets_removed": 0, "auto_backfill_removed": 0, "results_removed": 0, "changed_models_removed": 0}
    history = payload.get("history")
    if isinstance(history, list):
        for entry in history:
            if not isinstance(entry, dict):
                continue
            entry_stats = prune_run_payload(entry, retired_families, retired_tags, aliases)
            for key in history_stats:
                history_stats[key] += int(entry_stats.get(key, 0))
        if any(v > 0 for v in history_stats.values()):
            changed = True

    report = {
        "updated_at": utc_now_iso(),
        "results_file": str(results_path),
        "retired_policy_file": str(retired_policy_path),
        "tag_aliases_file": str(aliases_path),
        "retired_families": sorted(retired_families),
        "retired_tags": sorted(retired_tags),
        "models_removed_count": len(models_removed),
        "models_removed_sample": sorted(models_removed)[:30],
        "latest_removed": latest_stats,
        "history_removed": history_stats,
        "changed": changed,
        "dry_run": bool(args.dry_run),
    }

    if changed and not args.dry_run:
        results_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    emit(f"retired_families_count={len(retired_families)}")
    emit(f"retired_tags_count={len(retired_tags)}")
    emit(f"models_removed_count={len(models_removed)}")
    emit(f"latest_removed={latest_stats}")
    emit(f"history_removed={history_stats}")
    emit(f"changed={str(changed).lower()}")
    emit(f"dry_run={str(bool(args.dry_run)).lower()}")

    if args.report_file:
        report_path = resolve_path(args.report_file)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        emit(f"report_file={report_path}")


if __name__ == "__main__":
    main()
