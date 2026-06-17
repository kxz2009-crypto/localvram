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


def metric_int(row: dict, key: str) -> int:
    try:
        return int(float(row.get(key, 0) or 0))
    except Exception:  # noqa: BLE001
        return 0


def metric_float(row: dict, key: str) -> float:
    try:
        return float(row.get(key, 0) or 0)
    except Exception:  # noqa: BLE001
        return 0.0


def keyword(row: dict) -> str:
    return str(row.get("keyword", row.get("query", ""))).replace("|", " ").strip() or "-"


def landing(row: dict) -> str:
    return str(row.get("landing", "")).replace("|", " ").strip() or "-"


def append_search_rows(lines: list[str], rows: list[dict]) -> None:
    lines.append("| Keyword | Clicks | Impressions | CTR | Position | Landing |")
    lines.append("| --- | ---: | ---: | ---: | ---: | --- |")
    for row in rows:
        lines.append(
            "| {keyword} | {clicks} | {impr} | {ctr} | {pos} | {landing} |".format(
                keyword=keyword(row),
                clicks=fmt_num(row.get("clicks", 0)),
                impr=fmt_num(row.get("impressions", 0)),
                ctr=fmt_pct(row.get("ctr", 0)),
                pos=f"{metric_float(row, 'position'):.1f}",
                landing=landing(row),
            )
        )


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
    append_search_rows(lines, items[:10])

    low_ctr = [
        row
        for row in items
        if metric_int(row, "impressions") >= 100 and metric_float(row, "ctr") < 0.01
    ]
    low_ctr.sort(key=lambda row: metric_int(row, "impressions"), reverse=True)
    lines.append("")
    lines.append("## CTR Rewrite Candidates")
    lines.append("")
    lines.append("High-impression queries below 1% CTR. Review page titles, meta descriptions, and first-screen intent match.")
    lines.append("")
    append_search_rows(lines, low_ctr[:10])

    striking_distance = [
        row
        for row in items
        if 8 <= metric_float(row, "position") <= 20 and metric_int(row, "impressions") >= 50
    ]
    striking_distance.sort(
        key=lambda row: (metric_int(row, "impressions"), -metric_float(row, "position")),
        reverse=True,
    )
    lines.append("")
    lines.append("## Striking-Distance Pages")
    lines.append("")
    lines.append("Queries ranking around positions 8-20. Add internal links, benchmark evidence, or a sharper answer block.")
    lines.append("")
    append_search_rows(lines, striking_distance[:10])

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
