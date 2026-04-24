#!/usr/bin/env python3
import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_TARGETS = (
    "qwen3=128,deepseek-r1=128,qwen2.5=128,qwen3-coder=96,qwen3.5=96,"
    "qwen3.6=96,"
    "llama3.3=64,qwen2.5-coder=96,ministral-3=128,gpt-oss=96,mistral-small=96,"
    "gemma3=96,gemma4=96,llama4=64,qwq=96"
)
DEFAULT_RETRY_DELAYS = "5,10,20"
DEFAULT_PRIORITY_FAMILIES = (
    "qwen3.6,qwen3.5,qwen3,deepseek-r1,qwen2.5,qwen3-coder,llama3.3,qwen2.5-coder,"
    "ministral-3,gpt-oss,mistral-small,gemma3,gemma4,llama4,qwq"
)
DEFAULT_RETIRED_POLICY_FILE = "src/data/retired-models.json"
DEFAULT_EXCLUDE_FAMILIES = (
    "bge-m3,nomic-embed-text,mxbai-embed-large,all-minilm,snowflake-arctic-embed,"
    "deepseek-ocr,llava,llava-llama3,minicpm-v,qwen3-vl,qwen2.5vl,llama3.2-vision,gemma3n"
)
LOGGER = configure_logging("resolve-weekly-targets")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_endpoint(endpoint: str) -> str:
    return str(endpoint or "").strip().rstrip("/")


def resolve_default_endpoint() -> str:
    return os.getenv("LV_OLLAMA_ENDPOINT") or os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434"


def parse_retry_delays(raw: str) -> list[float]:
    out: list[float] = []
    for chunk in str(raw or "").split(","):
        part = chunk.strip()
        if not part:
            continue
        try:
            val = float(part)
        except ValueError:
            continue
        if val >= 0:
            out.append(val)
    return out


def parse_targets(raw: str) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    seen: set[str] = set()
    for chunk in str(raw or "").split(","):
        part = chunk.strip().lower()
        if not part:
            continue
        model = part
        num_predict = 96
        if "=" in part:
            model_raw, np_raw = part.rsplit("=", 1)
            model = model_raw.strip().lower()
            try:
                num_predict = max(16, int(np_raw.strip()))
            except ValueError:
                num_predict = 96
        if not model or model in seen:
            continue
        seen.add(model)
        out.append((model, num_predict))
    return out


def targets_to_csv(rows: list[tuple[str, int]]) -> str:
    return ",".join(f"{model}={num_predict}" for model, num_predict in rows)


def model_family(tag_or_family: str) -> str:
    value = str(tag_or_family).strip().lower()
    if not value:
        return ""
    return value.split(":", 1)[0].strip()


def parse_params_from_tag(tag: str) -> float | None:
    raw = str(tag).strip().lower()
    if ":" not in raw:
        return None
    size_part = raw.split(":", 1)[1]
    match = re.search(
        r"(e[0-9]+(?:\.[0-9]+)?b|[0-9]+(?:\.[0-9]+)?x[0-9]+(?:\.[0-9]+)?b|"
        r"[0-9]+(?:\.[0-9]+)?b-a[0-9]+(?:\.[0-9]+)?b|[0-9]+(?:\.[0-9]+)?b|[0-9]+(?:\.[0-9]+)?m)",
        size_part,
    )
    if not match:
        return None
    token = match.group(1)
    m = re.match(r"^e([0-9]+(?:\.[0-9]+)?)b$", token)
    if m:
        return float(m.group(1))
    m = re.match(r"^([0-9]+(?:\.[0-9]+)?)x([0-9]+(?:\.[0-9]+)?)b$", token)
    if m:
        return float(m.group(1)) * float(m.group(2))
    m = re.match(r"^([0-9]+(?:\.[0-9]+)?)b-a([0-9]+(?:\.[0-9]+)?)b$", token)
    if m:
        return float(m.group(1))
    m = re.match(r"^([0-9]+(?:\.[0-9]+)?)b$", token)
    if m:
        return float(m.group(1))
    m = re.match(r"^([0-9]+(?:\.[0-9]+)?)m$", token)
    if m:
        return float(m.group(1)) / 1000.0
    return None


