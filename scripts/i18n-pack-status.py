#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACK_DIR = ROOT / "src" / "data" / "i18n-packs"


def summarize_pack(pack_file: Path) -> dict:
    data = json.loads(pack_file.read_text(encoding="utf-8"))
    locale = str(data.get("locale", "")).strip().lower() or pack_file.stem
    phrases = data.get("phrases", [])
    if not isinstance(phrases, list):
        return {"locale": locale, "total": 0, "filled": 0, "ratio": 0.0, "file": pack_file}

    total = 0
    filled = 0
    for row in phrases:
        if not isinstance(row, dict):
            continue
        total += 1
        text = str(row.get("translation", ""))
        if text.strip():
            filled += 1
    ratio = (filled / total) if total else 0.0
    return {"locale": locale, "total": total, "filled": filled, "ratio": ratio, "file": pack_file}


def main() -> None:
    parser = argparse.ArgumentParser(description="Show completion status of i18n translation packs.")
    parser.add_argument(
        "--dir",
        default=str(DEFAULT_PACK_DIR),
        help="Pack directory root. Default: src/data/i18n-packs",
    )
    args = parser.parse_args()

    pack_root = Path(args.dir)
    if not pack_root.exists():
        print(f"pack status: directory not found: {pack_root}")
        return

    pack_files = sorted(pack_root.rglob("*.json"))
    if not pack_files:
        print(f"pack status: no json packs found under {pack_root}")
        return

    rows = [summarize_pack(pack_file) for pack_file in pack_files]
    rows.sort(key=lambda item: (item["locale"], str(item["file"])))

    print("locale\tfilled/total\tratio\tfile")
    for row in rows:
        ratio_pct = f"{row['ratio']*100:.1f}%"
        rel = Path(row["file"]).relative_to(ROOT)
        print(f"{row['locale']}\t{row['filled']}/{row['total']}\t{ratio_pct}\t{rel}")


if __name__ == "__main__":
    main()
