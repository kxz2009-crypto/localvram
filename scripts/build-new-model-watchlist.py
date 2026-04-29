#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_FILE = ROOT / "src" / "data" / "benchmark-results.json"
CATALOG_FILE = ROOT / "src" / "data" / "model-catalog.json"
WEEKLY_TARGET_PLAN_FILE = ROOT / "src" / "data" / "weekly-target-plan.json"
OUT_FILE = ROOT / "src" / "data" / "new-model-watchlist.json"
LOGGER = configure_logging("build-new-model-watchlist")

PRIORITY_FAMILY_TOKENS = (
    "qwen",
    "deepseek",
    "gpt-oss",
    "mistral",
    "magistral",
    "phi",
    "qwq",
    "coder",
    "llama",
    "gemma",
)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return default


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return cleaned or "untitled"


def family_from_tag(tag: str) -> str:
    return str(tag or "").strip().lower().split(":", 1)[0]


def params_from_tag(tag: str) -> float:
    text = str(tag or "").lower()
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)x([0-9]+(?:\.[0-9]+)?)b", text)
    if match:
        return float(match.group(1)) * float(match.group(2))
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)b-a([0-9]+(?:\.[0-9]+)?)b", text)
    if match:
        return float(match.group(1))
    match = re.search(r"e([0-9]+(?:\.[0-9]+)?)b", text)
    if match:
        return float(match.group(1))
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)b", text)
    if match:
        return float(match.group(1))
    return 7.0


