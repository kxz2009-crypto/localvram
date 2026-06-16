#!/usr/bin/env python3
"""AI hotspot auto-publisher: X/Twitter trending → WeChat Official Account draft."""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from logging_utils import configure_logging

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
LOG_FILE = ROOT / "src" / "data" / "hotspot-publish-log.json"
AUTH_DIR = Path(__file__).resolve().parent / ".wechat-auth"
STORAGE_STATE_FILE = AUTH_DIR / "storage_state.json"
OUTPUT_DIR = ROOT / "content-queue" / "hotspot"

LOGGER = configure_logging("ai-hotspot-publisher")

# ---------------------------------------------------------------------------
# Config from env
# ---------------------------------------------------------------------------
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
APIMART_API_KEY = os.getenv("APIMART_API_KEY", "").strip()
WECHAT_HEADLESS = os.getenv("WECHAT_HEADLESS", "false").lower() in ("1", "true", "yes")
WECHAT_SKIP_UPLOAD = os.getenv("WECHAT_SKIP_UPLOAD", "false").lower() in ("1", "true", "yes")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default if default is not None else []
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ===========================================================================
# STEP 1: Tavily Search
# ===========================================================================
def search_ai_hotspots() -> dict[str, Any]:
    """Search X/Twitter for trending AI topics in the last 24 hours via Tavily."""
    from tavily import TavilyClient

    if not TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY not set")

    client = TavilyClient(api_key=TAVILY_API_KEY)

    LOGGER.info("Searching AI hotspots on X/Twitter (last 24h)...")
    results = client.search(
        query="AI artificial intelligence new model release breakthrough",
        search_depth="advanced",
        topic="news",
        include_domains=["x.com", "twitter.com"],
        max_results=10,
        days=1,
    )

    items = results.get("results", [])

    if not items:
        LOGGER.info("No X results, trying broader search...")
        results = client.search(
            query="AI model release breakthrough trending",
            search_depth="advanced",
            topic="news",
            max_results=10,
            days=1,
        )
        items = results.get("results", [])

    if not items:
        raise RuntimeError("No AI hotspot found in last 24 hours")

    best = items[0]
    key_facts = [item.get("content", "")[:200] for item in items[:5] if item.get("content")]
    source_urls = [item.get("url", "") for item in items[:5] if item.get("url")]

    topic = {
        "title": best.get("title", "AI Hot Topic"),
        "summary": best.get("content", "")[:500],
        "key_facts": key_facts,
        "source_urls": source_urls,
    }
    LOGGER.info("Selected topic: %s", topic["title"])
    return topic


# ===========================================================================
# STEP 2: Generate Article with Claude
# ===========================================================================

ARTICLE_SYSTEM_PROMPT = """你是一位专业的微信公众号编辑，专注于AI技术领域内容创作。

写作要求：
- 面向中国科技爱好者，语言生动有趣但不失专业性
- 标题吸引眼球，不超过30个字
- 开头用一个引人入胜的hook抓住读者
- 正文分2-3个小节，每节有小标题
- 结尾有总结和互动引导（如"你怎么看？欢迎留言讨论"）
- 总字数1500-2500字
- 输出格式为Markdown
- 不要使用emoji
- 适当引用数据和事实增加可信度

输出格式：
第一行是标题（不带#号），空一行后是正文Markdown。"""

ARTICLE_USER_TEMPLATE = """请根据以下AI热点素材，撰写一篇微信公众号文章：

话题：{title}

摘要：{summary}

关键信息：
{facts}

来源：{urls}

请写一篇深入浅出、有观点有态度的公众号文章。注意结合本地部署AI模型的视角，给读者实用的参考。"""


