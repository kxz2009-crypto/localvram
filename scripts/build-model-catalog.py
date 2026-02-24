#!/usr/bin/env python3
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "data" / "model-catalog.json"
MODELS_OUT = ROOT / "src" / "data" / "models.json"
TOP20_CURATED_FILE = ROOT / "src" / "data" / "ollama-top20-curated.json"
VERIFIED_AT = "2026-02-24"
POPULAR_SOURCE = "https://ollama.com/library"


STANDARD_QUANTS = [
    {"label": "q4", "delta_min": -2, "delta_opt": 0, "speed_mult": 1.0},
    {"label": "q5", "delta_min": 0, "delta_opt": 2, "speed_mult": 0.9},
    {"label": "q8", "delta_min": 4, "delta_opt": 6, "speed_mult": 0.72},
    {"label": "fp16", "delta_min": 10, "delta_opt": 14, "speed_mult": 0.55},
]

EMBED_QUANTS = [{"label": "fp16", "delta_min": 0, "delta_opt": 0, "speed_mult": 1.0}]
CLOUD_QUANTS = [{"label": "cloud", "delta_min": 0, "delta_opt": 0, "speed_mult": 1.0}]
MIXED_CLOUD_QUANTS = STANDARD_QUANTS + CLOUD_QUANTS


