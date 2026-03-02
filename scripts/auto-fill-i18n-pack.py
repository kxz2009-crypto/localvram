#!/usr/bin/env python3
import argparse
import json
import re
import sys
import time
from pathlib import Path

try:
    from deep_translator import GoogleTranslator
except Exception as exc:  # pragma: no cover - runtime import guard
    raise SystemExit(
        f"auto-fill failed: deep-translator is required ({exc}). Install via: python -m pip install deep-translator"
    )


ROOT = Path(__file__).resolve().parents[1]
GLOSSARY_PATH = ROOT / "src" / "data" / "i18n-glossary.json"
PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z0-9_]+\}")


def load_protected_terms() -> list[str]:
    if not GLOSSARY_PATH.exists():
        return []
    payload = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))
    terms = payload.get("protected_terms", [])
    if not isinstance(terms, list):
        return []
    return [str(t).strip() for t in terms if str(t).strip()]


def mask_text(text: str, protected_terms: list[str]) -> tuple[str, dict[str, str]]:
    masked = text
    token_map: dict[str, str] = {}
    token_idx = 0

    placeholders = sorted(set(PLACEHOLDER_RE.findall(masked)), key=len, reverse=True)
    for ph in placeholders:
        token = f"LVPH{token_idx}TOKEN"
        token_idx += 1
        masked = masked.replace(ph, token)
        token_map[token] = ph

    for term in sorted(protected_terms, key=len, reverse=True):
        if term not in masked:
            continue
        token = f"LVPT{token_idx}TOKEN"
        token_idx += 1
        masked = masked.replace(term, token)
        token_map[token] = term

    return masked, token_map


def unmask_text(text: str, token_map: dict[str, str]) -> str:
    restored = text
    for token, original in token_map.items():
        restored = restored.replace(token, original)
    return restored


def fill_pack(pack_path: Path, only_empty: bool = True) -> tuple[int, int, int, str]:
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    locale = str(pack.get("locale", "")).strip().lower()
    if not locale:
        raise ValueError(f"pack missing locale: {pack_path}")

    phrases = pack.get("phrases")
    if not isinstance(phrases, list):
        raise ValueError(f"pack phrases must be array: {pack_path}")

    protected_terms = load_protected_terms()

    batch_inputs: list[str] = []
    batch_indices: list[int] = []
    batch_maps: list[dict[str, str]] = []

    for idx, row in enumerate(phrases):
        if not isinstance(row, dict):
            continue
        en = str(row.get("en", ""))
        tr = str(row.get("translation", ""))
        if not en.strip():
            continue
        if only_empty and tr.strip():
            continue
        masked, token_map = mask_text(en, protected_terms)
        batch_inputs.append(masked)
        batch_indices.append(idx)
        batch_maps.append(token_map)

    if not batch_inputs:
        return 0, 0, len(phrases), locale

    translator = GoogleTranslator(source="en", target=locale)
    updated = 0
    failed = 0
    for i, masked_text in enumerate(batch_inputs):
        idx = batch_indices[i]
        token_map = batch_maps[i]
        translated = ""
        try:
            translated = str(translator.translate(masked_text) or "").strip()
        except Exception:
            # Retry once after a brief pause for transient provider glitches.
            time.sleep(0.25)
            try:
                translated = str(translator.translate(masked_text) or "").strip()
            except Exception:
                failed += 1
                continue

        out = unmask_text(translated, token_map)
        if out:
            phrases[idx]["translation"] = out
            updated += 1

    pack["phrases"] = phrases
    pack_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return updated, failed, len(phrases), locale


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-fill i18n translation packs using machine translation.")
    parser.add_argument("--pack", help="Single pack file path.")
    parser.add_argument("--wave-dir", help="Directory containing pack json files.")
    parser.add_argument("--locales", help="Comma-separated locale filter for --wave-dir.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing non-empty translations. Default: only fill empty entries.",
    )
    args = parser.parse_args()

    if not args.pack and not args.wave_dir:
        print("auto-fill failed: provide --pack or --wave-dir")
        sys.exit(1)

    pack_files: list[Path] = []
    if args.pack:
        pack_files.append(Path(args.pack))
    if args.wave_dir:
        pack_files.extend(sorted(Path(args.wave_dir).glob("*.json")))

    if not pack_files:
        print("auto-fill failed: no pack files found")
        sys.exit(1)

    locale_filter = None
    if args.locales:
        locale_filter = {x.strip().lower() for x in args.locales.split(",") if x.strip()}

    total_updated = 0
    for pack_file in pack_files:
        if not pack_file.exists():
            print(f"auto-fill failed: pack file not found: {pack_file}")
            sys.exit(1)
        data = json.loads(pack_file.read_text(encoding="utf-8"))
        locale = str(data.get("locale", "")).strip().lower()
        if locale_filter and locale not in locale_filter:
            continue
        updated, failed, total, locale = fill_pack(pack_file, only_empty=not args.overwrite)
        total_updated += updated
        print(f"auto-filled locale={locale} updated={updated}/{total} failed={failed} file={pack_file}")

    print(f"auto-fill complete: total_updated={total_updated}")


if __name__ == "__main__":
    main()
