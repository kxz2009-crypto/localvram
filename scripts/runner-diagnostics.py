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
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from logging_utils import configure_logging


LOGGER = configure_logging("runner-diagnostics")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_cmd(cmd: list[str], timeout: int = 12) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as exc:  # noqa: BLE001
        return 1, "", str(exc)


def print_section(title: str, body: str) -> None:
    LOGGER.info("=== %s ===", title)
    content = body if body else "<empty>"
    for line in content.splitlines():
        LOGGER.info("%s", line)


def emit_kv(key: str, value: str) -> None:
    message = f"{key}={value}"
    LOGGER.info("%s", message)


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


def format_retry_delays(delays: list[float]) -> str:
    return ",".join(str(int(x)) if float(x).is_integer() else f"{x:g}" for x in delays) if delays else "<none>"


def normalize_endpoint(endpoint: str) -> str:
    return str(endpoint or "").strip().rstrip("/")


def endpoint_host_port(endpoint: str) -> tuple[str, int]:
    raw = normalize_endpoint(endpoint)
    parsed = urlparse(raw if "://" in raw else f"http://{raw}")
    host = (parsed.hostname or "").strip().lower()
    if not host:
        host = "127.0.0.1"
    port = int(parsed.port or 11434)
    return host, port


def is_loopback_host(host: str) -> bool:
    return str(host or "").strip().lower() in {"127.0.0.1", "localhost", "::1"}


def detect_ollama_serve_processes() -> list[str]:
    code, out, _err = run_cmd(["ps", "-ef"])
    if code != 0:
        return []
    rows: list[str] = []
    for line in out.splitlines():
        text = line.strip().lower()
        if "ollama serve" not in text:
            continue
        if "runner-diagnostics.py" in text:
            continue
        rows.append(line.strip())
    return rows


def detect_port_listeners(port: int) -> list[str]:
    port_marker = f":{port}"
    if shutil.which("ss"):
        code, out, _err = run_cmd(["ss", "-ltnp"])
        if code == 0:
            return [line.strip() for line in out.splitlines() if port_marker in line]
    if shutil.which("netstat"):
        code, out, _err = run_cmd(["netstat", "-ltnp"])
        if code == 0:
            return [line.strip() for line in out.splitlines() if port_marker in line]
    if shutil.which("lsof"):
        code, out, _err = run_cmd(["lsof", f"-iTCP:{port}", "-sTCP:LISTEN", "-n", "-P"])
        if code == 0:
            return [line.strip() for line in out.splitlines() if line.strip() and port_marker in line]
    return []


