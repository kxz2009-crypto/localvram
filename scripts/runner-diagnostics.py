#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_cmd(cmd: list[str], timeout: int = 12) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as exc:  # noqa: BLE001
        return 1, "", str(exc)


def print_section(title: str, body: str) -> None:
    print(f"=== {title} ===")
    print(body if body else "<empty>")


def parse_targets(raw: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for chunk in str(raw or "").split(","):
        part = chunk.strip().lower()
        if not part:
            continue
        if "=" in part:
            part = part.rsplit("=", 1)[0].strip()
        if not part or part in seen:
            continue
        seen.add(part)
        out.append(part)
    return out


def parse_retry_delays(raw: str) -> list[float]:
    out: list[float] = []
    for chunk in str(raw or "").split(","):
        part = chunk.strip()
        if not part:
            continue
        try:
            val = float(part)
        except ValueError:
            continue
        if val >= 0:
            out.append(val)
    return out


def normalize_endpoint(endpoint: str) -> str:
    return str(endpoint or "").strip().rstrip("/")


def model_family(tag_or_family: str) -> str:
    value = str(tag_or_family).strip().lower()
    if not value:
        return ""
    return value.split(":", 1)[0].strip()


def is_variant(local_tag: str, base_tag: str) -> bool:
    if local_tag == base_tag:
        return True
    if not local_tag.startswith(base_tag):
        return False
    if len(local_tag) == len(base_tag):
        return True
    return local_tag[len(base_tag)] in {"-", "_", ".", ":"}


def fetch_json(endpoint: str, route: str, timeout: int, retry_delays: list[float]) -> dict[str, Any]:
    url = f"{normalize_endpoint(endpoint)}{route}"
    for attempt in range(len(retry_delays) + 1):
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                return json.loads(resp.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            if attempt >= len(retry_delays):
                raise
            time.sleep(max(0.0, retry_delays[attempt]))
    raise RuntimeError("request retries exhausted")


def main() -> None:
    parser = argparse.ArgumentParser(description="Runner/Ollama diagnostics for self-hosted benchmark jobs.")
    parser.add_argument("--endpoint", default=os.getenv("LV_OLLAMA_ENDPOINT") or os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434")
    parser.add_argument("--required-targets", default=os.getenv("LV_WEEKLY_TARGETS", ""))
    parser.add_argument("--network-retry-delays", default=os.getenv("LV_NETWORK_RETRY_DELAYS_S", "5,10,20"))
    parser.add_argument("--port", type=int, default=11434)
    args = parser.parse_args()

    endpoint = normalize_endpoint(args.endpoint)
    required_targets = parse_targets(args.required_targets)
    retry_delays = parse_retry_delays(args.network_retry_delays)

    print(f"diag_timestamp_utc={utc_now_iso()}")
    print(f"diag_endpoint={endpoint}")
    print(f"diag_required_targets={','.join(required_targets) if required_targets else '<none>'}")
    print(f"diag_retry_delays_s={','.join(str(int(x)) if float(x).is_integer() else f'{x:g}' for x in retry_delays) if retry_delays else '<none>'}")

    base_lines = [
        f"runner_name={os.getenv('RUNNER_NAME', '')}",
        f"runner_os={os.getenv('RUNNER_OS', '')}",
        f"runner_arch={os.getenv('RUNNER_ARCH', '')}",
        f"hostname={os.getenv('HOSTNAME', '')}",
        f"user={os.getenv('USER', '') or os.getenv('USERNAME', '')}",
        f"OLLAMA_HOST={os.getenv('OLLAMA_HOST', '')}",
        f"LV_OLLAMA_ENDPOINT={os.getenv('LV_OLLAMA_ENDPOINT', '')}",
        f"OLLAMA_MODELS={os.getenv('OLLAMA_MODELS', '')}",
        f"HTTP_PROXY={os.getenv('HTTP_PROXY', '')}",
        f"HTTPS_PROXY={os.getenv('HTTPS_PROXY', '')}",
        f"ALL_PROXY={os.getenv('ALL_PROXY', '')}",
        f"NO_PROXY={os.getenv('NO_PROXY', '')}",
    ]
    print_section("ENV", "\n".join(base_lines))

    system_cmds = [
        ("WHOAMI", ["whoami"]),
        ("ID", ["id"]),
        ("UNAME", ["uname", "-a"]),
        ("PYTHON", [sys.executable, "--version"]),
        ("OLLAMA_VERSION", ["ollama", "--version"]),
    ]
    for title, cmd in system_cmds:
        code, out, err = run_cmd(cmd)
        text = out if out else err
        print_section(f"{title} (exit={code})", text)

    port_report = "<unavailable>"
    if shutil.which("ss"):
        code, out, err = run_cmd(["ss", "-ltnp"])
        if code == 0:
            lines = [line for line in out.splitlines() if f":{args.port}" in line]
            port_report = "\n".join(lines) if lines else f"no listeners on :{args.port}"
        else:
            port_report = err or "ss failed"
    elif shutil.which("netstat"):
        code, out, err = run_cmd(["netstat", "-ltnp"])
        if code == 0:
            lines = [line for line in out.splitlines() if f":{args.port}" in line]
            port_report = "\n".join(lines) if lines else f"no listeners on :{args.port}"
        else:
            port_report = err or "netstat failed"
    print_section("PORT_LISTENERS", port_report)

    code, out, err = run_cmd(["ps", "-ef"])
    if code == 0:
        lines = [line for line in out.splitlines() if "ollama" in line.lower()]
        print_section("PS_OLLAMA", "\n".join(lines[:20]) if lines else "no ollama processes found")
    else:
        print_section("PS_OLLAMA", err or "ps failed")

    if shutil.which("systemctl"):
        status_cmds = [
            ("SYSTEMD_OLLAMA_IS_ACTIVE", ["systemctl", "is-active", "ollama.service"]),
            ("SYSTEMD_OLLAMA_STATUS", ["systemctl", "status", "ollama.service", "--no-pager", "-l"]),
            ("SYSTEMD_RUNNER_UNITS", ["systemctl", "list-units", "--type=service", "--all", "actions.runner*", "--no-pager", "-l"]),
        ]
        for title, cmd in status_cmds:
            code, out, err = run_cmd(cmd, timeout=20)
            text = out if out else err
            if title == "SYSTEMD_OLLAMA_STATUS":
                lines = text.splitlines()
                text = "\n".join(lines[:40])
            print_section(f"{title} (exit={code})", text)

    local_models: set[str] = set()
    endpoint_error = ""
    try:
        ver = fetch_json(endpoint, "/api/version", timeout=10, retry_delays=retry_delays)
        print_section("API_VERSION", json.dumps(ver, ensure_ascii=False))
    except urllib.error.HTTPError as exc:
        endpoint_error = f"HTTP {exc.code} {exc.reason}"
        print_section("API_VERSION", endpoint_error)
    except Exception as exc:  # noqa: BLE001
        endpoint_error = str(exc)
        print_section("API_VERSION", endpoint_error)

    try:
        tags_payload = fetch_json(endpoint, "/api/tags", timeout=20, retry_delays=retry_delays)
        models = tags_payload.get("models", [])
        for row in models:
            name = str(row.get("name", "")).strip().lower()
            model = str(row.get("model", "")).strip().lower()
            if name:
                local_models.add(name)
            if model:
                local_models.add(model)
        sample = sorted(local_models)[:20]
        tags_info = {
            "model_count": len(local_models),
            "sample": sample,
        }
        print_section("API_TAGS", json.dumps(tags_info, ensure_ascii=False))
    except urllib.error.HTTPError as exc:
        endpoint_error = endpoint_error or f"HTTP {exc.code} {exc.reason}"
        print_section("API_TAGS", f"HTTP {exc.code} {exc.reason}")
    except Exception as exc:  # noqa: BLE001
        endpoint_error = endpoint_error or str(exc)
        print_section("API_TAGS", str(exc))

    runnable = []
    if required_targets and local_models:
        for target in required_targets:
            if ":" in target:
                ok = any(is_variant(local_tag, target) for local_tag in local_models)
            else:
                fam = model_family(target)
                ok = any(model_family(local_tag) == fam for local_tag in local_models)
            if ok:
                runnable.append(target)

    summary_lines = [
        f"diag_model_count={len(local_models)}",
        f"diag_required_targets_count={len(required_targets)}",
        f"diag_required_targets_runnable_count={len(runnable)}",
        f"diag_required_targets_runnable={','.join(runnable) if runnable else '<none>'}",
    ]
    if endpoint_error:
        summary_lines.append("diag_failure_class=ollama_not_visible")
        summary_lines.append(f"diag_failure_detail={endpoint_error}")
    elif required_targets and not runnable:
        summary_lines.append("diag_failure_class=model_missing")
        summary_lines.append("diag_failure_detail=no runnable required targets found")
    else:
        summary_lines.append("diag_failure_class=none")
        summary_lines.append("diag_failure_detail=")
    print_section("DIAG_SUMMARY", "\n".join(summary_lines))


if __name__ == "__main__":
    main()

