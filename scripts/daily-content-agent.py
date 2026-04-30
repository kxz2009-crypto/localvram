#!/usr/bin/env python3
import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
OPPORTUNITY_FILE = ROOT / "src" / "data" / "content-opportunities.json"
SC_FILE = ROOT / "src" / "data" / "search-console-keywords.json"
UPDATES_FILE = ROOT / "src" / "data" / "daily-updates.json"
DRAFT_INDEX_FILE = ROOT / "src" / "data" / "daily-content-drafts.json"
BENCHMARK_FILE = ROOT / "src" / "data" / "benchmark-results.json"
NEW_MODEL_WATCHLIST_FILE = ROOT / "src" / "data" / "new-model-watchlist.json"
AFFILIATE_LINKS_FILE = ROOT / "src" / "data" / "affiliate-links.json"
PUBLISH_LOG_FILE = ROOT / "src" / "data" / "content-publish-log.json"
BLOG_DIR = ROOT / "src" / "content" / "blog"
QUEUE_DIR = ROOT / "content-queue"
LOGGER = configure_logging("daily-content-agent")
MODEL_TAG_RE = re.compile(r"\b([a-z0-9][a-z0-9.\-_]*:[a-z0-9][a-z0-9.\-_]*)\b", re.IGNORECASE)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return cleaned or "untitled"


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text.strip()
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return {}, text.strip()
    header = parts[0][4:]
    body = parts[1].strip()
    out: dict[str, str] = {}
    for raw in header.splitlines():
        line = raw.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        k = key.strip()
        v = value.strip()
        if v.startswith('"') and v.endswith('"') and len(v) >= 2:
            v = v[1:-1]
        out[k] = v
    return out, body


def dump_frontmatter(frontmatter: dict[str, str]) -> str:
    lines: list[str] = []
    for key, value in frontmatter.items():
        raw = str(value)
        if re.search(r"[\s:#]", raw) or raw == "":
            escaped = raw.replace("\\", "\\\\").replace('"', '\\"')
            raw = f'"{escaped}"'
        lines.append(f"{key}: {raw}")
    return "---\n" + "\n".join(lines) + "\n---\n"


def archive_stale_queue_drafts(queue_day_dir: Path, marker: str) -> None:
    for stale_file in queue_day_dir.glob("*.md"):
        try:
            raw = stale_file.read_text(encoding="utf-8-sig")
            frontmatter, body = parse_frontmatter(raw)
            if not frontmatter:
                frontmatter = {"title": stale_file.stem}
            frontmatter["status"] = "rejected_manual"
            frontmatter["reviewed_at"] = marker
            content = f"{dump_frontmatter(frontmatter)}\n{body.strip()}\n"
            stale_file.write_text(content, encoding="utf-8")
        except OSError:
            # Stale queue files should not break generation.
            continue


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


def topic_key(item: dict[str, Any]) -> str:
    keyword = slugify(str(item.get("keyword", "")).strip())
    if keyword and keyword != "untitled":
        return keyword
    slug = slugify(str(item.get("slug", "")).strip())
    if slug and slug != "untitled":
        return slug
    return ""


def model_key_from_tag(value: str) -> str:
    return slugify(str(value or "").strip().replace(":", "-"))


def model_key_from_text(value: str) -> str:
    text = str(value or "")
    match = MODEL_TAG_RE.search(text)
    if match:
        return model_key_from_tag(match.group(1))
    slug = slugify(text)
    for pattern in (
        r"^model-(?P<model>.+?)-rtx-3090-ollama-benchmark$",
        r"^model-(?P<model>.+?)-local-benchmark$",
        r"^model-(?P<model>.+?)-vram-requirements-rtx-3090$",
    ):
        m = re.match(pattern, slug)
        if m:
            return slugify(m.group("model"))
    return ""


def date_from_frontmatter(value: str) -> dt.date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return dt.date.fromisoformat(raw[:10])
    except ValueError:
        return None