def catalog_by_tag(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in catalog.get("items", []):
        if not isinstance(item, dict):
            continue
        tag = str(item.get("ollama_tag", "")).strip().lower()
        if tag and tag not in out:
            out[tag] = item
    return out


def source_url_for(tag: str, catalog_item: dict[str, Any] | None = None) -> str:
    if catalog_item:
        url = str(catalog_item.get("ollama_source_url", "")).strip()
        if url:
            return url
    family = family_from_tag(tag)
    return f"https://ollama.com/library/{family}" if family else "https://ollama.com/library"


def title_for(tag: str) -> str:
    return f"{tag} on RTX 3090: Ollama Benchmark, VRAM, and Setup"


def keyword_for(tag: str, measured: bool) -> str:
    if measured:
        return f"{tag} rtx 3090 ollama benchmark"
    return f"{tag} vram requirements rtx 3090"


def score_candidate(
    *,
    tag: str,
    source: str,
    measured_at: dt.datetime | None,
    now: dt.datetime,
    tokens_per_second: float | None,
    catalog_item: dict[str, Any] | None,
) -> int:
    score = 40
    family = family_from_tag(tag)
    params_b = params_from_tag(tag)
    scenario = str((catalog_item or {}).get("scenario", "")).lower()

    if source == "recent_benchmark":
        score += 35
    elif source == "weekly_target_plan":
        score += 18

    if measured_at is not None:
        age_hours = max(0.0, (now - measured_at).total_seconds() / 3600)
        score += max(0, 28 - int(age_hours / 4))

    if tokens_per_second is not None:
        if tokens_per_second >= 80:
            score += 16
        elif tokens_per_second >= 25:
            score += 10
        else:
            score += 4

    if 14 <= params_b <= 35:
        score += 16
    elif 7 <= params_b < 14:
        score += 10
    elif params_b > 35:
        score += 4

    if any(token in family for token in PRIORITY_FAMILY_TOKENS):
        score += 12
    if scenario in {"coding", "reasoning", "multimodal"}:
        score += 8

    return min(score, 100)


def benchmark_candidates(
    benchmark: dict[str, Any],
    catalog_index: dict[str, dict[str, Any]],
    *,
    now: dt.datetime,
    window_hours: int,
) -> list[dict[str, Any]]:
    rows = benchmark.get("models", {})
    if not isinstance(rows, dict):
        return []

    out: list[dict[str, Any]] = []
    max_age = dt.timedelta(hours=window_hours)
    for tag, row in rows.items():
        if not isinstance(row, dict):
            continue
        if str(row.get("status", "")).strip().lower() != "ok":
            continue
        tag_text = str(tag).strip().lower()
        if not tag_text or ":" not in tag_text:
            continue
        measured_at = parse_iso_utc(str(row.get("test_time", "")))
        if measured_at is None or now - measured_at > max_age:
            continue

        tps_raw = row.get("tokens_per_second")
        tps = float(tps_raw) if isinstance(tps_raw, (int, float)) else None
        catalog_item = catalog_index.get(tag_text)
        source_url = source_url_for(tag_text, catalog_item)
        priority = score_candidate(
            tag=tag_text,
            source="recent_benchmark",
            measured_at=measured_at,
            now=now,
            tokens_per_second=tps,
            catalog_item=catalog_item,
        )
        out.append(
            {
                "tag": tag_text,
                "family": family_from_tag(tag_text),
                "keyword": keyword_for(tag_text, measured=True),
                "slug": f"model-{slugify(tag_text.replace(':', '-'))}-rtx-3090-ollama-benchmark",
                "title": title_for(tag_text),
                "source": "recent_benchmark",
                "priority_score": priority,
                "status": "measured",
                "measured_at": measured_at.isoformat().replace("+00:00", "Z"),
                "tokens_per_second": tps,
                "latency_ms": row.get("latency_ms"),
                "ollama_command": f"ollama run {tag_text}",
                "source_url": source_url,
                "landing": f"/en/models/{slugify(tag_text.replace(':', '-'))}/",
                "content_angle": "Fresh RTX 3090 result; publish while Ollama search demand is warm.",
            }
        )
    return out


def weekly_plan_candidates(
    weekly_plan: dict[str, Any],
    catalog_index: dict[str, dict[str, Any]],
    *,
    now: dt.datetime,
) -> list[dict[str, Any]]:
    tags: set[str] = set()
    for key in ("local_models_sample", "added_targets"):
        value = weekly_plan.get(key, [])
        if not isinstance(value, list):
            continue
        for raw in value:
            text = str(raw or "").strip().lower()
            if ":" in text:
                tags.add(text)
            elif text:
                tags.add(f"{text}:latest")

    out: list[dict[str, Any]] = []
    for tag in sorted(tags):
        catalog_item = catalog_index.get(tag)
        priority = score_candidate(
            tag=tag,
            source="weekly_target_plan",
            measured_at=None,
            now=now,
            tokens_per_second=None,
            catalog_item=catalog_item,
        )
        out.append(
            {
                "tag": tag,
                "family": family_from_tag(tag),
                "keyword": keyword_for(tag, measured=False),
                "slug": f"model-{slugify(tag.replace(':', '-'))}-vram-requirements-rtx-3090",
                "title": title_for(tag),
                "source": "weekly_target_plan",
                "priority_score": priority,
                "status": "pending_measurement",
                "measured_at": "",
                "tokens_per_second": None,
                "latency_ms": None,
                "ollama_command": f"ollama run {tag}",
                "source_url": source_url_for(tag, catalog_item),
                "landing": "/en/models/",
                "content_angle": "Fresh local target; publish a setup and VRAM page, then update after benchmark.",
            }
        )
    return out


def dedupe_rank(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for item in items:
        tag = str(item.get("tag", "")).strip().lower()
        if not tag:
            continue
        existing = best.get(tag)
        if existing is None or int(item.get("priority_score", 0)) > int(existing.get("priority_score", 0)):
            best[tag] = item
    ranked = sorted(best.values(), key=lambda row: int(row.get("priority_score", 0)), reverse=True)
    return ranked[:limit]


def build_watchlist(
    *,
    benchmark_file: Path = BENCHMARK_FILE,
    catalog_file: Path = CATALOG_FILE,
    weekly_target_plan_file: Path = WEEKLY_TARGET_PLAN_FILE,
    window_hours: int = 48,
    limit: int = 20,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    current = now or dt.datetime.now(dt.timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=dt.timezone.utc)
    current = current.astimezone(dt.timezone.utc)

    catalog = load_json(catalog_file, {"items": []})
    catalog_index = catalog_by_tag(catalog if isinstance(catalog, dict) else {"items": []})
    benchmark = load_json(benchmark_file, {"models": {}})
    weekly_plan = load_json(weekly_target_plan_file, {})

    items = benchmark_candidates(
        benchmark if isinstance(benchmark, dict) else {"models": {}},
        catalog_index,
        now=current,
        window_hours=window_hours,
    )
    items.extend(
        weekly_plan_candidates(
            weekly_plan if isinstance(weekly_plan, dict) else {},
            catalog_index,
            now=current,
        )
    )
    ranked = dedupe_rank(items, limit=limit)
    return {
        "updated_at": current.isoformat().replace("+00:00", "Z"),
        "window_hours": window_hours,
        "strategy": "Prioritize new Ollama model pages while RTX 3090 benchmark demand is fresh.",
        "items": ranked,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a fresh Ollama model content watchlist for daily publishing.")
    parser.add_argument("--benchmark-file", default=str(BENCHMARK_FILE))
    parser.add_argument("--catalog-file", default=str(CATALOG_FILE))
    parser.add_argument("--weekly-target-plan-file", default=str(WEEKLY_TARGET_PLAN_FILE))
    parser.add_argument("--output-file", default=str(OUT_FILE))
    parser.add_argument("--window-hours", type=int, default=48)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    payload = build_watchlist(
        benchmark_file=Path(args.benchmark_file),
        catalog_file=Path(args.catalog_file),
        weekly_target_plan_file=Path(args.weekly_target_plan_file),
        window_hours=max(1, args.window_hours),
        limit=max(1, args.limit),
    )
    save_json(Path(args.output_file), payload)
    LOGGER.info("new model watchlist: %s items -> %s", len(payload["items"]), args.output_file)


if __name__ == "__main__":
    main()
