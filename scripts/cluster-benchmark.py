#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "src" / "data" / "cluster-benchmarks.json"
LOG_DIR = ROOT / "logs"

DEFAULT_ENDPOINTS = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3:8b"
DEFAULT_PROMPT = (
    "Provide exactly three short bullet points about distributed local inference stability."
)


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_endpoint(endpoint: str) -> str:
    return endpoint.rstrip("/")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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
    return urllib.request.urlopen(req, timeout=timeout)  # noqa: S310


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


def stream_generate_once(endpoint: str, model: str, prompt: str, num_predict: int, timeout_s: int) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": 0, "num_predict": num_predict},
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
    model: str,
    prompt: str,
    num_predict: int,
    timeout_s: int,
    runs: int,
    log_file: Path,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "endpoint": endpoint,
        "status": "ok",
        "runs": [],
        "error": "",
    }
    try:
        local_models = list_local_models(endpoint)
    except Exception as exc:  # noqa: BLE001
        report["status"] = "error"
        report["error"] = f"endpoint unavailable: {exc}"
        append_log(log_file, {"event": "endpoint_unavailable", **report})
        return report

    if model not in local_models:
        report["status"] = "error"
        report["error"] = "model not available on endpoint"
        append_log(log_file, {"event": "cluster_model_missing", **report, "model": model})
        return report

    for idx in range(max(1, runs)):
        try:
            row = stream_generate_once(endpoint, model, prompt, num_predict, timeout_s)
            row["run_index"] = idx + 1
            report["runs"].append(row)
            append_log(log_file, {"event": "cluster_run", **row, "model": model})
        except Exception as exc:  # noqa: BLE001
            report["status"] = "error"
            report["error"] = str(exc)
            append_log(
                log_file,
                {
                    "event": "cluster_run_failed",
                    "endpoint": endpoint,
                    "model": model,
                    "run_index": idx + 1,
                    "error": str(exc),
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
    parser.add_argument("--runs", type=int, default=int(os.getenv("LV_CLUSTER_RUNS", "2")))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("LV_CLUSTER_TIMEOUT_S", "600")))
    parser.add_argument("--prompt", default=os.getenv("LV_CLUSTER_PROMPT", DEFAULT_PROMPT))
    parser.add_argument("--allow-empty", action="store_true", help="Do not fail when no endpoint succeeds.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    endpoints = [normalize_endpoint(x.strip()) for x in args.endpoints.split(",") if x.strip()]
    if not endpoints:
        raise SystemExit("no cluster endpoints configured")

    log_file = LOG_DIR / f"cluster-benchmark-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d')}.log"
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        print("dry-run: cluster benchmark execution skipped")
        print(f"endpoints={endpoints}")
        print(f"model={args.model}")
        return

    append_log(
        log_file,
        {
            "event": "cluster_benchmark_start",
            "ts": utc_now_iso(),
            "endpoints": endpoints,
            "model": args.model,
            "runs": args.runs,
            "num_predict": args.num_predict,
        },
    )

    reports: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(8, len(endpoints))) as pool:
        futures = [
            pool.submit(
                benchmark_endpoint,
                endpoint,
                args.model,
                args.prompt,
                max(16, args.num_predict),
                args.timeout,
                max(1, args.runs),
                log_file,
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
            "metrics": {
                "avg_node_latency_ms": avg_node_latency_ms,
                "cross_node_ttft_jitter_ms": cross_node_ttft_jitter_ms,
                "tokens_per_s": tokens_per_s,
            },
            "verified_date": dt.datetime.now(dt.timezone.utc).date().isoformat(),
            "nodes": reports,
        },
    )
    payload["tests"] = payload["tests"][:120]
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

    print(f"cluster benchmark completed: success={len(ok_reports)}, total={len(reports)}")
    print(f"output file: {FILE}")
    print(f"log file: {log_file}")

    if not ok_reports and not args.allow_empty:
        raise SystemExit("no successful cluster benchmark samples collected")


if __name__ == "__main__":
    main()