POPULAR_MODELS = [
    {"id": "llama3.1", "name": "Llama 3.1", "scenario": "chat", "license_scope": "closed-weight", "sizes": ["8b", "70b", "405b"], "source_url": "https://ollama.com/library/llama3.1"},
    {"id": "deepseek-r1", "name": "DeepSeek-R1", "scenario": "reasoning", "license_scope": "open-source", "sizes": ["1.5b", "7b", "8b", "14b", "32b", "67b", "70b", "671b"], "source_url": "https://ollama.com/library/deepseek-r1"},
    {"id": "llama3.2", "name": "Llama 3.2", "scenario": "chat", "license_scope": "closed-weight", "sizes": ["1b", "3b"], "source_url": "https://ollama.com/library/llama3.2"},
    {"id": "nomic-embed-text", "name": "Nomic Embed Text", "scenario": "embedding", "license_scope": "open-source", "sizes": ["137m"], "quant_mode": "embedding", "source_url": "https://ollama.com/library/nomic-embed-text"},
    {"id": "gemma3", "name": "Gemma 3", "scenario": "multimodal", "license_scope": "open-source", "sizes": ["270m", "1b", "4b", "12b", "27b"], "source_url": "https://ollama.com/library/gemma3"},
    {"id": "mistral", "name": "Mistral", "scenario": "chat", "license_scope": "open-source", "sizes": ["7b"], "source_url": "https://ollama.com/library/mistral"},
    {"id": "qwen2.5", "name": "Qwen2.5", "scenario": "coding", "license_scope": "open-source", "sizes": ["0.5b", "1.5b", "3b", "7b", "14b", "32b", "72b"], "source_url": "https://ollama.com/library/qwen2.5"},
    {"id": "qwen3", "name": "Qwen3", "scenario": "coding", "license_scope": "open-source", "sizes": ["0.6b", "1.7b", "4b", "8b", "14b", "30b", "32b", "235b"], "source_url": "https://ollama.com/library/qwen3"},
    {"id": "gemma2", "name": "Gemma 2", "scenario": "chat", "license_scope": "open-source", "sizes": ["2b", "9b", "27b"], "source_url": "https://ollama.com/library/gemma2"},
    {"id": "phi3", "name": "Phi-3", "scenario": "reasoning", "license_scope": "open-source", "sizes": ["3.8b", "14b"], "source_url": "https://ollama.com/library/phi3"},
    {"id": "llama3", "name": "Llama 3", "scenario": "chat", "license_scope": "closed-weight", "sizes": ["8b", "70b"], "source_url": "https://ollama.com/library/llama3"},
    {"id": "llava", "name": "LLaVA", "scenario": "multimodal", "license_scope": "open-source", "sizes": ["7b", "13b", "34b"], "source_url": "https://ollama.com/library/llava"},
    {"id": "qwen2.5-coder", "name": "Qwen2.5 Coder", "scenario": "coding", "license_scope": "open-source", "sizes": ["0.5b", "1.5b", "3b", "7b", "14b", "32b"], "source_url": "https://ollama.com/library/qwen2.5-coder"},
    {"id": "mxbai-embed-large", "name": "MXBAI Embed Large", "scenario": "embedding", "license_scope": "open-source", "sizes": ["335m"], "quant_mode": "embedding", "source_url": "https://ollama.com/library/mxbai-embed-large"},
    {"id": "phi4", "name": "Phi-4", "scenario": "reasoning", "license_scope": "open-source", "sizes": ["14b"], "source_url": "https://ollama.com/library/phi4"},
    {"id": "gpt-oss", "name": "GPT-OSS", "scenario": "reasoning", "license_scope": "open-weight", "sizes": ["20b", "120b"], "quant_mode": "mixed-cloud", "source_url": "https://ollama.com/library/gpt-oss"},
    {"id": "gemma", "name": "Gemma", "scenario": "chat", "license_scope": "open-source", "sizes": ["2b", "7b"], "source_url": "https://ollama.com/library/gemma"},
    {"id": "qwen", "name": "Qwen", "scenario": "chat", "license_scope": "open-source", "sizes": ["0.5b", "1.8b", "4b", "7b", "14b", "32b", "72b", "110b"], "source_url": "https://ollama.com/library/qwen"},
    {"id": "llama2", "name": "Llama 2", "scenario": "chat", "license_scope": "closed-weight", "sizes": ["7b", "13b", "70b"], "source_url": "https://ollama.com/library/llama2"},
    {"id": "qwen2", "name": "Qwen2", "scenario": "chat", "license_scope": "open-source", "sizes": ["0.5b", "1.5b", "7b", "72b"], "source_url": "https://ollama.com/library/qwen2"},
    {"id": "minicpm-v", "name": "MiniCPM-V", "scenario": "multimodal", "license_scope": "open-source", "sizes": ["8b"], "source_url": "https://ollama.com/library/minicpm-v"},
    {"id": "codellama", "name": "CodeLlama", "scenario": "coding", "license_scope": "closed-weight", "sizes": ["7b", "13b", "34b", "70b"], "source_url": "https://ollama.com/library/codellama"},
    {"id": "llama3.2-vision", "name": "Llama 3.2 Vision", "scenario": "multimodal", "license_scope": "closed-weight", "sizes": ["11b", "90b"], "source_url": "https://ollama.com/library/llama3.2-vision"},
    {"id": "tinyllama", "name": "TinyLlama", "scenario": "chat", "license_scope": "open-source", "sizes": ["1.1b"], "source_url": "https://ollama.com/library/tinyllama"},
    {"id": "dolphin3", "name": "Dolphin 3", "scenario": "chat", "license_scope": "open-source", "sizes": ["8b"], "source_url": "https://ollama.com/library/dolphin3"},
    {"id": "deepseek-v3", "name": "DeepSeek-V3", "scenario": "reasoning", "license_scope": "open-source", "sizes": ["67b", "671b"], "source_url": "https://ollama.com/library/deepseek-v3"},
    {"id": "olmo2", "name": "OLMo 2", "scenario": "reasoning", "license_scope": "open-source", "sizes": ["7b", "13b"], "source_url": "https://ollama.com/library/olmo2"},
    {"id": "mistral-nemo", "name": "Mistral Nemo", "scenario": "chat", "license_scope": "open-source", "sizes": ["12b"], "source_url": "https://ollama.com/library/mistral-nemo"},
    {"id": "llama3.3", "name": "Llama 3.3", "scenario": "chat", "license_scope": "closed-weight", "sizes": ["70b"], "source_url": "https://ollama.com/library/llama3.3"},
    {"id": "bge-m3", "name": "BGE-M3", "scenario": "embedding", "license_scope": "open-source", "sizes": ["567m"], "quant_mode": "embedding", "source_url": "https://ollama.com/library/bge-m3"},
    {"id": "qwen3-coder", "name": "Qwen3 Coder", "scenario": "coding", "license_scope": "open-source", "sizes": ["30b", "480b"], "quant_mode": "mixed-cloud", "source_url": "https://ollama.com/library/qwen3-coder"},
    {"id": "deepseek-coder", "name": "DeepSeek Coder", "scenario": "coding", "license_scope": "open-source", "sizes": ["1.3b", "6.7b", "33b"], "source_url": "https://ollama.com/library/deepseek-coder"},
    {"id": "smollm2", "name": "SmolLM2", "scenario": "chat", "license_scope": "open-source", "sizes": ["135m", "360m", "1.7b"], "source_url": "https://ollama.com/library/smollm2"},
    {"id": "all-minilm", "name": "All-MiniLM", "scenario": "embedding", "license_scope": "open-source", "sizes": ["22m", "33m"], "quant_mode": "embedding", "source_url": "https://ollama.com/library/all-minilm"},
    {"id": "mistral-small", "name": "Mistral Small", "scenario": "chat", "license_scope": "closed-weight", "sizes": ["22b", "24b"], "source_url": "https://ollama.com/library/mistral-small"},
    {"id": "codegemma", "name": "CodeGemma", "scenario": "coding", "license_scope": "open-source", "sizes": ["2b", "7b"], "source_url": "https://ollama.com/library/codegemma"},
    {"id": "granite3.1-moe", "name": "Granite 3.1 MoE", "scenario": "reasoning", "license_scope": "open-source", "sizes": ["1b", "3b"], "source_url": "https://ollama.com/library/granite3.1-moe"},
    {"id": "falcon3", "name": "Falcon 3", "scenario": "chat", "license_scope": "open-source", "sizes": ["1b", "3b", "7b", "10b"], "source_url": "https://ollama.com/library/falcon3"},
    {"id": "llava-llama3", "name": "LLaVA Llama3", "scenario": "multimodal", "license_scope": "open-source", "sizes": ["8b"], "source_url": "https://ollama.com/library/llava-llama3"},
    {"id": "starcoder2", "name": "StarCoder2", "scenario": "coding", "license_scope": "open-source", "sizes": ["3b", "7b", "15b"], "source_url": "https://ollama.com/library/starcoder2"},
    {"id": "snowflake-arctic-embed", "name": "Snowflake Arctic Embed", "scenario": "embedding", "license_scope": "open-source", "sizes": ["22m", "33m", "110m", "137m", "335m"], "quant_mode": "embedding", "source_url": "https://ollama.com/library/snowflake-arctic-embed"},
    {"id": "qwq", "name": "QwQ", "scenario": "reasoning", "license_scope": "open-source", "sizes": ["32b"], "source_url": "https://ollama.com/library/qwq"},
    {"id": "mixtral", "name": "Mixtral", "scenario": "chat", "license_scope": "open-source", "sizes": ["8x7b", "8x22b"], "source_url": "https://ollama.com/library/mixtral"},
    {"id": "zephyr", "name": "Zephyr", "scenario": "chat", "license_scope": "open-source", "sizes": ["7b"], "source_url": "https://ollama.com/library/zephyr"},
    {"id": "openhermes", "name": "OpenHermes", "scenario": "chat", "license_scope": "open-source", "sizes": ["7b"], "source_url": "https://ollama.com/library/openhermes"},
    {"id": "deepseek-coder-v2", "name": "DeepSeek Coder V2", "scenario": "coding", "license_scope": "open-source", "sizes": ["16b", "236b"], "source_url": "https://ollama.com/library/deepseek-coder-v2"},
    {"id": "qwen3-vl", "name": "Qwen3 VL", "scenario": "multimodal", "license_scope": "open-source", "sizes": ["2b", "4b", "8b", "30b", "32b", "235b"], "quant_mode": "mixed-cloud", "source_url": "https://ollama.com/library/qwen3-vl"},
    {"id": "qwen2.5vl", "name": "Qwen2.5 VL", "scenario": "multimodal", "license_scope": "open-source", "sizes": ["3b", "7b", "32b", "72b"], "source_url": "https://ollama.com/library/qwen2.5vl"},
    {"id": "gemma3n", "name": "Gemma 3n", "scenario": "multimodal", "license_scope": "open-source", "sizes": ["e2b", "e4b"], "source_url": "https://ollama.com/library/gemma3n"},
    {"id": "llama4", "name": "Llama 4", "scenario": "multimodal", "license_scope": "closed-weight", "sizes": ["16x17b", "128x17b"], "source_url": "https://ollama.com/library/llama4"},
    {"id": "phi4-reasoning", "name": "Phi-4 Reasoning", "scenario": "reasoning", "license_scope": "open-source", "sizes": ["14b"], "source_url": "https://ollama.com/library/phi4-reasoning"},
    {"id": "magistral", "name": "Magistral", "scenario": "reasoning", "license_scope": "open-source", "sizes": ["24b"], "source_url": "https://ollama.com/library/magistral"},
    {"id": "qwen3.5", "name": "Qwen3.5", "scenario": "multimodal", "license_scope": "open-source", "sizes": ["397b-a17b"], "quant_mode": "cloud", "source_url": "https://ollama.com/library/qwen3.5%3Acloud"},
]

