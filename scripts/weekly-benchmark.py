#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STATUS_FILE = ROOT / "src" / "data" / "status.json"
CHANGELOG_FILE = ROOT / "src" / "data" / "benchmark-changelog.json"
RESULTS_FILE = ROOT / "src" / "data" / "benchmark-results.json"
LOG_DIR = ROOT / "logs"

DEFAULT_TARGETS = "llama3:8b=128,qwen3:8b=128,deepseek-r1:8b=128"
DEFAULT_PROMPT = (
    "You are an inference benchmark probe. "
    "Respond with exactly three short bullet points about local LLM deployment stability."
)


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def run_cmd(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as exc:  # noqa: BLE001
        return 1, "", str(exc)


def normalize_endpoint(endpoint: str) -> str:
    return endpoint.rstrip("/")


def api_request(endpoint: str, route: str, payload: dict[str, Any] | None = None, timeout: int = 600) -> dict[str, Any]:
    url = f"{normalize_endpoint(endpoint)}{route}"
    data = None
    method = "GET"
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        method = "POST"
        headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def list_local_models(endpoint: str) -> set[str]:
    payload = api_request(endpoint, "/api/tags", None, timeout=20)
    models = set()
    for item in payload.get("models", []):
        name = str(item.get("name", "")).strip()
        model = str(item.get("model", "")).strip()
        if name:
            models.add(name)
        if model:
            models.add(model)
    return models


def fetch_ollama_version(endpoint: str) -> str:
    try:
        payload = api_request(endpoint, "/api/version", None, timeout=10)
        if payload.get("version"):
            return str(payload["version"])
    except Exception:  # noqa: BLE001
        pass
    code, out, _ = run_cmd(["ollama", "--version"], timeout=10)
    if code == 0 and out:
        return out
    return "unknown"


def collect_gpu_snapshot() -> dict[str, Any]:
    cmd = [
        "nvidia-smi",
        "--query-gpu=name,driver_version,memory.total,memory.used,temperature.gpu,power.draw,utilization.gpu",
        "--format=csv,noheader,nounits",
    ]
    code, out, err = run_cmd(cmd, timeout=10)
    if code != 0:
        return {"available": False, "error": err or "nvidia-smi failed", "gpus": []}
    gpus: list[dict[str, Any]] = []
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 7:
            continue
        gpus.append(
            {
                "name": parts[0],
                "driver": parts[1],
                "memory_total_mb": _to_float(parts[2]),
                "memory_used_mb": _to_float(parts[3]),
                "temperature_c": _to_float(parts[4]),
                "power_w": _to_float(parts[5]),
                "utilization_pct": _to_float(parts[6]),
            }
        )
    return {"available": True, "gpus": gpus}


def _to_float(value: str) -> float:
    try:
        return float(value)
    except ValueError:
        return 0.0


def ns_to_seconds(value: Any) -> float:
    try:
        val = float(value)
    except (TypeError, ValueError):
        return 0.0
    if val <= 0:
        return 0.0
    return val / 1_000_000_000.0


def parse_targets(raw: str) -> list[tuple[str, int]]:
    targets: list[tuple[str, int]] = []
    for chunk in raw.split(","):
        part = chunk.strip()
        if not part:
            continue
        if "=" in part:
            model, num_predict_raw = part.rsplit("=", 1)
        else:
            model, num_predict_raw = part, "128"
        model = model.strip()
        if not model:
            continue
        try:
            num_predict = max(16, int(num_predict_raw))
        except ValueError:
            num_predict = 128
        targets.append((model, num_predict))
    return targets


def run_single_generation(endpoint: str, model: str, prompt: str, num_predict: int, timeout_s: int) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0, "num_predict": num_predict},
    }
    started_at = time.perf_counter()
    response = api_request(endpoint, "/api/generate", payload=payload, timeout=timeout_s)
    wall_s = max(0.001, time.perf_counter() - started_at)
    eval_count = int(response.get("eval_count") or 0)
    eval_s = ns_to_seconds(response.get("eval_duration"))
    prompt_eval_count = int(response.get("prompt_eval_count") or 0)
    prompt_eval_s = ns_to_seconds(response.get("prompt_eval_duration"))
    total_s = ns_to_seconds(response.get("total_duration")) or wall_s
    tok_s = (eval_count / eval_s) if eval_s > 0 else (eval_count / wall_s if eval_count > 0 else 0.0)
    prompt_tok_s = (prompt_eval_count / prompt_eval_s) if prompt_eval_s > 0 else 0.0
    return {
        "model": model,
        "num_predict": num_predict,
        "eval_count": eval_count,
        "eval_duration_s": round(eval_s, 4),
        "prompt_eval_count": prompt_eval_count,
        "prompt_eval_duration_s": round(prompt_eval_s, 4),
        "total_duration_s": round(total_s, 4),
        "wall_duration_s": round(wall_s, 4),
        "tokens_per_s": round(tok_s, 3),
        "prompt_tokens_per_s": round(prompt_tok_s, 3),
    }


