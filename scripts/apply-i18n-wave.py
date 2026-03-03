#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
APPLY_SCRIPT = ROOT / "scripts" / "apply-i18n-translation-pack.py"
LOGGER = configure_logging("apply-i18n-wave")


def emit(message: str, *, level: str = "info", stderr: bool = False) -> None:
    if level == "error":
        LOGGER.error("%s", message)
    elif level == "warning":
        LOGGER.warning("%s", message)
    else:
        LOGGER.info("%s", message)


def detect_locale(pack_path: Path) -> str:
    data = json.loads(pack_path.read_text(encoding="utf-8"))
    locale = str(data.get("locale", "")).strip().lower()
    if locale:
        return locale
    stem = pack_path.stem.lower()
    if stem.startswith("i18n-template-"):
        return stem.replace("i18n-template-", "", 1)
    raise ValueError(f"cannot detect locale from pack: {pack_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply a directory of translation packs in sequence.")
    parser.add_argument("--wave-dir", required=True, help="Directory containing pack json files.")
    parser.add_argument(
        "--locales",
        help="Comma-separated locales filter, e.g. fr,de,ru. Default: apply all packs in wave-dir.",
    )
    parser.add_argument("--strict", action="store_true", help="Enable strict validation for each pack.")
    parser.add_argument("--dry-run", action="store_true", help="Validate all packs without writing copy file.")
    args = parser.parse_args()

    wave_dir = Path(args.wave_dir)
    if not wave_dir.exists():
        emit(f"apply-wave failed: directory not found: {wave_dir}", level="error")
        sys.exit(1)
    if not APPLY_SCRIPT.exists():
        emit(f"apply-wave failed: missing script: {APPLY_SCRIPT}", level="error")
        sys.exit(1)

    locale_filter = None
    if args.locales:
        locale_filter = {x.strip().lower() for x in args.locales.split(",") if x.strip()}

    packs = sorted(wave_dir.glob("*.json"))
    if not packs:
        emit(f"apply-wave failed: no pack files under {wave_dir}", level="error")
        sys.exit(1)

    selected: list[tuple[str, Path]] = []
    for pack in packs:
        try:
            locale = detect_locale(pack)
        except Exception as exc:
            emit(f"apply-wave failed: {exc}", level="error")
            sys.exit(1)
        if locale_filter and locale not in locale_filter:
            continue
        selected.append((locale, pack))

    if not selected:
        emit("apply-wave failed: no packs matched locale filter", level="error")
        sys.exit(1)

    for locale, pack in selected:
        cmd = [sys.executable, str(APPLY_SCRIPT), "--locale", locale, "--pack", str(pack)]
        if args.strict:
            cmd.append("--strict")
        if args.dry_run:
            cmd.append("--dry-run")
        result = subprocess.run(cmd, cwd=ROOT)
        if result.returncode != 0:
            emit(f"apply-wave failed on locale={locale} pack={pack}", level="error")
            sys.exit(result.returncode)

    mode = "dry-run" if args.dry_run else "apply"
    emit(f"apply-wave {mode} complete: locales={','.join(locale for locale, _ in selected)}")


if __name__ == "__main__":
    main()
