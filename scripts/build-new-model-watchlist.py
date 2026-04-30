#!/usr/bin/env python3
import argparse
import datetime as dt
import html
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_FILE = ROOT / "src" / "data" / "benchmark-results.json"
CATALOG_FILE = ROOT / "src" / "data" / "model-catalog.json"
WEEKLY_TARGET_PLAN_FILE = ROOT / "src" / "data" / "weekly-target-plan.json"
RUNNER_STATUS_FILE = ROOT / "src" / "data" / "runner-status.json"
OUT_FILE = ROOT / "src" / "data" / "new-model-watchlist.json"
LOGGER = configure_logging("build-new-model-watchlist")
OLLAMA_LIBRARY_BASE = "https://ollama.com/library"

NEW_MODEL_FAMILY_WEIGHTS = {
    "qwen3.6": 120,
    "qwen3.5": 116,
    "qwen3-coder": 112,
    "gpt-oss": 110,
    "ministral-3": 108,
    "mistral-small": 106,
    "llama4": 104,
    "magistral": 102,
    "phi4-reasoning": 100,
    "qwen3-vl": 98,
    "gemma3n": 96,
}

EVERGREEN_FAMILIES = {
    "deepseek-r1",
    "gemma3",
    "llama3.3",
    "qwen2.5",
    "qwen2.5-coder",
    "qwq",
}


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


def relative_age_to_days(label: str) -> int | None:
    text = str(label or "").strip().lower()
    match = re.search(r"(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago", text)
    if not match:
        return None
    value = int(match.group(1))
    unit = match.group(2)
    if unit == "minute":
        return 0
    if unit == "hour":
        return 0
    if unit == "day":
        return value
    if unit == "week":
        return value * 7
    if unit == "month":
        return value * 30
    if unit == "year":
        return value * 365
    return None


def html_to_text(raw_html: str) -> str:
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", raw_html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text


def parse_ollama_library_page(family: str, raw_html: str) -> dict[str, Any]:
    text = html_to_text(raw_html)
    compact = re.sub(r"\s+", " ", text)
    updated_match = re.search(r"Downloads\s+Updated\s+([0-9]+\s+(?:minute|hour|day|week|month|year)s?\s+ago)", compact, re.IGNORECASE)
    downloads_match = re.search(r"([0-9]+(?:\.[0-9]+)?[KMB]?)\s+Downloads\s+Updated", compact, re.IGNORECASE)
    updated_label = updated_match.group(1) if updated_match else ""
    downloads = downloads_match.group(1) if downloads_match else ""

    family_text = re.escape(str(family or "").strip().lower())
    tag_ages: dict[str, dict[str, Any]] = {}
    for match in re.finditer(
        rf"({family_text}:[a-z0-9_.\-]+).*?([0-9]+\s+(?:minute|hour|day|week|month|year)s?\s+ago)",
        compact,
        flags=re.IGNORECASE,
    ):
        tag = match.group(1).strip().lower()
        age_label = match.group(2).strip()
        tag_ages[tag] = {"updated_label": age_label, "updated_days": relative_age_to_days(age_label)}

    return {
        "family": str(family or "").strip().lower(),
        "source_url": f"{OLLAMA_LIBRARY_BASE}/{family}",
        "downloads": downloads,
        "updated_label": updated_label,
        "updated_days": relative_age_to_days(updated_label),
        "tag_ages": tag_ages,
    }


