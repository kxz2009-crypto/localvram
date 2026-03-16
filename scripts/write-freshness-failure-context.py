#!/usr/bin/env python3
import json
from pathlib import Path


def main() -> None:
    report_path = Path("logs/model-freshness-report.json")
    failure_detail = "check-data-freshness.py failed"
    if report_path.exists():
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            errors = payload.get("errors", [])
            if isinstance(errors, list) and errors:
                failure_detail = "; ".join(str(item) for item in errors[:6])
        except Exception as exc:  # noqa: BLE001
            failure_detail = f"failed to parse model-freshness-report.json: {exc}"

    Path("logs/failure-context.json").write_text(
        json.dumps(
            {
                "failure_class": "model_data_stale",
                "failure_detail": failure_detail,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
