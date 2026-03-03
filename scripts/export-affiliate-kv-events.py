#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from logging_utils import configure_logging


LOGGER = configure_logging("export-affiliate-kv-events")
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_FILE = ROOT / "logs" / "affiliate-events-export.json"


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def cf_request_json(url: str, token: str, timeout_s: int) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=max(5, int(timeout_s))) as resp:  # noqa: S310
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("cloudflare api payload must be an object")
    if not payload.get("success", False):
        errors = payload.get("errors", [])
        raise RuntimeError(f"cloudflare api error: {errors}")
    return payload


def list_kv_keys(
    *,
    account_id: str,
    namespace_id: str,
    token: str,
    prefix: str,
    max_keys: int,
    timeout_s: int,
) -> list[str]:
    out: list[str] = []
    cursor = ""
    remaining = max(1, int(max_keys))
    while remaining > 0:
        batch_limit = min(1000, remaining)
        query = {
            "limit": str(batch_limit),
        }
        if prefix:
            query["prefix"] = prefix
        if cursor:
            query["cursor"] = cursor
        query_str = urllib.parse.urlencode(query)
        url = (
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/"
            f"{namespace_id}/keys?{query_str}"
        )
        payload = cf_request_json(url, token, timeout_s=timeout_s)
        result = payload.get("result", [])
        if not isinstance(result, list):
            break
        for row in result:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name", "")).strip()
            if name:
                out.append(name)
                remaining -= 1
                if remaining <= 0:
                    break
        info = payload.get("result_info", {})
        if not isinstance(info, dict):
            break
        cursor = str(info.get("cursor", "")).strip()
        if not cursor:
            break
    return out


def fetch_kv_value(
    *,
    account_id: str,
    namespace_id: str,
    token: str,
    key: str,
    timeout_s: int,
) -> str:
    safe_key = urllib.parse.quote(key, safe="")
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/"
        f"{namespace_id}/values/{safe_key}"
    )
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=max(5, int(timeout_s))) as resp:  # noqa: S310
        return resp.read().decode("utf-8", errors="replace")


def mask_value(raw: str, keep: int = 6) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    if len(text) <= keep * 2:
        return f"{text[:keep]}***"
    return f"{text[:keep]}***{text[-keep:]}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export affiliate click events from Cloudflare KV to local JSON.")
    parser.add_argument("--account-id", default=os.getenv("CF_ACCOUNT_ID", ""))
    parser.add_argument("--namespace-id", default=os.getenv("CF_AFFILIATE_EVENTS_NAMESPACE_ID", ""))
    parser.add_argument("--api-token", default=os.getenv("CF_API_TOKEN", ""))
    parser.add_argument("--prefix", default="click:")
    parser.add_argument("--max-keys", type=int, default=5000)
    parser.add_argument("--request-timeout-s", type=int, default=20)
    parser.add_argument("--output-file", default=str(DEFAULT_OUT_FILE))
    args = parser.parse_args()

    account_id = str(args.account_id).strip()
    namespace_id = str(args.namespace_id).strip()
    token = str(args.api_token).strip()
    if not account_id:
        raise SystemExit("missing --account-id (or CF_ACCOUNT_ID)")
    if not namespace_id:
        raise SystemExit("missing --namespace-id (or CF_AFFILIATE_EVENTS_NAMESPACE_ID)")
    if not token:
        raise SystemExit("missing --api-token (or CF_API_TOKEN)")

    key_names = list_kv_keys(
        account_id=account_id,
        namespace_id=namespace_id,
        token=token,
        prefix=str(args.prefix).strip(),
        max_keys=max(1, int(args.max_keys)),
        timeout_s=max(5, int(args.request_timeout_s)),
    )

    events: list[dict[str, Any]] = []
    parse_errors = 0
    fetch_errors = 0
    for key in key_names:
        try:
            raw = fetch_kv_value(
                account_id=account_id,
                namespace_id=namespace_id,
                token=token,
                key=key,
                timeout_s=max(5, int(args.request_timeout_s)),
            )
        except urllib.error.HTTPError as exc:
            fetch_errors += 1
            LOGGER.warning("kv_value_fetch_failed key=%s status=%s", key, exc.code)
            continue
        except Exception as exc:  # noqa: BLE001
            fetch_errors += 1
            LOGGER.warning("kv_value_fetch_failed key=%s error=%s", key, exc)
            continue

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            parse_errors += 1
            LOGGER.warning("kv_value_parse_failed key=%s", key)
            continue
        if isinstance(payload, dict):
            payload["_kv_key"] = key
            events.append(payload)
        else:
            parse_errors += 1
            LOGGER.warning("kv_value_non_object key=%s", key)

    events.sort(key=lambda x: str(x.get("ts", "")), reverse=True)
    out = {
        "updated_at": utc_now_iso(),
        "source": "cloudflare_kv_api",
        "account_id_masked": mask_value(account_id),
        "namespace_id_masked": mask_value(namespace_id),
        "prefix": str(args.prefix).strip(),
        "key_count": len(key_names),
        "event_count": len(events),
        "fetch_errors": fetch_errors,
        "parse_errors": parse_errors,
        "events": events,
    }
    out_path = Path(args.output_file)
    if not out_path.is_absolute():
        out_path = (ROOT / out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    LOGGER.info("cloudflare_keys=%d", len(key_names))
    LOGGER.info("events_exported=%d", len(events))
    LOGGER.info("fetch_errors=%d parse_errors=%d", fetch_errors, parse_errors)
    LOGGER.info("output_file=%s", out_path)


if __name__ == "__main__":
    main()