VERIFIED_IDS = {
    "qwen3-32b-q4",
    "qwen3-32b-q5",
    "deepseek-r1-32b-q4",
}

SIZE_CLASS_LABELS = {
    "tiny-class": "Sub-2B Models",
    "4b-class": "2B-4B Models",
    "7b-8b": "7B-8B Models",
    "14b-class": "9B-14B Models",
    "30b-34b": "15B-34B Models",
    "70b-class": "35B-72B Models",
    "100b-250b": "73B-250B Models",
    "250b-plus": "250B+ Models",
}


def safe_slug(text: str) -> str:
    return text.lower().replace(" ", "-").replace(".", "").replace("_", "-").replace("/", "-")


def parse_params(size_label: str) -> float:
    s = size_label.lower().strip()
    if s == "cloud":
        return 120.0

    m = re.match(r"^e([0-9.]+)b$", s)
    if m:
        return float(m.group(1))

    m = re.match(r"^([0-9.]+)x([0-9.]+)b$", s)
    if m:
        return float(m.group(1)) * float(m.group(2))

    m = re.match(r"^([0-9.]+)b-a([0-9.]+)b$", s)
    if m:
        return float(m.group(1))

    m = re.match(r"^([0-9.]+)b$", s)
    if m:
        return float(m.group(1))

    m = re.match(r"^([0-9.]+)m$", s)
    if m:
        return float(m.group(1)) / 1000.0

    return 7.0


