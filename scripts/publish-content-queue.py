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
) -> None:
    tags_json = ", ".join(f'"{markdown_escape(tag)}"' for tag in tags)
    keyword_line = f'keyword: "{markdown_escape(keyword)}"\n' if keyword.strip() else ""
    model_tag_line = f'model_tag: "{markdown_escape(model_tag)}"\n' if model_tag.strip() else ""
    content = (
        "---\n"
        f'title: "{markdown_escape(title)}"\n'
        f'description: "{markdown_escape(description)}"\n'
        f"{keyword_line}"
        f"{model_tag_line}"
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


def pick_measured_highlights(max_count: int = 5) -> list[dict[str, Any]]:
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


def pick_today_model(measured: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not measured:
        return None
    def utility(row: dict[str, Any]) -> tuple[int, float]:
        tag = str(row.get("tag", "")).lower()
        tps = float(row.get("tokens_per_second", 0) or 0)
        score = 0
        if any(token in tag for token in ("coder", "qwen", "deepseek", "mistral", "gemma")):
            score += 3
        if any(token in tag for token in ("30b", "32b", "35b", "27b", "24b", "20b", "14b")):
            score += 2
        if tps >= 20:
            score += 2
        if tps >= 60:
            score += 1
        return (score, tps)

    return sorted(measured, key=utility, reverse=True)[0]


def unique_slug(base_slug: str, existing_slugs: set[str]) -> str:
    if base_slug not in existing_slugs:
        return base_slug
    idx = 2
    while True:
        candidate = f"{base_slug}-{idx}"
        if candidate not in existing_slugs:
            return candidate
        idx += 1


def build_daily_fallback_content(queue_date: str, measured: list[dict[str, Any]]) -> dict[str, Any]:
    year = queue_date[:4] if len(queue_date) >= 4 else "2026"
    pick = pick_today_model(measured)
    pick_tag = str(pick.get("tag", "local LLM")).strip() if pick else "local LLM"
    pick_slug = slugify(pick_tag.replace(":", "-")) if pick else "local-llm"
    pick_tps = float(pick.get("tokens_per_second", 0) or 0) if pick else 0.0
    pick_latency = float(pick.get("latency_ms", 0) or 0) if pick else 0.0
    pick_test_time = str(pick.get("test_time", "")).strip() if pick else ""
    title = f"Today's Local LLM Pick: {pick_tag} on RTX 3090 ({year})"
    keyword = f"{pick_tag} rtx 3090 ollama benchmark" if pick else "best local llm rtx 3090 today"
    summary = (
        f"Daily 3090 recommendation for {pick_tag}: verified speed, VRAM decision guidance, "
        "Ollama setup path, and local-vs-cloud fallback triggers."
    )
    lines = []
    for row in measured:
        lines.append(
            f"- `{row['tag']}`: {row['tokens_per_second']:.1f} tok/s | latency {row['latency_ms']:.0f} ms | test {row['test_time']}"
        )
    measured_block = "\n".join(lines) if lines else "- Latest benchmark feed is temporarily unavailable."
    if pick_tps >= 60:
        verdict = f"Download `{pick_tag}` first if you want a fast local baseline on a 24GB RTX 3090."
    elif pick_tps >= 20:
        verdict = f"`{pick_tag}` is worth testing locally, but watch context length and sustained latency."
    elif pick:
        verdict = f"`{pick_tag}` is a specialist or heavy model on 24GB; test locally before relying on it for production."
    else:
        verdict = "No verified model changed enough today to justify a full SEO article; use this as a feed update."
    body = (
        "## Fast verdict\n\n"
        f"{verdict}\n\n"
        "The daily goal is simple: help a 3090 owner decide what to download tonight, what to skip, and when a cloud fallback is the better use of time. This page is not a generic changelog; it is a practical decision note built from the latest verified LocalVRAM benchmark feed.\n\n"
        "## Today's pick\n\n"
        f"- Model: `{pick_tag}`\n"
        f"- RTX 3090 speed: {pick_tps:.1f} tok/s\n"
        f"- Latency: {pick_latency:.0f} ms\n"
        f"- Test time: {pick_test_time or 'pending'}\n"
        "- Baseline command:\n\n"
        "```bash\n"
        f"ollama run {pick_tag if ':' in pick_tag else '<model-tag>'}\n"
        "```\n\n"
        "## Who should try it\n\n"
        f"- Developers and local AI users who want a fresh 24GB RTX 3090 baseline for `{pick_tag}`.\n"
        "- Readers comparing local speed against RunPod/Vast before spending cloud credits.\n"
        "- Anyone deciding whether a new Ollama model is worth downloading in the first 24-48 hour traffic window.\n\n"
        "## Who should skip it\n\n"
        "- Users who need long-context production stability before a sustained run has been verified.\n"
        "- Teams whose workload requires predictable p95 latency under concurrency; validate locally first, then burst to cloud.\n"
        "- 8GB/12GB GPU owners unless the model has a smaller quantization or distilled variant.\n\n"
        "## Verified benchmark anchors\n\n"
        f"{measured_block}\n\n"
        "## 3090 decision guide\n\n"
        "1. If the model fits VRAM with headroom and response time is acceptable, run it locally first.\n"
        "2. If it fits but misses p95 latency, keep the local machine for validation and burst to cloud for peak windows.\n"
        "3. If it OOMs, reduce context or quantization before buying hardware.\n"
        "4. If a new Ollama release is trending, publish the estimated page early and update it with verified 3090 data within 24-48 hours.\n\n"
        "## Comparison prompts to run next\n\n"
        f"- `{pick_tag}` vs the current coding baseline.\n"
        f"- `{pick_tag}` vs the best 14B/20B fast local model.\n"
        f"- `{pick_tag}` local power cost vs A100 rental for the same workload.\n\n"
        "## Next actions\n\n"
        "- Estimate fit: /en/tools/vram-calculator/\n"
        f"- Model page: /en/models/{pick_slug}-q4/\n"
        "- Benchmark changelog: /en/benchmarks/changelog/\n"
        "- Hardware path: /en/affiliate/hardware-upgrade/\n"
        "- Cloud fallback: /go/runpod and /go/vast\n\n"
        "Affiliate Disclosure: This post may include affiliate links. LocalVRAM may earn a commission at no extra cost.\n"
    )
    return {
        "title": title,
        "keyword": keyword,
        "description": summary,
        "intent": "benchmark",
        "tags": ["ollama", "benchmark", "vram", "latency", "throughput"],
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
            }
        )
        existing_slugs.add(cand.candidate_slug)
        published_topics.add(cand.topic_key)

    fallback_generated = 0
    if len(published) < min_publish:
        needed = min_publish - len(published)
        measured = pick_measured_highlights(max_count=5)
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
