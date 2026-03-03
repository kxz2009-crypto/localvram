#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
QUEUE_ROOT = ROOT / "content-queue"
BLOG_DIR = ROOT / "src" / "content" / "blog"
REVIEW_LOG_FILE = ROOT / "src" / "data" / "content-review-log.json"
DATE_DIR_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
URL_PATTERN = re.compile(r"https?://[^\s)>\]\"']+")
DISCLOSURE_PATTERN = re.compile(
    r"(affiliate disclosure|affiliate link|may earn a commission|commission at no extra cost)",
    re.IGNORECASE,
)
TOPIC_STOPWORDS = {
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
LOGGER = configure_logging("review-content-queue")


def emit(message: str, *, level: str = "info", stderr: bool = False) -> None:
    if level == "error":
        LOGGER.error("%s", message)
    elif level == "warning":
        LOGGER.warning("%s", message)
    else:
        LOGGER.info("%s", message)


@dataclass
class ReviewItem:
    path: Path
    queue_date: str
    slug: str
    topic_key: str
    title: str
    keyword: str
    score: float
    status_before: str
    status_after: str
    word_count: int
    similarity_score: float
    topic_similarity_score: float
    similarity_slug: str
    risk_flags: list[str]


@dataclass
class BlogSignature:
    slug: str
    full_tokens: set[str]
    topic_tokens: set[str]


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


def dump_frontmatter(frontmatter: dict[str, str]) -> str:
    lines: list[str] = []
    for key, value in frontmatter.items():
        raw = str(value)
        if re.search(r"[\s:#]", raw) or raw == "":
            escaped = raw.replace("\\", "\\\\").replace('"', '\\"')
            raw = f'"{escaped}"'
        lines.append(f"{key}: {raw}")
    return "---\n" + "\n".join(lines) + "\n---\n"


def write_draft(path: Path, frontmatter: dict[str, str], body: str) -> None:
    content = f"{dump_frontmatter(frontmatter)}\n{body.strip()}\n"
    path.write_text(content, encoding="utf-8")


def read_latest_queue_date(queue_root: Path) -> str:
    if not queue_root.exists():
        raise SystemExit(f"queue folder not found: {queue_root}")
    candidates = sorted(
        [p.name for p in queue_root.iterdir() if p.is_dir() and DATE_DIR_PATTERN.match(p.name)],
        reverse=True,
    )
    if not candidates:
        raise SystemExit(f"no queue date folders found in {queue_root}")
    return candidates[0]


def normalize_text(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]{3,}", (text or "").lower())


def normalize_topic_text(text: str) -> list[str]:
    return [token for token in normalize_text(text) if token not in TOPIC_STOPWORDS]


def jaccard_similarity(a_tokens: set[str], b_tokens: set[str]) -> float:
    if not a_tokens or not b_tokens:
        return 0.0
    inter = len(a_tokens.intersection(b_tokens))
    union = len(a_tokens.union(b_tokens))
    return float(inter) / float(union) if union else 0.0


def word_count(body: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", body or ""))


def quote_ratio(body: str) -> float:
    quote_words = 0
    total_words = word_count(body)
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith(">"):
            quote_words += len(re.findall(r"[A-Za-z0-9']+", stripped))
    if total_words <= 0:
        return 0.0
    return quote_words / total_words


def domain_allowed(url: str, allowed_domains: set[str]) -> bool:
    host = urlparse(url).hostname or ""
    host = host.lower().lstrip(".")
    if host.startswith("www."):
        host = host[4:]
    for domain in allowed_domains:
        d = domain.lower().strip()
        if not d:
            continue
        if host == d or host.endswith(f".{d}"):
            return True
    return False


def collect_blog_signatures() -> list[BlogSignature]:
    out: list[BlogSignature] = []
    if not BLOG_DIR.exists():
        return out
    for path in BLOG_DIR.glob("*.md"):
        raw = path.read_text(encoding="utf-8-sig")
        frontmatter, body = parse_frontmatter(raw)
        title = str(frontmatter.get("title", "")).strip()
        keyword = str(frontmatter.get("keyword", "")).strip()
        desc = str(frontmatter.get("description", "")).strip()
        full_signature = " ".join([title, desc, body[:1800]])
        topic_signature = " ".join([title, keyword, path.stem.replace("-", " ")])
        out.append(
            BlogSignature(
                slug=path.stem,
                full_tokens=set(normalize_text(full_signature)),
                topic_tokens=set(normalize_topic_text(topic_signature)),
            )
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Risk-review content queue drafts and mark auto-approvable drafts.")
    parser.add_argument("--queue-date", default="")
    parser.add_argument("--min-score", type=float, default=120.0)
    parser.add_argument("--min-words", type=int, default=180)
    parser.add_argument("--max-quote-ratio", type=float, default=0.35)
    parser.add_argument("--duplicate-threshold", type=float, default=0.90)
    parser.add_argument("--duplicate-topic-threshold", type=float, default=0.55)
    parser.add_argument("--history-limit", type=int, default=60)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--allowed-external-domains",
        default="localvram.com,runpod.io,vast.ai,amazon.com,amzn.to,github.com",
        help="Comma separated allowlist for outbound URLs in draft body.",
    )
    args = parser.parse_args()

    queue_date = str(args.queue_date).strip() or read_latest_queue_date(QUEUE_ROOT)
    queue_dir = QUEUE_ROOT / queue_date
    if not queue_dir.exists():
        raise SystemExit(f"queue date folder not found: {queue_dir}")

    allowed_domains = {
        item.strip().lower()
        for item in str(args.allowed_external_domains).split(",")
        if item.strip()
    }
    blog_signatures = collect_blog_signatures()
    blog_slugs = {item.slug for item in blog_signatures}

    reviewers = {"approved_manual", "rejected_manual"}
    risk_counter: dict[str, int] = {}
    reviewed: list[ReviewItem] = []
    topic_to_paths: dict[str, list[Path]] = {}

    draft_paths = sorted(queue_dir.glob("*.md"))
    for path in draft_paths:
        raw = path.read_text(encoding="utf-8-sig")
        frontmatter, body = parse_frontmatter(raw)
        status_before = str(frontmatter.get("status", "draft")).strip().lower() or "draft"
        score_raw = str(frontmatter.get("score", "0")).strip()
        try:
            score = float(score_raw)
        except ValueError:
            score = 0.0
        keyword = str(frontmatter.get("keyword", "")).strip()
        title = str(frontmatter.get("title", path.stem)).strip() or path.stem
        slug = slugify(re.sub(r"^\d+-", "", path.stem))
        topic_key = slugify(keyword) if keyword else slug

        topic_to_paths.setdefault(topic_key, []).append(path)
        flags: list[str] = []
        similarity_score = 0.0
        topic_similarity_score = 0.0
        similarity_slug = ""
        wc = word_count(body)

        if score < float(args.min_score):
            flags.append("low_score")
        if wc < int(args.min_words):
            flags.append("low_content_words")
        if not DISCLOSURE_PATTERN.search(body):
            flags.append("missing_affiliate_disclosure")
        if quote_ratio(body) > float(args.max_quote_ratio):
            flags.append("high_quote_ratio")

        urls = URL_PATTERN.findall(body)
        for url in urls:
            if not domain_allowed(url, allowed_domains):
                flags.append("unapproved_external_link")
                break

        if slug in blog_slugs:
            flags.append("existing_blog_slug")

        candidate_tokens = set(normalize_text(" ".join([title, keyword, body[:1800]])))
        candidate_topic_tokens = set(normalize_topic_text(" ".join([title, keyword, slug.replace("-", " ")])))
        duplicate_slug = ""
        duplicate_score = 0.0
        duplicate_topic_score = 0.0
        for existing in blog_signatures:
            sim = jaccard_similarity(candidate_tokens, existing.full_tokens)
            topic_sim = jaccard_similarity(candidate_topic_tokens, existing.topic_tokens)
            if sim > similarity_score:
                similarity_score = sim
                similarity_slug = existing.slug
                topic_similarity_score = topic_sim
            if sim >= float(args.duplicate_threshold) and topic_sim >= float(args.duplicate_topic_threshold):
                if sim > duplicate_score:
                    duplicate_score = sim
                    duplicate_topic_score = topic_sim
                    duplicate_slug = existing.slug

        if duplicate_slug:
            similarity_slug = duplicate_slug
            similarity_score = duplicate_score
            topic_similarity_score = duplicate_topic_score
            flags.append("near_duplicate_published")

        if status_before in reviewers:
            status_after = status_before
        else:
            status_after = "approved_auto" if not flags else "pending_manual_review"

        for flag in flags:
            risk_counter[flag] = int(risk_counter.get(flag, 0)) + 1

        reviewed.append(
            ReviewItem(
                path=path,
                queue_date=queue_date,
                slug=slug,
                topic_key=topic_key,
                title=title,
                keyword=keyword,
                score=score,
                status_before=status_before,
                status_after=status_after,
                word_count=wc,
                similarity_score=similarity_score,
                topic_similarity_score=topic_similarity_score,
                similarity_slug=similarity_slug,
                risk_flags=flags,
            )
        )

    duplicate_topics = {k for k, rows in topic_to_paths.items() if len(rows) > 1}
    for item in reviewed:
        if item.topic_key in duplicate_topics:
            if "duplicate_queue_topic" not in item.risk_flags:
                item.risk_flags.append("duplicate_queue_topic")
                risk_counter["duplicate_queue_topic"] = int(risk_counter.get("duplicate_queue_topic", 0)) + 1
            if item.status_before not in reviewers:
                item.status_after = "pending_manual_review"

    if not args.dry_run:
        run_at = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        for item in reviewed:
            raw = item.path.read_text(encoding="utf-8-sig")
            frontmatter, body = parse_frontmatter(raw)
            frontmatter["status"] = item.status_after
            frontmatter["reviewed_at"] = run_at
            frontmatter["risk_flags"] = ",".join(item.risk_flags) if item.risk_flags else ""
            write_draft(item.path, frontmatter, body)

        log_payload = load_json(
            REVIEW_LOG_FILE,
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

        auto_approved_count = len([x for x in reviewed if x.status_after == "approved_auto"])
        pending_count = len([x for x in reviewed if x.status_after == "pending_manual_review"])
        rejected_count = len([x for x in reviewed if x.status_after == "rejected_manual"])
        high_risk_count = len(
            [
                x
                for x in reviewed
                if any(
                    flag == "near_duplicate_published"
                    or flag in {"unapproved_external_link", "missing_affiliate_disclosure"}
                    for flag in x.risk_flags
                )
            ]
        )

        run_row = {
            "run_at": run_at,
            "queue_date": queue_date,
            "reviewed_count": len(reviewed),
            "auto_approved_count": auto_approved_count,
            "pending_manual_review_count": pending_count,
            "rejected_manual_count": rejected_count,
            "high_risk_count": high_risk_count,
            "risk_flag_counts": dict(sorted(risk_counter.items(), key=lambda x: x[0])),
            "items": [
                {
                    "draft": str(item.path.relative_to(ROOT)).replace("\\", "/"),
                    "slug": item.slug,
                    "score": item.score,
                    "status_before": item.status_before,
                    "status_after": item.status_after,
                    "word_count": item.word_count,
                    "risk_flags": item.risk_flags,
                    "similarity": {
                        "score": round(item.similarity_score, 4),
                        "topic_score": round(item.topic_similarity_score, 4),
                        "slug": item.similarity_slug,
                    },
                }
                for item in reviewed[:120]
            ],
        }

        history.insert(0, run_row)
        log_payload["updated_at"] = run_at
        log_payload["last_run"] = run_row
        log_payload["history"] = history[: max(10, int(args.history_limit))]
        save_json(REVIEW_LOG_FILE, log_payload)

    emit(f"queue_date={queue_date}")
    emit(f"reviewed_count={len(reviewed)}")
    emit(f"auto_approved_count={len([x for x in reviewed if x.status_after == 'approved_auto'])}")
    emit(f"pending_manual_review_count={len([x for x in reviewed if x.status_after == 'pending_manual_review'])}")
    emit(f"rejected_manual_count={len([x for x in reviewed if x.status_after == 'rejected_manual'])}")
    emit(f"risk_flags={json.dumps(dict(sorted(risk_counter.items())), ensure_ascii=False)}")


if __name__ == "__main__":
    main()