def base_vram_floor(params_b: float) -> int:
    if params_b <= 0.5:
        return 2
    if params_b <= 2:
        return 4
    if params_b <= 4:
        return 6
    if params_b <= 8:
        return 8
    if params_b <= 14:
        return 12
    if params_b <= 34:
        return 20
    if params_b <= 72:
        return 40
    if params_b <= 120:
        return 70
    if params_b <= 250:
        return 140
    if params_b <= 500:
        return 215
    return 420


def base_tokens(params_b: float) -> float:
    if params_b <= 1:
        return 48.0
    if params_b <= 2:
        return 42.0
    if params_b <= 4:
        return 36.0
    if params_b <= 8:
        return 30.0
    if params_b <= 14:
        return 21.0
    if params_b <= 34:
        return 11.0
    if params_b <= 72:
        return 6.8
    if params_b <= 250:
        return 1.9
    return 1.1


def size_class_for(params_b: float) -> str:
    if params_b <= 2:
        return "tiny-class"
    if params_b <= 4:
        return "4b-class"
    if params_b <= 8:
        return "7b-8b"
    if params_b <= 14:
        return "14b-class"
    if params_b <= 34:
        return "30b-34b"
    if params_b <= 72:
        return "70b-class"
    if params_b <= 250:
        return "100b-250b"
    return "250b-plus"


