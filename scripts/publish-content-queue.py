#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
QUEUE_ROOT = ROOT / "content-queue"
BLOG_DIR = ROOT / "src" / "content" / "blog"
LOG_FILE = ROOT / "src" / "data" / "content-publish-log.json"
UPDATES_FILE = ROOT / "src" / "data" / "daily-updates.json"
BENCHMARK_FILE = ROOT / "src" / "data" / "benchmark-results.json"
MODEL_CATALOG_FILE = ROOT / "src" / "data" / "model-catalog.json"

DATE_DIR_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "local",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "vs",
    "with",
}
LOGGER = configure_logging("publish-content-queue")


@dataclass
class DraftCandidate:
    path: Path
    queue_date: str
    title: str
    keyword: str
    score: float
    date_value: str
    status: str
    body: str
    candidate_slug: str
    topic_key: str
    model_tag: str
    model_key: str
    traffic_priority: str
    ollama_updated_label: str
    benchmark_measured_at: str


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return cleaned or "untitled"


def model_landing_from_tag(tag: str, fallback: str = "/en/models/") -> str:
    raw = str(tag or "").strip()
    if not raw:
        return fallback
    catalog = load_json(MODEL_CATALOG_FILE, {"items": []})
    items = catalog.get("items", []) if isinstance(catalog, dict) else []
    if not isinstance(items, list):
        return fallback

    matches = [
        item
        for item in items
        if isinstance(item, dict) and str(item.get("ollama_tag", "")).strip().lower() == raw.lower()
    ]
    if not matches:
        return fallback
    matches.sort(
        key=lambda item: (
            {"Q4": 0, "Q5": 1, "Q8": 2, "FP16": 3, "CLOUD": 4}.get(
                str(item.get("quantization", "")).strip().upper(),
                9,
            ),
            str(item.get("id", "")),
        )
    )
    slug = str(matches[0].get("slug") or matches[0].get("id") or "").strip()
    return f"/en/models/{slug}/" if slug else fallback


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


def read_latest_queue_date(queue_root: Path) -> str:
    candidates = sorted(
        [p.name for p in queue_root.iterdir() if p.is_dir() and DATE_DIR_PATTERN.match(p.name)],
        reverse=True,
    )
    if not candidates:
        raise SystemExit(f"no queue date folders found in {queue_root}")
    return candidates[0]


def infer_intent(keyword: str, slug: str) -> str:
    text = f"{keyword} {slug}".lower()
    if any(token in text for token in ("error", "fix", "oom", "cuda", "failed")):
        return "troubleshooting"
    if any(token in text for token in ("cost", "price", "roi", "rent", "cloud")):
        return "cost"
    if any(token in text for token in ("gpu", "vram", "rtx", "hardware")):
        return "hardware"
    if any(token in text for token in ("benchmark", "tok/s", "latency", "throughput")):
        return "benchmark"
    return "guide"


def derive_tags(keyword: str, slug: str) -> list[str]:
    raw_tokens = re.split(r"[^a-z0-9]+", f"{keyword.lower()} {slug.lower()}")
    tags: list[str] = []
    for token in raw_tokens:
        if not token or token in STOPWORDS or len(token) < 2:
            continue
        if token not in tags:
            tags.append(token)
        if len(tags) >= 5:
            break
    if "ollama" not in tags:
        tags.insert(0, "ollama")
    return tags[:5]


def first_paragraph(body: str) -> str:
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith("- ") or re.match(r"^\d+\.", line):
            continue
        return line
    return ""


def derive_description(title: str, keyword: str, body: str) -> str:
    paragraph = first_paragraph(body)
    if paragraph:
        return paragraph[:180]
    key = keyword.strip() or title.strip()
    return f"Practical LocalVRAM guide for {key}."


