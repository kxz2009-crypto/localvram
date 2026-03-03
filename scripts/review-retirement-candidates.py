#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATES_FILE = "src/data/retirement-candidates.json"
DEFAULT_POLICY_FILE = "src/data/retired-models.json"
DEFAULT_PROPOSAL_FILE = "src/data/retirement-proposal.json"
LOGGER = configure_logging("review-retirement-candidates")


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


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_json_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        raw = ",".join(str(x) for x in value)
    else:
        raw = str(value or "")
    out: list[str] = []
    seen: set[str] = set()
    for chunk in raw.split(","):
        item = chunk.strip().lower()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:  # noqa: BLE001
        return default


def main() -> None:
    parser = argparse.ArgumentParser(description="Review retirement candidates and optionally apply into retired policy.")
    parser.add_argument("--candidates-file", default=DEFAULT_CANDIDATES_FILE)
    parser.add_argument("--policy-file", default=DEFAULT_POLICY_FILE)
    parser.add_argument("--proposal-file", default=DEFAULT_PROPOSAL_FILE)
    parser.add_argument("--min-last-seen-run-index", type=int, default=3)
    parser.add_argument("--max-seen-ok-count", type=int, default=2)
    parser.add_argument("--max-auto-approve", type=int, default=20)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--github-output", default="")
    args = parser.parse_args()

    candidates_path = resolve_path(args.candidates_file)
    policy_path = resolve_path(args.policy_file)
    proposal_path = resolve_path(args.proposal_file)

    payload = load_json(candidates_path, {})
    policy = load_json(policy_path, {})
    candidates = payload.get("candidates", []) if isinstance(payload, dict) else []
    if not isinstance(candidates, list):
        candidates = []

    retired_tags = set(parse_json_str_list(policy.get("retired_tags", [])))
    min_last_seen_run_index = max(1, int(args.min_last_seen_run_index))
    max_seen_ok_count = max(0, int(args.max_seen_ok_count))
    max_auto_approve = max(1, int(args.max_auto_approve))

    auto_approved: list[dict[str, Any]] = []
    manual_review: list[dict[str, Any]] = []
    skipped_already_retired: list[str] = []

    for row in candidates:
        if not isinstance(row, dict):
            continue
        model = str(row.get("model", "")).strip().lower()
        if not model or ":" not in model:
            continue
        if model in retired_tags:
            skipped_already_retired.append(model)
            continue

        last_seen_run_index = to_int(row.get("last_seen_run_index"), 9999)
        seen_ok_count = to_int(row.get("seen_ok_count"), 0)

        blockers: list[str] = []
        if last_seen_run_index < min_last_seen_run_index:
            blockers.append(f"last_seen_run_index<{min_last_seen_run_index}")
        if seen_ok_count > max_seen_ok_count:
            blockers.append(f"seen_ok_count>{max_seen_ok_count}")

        if blockers:
            manual_review.append(
                {
                    "model": model,
                    "family": str(row.get("family", "")).strip().lower(),
                    "last_seen_run_index": last_seen_run_index,
                    "seen_ok_count": seen_ok_count,
                    "blockers": blockers,
                    "source": row,
                }
            )
            continue

        auto_approved.append(
            {
                "model": model,
                "family": str(row.get("family", "")).strip().lower(),
                "last_seen_run_index": last_seen_run_index,
                "seen_ok_count": seen_ok_count,
                "reasons": row.get("reasons", []),
            }
        )

    auto_approved = auto_approved[:max_auto_approve]
    approved_tags = [x["model"] for x in auto_approved]

    proposal = {
        "generated_at": utc_now_iso(),
        "candidates_file": str(candidates_path),
        "policy_file": str(policy_path),
        "rules": {
            "min_last_seen_run_index": min_last_seen_run_index,
            "max_seen_ok_count": max_seen_ok_count,
            "max_auto_approve": max_auto_approve,
        },
        "source_candidate_count": len(candidates),
        "already_retired_count": len(skipped_already_retired),
        "already_retired_sample": sorted(skipped_already_retired)[:30],
        "auto_approved_count": len(auto_approved),
        "auto_approved": auto_approved,
        "manual_review_count": len(manual_review),
        "manual_review": manual_review[:80],
    }
    write_json(proposal_path, proposal)

    applied_count = 0
    if args.apply and approved_tags:
        merged = sorted(set(retired_tags).union(approved_tags))
        policy["retired_tags"] = merged
        policy["updated_at"] = utc_now_iso()
        notes = str(policy.get("notes", "")).strip()
        marker = "Auto-applied retirement candidates."
        if marker not in notes:
            policy["notes"] = (notes + " " + marker).strip() if notes else marker
        write_json(policy_path, policy)
        applied_count = len(approved_tags)

    LOGGER.info("source_candidate_count=%s", len(candidates))
    LOGGER.info("auto_approved_count=%s", len(auto_approved))
    LOGGER.info("manual_review_count=%s", len(manual_review))
    LOGGER.info("apply=%s", str(bool(args.apply)).lower())
    LOGGER.info("applied_count=%s", applied_count)
    LOGGER.info("retirement_proposal_out=%s", proposal_path)

    if args.github_output:
        gh_out = Path(args.github_output)
        gh_out.parent.mkdir(parents=True, exist_ok=True)
        with gh_out.open("a", encoding="utf-8") as f:
            f.write(f"source_candidate_count={len(candidates)}\n")
            f.write(f"auto_approved_count={len(auto_approved)}\n")
            f.write(f"manual_review_count={len(manual_review)}\n")
            f.write(f"applied_count={applied_count}\n")
            f.write("approved_tags_csv<<EOF\n")
            f.write(",".join(approved_tags) + "\n")
            f.write("EOF\n")


if __name__ == "__main__":
    main()
