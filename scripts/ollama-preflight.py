#!/usr/bin/env python3
import argparse
import json
import os
import urllib.error
import urllib.request


def normalize_endpoint(endpoint: str) -> str:
    return (endpoint or "").strip().rstrip("/")


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Ollama endpoint/model visibility before benchmark.")
    parser.add_argument(
        "--endpoint",
        default=os.getenv("LV_OLLAMA_ENDPOINT") or os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434",
    )
    parser.add_argument("--required-targets", default=os.getenv("LV_WEEKLY_TARGETS", ""))
    parser.add_argument("--allow-empty-models", action="store_true")
    parser.add_argument("--allow-no-runnable-targets", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    endpoint = normalize_endpoint(args.endpoint)
    required_targets = parse_targets(args.required_targets)

    print(f"ollama_endpoint={endpoint}")
    print(f"ollama_models_dir={os.getenv('OLLAMA_MODELS', '')}")
    try:
        local_models = fetch_local_models(endpoint)
    except urllib.error.URLError as exc:
        raise SystemExit(f"failed to connect to Ollama endpoint: {exc}") from exc
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Ollama endpoint returned HTTP {exc.code}: {exc.reason}") from exc

    local_models_sorted = sorted(local_models)
    print(f"ollama_models_count={len(local_models_sorted)}")
    sample = ", ".join(local_models_sorted[:12]) if local_models_sorted else "<empty>"
    print(f"ollama_models_sample={sample}")

    if required_targets:
        runnable: list[str] = []
        for target in required_targets:
            if any(is_variant(local_tag, target) for local_tag in local_models):
                runnable.append(target)
        print(f"required_targets_count={len(required_targets)}")
        print(f"required_targets_runnable_count={len(runnable)}")
        print(f"required_targets_runnable={','.join(runnable) if runnable else '<none>'}")
        if not args.allow_no_runnable_targets and len(runnable) == 0:
            raise SystemExit("no runnable required targets found in Ollama model list")

    if not args.allow_empty_models and len(local_models_sorted) == 0:
        raise SystemExit("Ollama model list is empty")


if __name__ == "__main__":
    main()

