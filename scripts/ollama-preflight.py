#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

DEFAULT_NETWORK_RETRY_DELAYS_S = "5,10,20"


def normalize_endpoint(endpoint: str) -> str:
    return (endpoint or "").strip().rstrip("/")


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


def run_cmd(cmd: list[str], timeout_s: int = 8) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s, check=False)
        return proc.returncode, proc.stdout, proc.stderr
    except Exception as exc:  # noqa: BLE001
        return 1, "", str(exc)


def detect_ollama_serve_processes() -> list[str]:
    code, out, _err = run_cmd(["ps", "-ef"])
    if code != 0:
        return []
    rows: list[str] = []
    for line in out.splitlines():
        text = line.strip().lower()
        if "ollama serve" not in text:
            continue
        if "ollama-preflight.py" in text:
            continue
        rows.append(line.strip())
    return rows


def detect_port_listeners(port: int) -> list[str]:
    port_marker = f":{port}"
    commands: list[list[str]] = []
    if shutil.which("ss"):
        commands.append(["ss", "-ltnp"])
    if shutil.which("netstat"):
        commands.append(["netstat", "-ltnp"])
    for cmd in commands:
        code, out, _err = run_cmd(cmd)
        if code != 0:
            continue
        lines = [line.strip() for line in out.splitlines() if port_marker in line]
        if lines:
            return lines
    if shutil.which("lsof"):
        code, out, _err = run_cmd(["lsof", f"-iTCP:{port}", "-sTCP:LISTEN", "-n", "-P"])
        if code == 0:
            lines = [line.strip() for line in out.splitlines() if line.strip() and port_marker in line]
            if lines:
                return lines
    return []


def has_non_ollama_listener(listener_lines: list[str]) -> bool:
    if not listener_lines:
        return False
    for line in listener_lines:
        if "ollama" not in line.lower():
            return True
    return False


