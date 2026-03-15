#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
from pathlib import Path

from logging_utils import configure_logging


LOGGER = configure_logging("build-cn-site")
ROOT = Path(__file__).resolve().parents[1]


def astro_command() -> list[str]:
    if os.name == "nt":
        candidate = ROOT / "node_modules" / ".bin" / "astro.cmd"
    else:
        candidate = ROOT / "node_modules" / ".bin" / "astro"
    if candidate.exists():
        return [str(candidate), "build"]
    return ["npx", "astro", "build"]


def run_step(cmd: list[str], env: dict[str, str]) -> None:
    LOGGER.info("run: %s", " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT, env=env)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def copy_overwrite(src: Path, dst: Path) -> None:
    if dst.exists():
        if dst.is_dir():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def materialize_cn_root(dist_dir: Path) -> None:
    en_dir = dist_dir / "en"
    if not en_dir.exists() or not en_dir.is_dir():
        LOGGER.warning("skip cn root materialization: missing %s", en_dir)
        return

    copied = 0
    for entry in en_dir.iterdir():
        target = dist_dir / entry.name
        copy_overwrite(entry, target)
        copied += 1
    LOGGER.info("materialized cn root from /en: copied_entries=%s", copied)


def overlay_cn_root_from_zh(dist_dir: Path) -> None:
    zh_dir = dist_dir / "zh"
    if not zh_dir.exists() or not zh_dir.is_dir():
        LOGGER.warning("skip cn zh overlay: missing %s", zh_dir)
        return
    copied = 0
    for entry in zh_dir.iterdir():
        target = dist_dir / entry.name
        copy_overwrite(entry, target)
        copied += 1
    LOGGER.info("overlayed cn root from /zh: copied_entries=%s", copied)


def normalize_cn_redirects(dist_dir: Path) -> None:
    redirects = dist_dir / "_redirects"
    if not redirects.exists():
        LOGGER.warning("skip cn redirect normalization: missing %s", redirects)
        return

    lines = redirects.read_text(encoding="utf-8").splitlines()
    normalized: list[str] = []
    for raw in lines:
        line = raw.strip()
        if line.lower() == "/ /en/ 301":
            continue
        normalized.append(raw)

    required_rules = [
        "/en / 301",
        "/en/ / 301",
        "/en/* /:splat 301",
    ]
    existing = {line.strip() for line in normalized}
    for rule in required_rules:
        if rule not in existing:
            normalized.append(rule)

    redirects.write_text("\n".join(normalized).rstrip() + "\n", encoding="utf-8")
    LOGGER.info("normalized cn redirects: %s", redirects)


def main() -> None:
    env = os.environ.copy()
    env["BUILD_TARGET"] = "cn"
    env.setdefault("SITE_URL", "https://localvram.cn")
    dist_dir = ROOT / "dist-cn"

    run_step(astro_command(), env)
    run_step([sys.executable, "scripts/rewrite-cn-html-links.py", "--dist", "dist-cn"], env)
    materialize_cn_root(dist_dir)
    overlay_cn_root_from_zh(dist_dir)
    normalize_cn_redirects(dist_dir)
    run_step([sys.executable, "scripts/build-sitemap.py", "--target", "cn", "--out-dir", "dist-cn"], env)
    run_step([sys.executable, "scripts/check-cn-artifact-integrity.py", "--dist", "dist-cn"], env)
    LOGGER.info("CN build completed: dist-cn")


if __name__ == "__main__":
    main()
