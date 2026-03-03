#!/usr/bin/env python3
import argparse
import datetime as dt
import os
import re
from pathlib import Path

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
QUEUE_ROOT = ROOT / "content-queue"
DATE_DIR_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STDOUT_CONTRACT_ENV = "LV_STDOUT_CONTRACT"
LOGGER = configure_logging("review-content-drafts")


def stdout_contract_enabled() -> bool:
    raw = str(os.getenv(STDOUT_CONTRACT_ENV, "true")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def emit_contract(message: str) -> None:
    LOGGER.info("%s", message)
    if stdout_contract_enabled():
        print(message)


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
    path.write_text(f"{dump_frontmatter(frontmatter)}\n{body.strip()}\n", encoding="utf-8")


def read_latest_queue_date() -> str:
    if not QUEUE_ROOT.exists():
        raise SystemExit(f"queue root not found: {QUEUE_ROOT}")
    candidates = sorted(
        [p.name for p in QUEUE_ROOT.iterdir() if p.is_dir() and DATE_DIR_PATTERN.match(p.name)],
        reverse=True,
    )
    if not candidates:
        raise SystemExit("no queue folders found")
    return candidates[0]


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return cleaned or "untitled"


def split_csv(value: str) -> list[str]:
    return [x.strip() for x in str(value or "").split(",") if x.strip()]


def action_to_status(action: str) -> str:
    mapping = {
        "approve": "approved_manual",
        "reject": "rejected_manual",
        "needs_info": "pending_manual_review",
    }
    return mapping[action]


def main() -> None:
    parser = argparse.ArgumentParser(description="Manual review command for content queue drafts.")
    parser.add_argument("--queue-date", default="")
    parser.add_argument("--drafts", default="", help="Comma-separated draft filenames or relative paths.")
    parser.add_argument("--slugs", default="", help="Comma-separated candidate slugs.")
    parser.add_argument("--action", required=True, choices=["approve", "reject", "needs_info"])
    parser.add_argument("--reviewer", default="manual_reviewer")
    parser.add_argument("--note", default="")
    parser.add_argument("--dry-run", action="store_true", help="Preview updates without writing draft files.")
    args = parser.parse_args()

    queue_date = str(args.queue_date).strip() or read_latest_queue_date()
    queue_dir = QUEUE_ROOT / queue_date
    if not queue_dir.exists():
        raise SystemExit(f"queue folder not found: {queue_dir}")

    slug_set = {slugify(x) for x in split_csv(args.slugs)}
    draft_names = set(split_csv(args.drafts))

    targets: list[Path] = []
    for path in sorted(queue_dir.glob("*.md")):
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        name = path.name
        slug = slugify(re.sub(r"^\d+-", "", path.stem))
        if draft_names and (name in draft_names or rel in draft_names):
            targets.append(path)
            continue
        if slug_set and slug in slug_set:
            targets.append(path)

    if not targets:
        raise SystemExit("no matching drafts found; use --drafts or --slugs")

    status = action_to_status(args.action)
    reviewed_at = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")

    updated = 0
    for path in targets:
        raw = path.read_text(encoding="utf-8-sig")
        frontmatter, body = parse_frontmatter(raw)
        frontmatter["status"] = status
        frontmatter["reviewed_at"] = reviewed_at
        frontmatter["reviewed_by"] = str(args.reviewer).strip() or "manual_reviewer"
        frontmatter["review_action"] = args.action
        if str(args.note).strip():
            frontmatter["review_note"] = str(args.note).strip()
        if not args.dry_run:
            write_draft(path, frontmatter, body)
        updated += 1
        prefix = "would_update" if args.dry_run else "updated"
        emit_contract(f"{prefix}={path.relative_to(ROOT)} status={status}")

    emit_contract(f"queue_date={queue_date}")
    emit_contract(f"updated_count={updated}")
    emit_contract(f"action={args.action}")
    emit_contract(f"dry_run={'true' if args.dry_run else 'false'}")


if __name__ == "__main__":
    main()