def fetch_ollama_library_freshness(family: str, timeout_s: int = 12) -> dict[str, Any]:
    normalized = str(family or "").strip().lower()
    if not normalized:
        return {}
    url = f"{OLLAMA_LIBRARY_BASE}/{normalized}"
    request = urllib.request.Request(url, headers={"User-Agent": "LocalVRAMBot/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except (OSError, urllib.error.URLError) as exc:
        LOGGER.warning("ollama library freshness unavailable family=%s error=%s", normalized, exc)
        return {}
    return parse_ollama_library_page(normalized, raw)


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


def catalog_by_family(catalog: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for item in catalog.get("items", []):
        if not isinstance(item, dict):
            continue
        family = str(item.get("library_id") or family_from_tag(str(item.get("ollama_tag", "")))).strip().lower()
        if not family:
            continue
        out.setdefault(family, []).append(item)
    return out


def is_new_model_family(family: str) -> bool:
    normalized = str(family or "").strip().lower()
    return normalized in NEW_MODEL_FAMILY_WEIGHTS and normalized not in EVERGREEN_FAMILIES


def is_fresh_on_ollama_library(
    family: str,
    tag: str,
    library_freshness: dict[str, dict[str, Any]],
    *,
    max_library_age_days: int,
) -> bool:
    freshness = library_freshness.get(str(family or "").strip().lower())
    if not freshness:
        return is_new_model_family(family)
    tag_age = freshness.get("tag_ages", {}).get(str(tag or "").strip().lower(), {})
    age_days = tag_age.get("updated_days")
    if age_days is None:
        age_days = freshness.get("updated_days")
    return isinstance(age_days, int) and age_days <= max_library_age_days


def benchmark_row_for_tag(benchmark: dict[str, Any], tag: str) -> dict[str, Any] | None:
    rows = benchmark.get("models", {})
    if not isinstance(rows, dict):
        return None
    row = rows.get(str(tag or "").strip().lower())
    return row if isinstance(row, dict) else None


def build_local_inventory_index(weekly_plan: dict[str, Any], runner_status: dict[str, Any]) -> dict[str, Any]:
    tags: set[str] = set()
    families: set[str] = set()

    for raw in weekly_plan.get("local_models_sample", []):
        tag = str(raw or "").strip().lower()
        if not tag:
            continue
        tags.add(tag)
        family = family_from_tag(tag)
        if family:
            families.add(family)
    for raw in weekly_plan.get("local_families", []):
        family = str(raw or "").strip().lower()
        if family:
            families.add(family)

    api_tags = runner_status.get("api", {}).get("tags", {}) if isinstance(runner_status, dict) else {}
    for raw in api_tags.get("sample", []):
        tag = str(raw or "").strip().lower()
        if not tag:
            continue
        tags.add(tag)
        family = family_from_tag(tag)
        if family:
            families.add(family)

    summary = runner_status.get("summary", {}) if isinstance(runner_status, dict) else {}
    for raw in summary.get("required_targets_runnable", []):
        family = str(raw or "").strip().lower()
        if family:
            families.add(family_from_tag(family))

    return {
        "tags": tags,
        "families": families,
        "model_count": int(api_tags.get("model_count", summary.get("model_count", weekly_plan.get("local_model_count", 0))) or 0),
        "sources": ["runner-status.json", "weekly-target-plan.json"],
    }


def local_inventory_status(tag: str, benchmark_row: dict[str, Any] | None, inventory: dict[str, Any]) -> dict[str, Any]:
    tag_text = str(tag or "").strip().lower()
    family = family_from_tag(tag_text)
    tags = inventory.get("tags", set())
    families = inventory.get("families", set())
    source = ""

    if tag_text in tags:
        status = "downloaded"
        source = "runner_api_tags_exact"
    elif benchmark_row:
        status = "downloaded"
        source = "benchmark_results"
    elif family and family in families:
        status = "family_available"
        source = "runner_api_tags_family"
    else:
        status = "not_seen_locally"
        source = "none"

    return {
        "status": status,
        "source": source,
        "model_count": int(inventory.get("model_count", 0) or 0),
    }


def benchmark_status_for_row(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        return {"status": "pending", "measured_at": "", "tokens_per_second": None, "latency_ms": None}
    tps_raw = row.get("tokens_per_second")
    return {
        "status": "measured" if str(row.get("status", "")).strip().lower() == "ok" else "error",
        "measured_at": str(row.get("test_time", "")),
        "tokens_per_second": float(tps_raw) if isinstance(tps_raw, (int, float)) else None,
        "latency_ms": row.get("latency_ms"),
    }


def ollama_freshness_status(freshness: dict[str, Any], max_library_age_days: int) -> str:
    age_days = freshness.get("updated_days")
    if isinstance(age_days, int):
        return "fresh" if age_days <= max_library_age_days else "stale"
    return "inferred"


def traffic_priority_label(priority_score: int, local_status: str, benchmark_status: str) -> str:
    if priority_score >= 90 and local_status in {"downloaded", "family_available", "measured_recently"} and benchmark_status == "measured":
        return "publish_now"
    if priority_score >= 80 and local_status in {"downloaded", "family_available", "measured_recently"}:
        return "benchmark_then_publish"
    if priority_score >= 70:
        return "watch"
    return "backlog"


def measured_tags_for_family(benchmark: dict[str, Any], family: str) -> list[tuple[str, dict[str, Any]]]:
    rows = benchmark.get("models", {})
    if not isinstance(rows, dict):
        return []
    normalized = str(family or "").strip().lower()
    out: list[tuple[str, dict[str, Any]]] = []
    for tag, row in rows.items():
        tag_text = str(tag or "").strip().lower()
        if family_from_tag(tag_text) != normalized:
            continue
        if not isinstance(row, dict) or str(row.get("status", "")).strip().lower() != "ok":
            continue
        out.append((tag_text, row))
    return out


def pick_family_tag(
    family: str,
    catalog_family_index: dict[str, list[dict[str, Any]]],
    benchmark: dict[str, Any],
) -> tuple[str, dict[str, Any] | None, dict[str, Any] | None]:
    measured = measured_tags_for_family(benchmark, family)
    if measured:
        measured.sort(
            key=lambda pair: (
                14 <= params_from_tag(pair[0]) <= 35,
                float(pair[1].get("tokens_per_second", 0) or 0),
            ),
            reverse=True,
        )
        tag, row = measured[0]
        catalog_item = next(
            (
                item
                for item in catalog_family_index.get(family, [])
                if str(item.get("ollama_tag", "")).strip().lower() == tag
            ),
            None,
        )
        return tag, catalog_item, row

    catalog_items = catalog_family_index.get(family, [])
    if catalog_items:
        ranked = sorted(
            catalog_items,
            key=lambda item: (
                14 <= float(item.get("params_b", params_from_tag(str(item.get("ollama_tag", "")))) or 0) <= 35,
                str(item.get("quantization", "")).upper() == "Q4",
                -abs(float(item.get("params_b", 7) or 7) - 24),
            ),
            reverse=True,
        )
        tag = str(ranked[0].get("ollama_tag", "")).strip().lower()
        return tag, ranked[0], None

    return f"{family}:latest", None, None


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
    family_weight = NEW_MODEL_FAMILY_WEIGHTS.get(family, 0)

    if source == "new_family_benchmark":
        score += 32
    elif source == "new_family_priority":
        score += 28
    elif source == "weekly_target_plan":
        score += 18

    score += min(24, max(0, family_weight - 92))

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

    if scenario in {"coding", "reasoning", "multimodal"}:
        score += 8

    return min(score, 100)


def benchmark_candidates(
    benchmark: dict[str, Any],
    catalog_index: dict[str, dict[str, Any]],
    library_freshness: dict[str, dict[str, Any]] | None = None,
    local_inventory: dict[str, Any] | None = None,
    *,
    now: dt.datetime,
    window_hours: int,
    max_library_age_days: int = 14,
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
        family = family_from_tag(tag_text)
        if not is_new_model_family(family):
            continue
        freshness = library_freshness or {}
        if not is_fresh_on_ollama_library(family, tag_text, freshness, max_library_age_days=max_library_age_days):
            continue
        measured_at = parse_iso_utc(str(row.get("test_time", "")))
        if measured_at is None or now - measured_at > max_age:
            continue

        tps_raw = row.get("tokens_per_second")
        tps = float(tps_raw) if isinstance(tps_raw, (int, float)) else None
        catalog_item = catalog_index.get(tag_text)
        family_freshness = freshness.get(family, {})
        source_url = source_url_for(tag_text, catalog_item)
        priority = score_candidate(
            tag=tag_text,
            source="new_family_benchmark",
            measured_at=measured_at,
            now=now,
            tokens_per_second=tps,
            catalog_item=catalog_item,
        )
        out.append(
            {
                "tag": tag_text,
                "family": family,
                "keyword": keyword_for(tag_text, measured=True),
                "slug": f"model-{slugify(tag_text.replace(':', '-'))}-rtx-3090-ollama-benchmark",
                "title": title_for(tag_text),
                "source": "new_family_benchmark",
                "priority_score": priority,
                "status": "measured",
                "measured_at": measured_at.isoformat().replace("+00:00", "Z"),
                "tokens_per_second": tps,
                "latency_ms": row.get("latency_ms"),
                "ollama_command": f"ollama run {tag_text}",
                "source_url": source_url,
                "ollama_updated_label": freshness.get(family, {}).get("updated_label", ""),
                "ollama_updated_days": freshness.get(family, {}).get("updated_days"),
                "ollama_downloads": freshness.get(family, {}).get("downloads", ""),
                "ollama_library_freshness": {
                    "status": ollama_freshness_status(family_freshness, max_library_age_days),
                    "updated_label": family_freshness.get("updated_label", ""),
                    "updated_days": family_freshness.get("updated_days"),
                    "downloads": family_freshness.get("downloads", ""),
                    "source_url": source_url,
                },
                "local_inventory_status": local_inventory_status(tag_text, row, local_inventory or {}),
                "benchmark_status": benchmark_status_for_row(row),
                "traffic_priority": traffic_priority_label(
                    priority,
                    local_inventory_status(tag_text, row, local_inventory or {})["status"],
                    benchmark_status_for_row(row)["status"],
                ),
                "landing": f"/en/models/{slugify(tag_text.replace(':', '-'))}/",
                "content_angle": "Fresh RTX 3090 result; publish while Ollama search demand is warm.",
            }
        )
    return out


def weekly_plan_candidates(
    weekly_plan: dict[str, Any],
    catalog_index: dict[str, dict[str, Any]],
    catalog_family_index: dict[str, list[dict[str, Any]]],
    benchmark: dict[str, Any],
    library_freshness: dict[str, dict[str, Any]] | None = None,
    local_inventory: dict[str, Any] | None = None,
    *,
    now: dt.datetime,
    max_library_age_days: int = 14,
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

    for raw_family in weekly_plan.get("priority_families", []):
        family = str(raw_family or "").strip().lower()
        if not is_new_model_family(family):
            continue
        tag, _, _ = pick_family_tag(family, catalog_family_index, benchmark)
        if tag:
            tags.add(tag)

    out: list[dict[str, Any]] = []
    freshness = library_freshness or {}
    for tag in sorted(tags):
        family = family_from_tag(tag)
        if not is_new_model_family(family):
            continue
        if not is_fresh_on_ollama_library(family, tag, freshness, max_library_age_days=max_library_age_days):
            continue
        catalog_item = catalog_index.get(tag)
        family_freshness = freshness.get(family, {})
        row = benchmark_row_for_tag(benchmark, tag)
        measured_at = parse_iso_utc(str(row.get("test_time", ""))) if row else None
        tps_raw = row.get("tokens_per_second") if row else None
        tps = float(tps_raw) if isinstance(tps_raw, (int, float)) else None
        source = "new_family_benchmark" if row else "new_family_priority"
        status = "measured" if row else "pending_measurement"
        priority = score_candidate(
            tag=tag,
            source=source,
            measured_at=measured_at,
            now=now,
            tokens_per_second=tps,
            catalog_item=catalog_item,
        )
        out.append(
            {
                "tag": tag,
                "family": family,
                "keyword": keyword_for(tag, measured=row is not None),
                "slug": (
                    f"model-{slugify(tag.replace(':', '-'))}-rtx-3090-ollama-benchmark"
                    if row
                    else f"model-{slugify(tag.replace(':', '-'))}-vram-requirements-rtx-3090"
                ),
                "title": title_for(tag),
                "source": source,
                "priority_score": priority,
                "status": status,
                "measured_at": measured_at.isoformat().replace("+00:00", "Z") if measured_at else "",
                "tokens_per_second": tps,
                "latency_ms": row.get("latency_ms") if row else None,
                "ollama_command": f"ollama run {tag}",
                "source_url": source_url_for(tag, catalog_item),
                "ollama_updated_label": freshness.get(family, {}).get("updated_label", ""),
                "ollama_updated_days": freshness.get(family, {}).get("updated_days"),
                "ollama_downloads": freshness.get(family, {}).get("downloads", ""),
                "ollama_library_freshness": {
                    "status": ollama_freshness_status(family_freshness, max_library_age_days),
                    "updated_label": family_freshness.get("updated_label", ""),
                    "updated_days": family_freshness.get("updated_days"),
                    "downloads": family_freshness.get("downloads", ""),
                    "source_url": source_url_for(tag, catalog_item),
                },
                "local_inventory_status": local_inventory_status(tag, row, local_inventory or {}),
                "benchmark_status": benchmark_status_for_row(row),
                "traffic_priority": traffic_priority_label(
                    priority,
                    local_inventory_status(tag, row, local_inventory or {})["status"],
                    benchmark_status_for_row(row)["status"],
                ),
                "landing": f"/en/models/{slugify(tag.replace(':', '-'))}/" if row else "/en/models/",
                "content_angle": (
                    "New model family with RTX 3090 evidence; publish while launch-search demand is warm."
                    if row
                    else "New model family target; publish setup and VRAM intent, then update after benchmark."
                ),
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
    runner_status_file: Path = RUNNER_STATUS_FILE,
    window_hours: int = 48,
    max_library_age_days: int = 14,
    fetch_library_freshness: bool = True,
    limit: int = 20,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    current = now or dt.datetime.now(dt.timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=dt.timezone.utc)
    current = current.astimezone(dt.timezone.utc)

    catalog = load_json(catalog_file, {"items": []})
    catalog_index = catalog_by_tag(catalog if isinstance(catalog, dict) else {"items": []})
    catalog_family_index = catalog_by_family(catalog if isinstance(catalog, dict) else {"items": []})
    benchmark = load_json(benchmark_file, {"models": {}})
    weekly_plan = load_json(weekly_target_plan_file, {})
    runner_status = load_json(runner_status_file, {})
    local_inventory = build_local_inventory_index(
        weekly_plan if isinstance(weekly_plan, dict) else {},
        runner_status if isinstance(runner_status, dict) else {},
    )

    families: set[str] = set()
    if isinstance(benchmark, dict):
        rows = benchmark.get("models", {})
        if isinstance(rows, dict):
            families.update(family_from_tag(str(tag)) for tag in rows.keys())
    if isinstance(weekly_plan, dict):
        families.update(str(family or "").strip().lower() for family in weekly_plan.get("priority_families", []))
    families = {family for family in families if is_new_model_family(family)}
    library_freshness = {
        family: fetch_ollama_library_freshness(family)
        for family in sorted(families)
        if fetch_library_freshness
    }

    items = benchmark_candidates(
        benchmark if isinstance(benchmark, dict) else {"models": {}},
        catalog_index,
        library_freshness,
        local_inventory,
        now=current,
        window_hours=window_hours,
        max_library_age_days=max_library_age_days,
    )
    items.extend(
        weekly_plan_candidates(
            weekly_plan if isinstance(weekly_plan, dict) else {},
            catalog_index,
            catalog_family_index,
            benchmark if isinstance(benchmark, dict) else {"models": {}},
            library_freshness,
            local_inventory,
            now=current,
            max_library_age_days=max_library_age_days,
        )
    )
    ranked = dedupe_rank(items, limit=limit)
    return {
        "updated_at": current.isoformat().replace("+00:00", "Z"),
        "window_hours": window_hours,
        "max_library_age_days": max_library_age_days,
        "strategy": "Prioritize new Ollama model families; use RTX 3090 benchmark recency as evidence, not as proof of model freshness.",
        "local_inventory": {
            "model_count": int(local_inventory.get("model_count", 0) or 0),
            "source": "runner /api/tags via runner-status.json and weekly-target-plan.json",
        },
        "items": ranked,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a fresh Ollama model content watchlist for daily publishing.")
    parser.add_argument("--benchmark-file", default=str(BENCHMARK_FILE))
    parser.add_argument("--catalog-file", default=str(CATALOG_FILE))
    parser.add_argument("--weekly-target-plan-file", default=str(WEEKLY_TARGET_PLAN_FILE))
    parser.add_argument("--runner-status-file", default=str(RUNNER_STATUS_FILE))
    parser.add_argument("--output-file", default=str(OUT_FILE))
    parser.add_argument("--window-hours", type=int, default=48)
    parser.add_argument("--max-library-age-days", type=int, default=14)
    parser.add_argument("--no-fetch-library-freshness", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    payload = build_watchlist(
        benchmark_file=Path(args.benchmark_file),
        catalog_file=Path(args.catalog_file),
        weekly_target_plan_file=Path(args.weekly_target_plan_file),
        runner_status_file=Path(args.runner_status_file),
        window_hours=max(1, args.window_hours),
        max_library_age_days=max(1, args.max_library_age_days),
        fetch_library_freshness=not args.no_fetch_library_freshness,
        limit=max(1, args.limit),
    )
    save_json(Path(args.output_file), payload)
    LOGGER.info("new model watchlist: %s items -> %s", len(payload["items"]), args.output_file)


if __name__ == "__main__":
    main()
