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


def overlay_cn_home_root(dist_dir: Path) -> None:
    zh_home = dist_dir / "zh" / "index.html"
    if not zh_home.exists() or not zh_home.is_file():
        LOGGER.warning("skip cn home overlay: missing %s", zh_home)
        return
    target = dist_dir / "index.html"
    copy_overwrite(zh_home, target)
    LOGGER.info("overlayed cn home root from /zh/index.html -> /index.html")


def overlay_cn_tools_index(dist_dir: Path) -> None:
    zh_tools_index = dist_dir / "zh" / "tools" / "index.html"
    if not zh_tools_index.exists() or not zh_tools_index.is_file():
        LOGGER.warning("skip cn tools index overlay: missing %s", zh_tools_index)
        return

    target = dist_dir / "tools" / "index.html"
    copy_overwrite(zh_tools_index, target)
    LOGGER.info("overlayed cn tools index from /zh/tools/index.html -> /tools/index.html")


def overlay_cn_guides_index(dist_dir: Path) -> None:
    zh_guides_index = dist_dir / "zh" / "guides" / "index.html"
    if not zh_guides_index.exists() or not zh_guides_index.is_file():
        LOGGER.warning("skip cn guides index overlay: missing %s", zh_guides_index)
        return

    target = dist_dir / "guides" / "index.html"
    copy_overwrite(zh_guides_index, target)
    LOGGER.info("overlayed cn guides index from /zh/guides/index.html -> /guides/index.html")


def overlay_cn_blog_root(dist_dir: Path) -> None:
    zh_blog_dir = dist_dir / "zh" / "blog"
    if not zh_blog_dir.exists() or not zh_blog_dir.is_dir():
        LOGGER.warning("skip cn blog root overlay: missing %s", zh_blog_dir)
        return

    target = dist_dir / "blog"
    copy_overwrite(zh_blog_dir, target)
    LOGGER.info("overlayed cn blog root from /zh/blog -> /blog")


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
    overlay_cn_home_root(dist_dir)
    overlay_cn_tools_index(dist_dir)
    overlay_cn_guides_index(dist_dir)
    overlay_cn_blog_root(dist_dir)
    normalize_cn_redirects(dist_dir)
    run_step([sys.executable, "scripts/build-sitemap.py", "--target", "cn", "--out-dir", "dist-cn"], env)
    run_step([sys.executable, "scripts/check-cn-artifact-integrity.py", "--dist", "dist-cn"], env)
    LOGGER.info("CN build completed: dist-cn")


if __name__ == "__main__":
    main()
