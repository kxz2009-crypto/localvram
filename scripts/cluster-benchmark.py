#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "src" / "data" / "cluster-benchmarks.json"
LOG_DIR = ROOT / "logs"
LOGGER = configure_logging("cluster-benchmark")

DEFAULT_ENDPOINTS = ""
DEFAULT_MODEL = "qwen3:8b"
DEFAULT_NUM_CTX = 4096
DEFAULT_PROMPT = (
    "Provide exactly three short bullet points about distributed local inference stability."
)


def emit(message: str, *, level: str = "info", stderr: bool = False) -> None:
    if level == "error":
        LOGGER.error("%s", message)
    elif level == "warning":
        LOGGER.warning("%s", message)
    else:
        LOGGER.info("%s", message)


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_endpoint(endpoint: str) -> str:
    return endpoint.rstrip("/")


def redact_endpoint(endpoint: str) -> str:
    raw = normalize_endpoint(endpoint)
    try:
        parts = urlsplit(raw)
        host = parts.hostname or ""
        masked = host
        octets = host.split(".")
        if len(octets) == 4 and all(x.isdigit() for x in octets):
            masked = f"{octets[0]}.{octets[1]}.x.x"
        netloc = masked
        if parts.port:
            netloc = f"{netloc}:{parts.port}"
        return urlunsplit((parts.scheme, netloc, "", "", ""))
    except Exception:  # noqa: BLE001
        return "redacted-endpoint"


def run_cmd(args: list[str], timeout: int = 20) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("run_cmd failed args=%s error=%s", " ".join(args), exc)
        return 1, "", str(exc)


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    val = str(raw).strip().lower()
    if val in {"1", "true", "yes", "on"}:
        return True
    if val in {"0", "false", "no", "off"}:
        return False
    return default


def total_power_draw_w() -> float:
    code, out, _ = run_cmd(
        ["nvidia-smi", "--query-gpu=power.draw", "--format=csv,noheader,nounits"],
        timeout=8,
    )
    if code != 0 or not out:
        return 0.0
    values = []
    for line in out.splitlines():
        try:
            values.append(float(line.strip()))
        except ValueError:
            continue
    return round(sum(values), 2) if values else 0.0


def classify_error(error_text: str) -> str:
    txt = (error_text or "").lower()
    if "out of memory" in txt or "oom" in txt:
        return "oom"
    if "timed out" in txt or "timeout" in txt:
        return "timeout"
    if "connection refused" in txt or "failed to connect" in txt:
        return "connectivity"
    return "runtime"


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def prune_old_logs(log_dir: Path, prefix: str, retention_days: int) -> int:
    if retention_days <= 0 or not log_dir.exists():
        return 0
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=retention_days)
    deleted = 0
    for log_file in log_dir.glob(f"{prefix}*.log"):
        try:
            modified_at = dt.datetime.fromtimestamp(log_file.stat().st_mtime, tz=dt.timezone.utc)
        except FileNotFoundError:
            continue
        if modified_at < cutoff:
            log_file.unlink(missing_ok=True)
            deleted += 1
    return deleted


