#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
QUEUE_ROOT = ROOT / "content-queue"
BLOG_DIR = ROOT / "src" / "content" / "blog"
LOG_FILE = ROOT / "src" / "data" / "content-publish-log.json"
UPDATES_FILE = ROOT / "src" / "data" / "daily-updates.json"

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


def write_blog_post(path: Path, *, title: str, description: str, pub_date: str, tags: list[str], intent: str, body: str) -> None:
    tags_json = ", ".join(f'"{markdown_escape(tag)}"' for tag in tags)
    content = (
        "---\n"
        f'title: "{markdown_escape(title)}"\n'
        f'description: "{markdown_escape(description)}"\n'
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
    parser.add_argument("--min-score", type=float, default=float(os.getenv("LV_CONTENT_AUTO_PUBLISH_MIN_SCORE", "120")))
    parser.add_argument("--history-limit", type=int, default=60)
    args = parser.parse_args()

    queue_date = str(args.queue_date).strip() or read_latest_queue_date(QUEUE_ROOT)
    queue_dir = QUEUE_ROOT / queue_date
    if not queue_dir.exists():
        raise SystemExit(f"queue date folder not found: {queue_dir}")

    max_publish = max(0, int(args.max_publish))
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
        if len(published) >= max_publish:
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
            }
        )
        existing_slugs.add(cand.candidate_slug)
        published_topics.add(cand.topic_key)

    run_at = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    run_summary = {
        "run_at": run_at,
        "queue_date": queue_date,
        "candidate_count": len(candidates),
        "published_count": len(published),
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

    print(f"queue_date={queue_date}")
    print(f"candidate_count={len(candidates)}")
    print(f"published_count={len(published)}")
    print(f"skipped_count={len(skipped)}")
    for row in published:
        print(f"published={row['slug']} score={row['score']}")
    if not published:
        print("published=none")


if __name__ == "__main__":
    main()
