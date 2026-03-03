#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from logging_utils import configure_logging


LOGGER = configure_logging("diff-i18n-section-parity")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Diff i18n section parity summary files.")
    parser.add_argument("--current", required=True, help="Path to current parity summary JSON.")
    parser.add_argument("--previous", default="", help="Path to previous parity summary JSON.")
    parser.add_argument("--out", required=True, help="Path to output diff JSON.")
    args = parser.parse_args()

    current_path = Path(args.current)
    previous_path = Path(args.previous) if args.previous else None
    out_path = Path(args.out)

    if not current_path.exists():
        LOGGER.error("missing current summary file: %s", current_path)
        return 1

    current = _load_json(current_path)
    previous = _load_json(previous_path) if previous_path and previous_path.exists() else None

    locales = current.get("target_locales", []) if isinstance(current, dict) else []
    sections = current.get("key_sections", []) if isinstance(current, dict) else []
    current_counts = current.get("locale_section_counts", {}) if isinstance(current, dict) else {}
    current_parity = current.get("locale_section_parity", {}) if isinstance(current, dict) else {}

    prev_counts = previous.get("locale_section_counts", {}) if isinstance(previous, dict) else {}
    prev_parity = previous.get("locale_section_parity", {}) if isinstance(previous, dict) else {}

    count_deltas: list[dict[str, object]] = []
    parity_deltas: list[dict[str, object]] = []
    mismatch_delta = 0
    if previous is not None:
        for locale in locales:
            for section in sections:
                cur_count = int(current_counts.get(locale, {}).get(section, 0) or 0)
                prev_count = int(prev_counts.get(locale, {}).get(section, 0) or 0)
                delta = cur_count - prev_count
                if delta != 0:
                    count_deltas.append(
                        {
                            "locale": locale,
                            "section": section,
                            "previous": prev_count,
                            "current": cur_count,
                            "delta": delta,
                        }
                    )

                cur_ratio = _to_float(current_parity.get(locale, {}).get(section))
                prev_ratio = _to_float(prev_parity.get(locale, {}).get(section))
                if cur_ratio is None and prev_ratio is None:
                    continue
                if cur_ratio is None or prev_ratio is None:
                    parity_deltas.append(
                        {
                            "locale": locale,
                            "section": section,
                            "previous": prev_ratio,
                            "current": cur_ratio,
                            "delta": None,
                        }
                    )
                    continue
                ratio_delta = cur_ratio - prev_ratio
                if abs(ratio_delta) > 1e-9:
                    parity_deltas.append(
                        {
                            "locale": locale,
                            "section": section,
                            "previous": prev_ratio,
                            "current": cur_ratio,
                            "delta": round(ratio_delta, 6),
                        }
                    )

        current_mismatch = int(current.get("counts", {}).get("mismatch_count", 0) or 0)
        previous_mismatch = int(previous.get("counts", {}).get("mismatch_count", 0) or 0)
        mismatch_delta = current_mismatch - previous_mismatch

    result = {
        "previous_available": previous is not None,
        "has_drift": bool(count_deltas or parity_deltas or mismatch_delta != 0),
        "counts": {
            "count_delta_items": len(count_deltas),
            "parity_delta_items": len(parity_deltas),
            "mismatch_delta": mismatch_delta,
        },
        "count_deltas": count_deltas,
        "parity_deltas": parity_deltas,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOGGER.info(
        "section parity diff generated: file=%s previous_available=%s drift=%s",
        out_path,
        result["previous_available"],
        result["has_drift"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