def recommend_num_predict(params_b: float | None) -> int:
    if params_b is None:
        return 96
    if params_b <= 14:
        return 128
    if params_b <= 34:
        return 96
    if params_b <= 72:
        return 64
    return 48


def fetch_local_models(endpoint: str, retry_delays: list[float]) -> set[str]:
    url = f"{normalize_endpoint(endpoint)}/api/tags"
    for attempt in range(len(retry_delays) + 1):
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
                payload = json.loads(resp.read().decode("utf-8"))
            models: set[str] = set()
            for item in payload.get("models", []):
                name = str(item.get("name", "")).strip().lower()
                model = str(item.get("model", "")).strip().lower()
                if name:
                    models.add(name)
                if model:
                    models.add(model)
            return models
        except Exception:  # noqa: BLE001
            if attempt >= len(retry_delays):
                raise
            time.sleep(max(0.0, retry_delays[attempt]))
    return set()


def load_catalog_family_scenarios() -> dict[str, str]:
    path = ROOT / "src" / "data" / "model-catalog.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return {}
    out: dict[str, str] = {}
    for row in payload.get("items", []):
        family = str(row.get("library_id", "")).strip().lower()
        if not family:
            tag = str(row.get("ollama_tag", "")).strip().lower()
            family = model_family(tag)
        scenario = str(row.get("scenario", "")).strip().lower()
        if family and family not in out and scenario:
            out[family] = scenario
    return out


