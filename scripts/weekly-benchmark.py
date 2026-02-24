#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STATUS_FILE = ROOT / "src" / "data" / "status.json"
CHANGELOG_FILE = ROOT / "src" / "data" / "benchmark-changelog.json"
RESULTS_FILE = ROOT / "src" / "data" / "benchmark-results.json"
MODEL_CATALOG_FILE = ROOT / "src" / "data" / "model-catalog.json"
LOG_DIR = ROOT / "logs"
SCREENSHOT_DIR = ROOT / "public" / "screenshots"

DEFAULT_TARGETS = "llama3:8b=128,qwen3:8b=128,deepseek-r1:8b=128"
DEFAULT_NUM_CTX = 4096
DEFAULT_PRE_COOLDOWN_S = 5.0
DEFAULT_PROMPT = (
    "You are an inference benchmark probe. "
    "Respond with exactly three short bullet points about local LLM deployment stability."
)


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def run_cmd(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as exc:  # noqa: BLE001
        return 1, "", str(exc)


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


def resolve_default_endpoint() -> str:
    return os.getenv("LV_OLLAMA_ENDPOINT") or os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434"


def safe_file_token(value: str, fallback: str = "unknown") -> str:
    token = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return token or fallback


def get_git_short_sha() -> str:
    env_sha = (os.getenv("GITHUB_SHA") or "").strip()
    if env_sha:
        return env_sha[:7]
    code, out, _ = run_cmd(["git", "rev-parse", "--short", "HEAD"], timeout=10)
    if code == 0 and out:
        return out.strip()
    return "nosha"


def classify_error(error_text: str) -> str:
    txt = (error_text or "").lower()
    if "out of memory" in txt or "oom" in txt:
        return "oom"
    if "timed out" in txt or "timeout" in txt:
        return "timeout"
    if "connection refused" in txt or "failed to connect" in txt:
        return "connectivity"
    return "runtime"


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
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
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


def load_known_model_tags() -> set[str]:
    catalog = read_json(MODEL_CATALOG_FILE, {"items": []})
    tags = set()
    for row in catalog.get("items", []):
        tag = str(row.get("ollama_tag", "")).strip().lower()
        if tag:
            tags.add(tag)
    return tags


def extract_legacy_model_map(payload: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict):
        return {}
    models = payload.get("models")
    if isinstance(models, dict):
        return models
    latest = payload.get("latest")
    if not isinstance(latest, dict):
        return {}

    model_map: dict[str, dict[str, Any]] = {}
    for report in latest.get("results", []):
        model = str(report.get("model", "")).strip().lower()
        if not model:
            continue
        runs = report.get("runs", [])
        prompt_tokens = 0
        eval_tokens = 0
        if runs:
            prompt_tokens = int(round(statistics.mean(r.get("prompt_eval_count", 0) for r in runs)))
            eval_tokens = int(round(statistics.mean(r.get("eval_count", 0) for r in runs)))
        model_map[model] = {
            "tokens_per_second": round(float(report.get("tokens_per_s_avg", 0.0)), 3),
            "latency_ms": round(float(report.get("latency_s_avg", 0.0)) * 1000.0, 2),
            "prompt_tokens": prompt_tokens,
            "eval_tokens": eval_tokens,
            "gpu_snapshot": "",
            "test_time": str(latest.get("updated_at", "")),
            "gpu_model": (
                str(latest.get("gpu_after", {}).get("gpus", [{}])[0].get("name", "unknown"))
                if latest.get("gpu_after", {}).get("gpus")
                else "unknown"
            ),
            "status": report.get("status", "ok"),
        }
    return model_map


def collect_gpu_snapshot_text() -> str:
    cmd = [
        "nvidia-smi",
        "--query-gpu=name,driver_version,memory.total,memory.used,temperature.gpu,power.draw,utilization.gpu",
        "--format=csv",
    ]
    code, out, err = run_cmd(cmd, timeout=10)
    if code != 0:
        return f"nvidia-smi unavailable: {err or 'unknown error'}\n"
    return out + "\n"


def write_gpu_snapshot(now_iso: str, endpoint: str, ollama_version: str, snapshot_text: str, gpu_name: str) -> str:
    ts = now_iso.replace(":", "").replace("-", "")
    gpu_token = safe_file_token(gpu_name, fallback="gpu")
    short_sha = safe_file_token(get_git_short_sha(), fallback="nosha")
    filename = f"{gpu_token}-weekly-{ts}-{short_sha}.txt"
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    file_path = SCREENSHOT_DIR / filename
    content = [
        f"captured_at_utc={now_iso}",
        f"ollama_endpoint={redact_endpoint(endpoint)}",
        f"ollama_version={ollama_version}",
        "",
        snapshot_text.strip(),
        "",
    ]
    file_path.write_text("\n".join(content), encoding="utf-8")
    return f"/screenshots/{filename}"


def has_significant_change(old_row: dict[str, Any] | None, new_row: dict[str, Any], min_delta: float) -> bool:
    if not old_row:
        return True
    if old_row.get("status") != new_row.get("status"):
        return True
    old_tps = old_row.get("tokens_per_second")
    new_tps = new_row.get("tokens_per_second")
    if old_tps is None and new_tps is not None:
        return True
    if isinstance(old_tps, (int, float)) and isinstance(new_tps, (int, float)):
        if abs(float(old_tps) - float(new_tps)) > min_delta:
            return True
    return False


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


def run_single_generation(
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
        "stream": False,
        "options": {"temperature": 0, "num_predict": num_predict, "num_ctx": num_ctx},
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
    num_ctx: int,
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
        "error_type": "",
    }
    if warmup_predict > 0:
        try:
            run_single_generation(endpoint, model, prompt, warmup_predict, num_ctx, timeout_s)
        except Exception as exc:  # noqa: BLE001
            append_log(log_file, {"level": "warn", "event": "warmup_failed", "model": model, "error": str(exc)})

    for idx in range(runs):
        try:
            row = run_single_generation(endpoint, model, prompt, num_predict, num_ctx, timeout_s)
            row["run_index"] = idx + 1
            model_report["runs"].append(row)
            append_log(log_file, {"level": "info", "event": "benchmark_run", **row})
        except Exception as exc:  # noqa: BLE001
            model_report["status"] = "error"
            model_report["error"] = str(exc)
            model_report["error_type"] = classify_error(str(exc))
            append_log(
                log_file,
                {
                    "level": "error",
                    "event": "benchmark_run_failed",
                    "model": model,
                    "run_index": idx + 1,
                    "error": str(exc),
                    "error_type": model_report["error_type"],
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
        oom_models = [r["model"] for r in failed_reports if r.get("error_type") == "oom"]
        if oom_models:
            changes.append(f"OOM captured for: {', '.join(oom_models[:5])}")
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
    parser.add_argument("--endpoint", default=resolve_default_endpoint())
    parser.add_argument("--targets", default=os.getenv("LV_WEEKLY_TARGETS", DEFAULT_TARGETS))
    parser.add_argument("--runs", type=int, default=int(os.getenv("LV_RUNS_PER_MODEL", "2")))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("LV_BENCHMARK_TIMEOUT_S", "600")))
    parser.add_argument("--warmup-predict", type=int, default=int(os.getenv("LV_WARMUP_PREDICT", "24")))
    parser.add_argument("--num-ctx", type=int, default=int(os.getenv("LV_BENCHMARK_NUM_CTX", str(DEFAULT_NUM_CTX))))
    parser.add_argument(
        "--pre-cooldown-s",
        type=float,
        default=float(os.getenv("LV_PRE_COOLDOWN_S", str(DEFAULT_PRE_COOLDOWN_S))),
    )
    parser.add_argument(
        "--verified-tooltip",
        default=os.getenv(
            "LV_VERIFIED_TOOLTIP",
            "Tested on local RTX 3090, 450W TDP, Ambient 25C",
        ),
    )
    parser.add_argument("--prompt", default=os.getenv("LV_BENCHMARK_PROMPT", DEFAULT_PROMPT))
    parser.add_argument("--min-delta", type=float, default=float(os.getenv("LV_SIGNIFICANT_TPS_DELTA", "0.5")))
    parser.add_argument(
        "--log-retention-days",
        type=int,
        default=int(os.getenv("LV_BENCHMARK_LOG_RETENTION_DAYS", "30")),
    )
    parser.add_argument("--allow-empty", action="store_true", help="Do not fail when no successful sample is collected.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    endpoint = normalize_endpoint(args.endpoint)
    redacted_endpoint = redact_endpoint(endpoint)
    now_iso = utc_now_iso()
    log_file = LOG_DIR / f"weekly-benchmark-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d')}.log"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    deleted_logs = prune_old_logs(LOG_DIR, "weekly-benchmark-", max(0, args.log_retention_days))

    if args.dry_run:
        print("dry-run: weekly benchmark execution skipped")
        print(f"endpoint={redacted_endpoint}")
        print(f"targets={args.targets}")
        print(f"num_ctx={max(256, args.num_ctx)}")
        print("temperature=0")
        print(f"log_retention_days={args.log_retention_days}")
        return

    targets = parse_targets(args.targets)
    if not targets:
        raise SystemExit("no valid benchmark targets configured")
    known_tags = load_known_model_tags()

    try:
        local_models = list_local_models(endpoint)
    except urllib.error.URLError as exc:
        raise SystemExit(f"failed to connect to Ollama at {endpoint}: {exc}") from exc
    local_models = {x.lower() for x in local_models}

    pre_cooldown_s = max(0.0, args.pre_cooldown_s)
    if pre_cooldown_s > 0:
        time.sleep(pre_cooldown_s)

    gpu_before = collect_gpu_snapshot()
    ollama_version = fetch_ollama_version(endpoint)
    append_log(
        log_file,
        {
            "level": "info",
            "event": "benchmark_start",
            "ts": now_iso,
            "endpoint": redacted_endpoint,
            "targets": targets,
            "num_ctx": max(256, args.num_ctx),
            "temperature": 0,
            "pre_cooldown_s": pre_cooldown_s,
            "ollama_version": ollama_version,
            "gpu_before": gpu_before,
            "deleted_logs": deleted_logs,
            "significant_tps_delta": args.min_delta,
        },
    )

    reports: list[dict[str, Any]] = []
    for model, num_predict in targets:
        model_tag = model.strip().lower()
        if known_tags and model_tag not in known_tags:
            report = {
                "model": model_tag,
                "num_predict": num_predict,
                "status": "error",
                "runs": [],
                "error": "model tag not found in model-catalog (ollama_tag mismatch)",
                "error_type": "unknown_model_tag",
            }
            reports.append(report)
            append_log(log_file, {"level": "error", "event": "model_tag_unknown", **report})
            continue

        if model_tag not in local_models:
            report = {
                "model": model_tag,
                "num_predict": num_predict,
                "status": "error",
                "runs": [],
                "error": "model not found locally (run `ollama pull` on runner first)",
                "error_type": "missing_model",
            }
            reports.append(report)
            append_log(log_file, {"level": "error", "event": "model_missing", **report})
            continue
        report = benchmark_model(
            endpoint=endpoint,
            model=model_tag,
            prompt=args.prompt,
            num_predict=num_predict,
            num_ctx=max(256, args.num_ctx),
            timeout_s=args.timeout,
            runs=max(1, args.runs),
            warmup_predict=max(0, args.warmup_predict),
            log_file=log_file,
        )
        reports.append(report)

    success_reports = [r for r in reports if r.get("status") == "ok" and r.get("runs")]
    failed_reports = [r for r in reports if r.get("status") != "ok"]
    gpu_after = collect_gpu_snapshot()

    gpu_name = "unknown"
    if gpu_after.get("available") and gpu_after.get("gpus"):
        gpu_name = str(gpu_after["gpus"][0].get("name", "unknown"))

    history_limit = max(5, int(os.getenv("LV_BENCHMARK_HISTORY_LIMIT", "20")))
    old_payload = read_json(RESULTS_FILE, {})
    old_model_map_raw = extract_legacy_model_map(old_payload)
    old_model_map: dict[str, dict[str, Any]] = {
        str(k).strip().lower(): v for k, v in old_model_map_raw.items() if isinstance(v, dict)
    }

    next_model_rows: dict[str, dict[str, Any]] = {}
    for report in success_reports:
        runs = report.get("runs", [])
        prompt_tokens = int(round(statistics.mean(r.get("prompt_eval_count", 0) for r in runs))) if runs else 0
        eval_tokens = int(round(statistics.mean(r.get("eval_count", 0) for r in runs))) if runs else 0
        model_tag = str(report.get("model", "")).strip().lower()
        next_model_rows[model_tag] = {
            "tokens_per_second": round(float(report.get("tokens_per_s_avg", 0.0)), 3),
            "latency_ms": round(float(report.get("latency_s_avg", 0.0)) * 1000.0, 2),
            "prompt_tokens": prompt_tokens,
            "eval_tokens": eval_tokens,
            "gpu_snapshot": "",
            "test_time": now_iso,
            "gpu_model": gpu_name,
            "status": "ok",
            "error_type": "",
            "error": "",
            "run_count": len(runs),
            "num_ctx": max(256, args.num_ctx),
            "temperature": 0,
            "verified_tooltip": str(args.verified_tooltip).strip(),
        }

    changed_models = sorted(
        [
            model_tag
            for model_tag, row in next_model_rows.items()
            if has_significant_change(old_model_map.get(model_tag), row, max(0.0, args.min_delta))
        ]
    )
    should_write_results = bool(changed_models or failed_reports or not old_model_map)
    snapshot_path = ""
    if should_write_results and changed_models:
        snapshot_path = write_gpu_snapshot(
            now_iso,
            endpoint,
            ollama_version,
            collect_gpu_snapshot_text(),
            gpu_name,
        )

    if should_write_results:
        for model_tag in changed_models:
            row = dict(next_model_rows[model_tag])
            row["gpu_snapshot"] = snapshot_path or str(old_model_map.get(model_tag, {}).get("gpu_snapshot", ""))
            old_model_map[model_tag] = row

    latest_run = {
        "updated_at": now_iso,
        "runner": {
            "hostname": platform.node(),
            "platform": platform.platform(),
            "python": sys.version.split()[0],
        },
        "ollama": {
            "endpoint": redacted_endpoint,
            "version": ollama_version,
            "available_model_count": len(local_models),
        },
        "gpu_before": gpu_before,
        "gpu_after": gpu_after,
        "targets": [{"model": m, "num_predict": n, "num_ctx": max(256, args.num_ctx), "temperature": 0} for m, n in targets],
        "results": reports,
        "changed_models": changed_models,
        "significant_tps_delta": max(0.0, args.min_delta),
        "num_ctx": max(256, args.num_ctx),
        "temperature": 0,
        "pre_cooldown_s": pre_cooldown_s,
        "success_count": len(success_reports),
        "failed_count": len(failed_reports),
    }

    env_name = "unknown-gpu"
    if gpu_after.get("available") and gpu_after.get("gpus"):
        first = gpu_after["gpus"][0]
        env_name = f"{first.get('name', 'GPU')} | driver {first.get('driver', 'unknown')} | Ollama {ollama_version}"
    else:
        env_name = f"CPU/unknown GPU | Ollama {ollama_version}"

    if should_write_results:
        history: list[dict[str, Any]]
        if isinstance(old_payload.get("history"), list):
            history = old_payload["history"]
        elif old_payload.get("results"):
            history = [old_payload]
        else:
            history = []
        history.insert(0, latest_run)
        history = history[:history_limit]
        write_json(
            RESULTS_FILE,
            {
                "updated_at": now_iso,
                "history_limit": history_limit,
                "models": dict(sorted(old_model_map.items())),
                "latest": latest_run,
                "history": history,
            },
        )

        update_status(len(success_reports), now_iso)
        update_changelog(success_reports, failed_reports, env_name, now_iso)
    else:
        append_log(
            log_file,
            {
                "level": "info",
                "event": "no_significant_change",
                "ts": now_iso,
                "threshold_tps_delta": max(0.0, args.min_delta),
                "candidate_models": sorted(next_model_rows.keys()),
            },
        )

    append_log(
        log_file,
        {
            "level": "info",
            "event": "benchmark_end",
            "ts": utc_now_iso(),
            "success_count": len(success_reports),
            "failed_count": len(failed_reports),
            "updated_results": should_write_results,
            "changed_models": changed_models,
        },
    )

    print(f"weekly benchmark completed: success={len(success_reports)}, failed={len(failed_reports)}")
    print(f"results file: {RESULTS_FILE}")
    print(f"log file: {log_file}")
    if not should_write_results:
        print(f"no significant model changes detected (> {args.min_delta} tok/s); results file unchanged")

    if not success_reports and not args.allow_empty:
        raise SystemExit("no successful benchmark samples collected")


if __name__ == "__main__":
    main()
