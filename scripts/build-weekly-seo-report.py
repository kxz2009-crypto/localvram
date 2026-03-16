#!/usr/bin/env python3
import datetime as dt
import json
from pathlib import Path


def fmt_num(value: object) -> str:
    try:
        return str(int(value))
    except Exception:  # noqa: BLE001
        return "0"


def fmt_pct(value: object) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except Exception:  # noqa: BLE001
        return "0.0%"


def main() -> None:
    root = Path(".")
    status_path = root / "src" / "data" / "status.json"
    keywords_path = root / "src" / "data" / "search-console-keywords.json"
    opps_path = root / "src" / "data" / "content-opportunities.json"
    report_path = root / "logs" / "weekly-seo-report.md"

    status = json.loads(status_path.read_text(encoding="utf-8"))
    keywords_payload = json.loads(keywords_path.read_text(encoding="utf-8"))
    opps_payload = json.loads(opps_path.read_text(encoding="utf-8"))

    items = keywords_payload.get("items", []) if isinstance(keywords_payload, dict) else []
    items = [item for item in items if isinstance(item, dict)]
    items.sort(key=lambda item: int(item.get("clicks", 0) or 0), reverse=True)

    opps = opps_payload.get("items", []) if isinstance(opps_payload, dict) else []
    opps = [item for item in opps if isinstance(item, dict)]
    opps.sort(
        key=lambda item: (
            int(item.get("search_intent_score", 0) or 0)
            * int(item.get("commercial_intent_score", 0) or 0)
            * int(item.get("freshness_gap_score", 0) or 0)
        ),
        reverse=True,
    )

    generated_at = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    lines: list[str] = []
    lines.append("# Weekly SEO Report")
    lines.append("")
    lines.append(f"- Generated at: {generated_at}")
    lines.append(f"- search_console.updated_at: {keywords_payload.get('updated_at', 'unknown')}")
    lines.append(f"- status.last_verified: {status.get('last_verified', 'unknown')}")
    lines.append(f"- status.freshness_score: {status.get('freshness_score', 'unknown')}")
    lines.append("")
    lines.append("## Top Search Queries (by clicks)")
    lines.append("")
    lines.append("| Keyword | Clicks | Impressions | CTR | Position | Landing |")
    lines.append("| --- | ---: | ---: | ---: | ---: | --- |")

    for row in items[:10]:
        lines.append(
            "| {keyword} | {clicks} | {impr} | {ctr} | {pos} | {landing} |".format(
                keyword=str(row.get("keyword", row.get("query", ""))).replace("|", " ").strip() or "-",
                clicks=fmt_num(row.get("clicks", 0)),
                impr=fmt_num(row.get("impressions", 0)),
                ctr=fmt_pct(row.get("ctr", 0)),
                pos=f"{float(row.get('position', 0) or 0):.1f}",
                landing=str(row.get("landing", "")).replace("|", " ").strip() or "-",
            )
        )

    lines.append("")
    lines.append("## Top Content Opportunities")
    lines.append("")
    lines.append("| Topic | Intent | Commercial | Freshness | Score |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")

    for row in opps[:10]:
        intent = int(row.get("search_intent_score", 0) or 0)
        commercial = int(row.get("commercial_intent_score", 0) or 0)
        freshness = int(row.get("freshness_gap_score", 0) or 0)
        score = intent * commercial * freshness
        lines.append(
            f"| {str(row.get('keyword', row.get('slug', '-'))).replace('|', ' ').strip() or '-'} | "
            f"{intent} | {commercial} | {freshness} | {score} |"
        )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"weekly_seo_report={report_path}")


if __name__ == "__main__":
    main()