def parse_csv_list(raw: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for chunk in str(raw or "").split(","):
        item = chunk.strip().lower()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def parse_json_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return parse_csv_list(",".join(str(x) for x in value))
    return parse_csv_list(str(value or ""))


def load_retired_policy(policy_file: str) -> tuple[set[str], set[str], str]:
    raw_path = str(policy_file or "").strip() or DEFAULT_RETIRED_POLICY_FILE
    path = Path(raw_path)
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    if not path.exists():
        return set(), set(), str(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return set(), set(), str(path)
    retired_families = set(parse_json_str_list(payload.get("retired_families", [])))
    retired_tags = set(parse_json_str_list(payload.get("retired_tags", [])))
    return retired_families, retired_tags, str(path)


def is_retired_target(model: str, retired_families: set[str], retired_tags: set[str]) -> bool:
    raw = str(model or "").strip().lower()
    if not raw:
        return False
    if raw in retired_tags:
        return True
    fam = model_family(raw)
    return fam in retired_families


def is_family_eligible(family: str, scenario: str, excludes: set[str]) -> bool:
    fam = str(family or "").strip().lower()
    if not fam:
        return False
    if fam in excludes:
        return False
    scenario_norm = str(scenario or "").strip().lower()
    if scenario_norm in {"embedding", "multimodal"}:
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve weekly benchmark targets from local models.")
    parser.add_argument("--endpoint", default=resolve_default_endpoint())
    parser.add_argument("--base-targets", default=DEFAULT_BASE_TARGETS)
    parser.add_argument("--retry-delays", default=DEFAULT_RETRY_DELAYS)
    parser.add_argument("--max-new-families", type=int, default=5)
    parser.add_argument("--max-total-targets", type=int, default=15)
    parser.add_argument("--priority-families", default=DEFAULT_PRIORITY_FAMILIES)
    parser.add_argument("--exclude-families", default=DEFAULT_EXCLUDE_FAMILIES)
    parser.add_argument("--retired-policy-file", default=DEFAULT_RETIRED_POLICY_FILE)
    parser.add_argument("--output-file", default="src/data/weekly-target-plan.json")
    parser.add_argument("--github-output", default="")
    parser.add_argument("--strict-endpoint", action="store_true")
    args = parser.parse_args()

    base_targets = parse_targets(args.base_targets)
    retry_delays = parse_retry_delays(args.retry_delays) or [5.0, 10.0, 20.0]
    priority_families = parse_csv_list(args.priority_families)
    exclude_families = set(parse_csv_list(args.exclude_families))
    retired_families, retired_tags, retired_policy_path = load_retired_policy(args.retired_policy_file)
    effective_excludes = set(exclude_families) | set(retired_families)
    scenario_by_family = load_catalog_family_scenarios()

    warning = ""
    try:
        local_models = fetch_local_models(args.endpoint, retry_delays=retry_delays)
    except Exception as exc:  # noqa: BLE001
        if args.strict_endpoint:
            raise SystemExit(f"failed to fetch local models: {exc}") from exc
        warning = f"endpoint_unavailable_fallback_to_base: {exc}"
        local_models = set()

    local_models_sorted = sorted(local_models)
    local_families = sorted({model_family(tag) for tag in local_models_sorted if model_family(tag)})
    filtered_base_targets = [(m, np) for m, np in base_targets if not is_retired_target(m, retired_families, retired_tags)]
    dropped_base_targets = [{"model": model, "num_predict": num_predict} for model, num_predict in base_targets if is_retired_target(model, retired_families, retired_tags)]
    if not filtered_base_targets and base_targets:
        warning = (warning + "; " if warning else "") + "all_base_targets_retired_fallback_to_base_targets"
        filtered_base_targets = list(base_targets)
    base_families = {model_family(model) for model, _ in filtered_base_targets}

    family_min_params: dict[str, float] = {}
    for tag in local_models_sorted:
        fam = model_family(tag)
        if not fam:
            continue
        params = parse_params_from_tag(tag)
        if params is None:
            continue
        prev = family_min_params.get(fam)
        if prev is None or params < prev:
            family_min_params[fam] = params

    candidates: list[str] = []
    for fam in local_families:
        if fam in base_families:
            continue
        scenario = scenario_by_family.get(fam, "")
        if not is_family_eligible(fam, scenario, effective_excludes):
            continue
        candidates.append(fam)

    priority_index = {fam: idx for idx, fam in enumerate(priority_families)}

    def sort_key(fam: str) -> tuple[Any, ...]:
        pr = priority_index.get(fam, 9999)
        params = family_min_params.get(fam, 9999.0)
        return (pr, params, fam)

    candidates.sort(key=sort_key)

    budget = max(0, int(args.max_new_families))
    added_targets: list[tuple[str, int]] = []
    for fam in candidates:
        if len(added_targets) >= budget:
            break
        npredict = recommend_num_predict(family_min_params.get(fam))
        added_targets.append((fam, npredict))

    resolved = list(filtered_base_targets)
    resolved.extend(added_targets)
    resolved = resolved[: max(1, int(args.max_total_targets))]
    resolved_csv = targets_to_csv(resolved)
    retired_local_models = [tag for tag in local_models_sorted if is_retired_target(tag, retired_families, retired_tags)]

    report = {
        "generated_at": utc_now_iso(),
        "endpoint": normalize_endpoint(args.endpoint),
        "base_targets_csv": targets_to_csv(filtered_base_targets),
        "base_targets_raw_csv": targets_to_csv(base_targets),
        "resolved_targets_csv": resolved_csv,
        "local_model_count": len(local_models_sorted),
        "local_models_sample": local_models_sorted[:30],
        "local_family_count": len(local_families),
        "local_families": local_families,
        "retired_policy_file": retired_policy_path,
        "retired_families": sorted(retired_families),
        "retired_tags": sorted(retired_tags),
        "dropped_base_targets": dropped_base_targets,
        "retired_local_models_sample": retired_local_models[:30],
        "retired_local_model_count": len(retired_local_models),
        "candidate_families": candidates,
        "added_targets": [{"model": model, "num_predict": num_predict} for model, num_predict in added_targets],
        "excluded_families": sorted(effective_excludes),
        "priority_families": priority_families,
        "warning": warning,
    }

    out_path = Path(args.output_file)
    if not out_path.is_absolute():
        out_path = (ROOT / out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    LOGGER.info("resolved_targets_csv=%s", resolved_csv)
    LOGGER.info("added_target_count=%d", len(added_targets))
    if warning:
        LOGGER.warning("warning=%s", warning)
    LOGGER.info("weekly_target_plan_out=%s", out_path)

    if args.github_output:
        gh_out = Path(args.github_output)
        gh_out.parent.mkdir(parents=True, exist_ok=True)
        with gh_out.open("a", encoding="utf-8") as f:
            f.write(f"resolved_targets_csv={resolved_csv}\n")
            f.write(f"added_target_count={len(added_targets)}\n")
            f.write(f"dropped_base_target_count={len(dropped_base_targets)}\n")
            if warning:
                f.write("warning<<EOF\n")
                f.write(f"{warning}\n")
                f.write("EOF\n")


if __name__ == "__main__":
    main()
