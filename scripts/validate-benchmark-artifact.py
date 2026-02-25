#!/usr/bin/env python3
import argparse
import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_JSON_FILES = [
    "src/data/status.json",
    "src/data/benchmark-results.json",
    "src/data/cluster-benchmarks.json",
    "src/data/benchmark-changelog.json",
]
DEFAULT_COPY_OPTIONAL = [
    "src/data/runner-status.json",
    "src/data/pipeline-status.json",
    "src/data/weekly-target-plan.json",
]
DEFAULT_COPY_DIRS = [
    "logs",
    "public/screenshots",
]


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def resolve_source_dir(source_dir: Path, rel_files: list[str]) -> Path:
    direct_ok = any((source_dir / rel).exists() for rel in rel_files)
    if direct_ok:
        return source_dir
    children = [p for p in source_dir.iterdir() if p.is_dir()]
    if len(children) == 1:
        child = children[0]
        child_ok = any((child / rel).exists() for rel in rel_files)
        if child_ok:
            return child
    return source_dir


def ensure_json_files(source_dir: Path, rel_files: list[str]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for rel in rel_files:
        path = source_dir / rel
        if not path.exists():
            errors.append(f"missing file: {rel}")
            continue
        try:
            load_json(path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"invalid json: {rel}: {exc}")
    return (len(errors) == 0, errors)


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_tree(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def apply_artifact(source_dir: Path) -> list[str]:
    copied: list[str] = []
    for rel in REQUIRED_JSON_FILES + DEFAULT_COPY_OPTIONAL:
        src = source_dir / rel
        if not src.exists():
            continue
        dst = ROOT / rel
        copy_file(src, dst)
        copied.append(rel)

    for rel in DEFAULT_COPY_DIRS:
        src = source_dir / rel
        if not src.exists() or not src.is_dir():
            continue
        dst = ROOT / rel
        copy_tree(src, dst)
        copied.append(rel + "/")
    return copied


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate/apply benchmark collection artifacts.")
    parser.add_argument("--source-dir", required=True, help="Extracted artifact directory")
    parser.add_argument("--apply", action="store_true", help="Copy validated artifact files into the repository")
    parser.add_argument("--report-file", default="", help="Optional JSON report output path")
    args = parser.parse_args()

    source_dir = Path(args.source_dir).resolve()
    if not source_dir.exists():
        print(f"artifact validation failed: source dir not found: {source_dir}")
        sys.exit(1)

    source_dir = resolve_source_dir(source_dir, REQUIRED_JSON_FILES)
    ok, errors = ensure_json_files(source_dir, REQUIRED_JSON_FILES)
    report: dict[str, object] = {
        "ok": ok,
        "source_dir": str(source_dir),
        "errors": errors,
        "copied": [],
    }

    if not ok:
        print("artifact validation failed")
        for err in errors:
            print(f"- {err}")
    else:
        print("artifact validation passed")

    if ok and args.apply:
        copied = apply_artifact(source_dir)
        report["copied"] = copied
        print(f"artifact apply completed: copied={len(copied)}")

    if args.report_file:
        out_path = (ROOT / args.report_file).resolve() if not Path(args.report_file).is_absolute() else Path(args.report_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"report written: {out_path}")

    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