def benchmark_model(
    endpoint: str,
    model: str,
    prompt: str,
    num_predict: int,
    timeout_s: int,
    runs: int,
    warmup_predict: int,
    log_file: Path,
) -> dict[str, Any]:
    model_report: dict[str, Any] = {
        "model": model,
        "num_predict": num_predict,
        "status": "ok",
        "runs": [],
        "error": "",
    }
    if warmup_predict > 0:
        try:
            run_single_generation(endpoint, model, prompt, warmup_predict, timeout_s)
        except Exception as exc:  # noqa: BLE001
            append_log(log_file, {"level": "warn", "event": "warmup_failed", "model": model, "error": str(exc)})

    for idx in range(runs):
        try:
            row = run_single_generation(endpoint, model, prompt, num_predict, timeout_s)
            row["run_index"] = idx + 1
            model_report["runs"].append(row)
            append_log(log_file, {"level": "info", "event": "benchmark_run", **row})
        except Exception as exc:  # noqa: BLE001
            model_report["status"] = "error"
            model_report["error"] = str(exc)
            append_log(
                log_file,
                {
                    "level": "error",
                    "event": "benchmark_run_failed",
                    "model": model,
                    "run_index": idx + 1,
                    "error": str(exc),
                },
            )
            break

    if model_report["runs"]:
        tps_values = [r["tokens_per_s"] for r in model_report["runs"]]
        total_values = [r["total_duration_s"] for r in model_report["runs"]]
        model_report["tokens_per_s_avg"] = round(statistics.mean(tps_values), 3)
        model_report["tokens_per_s_max"] = round(max(tps_values), 3)
        model_report["latency_s_avg"] = round(statistics.mean(total_values), 3)
    else:
        model_report["status"] = "error"
        if not model_report["error"]:
            model_report["error"] = "no successful run"
    return model_report