def parse_targets(raw: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for chunk in (raw or "").split(","):
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


def parse_retry_delays(raw: str, default: list[float] | None = None) -> list[float]:
    delays: list[float] = []
    for chunk in str(raw or "").split(","):
        part = chunk.strip()
        if not part:
            continue
        try:
            val = float(part)
        except ValueError:
            continue
        if val >= 0:
            delays.append(val)
    if delays:
        return delays
    return list(default or [])


def format_retry_delays(delays: list[float]) -> str:
    out: list[str] = []
    for val in delays:
        if float(val).is_integer():
            out.append(str(int(val)))
        else:
            out.append(f"{val:g}")
    return ",".join(out) if out else "<none>"


def emit_failure_class(code: str, detail: str) -> None:
    message = str(detail).strip()
    print(f"failure_class={code}")
    print(f"failure_detail={message}")
    print(f"::error title=FailureClass::{code} - {message}")


def model_family(tag_or_family: str) -> str:
    value = str(tag_or_family).strip().lower()
    if not value:
        return ""
    return value.split(":", 1)[0].strip()


def is_family_target(target: str) -> bool:
    return ":" not in str(target).strip().lower()


def is_variant(local_tag: str, base_tag: str) -> bool:
    if local_tag == base_tag:
        return True
    if not local_tag.startswith(base_tag):
        return False
    if len(local_tag) == len(base_tag):
        return True
    return local_tag[len(base_tag)] in {"-", "_", ".", ":"}


def fetch_local_models(endpoint: str) -> set[str]:
    req = urllib.request.Request(f"{endpoint}/api/tags", method="GET")
    with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
        payload = json.loads(resp.read().decode("utf-8"))
    names: set[str] = set()
    for item in payload.get("models", []):
        name = str(item.get("name", "")).strip().lower()
        model = str(item.get("model", "")).strip().lower()
        if name:
            names.add(name)
        if model:
            names.add(model)
    return names


def start_ollama_service(endpoint: str) -> None:
    env = dict(os.environ)
    env.setdefault("OLLAMA_HOST", endpoint)
    log_path = os.getenv("LV_OLLAMA_SERVE_LOG") or (
        "/tmp/ollama-serve.log" if os.name != "nt" else os.path.join(tempfile.gettempdir(), "ollama-serve.log")
    )
    try:
        subprocess.run(["pkill", "-f", "ollama serve"], check=False)
    except Exception:
        pass
    with open(log_path, "ab") as logf:
        subprocess.Popen(["ollama", "serve"], stdout=logf, stderr=logf, env=env)  # noqa: S603


def fetch_local_models_with_retry(
    endpoint: str,
    retries: int = 20,
    sleep_s: float = 1.0,
    require_non_empty: bool = False,
    retry_delays: list[float] | None = None,
) -> set[str]:
    last_error: Exception | None = None
    last_models: set[str] = set()
    if retry_delays is not None:
        delays = [max(0.0, x) for x in retry_delays]
        attempts = len(delays) + 1
    else:
        attempts = max(1, retries)
        delays = [max(0.0, sleep_s)] * max(0, attempts - 1)

    for attempt in range(attempts):
        try:
            models = fetch_local_models(endpoint)
            last_models = models
            if not require_non_empty or models:
                return models
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        if attempt < len(delays):
            time.sleep(delays[attempt])
    if last_error is None:
        return last_models
    raise last_error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Ollama endpoint/model visibility before benchmark.")
    parser.add_argument(
        "--endpoint",
        default=os.getenv("LV_OLLAMA_ENDPOINT") or os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434",
    )
    parser.add_argument("--required-targets", default=os.getenv("LV_WEEKLY_TARGETS", ""))
    parser.add_argument("--allow-empty-models", action="store_true")
    parser.add_argument("--allow-no-runnable-targets", action="store_true")
    parser.add_argument("--restart-if-empty", action="store_true")
    parser.add_argument("--skip-single-instance-guard", action="store_true")
    parser.add_argument(
        "--require-local-process",
        action="store_true",
        help="Fail if endpoint is loopback and no local 'ollama serve' process is detected.",
    )
    parser.add_argument(
        "--network-retry-delays",
        default=os.getenv("LV_NETWORK_RETRY_DELAYS_S", DEFAULT_NETWORK_RETRY_DELAYS_S),
        help="Comma-separated retry delays in seconds for transient network errors (example: 5,10,20).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    endpoint = normalize_endpoint(args.endpoint)
    endpoint_host, endpoint_port = endpoint_host_port(endpoint)
    loopback_endpoint = is_loopback_host(endpoint_host)
    required_targets = parse_targets(args.required_targets)
    network_retry_delays = parse_retry_delays(args.network_retry_delays, [5.0, 10.0, 20.0])

    print(f"ollama_endpoint={endpoint}")
    print(f"ollama_endpoint_host={endpoint_host}")
    print(f"ollama_endpoint_port={endpoint_port}")
    print(f"ollama_endpoint_is_loopback={str(loopback_endpoint).lower()}")
    print(f"ollama_models_dir={os.getenv('OLLAMA_MODELS', '')}")
    print(f"ollama_network_retry_delays_s={format_retry_delays(network_retry_delays)}")

    if loopback_endpoint and not args.skip_single_instance_guard:
        ollama_processes = detect_ollama_serve_processes()
        listeners = detect_port_listeners(endpoint_port)
        print(f"ollama_serve_process_count={len(ollama_processes)}")
        print(f"ollama_port_listener_count={len(listeners)}")
        if ollama_processes:
            print(f"ollama_serve_process_sample={ollama_processes[:3]}")
        if listeners:
            print(f"ollama_port_listener_sample={listeners[:3]}")

        if len(ollama_processes) > 1:
            emit_failure_class("ollama_multi_instance", "multiple local 'ollama serve' processes detected")
            raise SystemExit("multiple local 'ollama serve' processes detected")
        if has_non_ollama_listener(listeners):
            emit_failure_class("ollama_port_conflict", f"port {endpoint_port} listener is not managed by ollama")
            raise SystemExit(f"port {endpoint_port} listener is not managed by ollama")
        if args.require_local_process and len(ollama_processes) == 0:
            if args.restart_if_empty:
                print("ollama_local_process_missing=1")
                print("ollama_local_recovery_attempt=start_ollama_serve")
                start_ollama_service(endpoint)
                time.sleep(2.0)
                ollama_processes = detect_ollama_serve_processes()
                listeners = detect_port_listeners(endpoint_port)
                print(f"ollama_serve_process_count_after_recovery={len(ollama_processes)}")
                print(f"ollama_port_listener_count_after_recovery={len(listeners)}")
                if ollama_processes:
                    print(f"ollama_serve_process_sample_after_recovery={ollama_processes[:3]}")
                if listeners:
                    print(f"ollama_port_listener_sample_after_recovery={listeners[:3]}")
            if len(ollama_processes) == 0:
                emit_failure_class(
                    "ollama_instance_unmanaged",
                    "no local 'ollama serve' process detected for loopback endpoint",
                )
                raise SystemExit("no local 'ollama serve' process detected for loopback endpoint")
            if has_non_ollama_listener(listeners):
                emit_failure_class("ollama_port_conflict", f"port {endpoint_port} listener is not managed by ollama")
                raise SystemExit(f"port {endpoint_port} listener is not managed by ollama")

    try:
        local_models = fetch_local_models_with_retry(endpoint, retry_delays=network_retry_delays)
    except urllib.error.HTTPError as exc:
        emit_failure_class("ollama_not_visible", f"Ollama endpoint returned HTTP {exc.code}: {exc.reason}")
        raise SystemExit(f"Ollama endpoint returned HTTP {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        emit_failure_class("ollama_not_visible", f"failed to connect to Ollama endpoint: {exc}")
        raise SystemExit(f"failed to connect to Ollama endpoint: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        emit_failure_class("ollama_not_visible", f"failed to query Ollama endpoint: {exc}")
        raise SystemExit(f"failed to query Ollama endpoint: {exc}") from exc

    if args.restart_if_empty and len(local_models) == 0:
        print("ollama_models_count=0, attempting service restart")
        start_ollama_service(endpoint)
        try:
            restart_retry_delays = [1.0, 2.0, 3.0] + network_retry_delays
            local_models = fetch_local_models_with_retry(
                endpoint,
                require_non_empty=True,
                retry_delays=restart_retry_delays,
            )
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(f"failed to recover Ollama service after restart: {exc}") from exc

    local_models_sorted = sorted(local_models)
    print(f"ollama_models_count={len(local_models_sorted)}")
    sample = ", ".join(local_models_sorted[:12]) if local_models_sorted else "<empty>"
    print(f"ollama_models_sample={sample}")

    if not args.allow_empty_models and len(local_models_sorted) == 0:
        emit_failure_class("ollama_not_visible", "Ollama model list is empty")
        raise SystemExit("Ollama model list is empty")

    if required_targets:
        runnable: list[str] = []
        for target in required_targets:
            family_target = is_family_target(target)
            if family_target:
                target_family = model_family(target)
                ok = any(model_family(local_tag) == target_family for local_tag in local_models)
            else:
                ok = any(is_variant(local_tag, target) for local_tag in local_models)
            if ok:
                runnable.append(target)
        print(f"required_targets_count={len(required_targets)}")
        print(f"required_targets_runnable_count={len(runnable)}")
        print(f"required_targets_runnable={','.join(runnable) if runnable else '<none>'}")
        if not args.allow_no_runnable_targets and len(runnable) == 0:
            emit_failure_class("model_missing", "no runnable required targets found in Ollama model list")
            raise SystemExit("no runnable required targets found in Ollama model list")


if __name__ == "__main__":
    main()