def pick_hardware(opt_vram: int) -> tuple[str, str, float]:
    if opt_vram <= 24:
        return ("RTX 3090 24GB", "A6000 48GB", 0.76)
    if opt_vram <= 48:
        return ("RTX 6000 Ada 48GB", "A100 80GB", 1.95)
    if opt_vram <= 80:
        return ("Dual RTX 4090 (model parallel)", "A100 80GB", 2.55)
    return ("Cloud-first (no practical single-GPU local)", "H100/H200 class", 4.9)


def quant_list(entry: dict) -> list[dict]:
    mode = entry.get("quant_mode", "standard")
    if mode == "embedding":
        return EMBED_QUANTS
    if mode == "cloud":
        return CLOUD_QUANTS
    if mode == "mixed-cloud":
        return MIXED_CLOUD_QUANTS
    return STANDARD_QUANTS


def parse_vram_gb(text: str) -> int:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", text or "")
    if not match:
        return 0
    return int(float(match.group(1)))


def load_top20_overrides() -> dict[tuple[str, str], dict]:
    if not TOP20_CURATED_FILE.exists():
        return {}

    payload = json.loads(TOP20_CURATED_FILE.read_text(encoding="utf-8-sig"))
    overrides: dict[tuple[str, str], dict] = {}
    for rank, model in enumerate(payload.get("models", []), start=1):
        slug = str(model.get("slug", "")).strip().lower()
        if not slug:
            continue

        q4 = parse_vram_gb(str(model.get("vram_q4", "")))
        q5 = parse_vram_gb(str(model.get("vram_q5", "")))
        vram_q4 = q4 if q4 > 0 else 8
        vram_q5 = q5 if q5 > 0 else max(vram_q4 + 2, 10)
        common = {
            "top20_rank": rank,
            "popularity": model.get("popularity", ""),
            "category_label": model.get("category", ""),
            "seo_title": model.get("seo_title", ""),
            "ollama_command": model.get("ollama_command", f"ollama run {slug}"),
            "recommended_hardware": model.get("recommended_hardware", ""),
        }
        overrides[(slug, "q4")] = {
            **common,
            "vram_min_gb": vram_q4,
            "vram_optimal_gb": max(vram_q5, vram_q4 + 2),
        }
        overrides[(slug, "q5")] = {
            **common,
            "vram_min_gb": vram_q5,
            "vram_optimal_gb": max(vram_q5 + 2, vram_q4 + 4),
        }

    return overrides