def collect_blocked_topics(today: dt.date, lookback_days: int = 30) -> tuple[set[str], set[str], set[str]]:
    blocked_slugs: set[str] = set()
    blocked_topics: set[str] = set()
    blocked_model_keys: set[str] = set()
    threshold = today - dt.timedelta(days=max(1, int(lookback_days)))

    if BLOG_DIR.exists():
        for post in BLOG_DIR.glob("*.md"):
            blocked_slugs.add(post.stem.strip().lower())
            raw = post.read_text(encoding="utf-8-sig")
            frontmatter, _ = parse_frontmatter(raw)
            k = slugify(str(frontmatter.get("keyword", "")).strip())
            if k and k != "untitled":
                blocked_topics.add(k)
            pub_date = date_from_frontmatter(frontmatter.get("pubDate", "") or frontmatter.get("date", ""))
            if pub_date is None or pub_date >= threshold:
                model_from_slug = model_key_from_text(post.stem)
                if model_from_slug:
                    blocked_model_keys.add(model_from_slug)
                model_from_meta = model_key_from_tag(str(frontmatter.get("model_tag", "")).strip())
                if model_from_meta and model_from_meta != "untitled":
                    blocked_model_keys.add(model_from_meta)
                model_from_keyword = model_key_from_text(str(frontmatter.get("keyword", "")).strip())
                if model_from_keyword:
                    blocked_model_keys.add(model_from_keyword)

    publish_log = load_json(PUBLISH_LOG_FILE, {"history": []})
    for run in publish_log.get("history", []):
        if not isinstance(run, dict):
            continue
        run_date = date_from_frontmatter(run.get("queue_date", "") or run.get("run_at", ""))
        model_log_in_window = run_date is None or run_date >= threshold
        for item in run.get("published", []):
            if not isinstance(item, dict):
                continue
            s = slugify(str(item.get("slug", "")).strip())
            if s and s != "untitled":
                blocked_slugs.add(s)
            if model_log_in_window and s and s != "untitled":
                model_from_slug = model_key_from_text(s)
                if model_from_slug:
                    blocked_model_keys.add(model_from_slug)
            t = slugify(str(item.get("topic_key", "")).strip())
            if t and t != "untitled":
                blocked_topics.add(t)
            if model_log_in_window:
                model_from_meta = model_key_from_tag(str(item.get("model_tag", "")).strip())
                if model_from_meta and model_from_meta != "untitled":
                    blocked_model_keys.add(model_from_meta)

    draft_index = load_json(DRAFT_INDEX_FILE, {"items": []})
    for item in draft_index.get("items", []):
        if not isinstance(item, dict):
            continue
        row_date = str(item.get("date", "")).strip()
        try:
            parsed_date = dt.date.fromisoformat(row_date)
        except ValueError:
            continue
        if parsed_date < threshold:
            continue
        s = slugify(str(item.get("slug", "")).strip())
        if s and s != "untitled":
            blocked_slugs.add(s)
            model_from_slug = model_key_from_text(s)
            if model_from_slug:
                blocked_model_keys.add(model_from_slug)
        t = topic_key(item)
        if t:
            blocked_topics.add(t)
        model_from_meta = model_key_from_tag(str(item.get("model_tag", "")).strip())
        if model_from_meta and model_from_meta != "untitled":
            blocked_model_keys.add(model_from_meta)

    return blocked_slugs, blocked_topics, blocked_model_keys


def score(item: dict[str, Any]) -> int:
    return (
        int(item.get("search_intent_score", 0))
        * int(item.get("commercial_intent_score", 0))
        * int(item.get("freshness_gap_score", 0))
    )


def score_with_boost(item: dict[str, Any]) -> int:
    base = score(item)
    click_boost = int(item.get("clicks", 0))
    ctr_boost = int(float(item.get("ctr", 0)) * 100)
    return base + click_boost + ctr_boost