def markdown_escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def write_blog_post(
    path: Path,
    *,
    title: str,
    description: str,
    pub_date: str,
    tags: list[str],
    intent: str,
    body: str,
    keyword: str = "",
    model_tag: str = "",
    traffic_priority: str = "",
    ollama_updated_label: str = "",
    benchmark_measured_at: str = "",
) -> None:
    tags_json = ", ".join(f'"{markdown_escape(tag)}"' for tag in tags)
    keyword_line = f'keyword: "{markdown_escape(keyword)}"\n' if keyword.strip() else ""
    model_tag_line = f'model_tag: "{markdown_escape(model_tag)}"\n' if model_tag.strip() else ""
    traffic_line = f'traffic_priority: "{markdown_escape(traffic_priority)}"\n' if traffic_priority.strip() else ""
    ollama_line = f'ollama_updated_label: "{markdown_escape(ollama_updated_label)}"\n' if ollama_updated_label.strip() else ""
    benchmark_line = f'benchmark_measured_at: "{markdown_escape(benchmark_measured_at)}"\n' if benchmark_measured_at.strip() else ""
    content = (
        "---\n"
        f'title: "{markdown_escape(title)}"\n'
        f'description: "{markdown_escape(description)}"\n'
        f"{keyword_line}"
        f"{model_tag_line}"
        f"{traffic_line}"
        f"{ollama_line}"
        f"{benchmark_line}"
        f"pubDate: {pub_date}\n"
        f"updatedDate: {pub_date}\n"
        f"tags: [{tags_json}]\n"
        "lang: en\n"
        f"intent: {intent}\n"
        "---\n\n"
        f"{body.strip()}\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def pick_measured_highlights(max_count: int = 50) -> list[dict[str, Any]]:
    payload = load_json(BENCHMARK_FILE, {"models": {}})
    rows = payload.get("models", {})
    if not isinstance(rows, dict):
        return []
    measured: list[dict[str, Any]] = []
    for tag, row in rows.items():
        if not isinstance(row, dict):
            continue
        if str(row.get("status", "")).strip().lower() != "ok":
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


def pick_today_model(measured: list[dict[str, Any]], queue_date: str = "") -> dict[str, Any]:
    """Pick today's featured model via date-based rotation with cascading fallback.

    Priority:
      1. Models with test_time within last 3 months (newest up to 30)
      2. Models with test_time at any date (newest up to 30)
      3. Any available model

    Always returns a dict (never None).
    """
    try:
        today = dt.date.fromisoformat((queue_date or "")[:10])
    except (ValueError, TypeError):
        today = dt.date.today()

    three_months_ago = today - dt.timedelta(days=90)

    def parse_test_time(row: dict[str, Any]) -> dt.datetime | None:
        raw = str(row.get("test_time", "")).strip()
        if not raw:
            return None
        try:
            return dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

    def newest_key(row: dict[str, Any]) -> dt.datetime:
        parsed = parse_test_time(row)
        if parsed is not None:
            return parsed
        return dt.datetime.min.replace(tzinfo=dt.timezone.utc)

    # Tier 1: tested within last 3 months, newest 30
    tier1 = sorted(
        [m for m in measured if parse_test_time(m) is not None and parse_test_time(m).date() >= three_months_ago],
        key=newest_key,
        reverse=True,
    )[:30]

    # Tier 2: any model with test_time, newest 30
    tier2 = sorted(
        [m for m in measured if parse_test_time(m) is not None],
        key=newest_key,
        reverse=True,
    )[:30]

    # Tier 3: any model at all
    tier3 = list(measured)

    for pool in (tier1, tier2, tier3):
        if pool:
            day_seed = sum(ord(ch) for ch in today.isoformat())
            return pool[day_seed % len(pool)]

    # Ultimate guard — caller should have verified measured is non-empty
    return {"tag": "local LLM", "tokens_per_second": 0.0, "latency_ms": 0.0, "test_time": ""}


def unique_slug(base_slug: str, existing_slugs: set[str]) -> str:
    if base_slug not in existing_slugs:
        return base_slug
    idx = 2
    while True:
        candidate = f"{base_slug}-{idx}"
        if candidate not in existing_slugs:
            return candidate
        idx += 1


def _infer_model_category(tag: str) -> str:
    """Return one of: coding, reasoning, chat, vision, general."""
    t = tag.lower()
    if "coder" in t or "/code" in t or "-code" in t or "codeqwen" in t:
        return "coding"
    if "deepseek" in t or "qwq" in t or "reason" in t or "think" in t:
        return "reasoning"
    if "vision" in t or "vl" in t:
        return "vision"
    if "chat" in t or "instruct" in t:
        return "chat"
    return "general"


def _infer_size_tier(tag: str) -> str:
    """Return one of: small, medium, large, xl, unknown."""
    m = re.search(r'[:/-](\d+)b', tag.lower())
    if not m:
        return "unknown"
    n = int(m.group(1))
    if n < 7:
        return "small"
    if n < 20:
        return "medium"
    if n <= 40:
        return "large"
    return "xl"


def _build_benchmark_context(pick_tag: str, measured: list[dict[str, Any]]) -> dict[str, str | None]:
    """Build positioning context: rank, nearest faster/slower model comparisons."""
    ranked = sorted(measured, key=lambda r: float(r.get("tokens_per_second", 0) or 0), reverse=True)
    tags = [r["tag"] for r in ranked]
    try:
        idx = tags.index(pick_tag)
    except ValueError:
        return {"rank": None, "out_of": len(ranked), "faster": None, "slower": None}

    pick_tps = float(ranked[idx]["tokens_per_second"])
    faster = ranked[idx - 1] if idx > 0 else None
    slower = ranked[idx + 1] if idx < len(ranked) - 1 else None

    out: dict[str, str | None] = {
        "rank": str(idx + 1),
        "out_of": str(len(ranked)),
    }
    if faster:
        gap = ((faster["tokens_per_second"] / pick_tps) - 1) * 100 if pick_tps > 0 else 0
        out["faster"] = f"`{faster['tag']}` ({faster['tokens_per_second']:.1f} tok/s, {gap:.0f}% faster)"
    else:
        out["faster"] = None
    if slower:
        gap = ((pick_tps / slower["tokens_per_second"]) - 1) * 100 if slower["tokens_per_second"] > 0 else 0
        out["slower"] = f"`{slower['tag']}` ({slower['tokens_per_second']:.1f} tok/s, {gap:.0f}% slower)"
    else:
        out["slower"] = None
    return out


def _perf_tier(tps: float) -> str:
    if tps >= 100:
        return "fast"
    if tps >= 40:
        return "moderate"
    if tps >= 15:
        return "deliberate"
    return "heavy"


def build_daily_fallback_content(queue_date: str, measured: list[dict[str, Any]]) -> dict[str, Any]:
    year = queue_date[:4] if len(queue_date) >= 4 else "2026"
    pick = pick_today_model(measured, queue_date=queue_date)
    pick_tag = str(pick.get("tag", "local LLM")).strip()
    model_landing = model_landing_from_tag(pick_tag)
    pick_tps = float(pick.get("tokens_per_second", 0) or 0)
    pick_latency = float(pick.get("latency_ms", 0) or 0)
    pick_test_time = str(pick.get("test_time", "")).strip()

    category = _infer_model_category(pick_tag)
    size_tier = _infer_size_tier(pick_tag)
    perf = _perf_tier(pick_tps)
    context = _build_benchmark_context(pick_tag, measured)

    title = f"Today's Local LLM Pick: {pick_tag} on RTX 3090 ({year})"
    keyword = f"{pick_tag} rtx 3090 ollama benchmark"
    summary = (
        f"Daily 3090 recommendation for {pick_tag}: {perf} performer at {pick_tps:.1f} tok/s, "
        "RTX 3090 benchmark data, use-case fit, and local-vs-cloud decision guide."
    )

    # ---- measured block (top 5 TPS) ----
    top5 = sorted(measured, key=lambda r: float(r.get("tokens_per_second", 0) or 0), reverse=True)[:5]
    measured_block_lines = [
        f"- `{r['tag']}`: {r['tokens_per_second']:.1f} tok/s | latency {r['latency_ms']:.0f} ms | test {r['test_time']}"
        for r in top5
    ]
    measured_block = "\n".join(measured_block_lines) if measured_block_lines else "- No verified measurements available yet."

    # ---- category-specific personas and guidance ----
    category_personas = {
        "coding": (
            "## Who should try it\n\n"
            f"- Developers evaluating `{pick_tag}` for code completion, refactoring, or agentic coding on a local RTX 3090.\n"
            "- Teams that want a private, offline coding assistant without sending source code to a cloud API.\n"
            f"- Anyone comparing `{pick_tag}` against Copilot or cloud coding agents on latency and throughput.\n\n"
            "## Who should skip it\n\n"
            "- Users whose primary workload is long-context chat or document analysis rather than code.\n"
            "- Teams that need guaranteed performance on a specific programming language; test with your own benchmark first.\n"
            "- 8GB/12GB GPU owners unless a smaller quantized variant is available.\n"
        ),
        "reasoning": (
            "## Who should try it\n\n"
            f"- Users working on math, logic, planning, or multi-step reasoning tasks where `{pick_tag}`'s chain-of-thought adds accuracy.\n"
            "- Researchers and power users who want a local alternative to cloud reasoning APIs like o1 or Claude.\n"
            "- Anyone curious whether local reasoning models have caught up to cloud counterparts on a 24GB RTX 3090.\n\n"
            "## Who should skip it\n\n"
            "- Teams that need fast, single-turn responses for real-time applications; reasoning models trade speed for depth.\n"
            "- Users running simple classification or extraction tasks that don't benefit from extended reasoning chains.\n"
            "- Anyone deploying to production without first validating output quality on representative data.\n"
        ),
        "vision": (
            "## Who should try it\n\n"
            f"- Developers building local image analysis pipelines who want to run `{pick_tag}` entirely on-device.\n"
            "- Privacy-sensitive users who need to process images without uploading to cloud vision APIs.\n"
            "- Anyone testing whether local vision models can handle their document scanning or screenshot analysis workload.\n\n"
            "## Who should skip it\n\n"
            "- Users who primarily work with text-only tasks; a smaller text-only model will be faster and more efficient.\n"
            "- Teams needing real-time video processing; current local vision models are optimized for single-image inference.\n"
            "- 8GB/12GB GPU owners unless a quantized vision variant is available.\n"
        ),
        "chat": (
            "## Who should try it\n\n"
            f"- Teams building conversational agents, customer support bots, or interactive assistants using `{pick_tag}`.\n"
            "- Users who want a local everyday chat model that runs entirely on their own hardware.\n"
            f"- Anyone comparing `{pick_tag}`'s multi-turn coherence against their current local or cloud chat model.\n\n"
            "## Who should skip it\n\n"
            "- Users who need specialized coding or reasoning capabilities; consider a task-specific model instead.\n"
            "- Teams deploying at scale without first verifying p95 latency under concurrent conversations.\n"
            "- 8GB/12GB GPU owners unless a smaller quantized variant is available.\n"
        ),
    }
    general_personas = (
        "## Who should try it\n\n"
        f"- RTX 3090 owners deciding whether to download `{pick_tag}` tonight for local experimentation.\n"
        "- Users comparing local inference speed against cloud rental (RunPod, Vast) before committing to a workflow.\n"
        "- Anyone building a local LLM toolbox who wants a verified baseline for this model.\n\n"
        "## Who should skip it\n\n"
        "- Users who need long-context production stability before a sustained run has been verified.\n"
        "- Teams whose workload requires predictable p95 latency under concurrency.\n"
        "- 8GB/12GB GPU owners unless a smaller quantized variant exists.\n"
    )
    personas = category_personas.get(category, general_personas)

    # ---- perf-tier verdict ----
    cat_label = {"coding": "coding", "reasoning": "reasoning", "vision": "vision", "chat": "chat", "general": "general-purpose"}[category]
    if perf == "fast":
        verdict = (
            f"`{pick_tag}` is a **fast** {cat_label} model on a 24GB RTX 3090 ({pick_tps:.1f} tok/s). "
            "If it fits your VRAM with headroom for your target context length, it is a strong candidate for daily local use. "
            "Download it and validate on your own prompts — the numbers suggest it will handle interactive workloads comfortably."
        )
    elif perf == "moderate":
        verdict = (
            f"`{pick_tag}` is a **moderate-speed** {cat_label} model on a 24GB RTX 3090 ({pick_tps:.1f} tok/s). "
            "It is worth testing locally for batch or offline workloads. For real-time interactive use, "
            "measure end-to-end latency with your typical prompt length before committing."
        )
    elif perf == "deliberate":
        verdict = (
            f"`{pick_tag}` runs at **{pick_tps:.1f} tok/s** on a 24GB RTX 3090 — in the deliberate range. "
            "This model prioritizes quality or parameter count over raw speed. "
            "Test it on offline or background tasks first, and consider a smaller quantization if interactive response time matters."
        )
    else:
        verdict = (
            f"`{pick_tag}` is a **heavy** model on 24GB VRAM ({pick_tps:.1f} tok/s). "
            "It is best suited for offline batch processing, proof-of-concept validation, or cloud fallback scenarios. "
            "Reduce context or step down quantization before attempting interactive use."
        )

    # ---- size-specific vram note ----
    size_note = ""
    if size_tier == "small":
        size_note = f"\n\nAt this model scale, `{pick_tag}` leaves substantial VRAM headroom on a 24GB card. You can run it alongside other services or allocate extra context without OOM risk."
    elif size_tier == "medium":
        size_note = f"\n\n`{pick_tag}` fits comfortably in 24GB at standard quantizations. Monitor VRAM usage if you push context beyond 8K tokens."
    elif size_tier == "large":
        size_note = f"\n\n`{pick_tag}` approaches the 24GB boundary at higher quantizations. Consider Q4 or Q5 if you need context headroom on the RTX 3090."
    elif size_tier == "xl":
        size_note = f"\n\n`{pick_tag}` exceeds 24GB at full precision. Use Q4 or lower quantization, or treat this as a cloud-fallback candidate."

    # ---- benchmark positioning ----
    positioning = ""
    rank = context.get("rank")
    out_of = context.get("out_of")
    faster = context.get("faster")
    slower = context.get("slower")
    if rank and out_of:
        parts = [f"It ranks **#{rank} of {out_of}** in throughput among currently measured models on this RTX 3090."]
        if faster:
            parts.append(f"The next faster model is {faster}.")
        if slower:
            parts.append(f"The next slower model is {slower}.")
        positioning = " " + " ".join(parts)

    # ---- category-specific watch points ----
    watch_points = {
        "coding": (
            "- **Output quality varies by language**: test {tag} on your primary language before depending on it.\n"
            "- **Temperature sensitivity**: coding tasks usually perform best at temperature 0; higher values may introduce errors.\n"
            "- **Context window**: verify the model keeps instruction adherence stable at the context length you need."
        ),
        "reasoning": (
            "- **Over-thinking risk**: on simple prompts the model may produce unnecessary chain-of-thought, increasing latency.\n"
            "- **Temperature tuning**: lower temperatures (0–0.3) improve factual accuracy; higher values may hallucinate reasoning steps.\n"
            "- **Batch efficiency**: for throughput-critical tasks, group prompts and process offline rather than requesting real-time responses."
        ),
        "vision": (
            "- **Image resolution**: higher-resolution inputs increase processing time significantly; resize images when possible.\n"
            "- **Single-image focus**: current local vision models are optimized for one image at a time, not video streams.\n"
            "- **OCR accuracy**: test on your document types; results vary by font, layout, and image quality."
        ),
        "chat": (
            "- **Multi-turn coherence**: test the model on 5+ turn conversations to verify it maintains context.\n"
            "- **System prompt adherence**: {tag} may need explicit formatting instructions for production use.\n"
            "- **Concurrent sessions**: measure p95 latency under your expected concurrency before deploying to users."
        ),
        "general": (
            "- **Workload-specific testing**: generic benchmarks do not guarantee performance on your particular use case.\n"
            "- **Context length**: always test at your target context length before assuming production readiness.\n"
            "- **Quantization trade-off**: lower quantization saves VRAM but may reduce output quality on nuanced tasks."
        ),
    }
    watch_block = watch_points.get(category, watch_points["general"]).format(tag=pick_tag)

    # ---- decision guide (perf-tier adaptive) ----
    if perf == "fast":
        decision = (
            "1. **VRAM check first**: if {tag} fits with headroom at your target context length, run it locally.\n"
            "2. **Latency validation**: verify p95 latency matches your workload requirements under realistic concurrency.\n"
            "3. **Cloud only for bursts**: keep local as the default; use cloud rental for peak overflow or batch jobs.\n"
            "4. **New release watch**: if a newer version of {tag} drops, re-test within 48 hours to capture the traffic window."
        )
    elif perf == "moderate":
        decision = (
            "1. **Batch is the sweet spot**: {tag} is best for offline/batch jobs where throughput matters more than single-shot latency.\n"
            "2. **Test at your context length**: moderate-speed models can slow significantly at longer contexts.\n"
            "3. **Quantization choice matters**: stepping from Q8 to Q4 gains speed but test quality degradation first.\n"
            "4. **Cloud fallback plan**: if local latency misses your target, use RunPod/Vast for time-sensitive runs."
        )
    elif perf == "deliberate":
        decision = (
            "1. **Offline first**: prioritize {tag} for scheduled batch inference, research, or validation workflows.\n"
            "2. **Context is the bottleneck**: reduce context to the minimum viable length for your task.\n"
            "3. **Quantize before you buy hardware**: Q4 or Q5 may make this viable on 24GB where Q8 is not.\n"
            "4. **Cloud for interactive**: if real-time response is required, treat {tag} as a cloud-fallback candidate."
        )
    else:  # heavy
        decision = (
            "1. **Cloud may win**: at {tps:.1f} tok/s on 24GB, {tag} may be more cost-effective on RunPod or Vast.\n"
            "2. **Reduce aggressively**: step down to Q4 or IQ4 and minimize context to fit VRAM.\n"
            "3. **Offline only**: do not rely on this model for interactive or real-time local workloads.\n"
            "4. **Hardware path**: if you run models this size daily, consider multi-GPU or cloud as a permanent solution."
        )
    decision_block = decision.format(tag=pick_tag, tps=pick_tps)

    # ---- data-driven comparisons ----
    comp_lines = [f"- `{pick_tag}` vs the next-fastest and next-slowest model in the benchmark feed."]
    # Find comparable models in similar size range
    same_tier = [
        r for r in measured
        if r["tag"] != pick_tag and _infer_size_tier(r["tag"]) == size_tier
    ]
    if same_tier:
        fastest_same = max(same_tier, key=lambda r: r["tokens_per_second"])
        comp_lines.append(
            f"- `{pick_tag}` vs `{fastest_same['tag']}` — same size tier, "
            f"{pick_tps:.0f} vs {fastest_same['tokens_per_second']:.0f} tok/s."
        )
    comp_lines.append(f"- `{pick_tag}` local power cost vs A100 rental for the same workload.")

    body = (
        "## Fast verdict\n\n"
        f"{verdict}{size_note}{positioning}\n\n"
        "The daily goal is simple: help a 3090 owner decide what to download tonight, what to skip, "
        "and when a cloud fallback is the better use of time.\n\n"
        "## Today's pick\n\n"
        f"- **Model:** `{pick_tag}`\n"
        f"- **Category:** {cat_label}\n"
        f"- **Size tier:** {size_tier}\n"
        f"- **Performance tier:** {perf}\n"
        f"- **RTX 3090 speed:** {pick_tps:.1f} tok/s\n"
        f"- **Latency:** {pick_latency:.0f} ms\n"
        f"- **Test time:** {pick_test_time or 'pending'}\n"
        "- **Baseline command:**\n\n"
        "```bash\n"
        f"ollama run {pick_tag if ':' in pick_tag else '<model-tag>'}\n"
        "```\n\n"
        f"{personas}"
        "## Watch points\n\n"
        f"{watch_block}\n\n"
        "## Verified benchmark anchors\n\n"
        f"{measured_block}\n\n"
        "## RTX 3090 decision guide\n\n"
        f"{decision_block}\n\n"
        "## Comparisons to validate\n\n"
        + "\n".join(comp_lines) + "\n\n"
        "## Next actions\n\n"
        "- Estimate VRAM fit: /en/tools/vram-calculator/\n"
        f"- Model page: {model_landing}\n"
        "- Benchmark changelog: /en/benchmarks/changelog/\n"
        "- Local hardware path: /en/affiliate/hardware-upgrade/\n"
        "- Cloud fallback: /go/runpod and /go/vast\n\n"
        "Affiliate Disclosure: This post may include affiliate links. LocalVRAM may earn a commission at no extra cost.\n"
    )

    tags = ["ollama", "benchmark", "vram", "latency", perf]
    if category != "general":
        tags.append(category)

    return {
        "title": title,
        "keyword": keyword,
        "description": summary,
        "intent": "benchmark",
        "tags": tags,
        "body": body,
    }


def normalize_topic_key(keyword: str, slug: str) -> str:
    return slugify(keyword) or slugify(slug)


def has_topic_conflict(candidate_slug: str, topic_key: str, existing_slugs: set[str], published_topics: set[str]) -> tuple[bool, str]:
    if topic_key in published_topics:
        return True, "already_published_topic_key"
    for existing in existing_slugs:
        if candidate_slug == existing:
            return True, f"existing_slug:{existing}"
        if len(candidate_slug) >= 10 and (candidate_slug in existing or existing in candidate_slug):
            return True, f"similar_slug:{existing}"
        if topic_key and len(topic_key) >= 10 and (topic_key in existing or existing in topic_key):
            return True, f"similar_topic:{existing}"
    return False, ""


def collect_candidates(queue_dir: Path, queue_date: str, min_score: float) -> list[DraftCandidate]:
    out: list[DraftCandidate] = []
    for draft_path in sorted(queue_dir.glob("*.md")):
        raw = draft_path.read_text(encoding="utf-8-sig")
        frontmatter, body = parse_frontmatter(raw)
        title = str(frontmatter.get("title", "")).strip() or draft_path.stem
        keyword = str(frontmatter.get("keyword", "")).strip()
        score_raw = str(frontmatter.get("score", "0")).strip()
        try:
            score = float(score_raw)
        except ValueError:
            score = 0.0
        status = str(frontmatter.get("status", "draft")).strip().lower()
        date_value = str(frontmatter.get("date", queue_date)).strip() or queue_date
        base_slug = re.sub(r"^\d+-", "", draft_path.stem.strip())
        candidate_slug = slugify(base_slug)
        topic_key = normalize_topic_key(keyword, candidate_slug)
        model_tag = str(frontmatter.get("model_tag", "")).strip()
        model_key = slugify(model_tag.replace(":", "-")) if model_tag else ""
        traffic_priority = str(frontmatter.get("traffic_priority", "")).strip()
        ollama_updated_label = str(frontmatter.get("ollama_updated_label", "")).strip()
        benchmark_measured_at = str(frontmatter.get("benchmark_measured_at", "")).strip()

        if status not in {"approved_auto", "approved_manual"}:
            continue
        if score < min_score:
            continue
        if not body:
            continue

        out.append(
            DraftCandidate(
                path=draft_path,
                queue_date=queue_date,
                title=title,
                keyword=keyword,
                score=score,
                date_value=date_value,
                status=status,
                body=body,
                candidate_slug=candidate_slug,
                topic_key=topic_key,
                model_tag=model_tag,
                model_key=model_key,
                traffic_priority=traffic_priority,
                ollama_updated_label=ollama_updated_label,
                benchmark_measured_at=benchmark_measured_at,
            )
        )
    out.sort(key=lambda c: (-c.score, c.candidate_slug))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publish approved high-score drafts from content-queue into src/content/blog."
    )
    parser.add_argument("--queue-date", default="")
    parser.add_argument("--max-publish", type=int, default=int(os.getenv("LV_CONTENT_AUTO_PUBLISH_MAX", "2")))
    parser.add_argument(
        "--min-publish",
        type=int,
        default=int(os.getenv("LV_CONTENT_AUTO_PUBLISH_MIN_DAILY", "1")),
        help="Minimum posts to publish per day. If normal candidates are insufficient, fallback post(s) are generated.",
    )
    parser.add_argument("--min-score", type=float, default=float(os.getenv("LV_CONTENT_AUTO_PUBLISH_MIN_SCORE", "120")))
    parser.add_argument("--history-limit", type=int, default=60)
    args = parser.parse_args()

    queue_date = str(args.queue_date).strip() or read_latest_queue_date(QUEUE_ROOT)
    queue_dir = QUEUE_ROOT / queue_date
    if not queue_dir.exists():
        raise SystemExit(f"queue date folder not found: {queue_dir}")

    max_publish = max(0, int(args.max_publish))
    min_publish = max(0, int(args.min_publish))
    effective_max_publish = max(max_publish, min_publish)
    min_score = float(args.min_score)
    history_limit = max(10, int(args.history_limit))

    log_payload = load_json(
        LOG_FILE,
        {
            "version": "2026.02.26",
            "updated_at": "",
            "last_run": {},
            "history": [],
        },
    )
    history = log_payload.get("history", [])
    if not isinstance(history, list):
        history = []
    published_topics: set[str] = set()
    for row in history:
        if not isinstance(row, dict):
            continue
        for item in row.get("published", []):
            if not isinstance(item, dict):
                continue
            key = str(item.get("topic_key", "")).strip()
            if key:
                published_topics.add(key)

    existing_slugs = {p.stem for p in BLOG_DIR.glob("*.md")}
    candidates = collect_candidates(queue_dir, queue_date, min_score=min_score)

    published: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for cand in candidates:
        if len(published) >= effective_max_publish:
            skipped.append({"draft": str(cand.path.relative_to(ROOT)).replace("\\", "/"), "reason": "max_publish_reached"})
            continue

        has_conflict, reason = has_topic_conflict(cand.candidate_slug, cand.topic_key, existing_slugs, published_topics)
        if has_conflict:
            skipped.append({"draft": str(cand.path.relative_to(ROOT)).replace("\\", "/"), "reason": reason})
            continue

        description = derive_description(cand.title, cand.keyword, cand.body)
        intent = infer_intent(cand.keyword, cand.candidate_slug)
        tags = derive_tags(cand.keyword, cand.candidate_slug)
        pub_date = cand.date_value or queue_date
        out_file = BLOG_DIR / f"{cand.candidate_slug}.md"

        write_blog_post(
            out_file,
            title=cand.title,
            description=description,
            pub_date=pub_date,
            tags=tags,
            intent=intent,
            body=cand.body,
            keyword=cand.keyword,
            model_tag=cand.model_tag,
            traffic_priority=cand.traffic_priority,
            ollama_updated_label=cand.ollama_updated_label,
            benchmark_measured_at=cand.benchmark_measured_at,
        )

        published.append(
            {
                "slug": cand.candidate_slug,
                "title": cand.title,
                "topic_key": cand.topic_key,
                "score": cand.score,
                "source_draft": str(cand.path.relative_to(ROOT)).replace("\\", "/"),
                "out_file": str(out_file.relative_to(ROOT)).replace("\\", "/"),
                "intent": intent,
                "model_tag": cand.model_tag,
                "model_key": cand.model_key,
                "traffic_priority": cand.traffic_priority,
                "ollama_updated_label": cand.ollama_updated_label,
                "benchmark_measured_at": cand.benchmark_measured_at,
            }
        )
        existing_slugs.add(cand.candidate_slug)
        published_topics.add(cand.topic_key)

    fallback_generated = 0
    if len(published) < min_publish:
        needed = min_publish - len(published)
        measured = pick_measured_highlights(max_count=50)
        for _ in range(needed):
            fallback = build_daily_fallback_content(queue_date, measured)
            base_slug = slugify(f"daily-local-llm-benchmark-snapshot-{queue_date}")
            slug = unique_slug(base_slug, existing_slugs)
            topic_key = slugify(f"daily-benchmark-fallback-{queue_date}-{slug}")
            out_file = BLOG_DIR / f"{slug}.md"
            write_blog_post(
                out_file,
                title=fallback["title"],
                description=fallback["description"],
                pub_date=queue_date,
                tags=list(fallback["tags"]),
                intent=str(fallback["intent"]),
                body=str(fallback["body"]),
                keyword=str(fallback["keyword"]),
            )
            published.append(
                {
                    "slug": slug,
                    "title": fallback["title"],
                    "topic_key": topic_key,
                    "score": min_score,
                    "source_draft": "system:fallback-daily-generator",
                    "out_file": str(out_file.relative_to(ROOT)).replace("\\", "/"),
                    "intent": fallback["intent"],
                }
            )
            existing_slugs.add(slug)
            published_topics.add(topic_key)
            fallback_generated += 1

    run_at = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    run_summary = {
        "run_at": run_at,
        "queue_date": queue_date,
        "candidate_count": len(candidates),
        "min_publish": min_publish,
        "max_publish": max_publish,
        "published_count": len(published),
        "fallback_generated_count": fallback_generated,
        "skipped_count": len(skipped),
        "published": published,
        "skipped": skipped[:80],
    }

    history.insert(0, run_summary)
    log_payload["updated_at"] = run_at
    log_payload["last_run"] = run_summary
    log_payload["history"] = history[:history_limit]
    save_json(LOG_FILE, log_payload)

    updates = load_json(UPDATES_FILE, {"items": []})
    items = updates.get("items", []) if isinstance(updates, dict) else []
    if not isinstance(items, list):
        items = []
    date_row: dict[str, Any] | None = None
    for row in items:
        if isinstance(row, dict) and str(row.get("date", "")).strip() == queue_date:
            date_row = row
            break
    if date_row is None:
        date_row = {"date": queue_date, "summary": "", "candidates": []}
        items.insert(0, date_row)
    if published:
        date_row["published_posts"] = [{"slug": p["slug"], "title": p["title"]} for p in published]
        date_row["published_count"] = len(published)
        date_row["publish_run_at"] = run_at
    else:
        if int(date_row.get("published_count", 0) or 0) <= 0:
            for old_run in history:
                if not isinstance(old_run, dict):
                    continue
                if str(old_run.get("queue_date", "")).strip() != queue_date:
                    continue
                if int(old_run.get("published_count", 0) or 0) <= 0:
                    continue
                restored = old_run.get("published", [])
                if isinstance(restored, list) and restored:
                    date_row["published_posts"] = [
                        {"slug": str(item.get("slug", "")).strip(), "title": str(item.get("title", "")).strip()}
                        for item in restored
                        if isinstance(item, dict)
                    ]
                    date_row["published_count"] = len(date_row["published_posts"])
                    date_row["publish_run_at"] = str(old_run.get("run_at", "")).strip()
                    break
        date_row["publish_noop_run_at"] = run_at
    updates["items"] = items[:40]
    save_json(UPDATES_FILE, updates)

    LOGGER.info("queue_date=%s", queue_date)
    LOGGER.info("candidate_count=%s", len(candidates))
    LOGGER.info("published_count=%s", len(published))
    LOGGER.info("skipped_count=%s", len(skipped))
    for row in published:
        LOGGER.info("published=%s score=%s", row["slug"], row["score"])
    if not published:
        LOGGER.info("published=none")


if __name__ == "__main__":
    main()
