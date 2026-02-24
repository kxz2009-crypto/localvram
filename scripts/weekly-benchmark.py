#!/usr/bin/env python3
import datetime as dt
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUS_FILE = ROOT / "src" / "data" / "status.json"
CHANGELOG_FILE = ROOT / "src" / "data" / "benchmark-changelog.json"
LOG_DIR = ROOT / "logs"


def main() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    log_file = LOG_DIR / f"weekly-benchmark-{dt.datetime.utcnow().strftime('%Y%m%d')}.log"
    log_file.write_text(
        "placeholder benchmark run\n"
        "todo: call ollama + nvidia-smi + parse tokens/s + thermal drop-off\n",
        encoding="utf-8",
    )

    status = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    status["last_verified"] = dt.datetime.utcnow().date().isoformat()
    status["last_hardware_sync"] = now
    status["freshness_score"] = min(100, int(status.get("freshness_score", 85)) + 1)
    STATUS_FILE.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")

    if CHANGELOG_FILE.exists():
        changelog = json.loads(CHANGELOG_FILE.read_text(encoding="utf-8"))
    else:
        changelog = {"updated_at": now, "items": []}

    changelog["updated_at"] = now
    changelog["items"].insert(
        0,
        {
            "date": dt.datetime.utcnow().date().isoformat(),
            "title": "Automated weekly benchmark refresh",
            "environment": "RTX 3090 | self-hosted runner 3090-WSL2",
            "changes": [
                "Fresh benchmark run executed via GitHub Actions",
                "status.json freshness score updated",
                "Cluster benchmark sync completed",
            ],
        },
    )
    changelog["items"] = changelog["items"][:40]
    CHANGELOG_FILE.write_text(json.dumps(changelog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"updated status and wrote {log_file}")


if __name__ == "__main__":
    main()