def candidate_from_sc(item: dict[str, Any]) -> dict[str, Any]:
    landing = str(item.get("landing", "/")).strip()
    keyword = str(item.get("keyword", item.get("query", ""))).strip()
    derived_slug = slugify(landing.strip("/") or keyword)
    return {
        "slug": derived_slug,
        "keyword": keyword,
        "landing": landing,
        "search_intent_score": min(10, max(1, 11 - int(float(item.get("position", 10))))),
        "commercial_intent_score": min(10, max(1, int(item.get("clicks", 0) / 3) + 1)),
        "freshness_gap_score": min(10, max(1, int(item.get("impressions", 0) / 80))),
        "clicks": int(item.get("clicks", 0)),
        "ctr": float(item.get("ctr", 0)),
        "source": "search_console",
    }


def candidate_from_new_model_watchlist(item: dict[str, Any]) -> dict[str, Any]:
    tag = str(item.get("tag", "")).strip()
    keyword = str(item.get("keyword", "")).strip() or f"{tag} rtx 3090 ollama benchmark"
    try:
        raw_priority = int(item.get("priority_score", 70))
    except (TypeError, ValueError):
        raw_priority = 70
    priority = min(10, max(7, raw_priority // 10))
    return {
        "slug": str(item.get("slug", "")).strip() or f"model-{slugify(tag.replace(':', '-'))}-rtx-3090-ollama-benchmark",
        "keyword": keyword,
        "landing": str(item.get("landing", "/en/models/")).strip() or "/en/models/",
        "search_intent_score": priority,
        "commercial_intent_score": min(10, priority + 1),
        "freshness_gap_score": 10,
        "clicks": 0,
        "ctr": 0.0,
        "source": "new_model_watchlist",
        "tag": tag,
        "model_tag": tag,
        "model_key": model_key_from_tag(tag),
        "watchlist_priority_score": raw_priority,
    }


def dedupe_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = slugify(item.get("slug") or item.get("keyword") or "")
        if key in seen:
            continue
        seen.add(key)
        item["slug"] = key
        out.append(item)
    return out


def filter_fresh_candidates(
    items: list[dict[str, Any]],
    *,
    blocked_slugs: set[str],
    blocked_topics: set[str],
    blocked_model_keys: set[str] | None = None,
    min_score: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    model_keys = blocked_model_keys if blocked_model_keys is not None else set()
    for item in sorted(dedupe_candidates(items), key=score_with_boost, reverse=True):
        current_score = score_with_boost(item)
        if current_score < min_score:
            continue
        s = slugify(item.get("slug") or item.get("keyword") or "")
        t = topic_key(item)
        model_key = str(item.get("model_key") or model_key_from_tag(str(item.get("model_tag", ""))) or model_key_from_text(str(item.get("keyword", ""))) or model_key_from_text(s)).strip()
        if s in blocked_slugs:
            continue
        if t and t in blocked_topics:
            continue
        if model_key and model_key in model_keys:
            continue
        blocked_slugs.add(s)
        if t:
            blocked_topics.add(t)
        if model_key:
            model_keys.add(model_key)
        selected.append(item)
    return selected


def pick_measured_highlights(max_count: int = 3) -> list[dict[str, Any]]:
    payload = load_json(BENCHMARK_FILE, {"models": {}})
    rows = payload.get("models", {})
    if not isinstance(rows, dict):
        return []
    measured = []
    for tag, row in rows.items():
        if not isinstance(row, dict):
            continue
        if row.get("status") != "ok":
            continue
        tps = row.get("tokens_per_second")
        if not isinstance(tps, (int, float)):
            continue
        measured.append(
            {
                "tag": str(tag),
                "tokens_per_second": float(tps),
                "latency_ms": float(row.get("latency_ms", 0)),
                "test_time": str(row.get("test_time", "")),
            }
        )
    measured.sort(key=lambda x: x["tokens_per_second"], reverse=True)
    return measured[:max_count]


def build_benchmark_fallback_candidates(max_count: int = 120) -> list[dict[str, Any]]:
    payload = load_json(BENCHMARK_FILE, {"models": {}})
    rows = payload.get("models", {})
    if not isinstance(rows, dict):
        return []

    now_utc = dt.datetime.now(dt.timezone.utc)
    candidates: list[dict[str, Any]] = []
    for tag, row in rows.items():
        if not isinstance(row, dict):
            continue
        if str(row.get("status", "")).strip().lower() != "ok":
            continue
        tps = row.get("tokens_per_second")
        if not isinstance(tps, (int, float)):
            continue

        tested_at = parse_iso_utc(str(row.get("test_time", "")))
        age_days = 14
        if tested_at is not None:
            age_days = max(0, int((now_utc - tested_at).total_seconds() // 86400))
        freshness_gap = max(3, 10 - min(age_days, 7))
        search_intent = min(10, max(4, int(float(tps) // 15) + 3))
        commercial_intent = min(10, max(4, int(float(tps) // 20) + 4))

        tag_text = str(tag).strip()
        slug = f"model-{slugify(tag_text.replace(':', '-'))}-local-benchmark"
        keyword = f"{tag_text} local inference benchmark"
        candidates.append(
            {
                "slug": slug,
                "keyword": keyword,
                "landing": "/en/models/",
                "search_intent_score": search_intent,
                "commercial_intent_score": commercial_intent,
                "freshness_gap_score": freshness_gap,
                "clicks": 0,
                "ctr": 0.0,
                "source": "benchmark_fallback",
            }
        )

    candidates.sort(key=score_with_boost, reverse=True)
    return candidates[:max_count]


def infer_content_intent(keyword: str, slug: str = "") -> str:
    text = f"{keyword} {slug}".lower()
    if any(token in text for token in ("error", "fix", "oom", "cuda", "failed", "timeout")):
        return "troubleshooting"
    if any(token in text for token in ("cost", "price", "roi", "rent", "cloud", "billing")):
        return "cost"
    if any(token in text for token in ("gpu", "vram", "rtx", "hardware", "memory")):
        return "hardware"
    if any(token in text for token in ("benchmark", "tok/s", "latency", "throughput")):
        return "benchmark"
    return "guide"


def normalize_title_topic(keyword: str) -> str:
    text = str(keyword or "").strip().rstrip("?")
    if not text:
        return "local llm deployment"
    text = re.sub(
        r"\blocal inference benchmark(?:\s+update)?\b",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bpractical guide\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" -:")
    return text or str(keyword or "").strip()


def humanize_topic(topic: str) -> str:
    text = re.sub(r"[_/]+", " ", str(topic or "").strip())
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return "Local LLM Deployment"

    words: list[str] = []
    for token in text.split(" "):
        normalized = token.lower().strip(":,")
        acronym_map = {
            "rtx": "RTX",
            "gpu": "GPU",
            "vram": "VRAM",
            "llm": "LLM",
            "rag": "RAG",
            "cuda": "CUDA",
            "oom": "OOM",
            "q4": "Q4",
            "q5": "Q5",
            "q8": "Q8",
            "vllm": "vLLM",
        }
        if normalized in acronym_map:
            words.append(acronym_map[normalized])
            continue
        if any(ch.isdigit() for ch in token):
            token = re.sub(r"(\d+)b\b", r"\1B", token, flags=re.IGNORECASE)
            words.append(token)
            continue
        words.append(token.capitalize() if token.islower() else token)
    return " ".join(words)


def stable_template_index(seed: str, size: int) -> int:
    if size <= 1:
        return 0
    total = sum(ord(ch) for ch in str(seed or ""))
    return total % size


def build_title(keyword: str, date_iso: str) -> str:
    if keyword:
        base = keyword.strip().rstrip("?")
    else:
        base = "local llm deployment"
    year = date_iso.split("-")[0]
    intent = infer_content_intent(base)
    topic = humanize_topic(normalize_title_topic(base))

    templates: dict[str, list[str]] = {
        "benchmark": [
            "{topic} Local Benchmark: Throughput, Latency, and VRAM ({year})",
            "{topic} Benchmark Results: Local GPU Throughput Breakdown ({year})",
            "{topic}: Local Inference Performance Report ({year})",
        ],
        "hardware": [
            "{topic}: GPU and VRAM Sizing Guide ({year})",
            "{topic}: Hardware Decision Matrix for Local LLM ({year})",
            "{topic}: Practical GPU Selection for Stable Local Inference ({year})",
        ],
        "cost": [
            "{topic}: Local vs Cloud Cost Breakdown ({year})",
            "{topic}: Cloud Rental vs Self-Host Decision Model ({year})",
            "{topic}: Cost, Throughput, and ROI Analysis ({year})",
        ],
        "troubleshooting": [
            "{topic}: Root Cause Checklist and Reliable Fixes ({year})",
            "{topic}: Fast Triage Playbook for Local LLM Failures ({year})",
            "{topic}: Error-to-Fix Handbook ({year})",
        ],
        "guide": [
            "{topic}: Step-by-Step Deployment Workflow ({year})",
            "{topic}: Setup, Validation, and Scaling Playbook ({year})",
            "{topic}: Practical Local LLM Implementation Guide ({year})",
        ],
    }
    pool = templates.get(intent, templates["guide"])
    idx = stable_template_index(f"{base}:{date_iso}", len(pool))
    return pool[idx].format(topic=topic, year=year)


def draft_markdown(
    *,
    title: str,
    keyword: str,
    score_value: int,
    source: str,
    measured: list[dict[str, Any]],
    links: dict[str, str],
    landing: str,
    date_iso: str,
    model_tag: str = "",
) -> str:
    measured_lines = []
    for row in measured:
        measured_lines.append(
            f"- `{row['tag']}`: {row['tokens_per_second']:.1f} tok/s (latency {row['latency_ms']:.0f} ms, test {row['test_time']})"
        )
    measured_block = "\n".join(measured_lines) if measured_lines else "- No verified measurements available yet."

    runpod = links.get("runpod", "/go/runpod")
    vast = links.get("vast", "/go/vast")
    hardware = "/en/affiliate/hardware-upgrade/"
    tool = "/en/tools/vram-calculator/"
    landing_ref = landing if landing else "/en/models/"
    intent = infer_content_intent(keyword)
    intent_actions = {
        "benchmark": "The key evidence is throughput, latency, and whether the result is measured or still estimated.",
        "hardware": "The key decision is whether your VRAM tier has enough headroom for the model and context window.",
        "cost": "The key decision is whether local power and hardware time beat cloud rental for your weekly usage.",
        "troubleshooting": "The key decision is which failure symptom to fix first before changing hardware.",
        "guide": "The key decision is whether the setup path is reproducible enough for daily use.",
    }
    primary_action = intent_actions.get(intent, intent_actions["guide"])
    topic = humanize_topic(normalize_title_topic(keyword))
    detected_model_tag = str(model_tag or "").strip()
    model_match = re.search(r"([a-z0-9][a-z0-9.\-_]*:[a-z0-9][a-z0-9.\-_]*)", keyword, flags=re.IGNORECASE)
    if not detected_model_tag and model_match:
        detected_model_tag = model_match.group(1)
    run_command = f"ollama run {detected_model_tag}" if detected_model_tag else "ollama run <model-tag>"
    model_line = (
        f"The model tag to validate first is `{detected_model_tag}`."
        if detected_model_tag
        else "Start from the exact Ollama tag named in the query or model page before testing variants."
    )
    model_frontmatter = f'model_tag: "{detected_model_tag}"\n' if detected_model_tag else ""

    return f"""---
title: "{title}"
date: {date_iso}
keyword: "{keyword}"
{model_frontmatter}score: {score_value}
source: {source}
status: draft
---

## Fast verdict

This page targets "{keyword}" for readers who need a concrete local-vs-cloud decision, not a generic model announcement. The useful answer is whether {topic} is worth testing on a 24GB RTX 3090, what failure boundary to watch, and what to do if the model misses the target.

For the first pass, treat the RTX 3090 as the practical baseline. If the model is stable at the required context length with enough VRAM headroom, keep it local. If throughput or p95 latency misses the workload target, use local as the validation baseline and burst to cloud for peak jobs.

## Measured anchor data

{measured_block}

## Ollama setup path

{model_line}

```bash
{run_command}
```

After the first run, capture three facts before changing hardware: tokens per second, first-response latency, and whether the model stays inside VRAM at the intended context length. A fast short prompt is not enough; use a representative prompt from the real workload.

## RTX 3090 decision matrix

| Result on 24GB RTX 3090 | Recommendation |
| --- | --- |
| Fits VRAM with headroom and meets latency target | Run local first; use cloud only for bursts. |
| Fits but latency is too high | Keep local for testing, batch/offload heavy jobs to cloud. |
| OOM, retry spikes, or unstable context | Step down quantization, reduce context, or move to larger VRAM. |
| Cloud-only model size | Publish the page as a cloud fallback guide, not a local promise. |

## How to interpret the result

{primary_action} A model is a good local candidate only when it fits VRAM with headroom, stays stable at the intended context length, and meets the latency target for the workload. If any of those fail, the right answer is usually to reduce context, step down quantization, or use cloud capacity for the heavy path.

## Who should try it

- RTX 3090 owners deciding whether to download this model tonight.
- Developers comparing a fresh Ollama model against their current coding or RAG baseline.
- Operators who want a local validation run before spending RunPod or Vast credits.

## Who should skip it

- 8GB and 12GB GPU users unless a smaller quantized variant exists.
- Teams that need production p95 latency before a sustained benchmark has been verified.
- Anyone running long-context or concurrent workloads without checking VRAM headroom first.

## New-model timing

The traffic window is strongest in the first 24-48 hours after an Ollama model appears or becomes popular. If benchmark data is still pending, treat this as an estimated setup page and come back after the RTX 3090 runner verifies throughput and latency.

## Next actions

- Estimate VRAM fit: {tool}
- Related landing: {landing_ref}
- Local hardware path: {hardware}
- Cloud fallback: {runpod} and {vast}

Affiliate Disclosure: This post may include affiliate links. LocalVRAM may earn a commission at no extra cost.
"""


def main() -> None:
    max_drafts = max(1, int(os.getenv("LV_CONTENT_DRAFT_COUNT", "3")))
    min_candidate_score = max(0, int(os.getenv("LV_CONTENT_AUTO_PUBLISH_MIN_SCORE", "120")))
    today = dt.date.today()
    today_iso = today.isoformat()
    blocked_slugs, blocked_topics, blocked_model_keys = collect_blocked_topics(today, lookback_days=30)

    opportunities = load_json(OPPORTUNITY_FILE, {"items": []})
    ranked = sorted(opportunities.get("items", []), key=score, reverse=True)
    seeded = [{**row, "source": "opportunity"} for row in ranked]

    sc_payload = load_json(SC_FILE, {"items": []})
    sc_rows = [candidate_from_sc(item) for item in sc_payload.get("items", [])]
    sc_ranked = sorted(sc_rows, key=score_with_boost, reverse=True)

    watchlist_payload = load_json(NEW_MODEL_WATCHLIST_FILE, {"items": []})
    watchlist_rows = [
        candidate_from_new_model_watchlist(item)
        for item in watchlist_payload.get("items", [])
        if isinstance(item, dict) and str(item.get("tag", "")).strip()
    ]
    watchlist_ranked = sorted(watchlist_rows, key=score_with_boost, reverse=True)

    primary = filter_fresh_candidates(
        watchlist_ranked + seeded + sc_ranked,
        blocked_slugs=blocked_slugs,
        blocked_topics=blocked_topics,
        blocked_model_keys=blocked_model_keys,
        min_score=min_candidate_score,
    )
    selected = primary[:max_drafts]
    if len(selected) < max_drafts:
        fallback = filter_fresh_candidates(
            build_benchmark_fallback_candidates(max_count=200),
            blocked_slugs=blocked_slugs,
            blocked_topics=blocked_topics,
            blocked_model_keys=blocked_model_keys,
            min_score=min_candidate_score,
        )
        selected.extend(fallback[: max_drafts - len(selected)])

    links = load_json(AFFILIATE_LINKS_FILE, {"runpod": "/go/runpod", "vast": "/go/vast"})
    measured = pick_measured_highlights(max_count=3)

    queue_day_dir = QUEUE_DIR / today_iso
    queue_day_dir.mkdir(parents=True, exist_ok=True)
    archive_stale_queue_drafts(queue_day_dir, marker=f"{today_iso}T00:00:00Z")

    draft_records = []
    for idx, item in enumerate(selected, start=1):
        slug = slugify(item.get("slug") or item.get("keyword") or f"draft-{idx}")[:80]
        title = build_title(str(item.get("keyword", "")).strip(), today_iso)
        draft_text = draft_markdown(
            title=title,
            keyword=str(item.get("keyword", "")).strip(),
            score_value=score_with_boost(item),
            source=str(item.get("source", "unknown")),
            measured=measured,
            links=links,
            landing=str(item.get("landing", "")).strip(),
            date_iso=today_iso,
            model_tag=str(item.get("model_tag", item.get("tag", ""))).strip(),
        )
        draft_path = queue_day_dir / f"{idx:02d}-{slug}.md"
        draft_path.write_text(draft_text, encoding="utf-8")
        draft_records.append(
            {
                "date": today_iso,
                "slug": slug,
                "title": title,
                "keyword": str(item.get("keyword", "")),
                "score": score_with_boost(item),
                "source": str(item.get("source", "unknown")),
                "landing": str(item.get("landing", "")),
                "model_tag": str(item.get("model_tag", item.get("tag", ""))).strip(),
                "model_key": str(item.get("model_key", "")).strip(),
                "draft_path": str(draft_path.relative_to(ROOT)).replace("\\", "/"),
            }
        )

    updates = load_json(UPDATES_FILE, {"items": []})
    updates["items"] = [row for row in updates.get("items", []) if row.get("date") != today_iso]
    updates["items"].insert(
        0,
        {
            "date": today_iso,
            "summary": "Agent ranked SEO opportunities, filtered repeated topics, and generated review-ready content drafts.",
            "candidates": draft_records,
        },
    )
    updates["items"] = updates["items"][:30]
    save_json(UPDATES_FILE, updates)

    draft_index = load_json(DRAFT_INDEX_FILE, {"updated_at": "", "items": []})
    existing = [row for row in draft_index.get("items", []) if row.get("date") != today_iso]
    draft_index["updated_at"] = f"{today_iso}T00:00:00Z"
    draft_index["items"] = (draft_records + existing)[:120]
    save_json(DRAFT_INDEX_FILE, draft_index)

    LOGGER.info("daily content drafts generated:")
    for idx, row in enumerate(draft_records, start=1):
        LOGGER.info("%s. %s | score=%s | %s", idx, row["slug"], row["score"], row["draft_path"])
    LOGGER.info("updated %s", UPDATES_FILE)
    LOGGER.info("updated %s", DRAFT_INDEX_FILE)


if __name__ == "__main__":
    main()