def has_non_ollama_listener(listener_lines: list[str]) -> bool:
    if not listener_lines:
        return False
    return any("ollama" not in line.lower() for line in listener_lines)


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
    parser.add_argument("--json-out", default="", help="Optional JSON output path for machine-readable diagnostics.")
    args = parser.parse_args()

    diag_timestamp = utc_now_iso()
    endpoint = normalize_endpoint(args.endpoint)
    endpoint_host, endpoint_port_from_url = endpoint_host_port(endpoint)
    port_to_check = args.port
    if port_to_check == 11434 and endpoint_port_from_url != 11434:
        port_to_check = endpoint_port_from_url
    loopback_endpoint = is_loopback_host(endpoint_host)
    required_targets = parse_targets(args.required_targets)
    retry_delays = parse_retry_delays(args.network_retry_delays)
    retry_delays_text = format_retry_delays(retry_delays)
    report: dict[str, Any] = {
        "updated_at": diag_timestamp,
        "endpoint": endpoint,
        "required_targets": required_targets,
        "retry_delays_s": retry_delays,
        "port": port_to_check,
        "env": {},
        "commands": {},
        "checks": {},
        "api": {},
        "summary": {},
    }

    emit_kv("diag_timestamp_utc", diag_timestamp)
    emit_kv("diag_endpoint", endpoint)
    emit_kv("diag_endpoint_host", endpoint_host)
    emit_kv("diag_endpoint_is_loopback", str(loopback_endpoint).lower())
    emit_kv("diag_required_targets", ",".join(required_targets) if required_targets else "<none>")
    emit_kv("diag_retry_delays_s", retry_delays_text)

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
    report["env"] = {
        "runner_name": os.getenv("RUNNER_NAME", ""),
        "runner_os": os.getenv("RUNNER_OS", ""),
        "runner_arch": os.getenv("RUNNER_ARCH", ""),
        "hostname": os.getenv("HOSTNAME", ""),
        "user": os.getenv("USER", "") or os.getenv("USERNAME", ""),
        "OLLAMA_HOST": os.getenv("OLLAMA_HOST", ""),
        "LV_OLLAMA_ENDPOINT": os.getenv("LV_OLLAMA_ENDPOINT", ""),
        "OLLAMA_MODELS": os.getenv("OLLAMA_MODELS", ""),
        "HTTP_PROXY": os.getenv("HTTP_PROXY", ""),
        "HTTPS_PROXY": os.getenv("HTTPS_PROXY", ""),
        "ALL_PROXY": os.getenv("ALL_PROXY", ""),
        "NO_PROXY": os.getenv("NO_PROXY", ""),
    }
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
        report["commands"][title] = {"exit": code, "stdout": out, "stderr": err}

    port_report = "<unavailable>"
    listeners = detect_port_listeners(port_to_check)
    if listeners:
        port_report = "\n".join(listeners)
    else:
        port_report = f"no listeners on :{port_to_check}"
    print_section("PORT_LISTENERS", port_report)
    report["checks"]["port_listeners"] = listeners[:20]

    code, out, err = run_cmd(["ps", "-ef"])
    if code == 0:
        all_ollama_lines = [line for line in out.splitlines() if "ollama" in line.lower()]
        print_section("PS_OLLAMA", "\n".join(all_ollama_lines[:20]) if all_ollama_lines else "no ollama processes found")
        report["checks"]["ps_ollama"] = all_ollama_lines[:20]
    else:
        print_section("PS_OLLAMA", err or "ps failed")
        report["checks"]["ps_ollama"] = [err or "ps failed"]

    guard_failure_class = ""
    guard_failure_detail = ""
    ollama_serve_processes = detect_ollama_serve_processes()
    emit_kv("diag_ollama_serve_process_count", str(len(ollama_serve_processes)))
    if loopback_endpoint:
        if len(ollama_serve_processes) > 1:
            guard_failure_class = "ollama_multi_instance"
            guard_failure_detail = "multiple local 'ollama serve' processes detected"
        elif has_non_ollama_listener(listeners):
            guard_failure_class = "ollama_port_conflict"
            guard_failure_detail = f"port {port_to_check} listener is not managed by ollama"
        elif len(ollama_serve_processes) == 0:
            guard_failure_class = "ollama_instance_unmanaged"
            guard_failure_detail = "no local 'ollama serve' process detected for loopback endpoint"
    if guard_failure_class:
        print_section("SINGLE_INSTANCE_GUARD", f"{guard_failure_class}: {guard_failure_detail}")
    else:
        print_section("SINGLE_INSTANCE_GUARD", "ok")
    report["checks"]["single_instance_guard"] = {
        "endpoint_is_loopback": loopback_endpoint,
        "ollama_serve_process_count": len(ollama_serve_processes),
        "failure_class": guard_failure_class or "none",
        "failure_detail": guard_failure_detail,
    }

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
            report["checks"][title] = {"exit": code, "stdout": out, "stderr": err}

    local_models: set[str] = set()
    endpoint_error = ""
    try:
        ver = fetch_json(endpoint, "/api/version", timeout=10, retry_delays=retry_delays)
        print_section("API_VERSION", json.dumps(ver, ensure_ascii=False))
        report["api"]["version"] = ver
    except urllib.error.HTTPError as exc:
        endpoint_error = f"HTTP {exc.code} {exc.reason}"
        print_section("API_VERSION", endpoint_error)
        report["api"]["version_error"] = endpoint_error
    except Exception as exc:  # noqa: BLE001
        endpoint_error = str(exc)
        print_section("API_VERSION", endpoint_error)
        report["api"]["version_error"] = endpoint_error

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
        report["api"]["tags"] = tags_info
    except urllib.error.HTTPError as exc:
        endpoint_error = endpoint_error or f"HTTP {exc.code} {exc.reason}"
        print_section("API_TAGS", f"HTTP {exc.code} {exc.reason}")
        report["api"]["tags_error"] = f"HTTP {exc.code} {exc.reason}"
    except Exception as exc:  # noqa: BLE001
        endpoint_error = endpoint_error or str(exc)
        print_section("API_TAGS", str(exc))
        report["api"]["tags_error"] = str(exc)

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
    if guard_failure_class:
        failure_class = guard_failure_class
        failure_detail = guard_failure_detail
        summary_lines.append(f"diag_failure_class={guard_failure_class}")
        summary_lines.append(f"diag_failure_detail={guard_failure_detail}")
    elif endpoint_error:
        failure_class = "ollama_not_visible"
        failure_detail = endpoint_error
        summary_lines.append("diag_failure_class=ollama_not_visible")
        summary_lines.append(f"diag_failure_detail={endpoint_error}")
    elif required_targets and not runnable:
        failure_class = "model_missing"
        failure_detail = "no runnable required targets found"
        summary_lines.append("diag_failure_class=model_missing")
        summary_lines.append("diag_failure_detail=no runnable required targets found")
    else:
        failure_class = "none"
        failure_detail = ""
        summary_lines.append("diag_failure_class=none")
        summary_lines.append("diag_failure_detail=")
    print_section("DIAG_SUMMARY", "\n".join(summary_lines))
    report["summary"] = {
        "model_count": len(local_models),
        "required_targets_count": len(required_targets),
        "required_targets_runnable_count": len(runnable),
        "required_targets_runnable": runnable,
        "failure_class": failure_class,
        "failure_detail": failure_detail,
    }

    if args.json_out:
        out_path = Path(args.json_out)
        if not out_path.is_absolute():
            out_path = Path.cwd() / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        emit_kv("diag_json_out", str(out_path))


if __name__ == "__main__":
    main()