def main() -> None:
    items = []
    top20_overrides = load_top20_overrides()

    for entry in POPULAR_MODELS:
        base_slug = safe_slug(entry["id"])
        for size_label in entry["sizes"]:
            params_b = parse_params(size_label)
            base_vram = base_vram_floor(params_b)
            for q in quant_list(entry):
                model_id = f"{base_slug}-{size_label}-{q['label']}"
                ollama_tag = f"{entry['id']}:{size_label}".lower()
                min_vram = max(2, base_vram + q["delta_min"])
                opt_vram = max(min_vram + 2, base_vram + 8 + q["delta_opt"])
                override = top20_overrides.get((ollama_tag, q["label"]))
                if override:
                    min_vram = int(override["vram_min_gb"])
                    opt_vram = int(override["vram_optimal_gb"])
                tok_3090 = round(base_tokens(params_b) * q["speed_mult"], 1)
                tok_4090 = round(tok_3090 * 1.35, 1)
                tok_a100 = round(tok_3090 * 2.4, 1)
                best_local_gpu, cloud_fallback, cloud_hourly_usd = pick_hardware(opt_vram)
                seo_title = override["seo_title"] if override else f"{entry['name']} {size_label.upper()} on RTX 3090: Performance & VRAM Requirements"
                popularity = override["popularity"] if override else ""
                category_label = override["category_label"] if override else entry["scenario"]
                ollama_command = override["ollama_command"] if override else f"ollama run {entry['id']}:{size_label}"
                recommended_hardware = override["recommended_hardware"] if override else best_local_gpu

                items.append(
                    {
                        "id": safe_slug(model_id),
                        "slug": safe_slug(model_id),
                        "name": f"{entry['name']} {size_label.upper()} {q['label'].upper()}",
                        "family": entry["name"],
                        "library_id": entry["id"],
                        "license_scope": entry["license_scope"],
                        "scenario": entry["scenario"],
                        "params_b": params_b,
                        "size_class": size_class_for(params_b),
                        "quantization": q["label"].upper(),
                        "vram_min_gb": min_vram,
                        "vram_optimal_gb": opt_vram,
                        "best_local_gpu": best_local_gpu,
                        "recommended_hardware": recommended_hardware,
                        "cloud_fallback": cloud_fallback,
                        "cloud_hourly_usd": cloud_hourly_usd,
                        "local_monthly_power_usd": round((0.35 * 0.16) * 120, 2),
                        "data_status": "measured" if safe_slug(model_id) in VERIFIED_IDS else "estimated",
                        "verified": safe_slug(model_id) in VERIFIED_IDS,
                        "is_top20_curated": override is not None,
                        "top20_rank": override["top20_rank"] if override else None,
                        "popularity": popularity,
                        "category_label": category_label,
                        "ollama_tag": ollama_tag,
                        "seo_title": seo_title,
                        "ollama_command": ollama_command,
                        "ollama_source_url": entry["source_url"],
                        "ollama_verified_at": VERIFIED_AT,
                        "benchmarks": {
                            "rtx3090_tok_s": tok_3090,
                            "rtx4090_tok_s": tok_4090,
                            "a100_tok_s": tok_a100,
                        },
                        "focus": "Top-20 curated profile from ollama.com popular list." if override else f"Popular Ollama model family: {entry['name']}",
                        "caveat": "Estimated values are placeholders unless marked measured.",
                        "updated_at": VERIFIED_AT,
                    }
                )

    size_groups = sorted(set(item["size_class"] for item in items))
    scenario_groups = sorted(set(item["scenario"] for item in items))
    license_groups = sorted(set(item["license_scope"] for item in items))

    payload = {
        "version": "2026.02.24.ollama-popular",
        "generated_at": "2026-02-24T00:00:00Z",
        "ollama_verified_at": VERIFIED_AT,
        "ollama_source": POPULAR_SOURCE,
        "top20_curated_source": "src/data/ollama-top20-curated.json",
        "top20_curated_count": len({k[0] for k in top20_overrides.keys()}),
        "count": len(items),
        "items": items,
        "group_definitions": [
            {"id": lid, "label": f"{lid.title()} Models"} for lid in license_groups
        ] + [
            {"id": sid, "label": f"{sid.title()} Models"} for sid in scenario_groups
        ] + [
            {"id": sc, "label": SIZE_CLASS_LABELS.get(sc, sc)} for sc in size_groups
        ],
    }

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    models_payload = {
        "version": payload["version"],
        "count": len(items),
        "models": [
            {
                "id": item["id"],
                "name": item["name"],
                "quantizations": [item["quantization"]],
                "verified": bool(item["verified"]),
            }
            for item in items
        ],
    }
    MODELS_OUT.write_text(json.dumps(models_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"generated {len(items)} models -> {OUT}")
    print(f"synced {len(items)} model rows -> {MODELS_OUT}")


if __name__ == "__main__":
    main()