def generate_article(topic: dict[str, Any]) -> dict[str, str]:
    """Generate a WeChat article using Claude API."""
    import anthropic

    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    facts_text = "\n".join(f"- {f}" for f in topic["key_facts"])
    urls_text = "\n".join(topic["source_urls"][:3])

    user_msg = ARTICLE_USER_TEMPLATE.format(
        title=topic["title"],
        summary=topic["summary"],
        facts=facts_text,
        urls=urls_text,
    )

    LOGGER.info("Generating article with Claude...")
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        temperature=0.7,
        system=ARTICLE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )

    text = response.content[0].text.strip()
    lines = text.split("\n", 1)
    title = lines[0].strip().lstrip("#").strip()
    markdown = lines[1].strip() if len(lines) > 1 else text

    LOGGER.info("Article generated: %s (%d chars)", title, len(markdown))
    return {"title": title, "markdown": markdown}


# ===========================================================================
# STEP 3: Generate Cover Image via apimart.ai
# ===========================================================================

def _submit_image_task(prompt: str) -> str:
    """Submit image generation task to apimart.ai, return task_id."""
    url = "https://api.apimart.ai/v1/images/generations"
    payload = json.dumps({
        "model": "gpt-4o-image",
        "prompt": prompt,
        "size": "3:2",
        "n": 1,
    }).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {APIMART_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    task_id = data["data"][0]["task_id"]
    LOGGER.info("Image task submitted: %s", task_id)
    return task_id


def _poll_image_task(task_id: str, timeout_s: int = 120, interval_s: int = 5) -> str | None:
    """Poll task status until completed. Returns image URL or None."""
    deadline = time.time() + timeout_s
    url = f"https://api.apimart.ai/v1/tasks/{task_id}"
    headers = {"Authorization": f"Bearer {APIMART_API_KEY}"}

    while time.time() < deadline:
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
        except (urllib.error.URLError, OSError) as exc:
            LOGGER.warning("Poll request failed: %s", exc)
            time.sleep(interval_s)
            continue

        status = data.get("status", "")
        if status == "completed":
            images = data.get("result", {}).get("images", [])
            if images:
                img_url = images[0].get("url", "")
                if isinstance(img_url, list):
                    img_url = img_url[0] if img_url else ""
                return img_url or None
            return None
        elif status == "failed":
            LOGGER.warning("Image generation failed: %s", data.get("error", "unknown"))
            return None

        time.sleep(interval_s)

    LOGGER.warning("Image generation timed out after %ds", timeout_s)
    return None


def _download_image(url: str, dest: Path) -> Path:
    """Download image from URL to local path."""
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as resp:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(resp.read())
    return dest


def generate_cover_image(topic_title: str) -> Path | None:
    """Generate a cover image for the article. Returns local path or None on failure."""
    if not APIMART_API_KEY:
        LOGGER.warning("APIMART_API_KEY not set, skipping image generation")
        return None

    prompt = (
        f"A modern minimalist tech illustration for an article about: {topic_title}. "
        "Clean geometric lines, blue and white color scheme, abstract AI neural network elements, "
        "gradient background, no text, no watermark, suitable as WeChat article cover image."
    )

    try:
        task_id = _submit_image_task(prompt)
        image_url = _poll_image_task(task_id)
        if not image_url:
            return None

        timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S")
        dest = AUTH_DIR / f"cover_{timestamp}.png"
        _download_image(image_url, dest)
        LOGGER.info("Cover image saved: %s", dest)
        return dest
    except (urllib.error.URLError, OSError, KeyError, IndexError) as exc:
        LOGGER.warning("Image generation failed: %s", exc)
        return None


# ===========================================================================
# STEP 4: Markdown → WeChat HTML
# ===========================================================================

WECHAT_STYLES = {
    "section": "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',sans-serif;font-size:16px;line-height:1.8;color:#333;padding:0 8px;",
    "h1": "font-size:22px;font-weight:700;color:#1a1a1a;margin:24px 0 12px;border-bottom:2px solid #2b7de9;padding-bottom:8px;",
    "h2": "font-size:18px;font-weight:600;color:#1a1a1a;margin:20px 0 10px;padding-left:10px;border-left:3px solid #2b7de9;",
    "h3": "font-size:16px;font-weight:600;color:#333;margin:16px 0 8px;",
    "p": "margin:12px 0;text-align:justify;",
    "blockquote": "margin:16px 0;padding:12px 16px;border-left:4px solid #2b7de9;background:#f6f8fa;color:#555;font-size:15px;",
    "code_inline": "background:#f0f4f8;color:#d63384;padding:2px 6px;border-radius:3px;font-size:14px;font-family:'SF Mono',Consolas,monospace;",
    "code_block": "background:#1e293b;color:#e2e8f0;padding:16px;border-radius:6px;font-size:14px;line-height:1.5;overflow-x:auto;font-family:'SF Mono',Consolas,monospace;white-space:pre-wrap;",
    "ul": "margin:12px 0;padding-left:24px;",
    "ol": "margin:12px 0;padding-left:24px;",
    "li": "margin:6px 0;",
    "strong": "color:#1a1a1a;font-weight:600;",
    "hr": "border:none;border-top:1px solid #e5e7eb;margin:24px 0;",
}


def markdown_to_wechat_html(markdown: str) -> str:
    """Convert Markdown to WeChat-compatible HTML with inline styles."""
    lines = markdown.split("\n")
    html_parts: list[str] = []
    in_code_block = False
    code_buffer: list[str] = []
    in_list = False
    list_type = ""

    def _inline(text: str) -> str:
        text = html.escape(text, quote=False)
        text = re.sub(r"`([^`]+)`", rf'<code style="{WECHAT_STYLES["code_inline"]}">\1</code>', text)
        text = re.sub(r"\*\*(.+?)\*\*", rf'<strong style="{WECHAT_STYLES["strong"]}">\1</strong>', text)
        text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        return text

    def _close_list():
        nonlocal in_list, list_type
        if in_list:
            tag = "ul" if list_type == "ul" else "ol"
            html_parts.append(f"</{tag}>")
            in_list = False

    for line in lines:
        if line.startswith("```"):
            if in_code_block:
                code_text = "\n".join(code_buffer)
                html_parts.append(f'<pre style="{WECHAT_STYLES["code_block"]}">{code_text}</pre>')
                code_buffer = []
                in_code_block = False
            else:
                _close_list()
                in_code_block = True
            continue

        if in_code_block:
            code_buffer.append(html.escape(line, quote=False))
            continue

        stripped = line.strip()

        if not stripped:
            _close_list()
            continue

        if stripped.startswith("### "):
            _close_list()
            html_parts.append(f'<h3 style="{WECHAT_STYLES["h3"]}">{_inline(stripped[4:])}</h3>')
        elif stripped.startswith("## "):
            _close_list()
            html_parts.append(f'<h2 style="{WECHAT_STYLES["h2"]}">{_inline(stripped[3:])}</h2>')
        elif stripped.startswith("# "):
            _close_list()
            html_parts.append(f'<h1 style="{WECHAT_STYLES["h1"]}">{_inline(stripped[2:])}</h1>')
        elif stripped.startswith("> "):
            _close_list()
            html_parts.append(f'<blockquote style="{WECHAT_STYLES["blockquote"]}">{_inline(stripped[2:])}</blockquote>')
        elif stripped == "---" or stripped == "***":
            _close_list()
            html_parts.append(f'<hr style="{WECHAT_STYLES["hr"]}"/>')
        elif re.match(r"^[-*]\s", stripped):
            content = re.sub(r"^[-*]\s+", "", stripped)
            if not in_list or list_type != "ul":
                _close_list()
                html_parts.append(f'<ul style="{WECHAT_STYLES["ul"]}">')
                in_list = True
                list_type = "ul"
            html_parts.append(f'<li style="{WECHAT_STYLES["li"]}">{_inline(content)}</li>')
        elif re.match(r"^\d+\.\s", stripped):
            content = re.sub(r"^\d+\.\s+", "", stripped)
            if not in_list or list_type != "ol":
                _close_list()
                html_parts.append(f'<ol style="{WECHAT_STYLES["ol"]}">')
                in_list = True
                list_type = "ol"
            html_parts.append(f'<li style="{WECHAT_STYLES["li"]}">{_inline(content)}</li>')
        else:
            _close_list()
            html_parts.append(f'<p style="{WECHAT_STYLES["p"]}">{_inline(stripped)}</p>')

    _close_list()
    if in_code_block and code_buffer:
        code_text = "\n".join(code_buffer)
        html_parts.append(f'<pre style="{WECHAT_STYLES["code_block"]}">{code_text}</pre>')

    body = "\n".join(html_parts)
    return f'<section style="{WECHAT_STYLES["section"]}">\n{body}\n</section>'


# ===========================================================================
# STEP 5: Playwright Upload to WeChat
# ===========================================================================

def _ensure_wechat_login(page: Any) -> bool:
    """Ensure we are logged into mp.weixin.qq.com. Returns True if logged in."""
    page.goto("https://mp.weixin.qq.com", wait_until="domcontentloaded", timeout=30000)
    time.sleep(2)

    if "/cgi-bin/home" in page.url or "/cgi-bin/appmsg" in page.url:
        LOGGER.info("WeChat session still valid")
        return True

    if WECHAT_HEADLESS:
        LOGGER.error("WeChat session expired, cannot scan QR in headless mode")
        print("\n" + "=" * 60)
        print("ACTION REQUIRED: WeChat login expired.")
        print("Run locally with WECHAT_HEADLESS=false to re-scan QR code.")
        print("=" * 60 + "\n")
        return False

    print("\n" + "=" * 60)
    print("Please scan the QR code in the browser to log in to WeChat.")
    print("Waiting up to 120 seconds...")
    print("=" * 60 + "\n")

    try:
        page.wait_for_url("**/cgi-bin/home**", timeout=120000)
    except Exception:
        LOGGER.error("WeChat login timed out")
        return False

    page.context.storage_state(path=str(STORAGE_STATE_FILE))
    LOGGER.info("WeChat login successful, session saved")
    return True


def upload_to_wechat_draft(html_content: str, title: str, cover_image_path: Path | None) -> bool:
    """Upload article to WeChat Official Account draft box via Playwright."""
    from playwright.sync_api import sync_playwright

    AUTH_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser_args: dict[str, Any] = {"headless": WECHAT_HEADLESS}
        if STORAGE_STATE_FILE.exists():
            browser_args["storage_state"] = str(STORAGE_STATE_FILE)

        browser = p.chromium.launch(headless=WECHAT_HEADLESS)
        context = browser.new_context(
            storage_state=str(STORAGE_STATE_FILE) if STORAGE_STATE_FILE.exists() else None,
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        try:
            if not _ensure_wechat_login(page):
                return False

            LOGGER.info("Navigating to article editor...")
            page.goto(
                "https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit&action=edit&type=77&lang=zh_CN",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            time.sleep(3)

            title_input = page.locator("#title")
            if title_input.count() > 0:
                title_input.fill(title)
                LOGGER.info("Title set: %s", title)
            else:
                title_input = page.locator('[placeholder*="标题"]')
                if title_input.count() > 0:
                    title_input.fill(title)

            if cover_image_path and cover_image_path.exists():
                cover_btn = page.locator(".js_cover_area, .cover-ct, [class*='cover']").first
                if cover_btn.count() > 0:
                    cover_btn.click()
                    time.sleep(1)
                    upload_input = page.locator("input[type='file']").first
                    if upload_input.count() > 0:
                        upload_input.set_input_files(str(cover_image_path))
                        time.sleep(3)
                        confirm_btn = page.locator("button:has-text('确定'), .js_submit").first
                        if confirm_btn.count() > 0:
                            confirm_btn.click()
                            time.sleep(2)
                            LOGGER.info("Cover image uploaded")

            editor = page.locator("#edui1_contentplaceholder, .edui-body-container, #js_editor").first
            if editor.count() > 0:
                page.evaluate(
                    """(html) => {
                        const editor = document.querySelector('#edui1_contentplaceholder, .edui-body-container, #js_editor');
                        if (editor) editor.innerHTML = html;
                    }""",
                    html_content,
                )
                LOGGER.info("Article content injected")
            else:
                iframe = page.frame_locator("iframe").first
                iframe.locator("body").evaluate("(el, html) => el.innerHTML = html", html_content)
                LOGGER.info("Article content injected via iframe")

            time.sleep(2)
            save_btn = page.locator("#js_submit, button:has-text('保存'), .js_save").first
            if save_btn.count() > 0:
                save_btn.click()
                time.sleep(3)
                LOGGER.info("Draft saved successfully")

            context.storage_state(path=str(STORAGE_STATE_FILE))
            return True

        except Exception as exc:
            LOGGER.error("WeChat upload failed: %s", exc)
            fallback_path = OUTPUT_DIR / f"fallback_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d%H%M%S')}.html"
            fallback_path.parent.mkdir(parents=True, exist_ok=True)
            fallback_path.write_text(html_content, encoding="utf-8")
            LOGGER.info("HTML saved as fallback: %s", fallback_path)
            return False
        finally:
            browser.close()


# ===========================================================================
# STEP 6: Logging & Main
# ===========================================================================

def append_run_log(entry: dict[str, Any]) -> None:
    """Append run result to log file, keep last 30 entries."""
    history = load_json(LOG_FILE, [])
    history.insert(0, entry)
    history = history[:30]
    save_json(LOG_FILE, history)


def main() -> None:
    LOGGER.info("=== AI Hotspot Publisher started ===")
    run_entry: dict[str, Any] = {
        "run_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "topic_title": None,
        "article_title": None,
        "image_generated": False,
        "wechat_uploaded": False,
        "status": "failed",
        "error": None,
    }

    try:
        topic = search_ai_hotspots()
        run_entry["topic_title"] = topic["title"]

        article = generate_article(topic)
        run_entry["article_title"] = article["title"]

        cover_path = generate_cover_image(article["title"])
        run_entry["image_generated"] = cover_path is not None

        html_content = markdown_to_wechat_html(article["markdown"])

        if WECHAT_SKIP_UPLOAD:
            output_path = OUTPUT_DIR / f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d')}.html"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html_content, encoding="utf-8")
            LOGGER.info("WECHAT_SKIP_UPLOAD=true, HTML saved to: %s", output_path)
            run_entry["wechat_uploaded"] = False
            run_entry["status"] = "generated"
        else:
            uploaded = upload_to_wechat_draft(html_content, article["title"], cover_path)
            run_entry["wechat_uploaded"] = uploaded
            run_entry["status"] = "success" if uploaded else "upload_failed"

    except RuntimeError as exc:
        run_entry["error"] = str(exc)
        LOGGER.error("Pipeline failed: %s", exc)
    except Exception as exc:
        run_entry["error"] = f"{type(exc).__name__}: {exc}"
        LOGGER.error("Unexpected error: %s", exc, exc_info=True)
    finally:
        append_run_log(run_entry)

    if run_entry["status"] == "success":
        print("\n" + "=" * 60)
        print("DONE! Article draft saved to WeChat Official Account.")
        print(f"Title: {run_entry['article_title']}")
        print("Please go to https://mp.weixin.qq.com to review the draft.")
        print("=" * 60 + "\n")
    elif run_entry["status"] == "generated":
        print("\n" + "=" * 60)
        print("Article generated (upload skipped).")
        print(f"Title: {run_entry['article_title']}")
        print(f"HTML saved to: content-queue/hotspot/")
        print("=" * 60 + "\n")
    else:
        print(f"\nPipeline ended with status: {run_entry['status']}")
        if run_entry["error"]:
            print(f"Error: {run_entry['error']}")


if __name__ == "__main__":
    main()