def update_status(success_count: int, now_iso: str) -> None:
    status = read_json(
        STATUS_FILE,
        {
            "last_verified": "",
            "last_hardware_sync": "",
            "freshness_score": 80,
        },
    )
    score_before = int(status.get("freshness_score", 80))
    if success_count > 0:
        status["last_verified"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
        status["freshness_score"] = min(100, score_before + min(5, success_count))
    else:
        status["freshness_score"] = max(0, score_before - 5)
    status["last_hardware_sync"] = now_iso
    write_json(STATUS_FILE, status)


def update_changelog(success_reports: list[dict[str, Any]], failed_reports: list[dict[str, Any]], environment: str, now_iso: str) -> None:
    changelog = read_json(CHANGELOG_FILE, {"updated_at": now_iso, "items": []})
    changes: list[str] = []
    for report in success_reports:
        changes.append(
            f"{report['model']} avg {report['tokens_per_s_avg']} tok/s, "
            f"avg latency {report['latency_s_avg']}s ({len(report['runs'])} run(s))"
        )
    if failed_reports:
        failed_models = ", ".join(r["model"] for r in failed_reports[:5])
        changes.append(f"Skipped/failed targets: {failed_models}")
    if not changes:
        changes.append("No successful benchmark samples captured.")

    changelog["updated_at"] = now_iso
    changelog["items"].insert(
        0,
        {
            "date": dt.datetime.now(dt.timezone.utc).date().isoformat(),
            "title": f"Weekly benchmark run ({len(success_reports)} successful model(s))",
            "environment": environment,
            "changes": changes,
        },
    )
    changelog["items"] = changelog["items"][:40]
    write_json(CHANGELOG_FILE, changelog)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run real weekly Ollama benchmarks.")
    parser.add_argument("--endpoint", default=os.getenv("LV_OLLAMA_ENDPOINT", "http://127.0.0.1:11434"))
    parser.add_argument("--targets", default=os.getenv("LV_WEEKLY_TARGETS", DEFAULT_TARGETS))
    parser.add_argument("--runs", type=int, default=int(os.getenv("LV_RUNS_PER_MODEL", "2")))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("LV_BENCHMARK_TIMEOUT_S", "600")))
    parser.add_argument("--warmup-predict", type=int, default=int(os.getenv("LV_WARMUP_PREDICT", "24")))
    parser.add_argument("--prompt", default=os.getenv("LV_BENCHMARK_PROMPT", DEFAULT_PROMPT))
    parser.add_argument("--allow-empty", action="store_true", help="Do not fail when no successful sample is collected.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    endpoint = normalize_endpoint(args.endpoint)
    now_iso = utc_now_iso()
    log_file = LOG_DIR / f"weekly-benchmark-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d')}.log"
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        print("dry-run: weekly benchmark execution skipped")
        print(f"endpoint={endpoint}")
        print(f"targets={args.targets}")
        return

    targets = parse_targets(args.targets)
    if not targets:
        raise SystemExit("no valid benchmark targets configured")

    try:
        local_models = list_local_models(endpoint)
    except urllib.error.URLError as exc:
        raise SystemExit(f"failed to connect to Ollama at {endpoint}: {exc}") from exc

    gpu_before = collect_gpu_snapshot()
    ollama_version = fetch_ollama_version(endpoint)
    append_log(
        log_file,
        {
            "level": "info",
            "event": "benchmark_start",
            "ts": now_iso,
            "endpoint": endpoint,
            "targets": targets,
            "ollama_version": ollama_version,
            "gpu_before": gpu_before,
        },
    )

    reports: list[dict[str, Any]] = []
    for model, num_predict in targets:
        if model not in local_models:
            report = {
                "model": model,
                "num_predict": num_predict,
                "status": "error",
                "runs": [],
                "error": "model not found locally (run `ollama pull` on runner first)",
            }
            reports.append(report)
            append_log(log_file, {"level": "error", "event": "model_missing", **report})
            continue
        report = benchmark_model(
            endpoint=endpoint,
            model=model,
            prompt=args.prompt,
            num_predict=num_predict,
            timeout_s=args.timeout,
            runs=max(1, args.runs),
            warmup_predict=max(0, args.warmup_predict),
            log_file=log_file,
        )
        reports.append(report)

    success_reports = [r for r in reports if r.get("status") == "ok" and r.get("runs")]
    failed_reports = [r for r in reports if r.get("status") != "ok"]
    gpu_after = collect_gpu_snapshot()

    write_json(
        RESULTS_FILE,
        {
            "updated_at": now_iso,
            "runner": {
                "hostname": platform.node(),
                "platform": platform.platform(),
                "python": sys.version.split()[0],
            },
            "ollama": {
                "endpoint": endpoint,
                "version": ollama_version,
                "available_model_count": len(local_models),
            },
            "gpu_before": gpu_before,
            "gpu_after": gpu_after,
            "targets": [{"model": m, "num_predict": n} for m, n in targets],
            "results": reports,
        },
    )

    env_name = "unknown-gpu"
    if gpu_after.get("available") and gpu_after.get("gpus"):
        first = gpu_after["gpus"][0]
        env_name = f"{first.get('name', 'GPU')} | driver {first.get('driver', 'unknown')} | Ollama {ollama_version}"
    else:
        env_name = f"CPU/unknown GPU | Ollama {ollama_version}"

    update_status(len(success_reports), now_iso)
    update_changelog(success_reports, failed_reports, env_name, now_iso)

    append_log(
        log_file,
        {
            "level": "info",
            "event": "benchmark_end",
            "ts": utc_now_iso(),
            "success_count": len(success_reports),
            "failed_count": len(failed_reports),
        },
    )

    print(f"weekly benchmark completed: success={len(success_reports)}, failed={len(failed_reports)}")
    print(f"results file: {RESULTS_FILE}")
    print(f"log file: {log_file}")

    if not success_reports and not args.allow_empty:
        raise SystemExit("no successful benchmark samples collected")


if __name__ == "__main__":
    main()