def append_log(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def api_request(endpoint: str, route: str, payload: dict[str, Any] | None = None, timeout: int = 600, stream: bool = False):
    url = f"{normalize_endpoint(endpoint)}{route}"
    data = None
    method = "GET"
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        method = "POST"
        headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        return urllib.request.urlopen(req, timeout=timeout)  # noqa: S310
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            body = ""
        detail = body[:500].replace("\n", " ").strip()
        message = f"HTTP {exc.code} {exc.reason}"
        if detail:
            message = f"{message}: {detail}"
        raise RuntimeError(message) from exc


def list_local_models(endpoint: str) -> set[str]:
    with api_request(endpoint, "/api/tags", None, timeout=20, stream=False) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    models = set()
    for item in payload.get("models", []):
        name = str(item.get("name", "")).strip()
        model = str(item.get("model", "")).strip()
        if name:
            models.add(name)
        if model:
            models.add(model)
    return models


def ns_to_seconds(value: Any) -> float:
    try:
        val = float(value)
    except (TypeError, ValueError):
        return 0.0
    if val <= 0:
        return 0.0
    return val / 1_000_000_000.0


def stream_generate_once(
    endpoint: str,
    model: str,
    prompt: str,
    num_predict: int,
    num_ctx: int,
    timeout_s: int,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": 0, "num_predict": num_predict, "num_ctx": num_ctx},
    }
    started = time.perf_counter()
    first_token_ms = None
    final_chunk: dict[str, Any] = {}
    with api_request(endpoint, "/api/generate", payload=payload, timeout=timeout_s, stream=True) as resp:
        for raw in resp:
            line = raw.decode("utf-8").strip()
            if not line:
                continue
            chunk = json.loads(line)
            if first_token_ms is None and chunk.get("response"):
                first_token_ms = (time.perf_counter() - started) * 1000.0
            if chunk.get("done") is True:
                final_chunk = chunk
                break

    wall_s = max(0.001, time.perf_counter() - started)
    eval_count = int(final_chunk.get("eval_count") or 0)
    eval_s = ns_to_seconds(final_chunk.get("eval_duration"))
    total_s = ns_to_seconds(final_chunk.get("total_duration")) or wall_s
    tokens_per_s = (eval_count / eval_s) if eval_s > 0 else (eval_count / wall_s if eval_count > 0 else 0.0)
    return {
        "endpoint": endpoint,
        "ttft_ms": round(first_token_ms or 0.0, 2),
        "eval_count": eval_count,
        "total_duration_s": round(total_s, 4),
        "tokens_per_s": round(tokens_per_s, 3),
    }


def benchmark_endpoint(
    endpoint: str,
    redacted_endpoint: str,
    model: str,
    prompt: str,
    num_predict: int,
    num_ctx: int,
    timeout_s: int,
    runs: int,
    log_file: Path,
    cooldown_s: float,
    power_limit_w: float,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "endpoint": redacted_endpoint,
        "status": "ok",
        "runs": [],
        "error": "",
        "error_type": "",
    }
    try:
        local_models = list_local_models(endpoint)
    except Exception as exc:  # noqa: BLE001
        report["status"] = "error"
        report["error"] = f"endpoint unavailable: {exc}"
        report["error_type"] = "connectivity"
        append_log(log_file, {"event": "endpoint_unavailable", **report})
        return report

    if model not in local_models:
        report["status"] = "error"
        report["error"] = "model not available on endpoint"
        report["error_type"] = "missing_model"
        append_log(log_file, {"event": "cluster_model_missing", **report, "model": model})
        return report

    for idx in range(max(1, runs)):
        try:
            if power_limit_w > 0:
                wait_guard = time.perf_counter()
                while True:
                    power_now = total_power_draw_w()
                    if power_now <= 0 or power_now <= power_limit_w:
                        break
                    if time.perf_counter() - wait_guard > 60:
                        append_log(
                            log_file,
                            {
                                "event": "power_guard_timeout",
                                "endpoint": redacted_endpoint,
                                "power_now_w": power_now,
                                "power_limit_w": power_limit_w,
                            },
                        )
                        break
                    time.sleep(max(0.5, min(cooldown_s, 2.0)))

            row = stream_generate_once(endpoint, model, prompt, num_predict, num_ctx, timeout_s)
            row["run_index"] = idx + 1
            row["endpoint"] = redacted_endpoint
            report["runs"].append(row)
            append_log(log_file, {"event": "cluster_run", **row, "model": model})
            if idx < runs - 1 and cooldown_s > 0:
                time.sleep(cooldown_s)
        except Exception as exc:  # noqa: BLE001
            report["status"] = "error"
            report["error"] = str(exc)
            report["error_type"] = classify_error(str(exc))
            append_log(
                log_file,
                {
                    "event": "cluster_run_failed",
                    "endpoint": redacted_endpoint,
                    "model": model,
                    "run_index": idx + 1,
                    "error": str(exc),
                    "error_type": report["error_type"],
                },
            )
            break

    if report["runs"]:
        ttft = [r["ttft_ms"] for r in report["runs"]]
        tps = [r["tokens_per_s"] for r in report["runs"]]
        latency = [r["total_duration_s"] * 1000.0 for r in report["runs"]]
        report["avg_ttft_ms"] = round(statistics.mean(ttft), 2)
        report["avg_tokens_per_s"] = round(statistics.mean(tps), 3)
        report["avg_latency_ms"] = round(statistics.mean(latency), 2)
    else:
        report["status"] = "error"
        if not report["error"]:
            report["error"] = "no successful run"
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run cluster benchmark against one or multiple Ollama endpoints.")
    parser.add_argument("--endpoints", default=os.getenv("LV_CLUSTER_ENDPOINTS", DEFAULT_ENDPOINTS))
    parser.add_argument("--model", default=os.getenv("LV_CLUSTER_MODEL", DEFAULT_MODEL))
    parser.add_argument("--num-predict", type=int, default=int(os.getenv("LV_CLUSTER_NUM_PREDICT", "96")))
    parser.add_argument("--num-ctx", type=int, default=int(os.getenv("LV_CLUSTER_NUM_CTX", str(DEFAULT_NUM_CTX))))
    parser.add_argument("--runs", type=int, default=int(os.getenv("LV_CLUSTER_RUNS", "2")))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("LV_CLUSTER_TIMEOUT_S", "600")))
    parser.add_argument("--max-workers", type=int, default=int(os.getenv("LV_CLUSTER_MAX_WORKERS", "2")))
    parser.add_argument(
        "--min-endpoints",
        type=int,
        default=int(os.getenv("LV_CLUSTER_MIN_ENDPOINTS", "2")),
        help="Minimum endpoint count required to run a meaningful cluster benchmark.",
    )
    parser.add_argument(
        "--skip-if-under-min-endpoints",
        action="store_true",
        default=env_bool("LV_CLUSTER_SKIP_IF_UNDER_MIN_ENDPOINTS", True),
        help="Skip with exit code 0 when endpoint count is below min-endpoints.",
    )
    parser.add_argument("--cooldown-s", type=float, default=float(os.getenv("LV_CLUSTER_COOLDOWN_S", "2.0")))
    parser.add_argument("--power-limit-w", type=float, default=float(os.getenv("LV_CLUSTER_POWER_LIMIT_W", "0")))
    parser.add_argument(
        "--log-retention-days",
        type=int,
        default=int(os.getenv("LV_CLUSTER_LOG_RETENTION_DAYS", "30")),
    )
    parser.add_argument("--prompt", default=os.getenv("LV_CLUSTER_PROMPT", DEFAULT_PROMPT))
    parser.add_argument("--allow-empty", action="store_true", help="Do not fail when no endpoint succeeds.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    endpoints = [normalize_endpoint(x.strip()) for x in args.endpoints.split(",") if x.strip()]
    redacted_endpoints = [redact_endpoint(x) for x in endpoints]
    if not endpoints:
        message = "no cluster endpoints configured"
        if args.skip_if_under_min_endpoints:
            emit(f"cluster benchmark skipped: {message}", level="warning")
            return
        raise SystemExit(message)

    log_file = LOG_DIR / f"cluster-benchmark-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d')}.log"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    deleted_logs = prune_old_logs(LOG_DIR, "cluster-benchmark-", max(0, args.log_retention_days))

    if args.dry_run:
        emit("dry-run: cluster benchmark execution skipped")
        emit(f"endpoints={redacted_endpoints}")
        emit(f"model={args.model}")
        emit(f"num_ctx={max(256, args.num_ctx)}")
        emit("temperature=0")
        emit(f"min_endpoints={max(1, args.min_endpoints)}")
        emit(f"log_retention_days={args.log_retention_days}")
        return

    min_endpoints = max(1, args.min_endpoints)
    if len(endpoints) < min_endpoints:
        message = f"cluster benchmark skipped: endpoints {len(endpoints)} < required {min_endpoints}"
        if args.skip_if_under_min_endpoints:
            append_log(
                log_file,
                {
                    "event": "cluster_benchmark_skipped",
                    "ts": utc_now_iso(),
                    "reason": message,
                    "endpoints": redacted_endpoints,
                    "min_endpoints": min_endpoints,
                },
            )
            emit(message, level="warning")
            return
        raise SystemExit(message)

    append_log(
        log_file,
        {
            "event": "cluster_benchmark_start",
            "ts": utc_now_iso(),
            "endpoints": redacted_endpoints,
            "model": args.model,
            "runs": args.runs,
            "num_predict": args.num_predict,
            "num_ctx": max(256, args.num_ctx),
            "temperature": 0,
            "max_workers": max(1, args.max_workers),
            "cooldown_s": max(0.0, args.cooldown_s),
            "power_limit_w": max(0.0, args.power_limit_w),
            "deleted_logs": deleted_logs,
        },
    )

    reports: list[dict[str, Any]] = []
    max_workers = min(len(endpoints), max(1, args.max_workers))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [
            pool.submit(
                benchmark_endpoint,
                endpoint,
                redact_endpoint(endpoint),
                args.model,
                args.prompt,
                max(16, args.num_predict),
                max(256, args.num_ctx),
                args.timeout,
                max(1, args.runs),
                log_file,
                max(0.0, args.cooldown_s),
                max(0.0, args.power_limit_w),
            )
            for endpoint in endpoints
        ]
        for fut in as_completed(futures):
            reports.append(fut.result())

    ok_reports = [r for r in reports if r.get("status") == "ok" and r.get("runs")]
    if ok_reports:
        avg_node_latency_ms = round(statistics.mean(r["avg_latency_ms"] for r in ok_reports), 2)
        tokens_per_s = round(statistics.mean(r["avg_tokens_per_s"] for r in ok_reports), 3)
        ttft_values = [r["avg_ttft_ms"] for r in ok_reports]
        cross_node_ttft_jitter_ms = round(max(ttft_values) - min(ttft_values), 2) if len(ttft_values) > 1 else 0.0
    else:
        avg_node_latency_ms = 0.0
        tokens_per_s = 0.0
        cross_node_ttft_jitter_ms = 0.0

    payload = read_json(FILE, {"version": "2026.02.24", "updated_at": "", "tests": []})
    payload["updated_at"] = utc_now_iso()
    payload["tests"].insert(
        0,
        {
            "id": f"cluster_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "topology": f"{len(endpoints)} endpoint(s)",
            "model_id": args.model,
            "num_ctx": max(256, args.num_ctx),
            "temperature": 0,
            "metrics": {
                "avg_node_latency_ms": avg_node_latency_ms,
                "cross_node_ttft_jitter_ms": cross_node_ttft_jitter_ms,
                "tokens_per_s": tokens_per_s,
            },
            "verified_date": dt.datetime.now(dt.timezone.utc).date().isoformat(),
            "nodes": reports,
        },
    )
    payload["tests"] = payload["tests"][:20]
    write_json(FILE, payload)

    append_log(
        log_file,
        {
            "event": "cluster_benchmark_end",
            "ts": utc_now_iso(),
            "success_endpoints": len(ok_reports),
            "failed_endpoints": len(reports) - len(ok_reports),
            "avg_node_latency_ms": avg_node_latency_ms,
            "cross_node_ttft_jitter_ms": cross_node_ttft_jitter_ms,
            "tokens_per_s": tokens_per_s,
        },
    )

    emit(f"cluster benchmark completed: success={len(ok_reports)}, total={len(reports)}")
    emit(f"output file: {FILE}")
    emit(f"log file: {log_file}")

    if not ok_reports and not args.allow_empty:
        raise SystemExit("no successful cluster benchmark samples collected")


if __name__ == "__main__":
    main()
