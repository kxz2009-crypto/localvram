#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
QA_REPORT = ROOT / "dist" / "seo-audit" / "i18n-translation-qa.json"
OUT_CSV = ROOT / "dist" / "seo-audit" / "i18n-manual-review-checklist.csv"
LOGGER = configure_logging("export-i18n-manual-review-checklist")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export i18n manual review queue to CSV checklist.")
    parser.add_argument("--report", default=str(QA_REPORT), help="QA report json path.")
    parser.add_argument("--out", default=str(OUT_CSV), help="Output CSV path.")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max rows. 0 means export all.",
    )
    args = parser.parse_args()

    report_path = Path(args.report)
    if not report_path.exists():
        raise SystemExit(f"export failed: report file not found: {report_path}")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    queue = report.get("manual_review_queue", [])
    if not isinstance(queue, list):
        raise SystemExit("export failed: manual_review_queue missing or invalid")

    rows = queue[: args.limit] if args.limit and args.limit > 0 else queue
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "locale",
        "page_id",
        "field",
        "priority",
        "en",
        "translation",
        "status",
        "owner",
        "notes",
    ]
    with out_path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for item in rows:
            writer.writerow(
                {
                    "locale": item.get("locale", ""),
                    "page_id": item.get("page_id", ""),
                    "field": item.get("field", ""),
                    "priority": item.get("priority", ""),
                    "en": item.get("en", ""),
                    "translation": item.get("translation", ""),
                    "status": "pending",
                    "owner": "",
                    "notes": "",
                }
            )

    LOGGER.info("exported manual review checklist: rows=%s file=%s", len(rows), out_path)


if __name__ == "__main__":
    main()
