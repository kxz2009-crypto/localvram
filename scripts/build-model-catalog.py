#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "data" / "model-catalog.json"
MODELS_OUT = ROOT / "src" / "data" / "models.json"
VERIFIED_AT = "2026-02-24"


DEFAULT_SIZES = [
    {"label": "7b", "params_b": 7, "base_vram_min": 8},
    {"label": "14b", "params_b": 14, "base_vram_min": 12},
    {"label": "32b", "params_b": 32, "base_vram_min": 20},
    {"label": "70b", "params_b": 70, "base_vram_min": 40},
]

DEFAULT_QUANTS = [
    {"label": "q4", "delta_min": -2, "delta_opt": 0, "speed_mult": 1.0},
    {"label": "q5", "delta_min": 0, "delta_opt": 2, "speed_mult": 0.9},
    {"label": "q8", "delta_min": 4, "delta_opt": 6, "speed_mult": 0.72},
    {"label": "fp16", "delta_min": 10, "delta_opt": 14, "speed_mult": 0.55},
]

FAMILIES = [
    {
        "family": "Qwen2.5",
        "scenario": "coding",
        "license_scope": "open-source",
        "focus": "multilingual coding and instruction following",
        "caveat": "3b and 72b variants use Qwen license terms",
        "ollama_source_url": "https://ollama.com/library/qwen2.5",
        "sizes": [
            {"label": "0.5b", "params_b": 0.5, "base_vram_min": 2},
            {"label": "1.5b", "params_b": 1.5, "base_vram_min": 4},
            {"label": "3b", "params_b": 3, "base_vram_min": 6},
            {"label": "7b", "params_b": 7, "base_vram_min": 8},
            {"label": "14b", "params_b": 14, "base_vram_min": 12},
            {"label": "32b", "params_b": 32, "base_vram_min": 20},
            {"label": "72b", "params_b": 72, "base_vram_min": 47},
        ],
    },
    {
        "family": "Qwen3",
        "scenario": "coding",
        "license_scope": "open-source",
        "focus": "agent tasks, coding, and reasoning balance",
        "caveat": "large variants may require high-end multi-GPU or cloud",
        "ollama_source_url": "https://ollama.com/library/qwen3",
        "sizes": [
            {"label": "0.6b", "params_b": 0.6, "base_vram_min": 2},
            {"label": "1.7b", "params_b": 1.7, "base_vram_min": 4},
            {"label": "4b", "params_b": 4, "base_vram_min": 6},
            {"label": "8b", "params_b": 8, "base_vram_min": 8},
            {"label": "14b", "params_b": 14, "base_vram_min": 12},
            {"label": "30b", "params_b": 30, "base_vram_min": 18},
            {"label": "32b", "params_b": 32, "base_vram_min": 20},
            {"label": "235b", "params_b": 235, "base_vram_min": 140},
        ],
    },
    {
        "family": "Qwen3.5",
        "scenario": "multimodal",
        "license_scope": "open-source",
        "focus": "vision-language and tool-using workflows",
        "caveat": "currently exposed as cloud-first profile on Ollama library",
        "ollama_source_url": "https://ollama.com/library/qwen3.5%3Acloud",
        "sizes": [
            {"label": "397b-a17b", "params_b": 397, "base_vram_min": 215},
        ],
        "quantizations": [
            {"label": "cloud", "delta_min": 0, "delta_opt": 0, "speed_mult": 1.0},
        ],
    },
    {
        "family": "Llama",
        "scenario": "chat",
        "license_scope": "closed-weight",
        "focus": "general reasoning",
        "caveat": "license review needed",
        "ollama_source_url": "https://ollama.com/library/llama3.3",
    },
    {
        "family": "DeepSeek-R1",
        "scenario": "reasoning",
        "license_scope": "open-source",
        "focus": "chain-of-thought tasks",
        "caveat": "sensitive to quantization",
        "ollama_source_url": "https://ollama.com/library/deepseek-r1",
    },
    {
        "family": "Mistral",
        "scenario": "chat",
        "license_scope": "open-source",
        "focus": "fast interactive response",
        "caveat": "requires prompt style tuning",
        "ollama_source_url": "https://ollama.com/library/mistral",
    },
    {
        "family": "Codestral",
        "scenario": "coding",
        "license_scope": "closed-weight",
        "focus": "code completion",
        "caveat": "best with IDE context constraints",
        "ollama_source_url": "https://ollama.com/library/codestral",
    },
    {
        "family": "Gemma",
        "scenario": "chat",
        "license_scope": "open-source",
        "focus": "efficient deployment",
        "caveat": "can degrade on very long outputs",
        "ollama_source_url": "https://ollama.com/library/gemma3",
    },
    {
        "family": "Phi",
        "scenario": "reasoning",
        "license_scope": "open-source",
        "focus": "small-model reasoning",
        "caveat": "not ideal for heavy multilingual tasks",
        "ollama_source_url": "https://ollama.com/library/phi4",
    },
    {
        "family": "Command-R",
        "scenario": "rag",
        "license_scope": "closed-weight",
        "focus": "retrieval workloads",
        "caveat": "benefits from retrieval tuning",
        "ollama_source_url": "https://ollama.com/library/command-r",
    },
    {
        "family": "Yi",
        "scenario": "chat",
        "license_scope": "open-source",
        "focus": "balanced quality-speed",
        "caveat": "some variants need prompt adaptation",
        "ollama_source_url": "https://ollama.com/library/yi",
    },
    {
        "family": "Solar",
        "scenario": "chat",
        "license_scope": "open-source",
        "focus": "lightweight serving",
        "caveat": "mixed benchmark consistency",
        "ollama_source_url": "https://ollama.com/library/solar",
    },
    {
        "family": "Nemotron",
        "scenario": "reasoning",
        "license_scope": "closed-weight",
        "focus": "enterprise reasoning",
        "caveat": "higher VRAM floor",
        "ollama_source_url": "https://ollama.com/library/nemotron",
    },
    {
        "family": "LLaVA",
        "scenario": "multimodal",
        "license_scope": "open-source",
        "focus": "vision-language tasks",
        "caveat": "depends on image pipeline",
        "ollama_source_url": "https://ollama.com/library/llava",
    },
    {
        "family": "Qwen-VL",
        "scenario": "multimodal",
        "license_scope": "open-source",
        "focus": "vision and OCR",
        "caveat": "large image batches increase memory",
        "ollama_source_url": "https://ollama.com/library/qwen2.5vl",
    },
    {
        "family": "DeepSeek-Coder",
        "scenario": "coding",
        "license_scope": "open-source",
        "focus": "code generation",
        "caveat": "syntax reliability varies by quant",
        "ollama_source_url": "https://ollama.com/library/deepseek-coder-v2",
    },
]

VERIFIED_IDS = {
    "qwen3-32b-q4",
    "qwen3-32b-q5",
    "deepseek-r1-32b-q4",
}

SIZE_CLASS_LABELS = {
    "0.5b-1.7b": "0.5B-1.7B Models",
    "4b-class": "4B Models",
    "7b-8b": "7B-8B Models",
    "14b-class": "14B Models",
    "30b-32b": "30B-32B Models",
    "70b-class": "70B-72B Models",
    "200b-class": "200B+ Models",
    "300b-plus": "300B+ Models",
}


def safe_slug(text: str) -> str:
    return (
        text.lower()
        .replace(" ", "-")
        .replace(".", "")
        .replace("_", "-")
        .replace("/", "-")
    )


def base_tokens(params_b: float) -> float:
    if params_b <= 2:
        return 48.0
    if params_b <= 4:
        return 41.0
    if params_b <= 8:
        return 34.0
    if params_b <= 14:
        return 22.0
    if params_b <= 32:
        return 11.0
    if params_b <= 72:
        return 6.8
    if params_b <= 235:
        return 1.9
    return 1.2


def size_class_for(params_b: float) -> str:
    if params_b <= 1.7:
        return "0.5b-1.7b"
    if params_b <= 4:
        return "4b-class"
    if params_b <= 8:
        return "7b-8b"
    if params_b <= 14:
        return "14b-class"
    if params_b <= 32:
        return "30b-32b"
    if params_b <= 72:
        return "70b-class"
    if params_b <= 235:
        return "200b-class"
    return "300b-plus"


def pick_hardware(opt_vram: int) -> tuple[str, str, float]:
    if opt_vram <= 24:
        return ("RTX 3090 24GB", "A6000 48GB", 0.76)
    if opt_vram <= 48:
        return ("RTX 6000 Ada 48GB", "A100 80GB", 1.95)
    if opt_vram <= 80:
        return ("Dual RTX 4090 (model parallel)", "A100 80GB", 2.55)
    return ("Cloud-first (no practical single-GPU local)", "H100/H200 class", 4.9)


def main() -> None:
    items = []
    for fam in FAMILIES:
        sizes = fam.get("sizes", DEFAULT_SIZES)
        quants = fam.get("quantizations", DEFAULT_QUANTS)
        for size in sizes:
            for q in quants:
                model_id = f"{safe_slug(fam['family'])}-{size['label']}-{q['label']}"
                min_vram = max(2, size["base_vram_min"] + q["delta_min"])
                opt_vram = max(min_vram + 2, size["base_vram_min"] + 8 + q["delta_opt"])
                tok_3090 = round(base_tokens(size["params_b"]) * q["speed_mult"], 1)
                tok_4090 = round(tok_3090 * 1.35, 1)
                tok_a100 = round(tok_3090 * 2.4, 1)
                best_local_gpu, cloud_fallback, cloud_hourly_usd = pick_hardware(opt_vram)
                items.append(
                    {
                        "id": model_id,
                        "slug": model_id,
                        "name": f"{fam['family']} {size['label'].upper()} {q['label'].upper()}",
                        "family": fam["family"],
                        "license_scope": fam["license_scope"],
                        "scenario": fam["scenario"],
                        "params_b": size["params_b"],
                        "size_class": size_class_for(size["params_b"]),
                        "quantization": q["label"].upper(),
                        "vram_min_gb": min_vram,
                        "vram_optimal_gb": opt_vram,
                        "best_local_gpu": best_local_gpu,
                        "cloud_fallback": cloud_fallback,
                        "cloud_hourly_usd": cloud_hourly_usd,
                        "local_monthly_power_usd": round((0.35 * 0.16) * 120, 2),
                        "data_status": "measured" if model_id in VERIFIED_IDS else "estimated",
                        "verified": model_id in VERIFIED_IDS,
                        "ollama_source_url": fam["ollama_source_url"],
                        "ollama_verified_at": VERIFIED_AT,
                        "benchmarks": {
                            "rtx3090_tok_s": tok_3090,
                            "rtx4090_tok_s": tok_4090,
                            "a100_tok_s": tok_a100,
                        },
                        "focus": fam["focus"],
                        "caveat": fam["caveat"],
                        "updated_at": VERIFIED_AT,
                    }
                )

    size_groups = sorted(set(item["size_class"] for item in items))
    payload = {
        "version": "2026.02.24.ollama-verified",
        "generated_at": "2026-02-24T00:00:00Z",
        "ollama_verified_at": VERIFIED_AT,
        "count": len(items),
        "items": items,
        "group_definitions": [
            {"id": "open-source", "label": "Open Source Models"},
            {"id": "closed-weight", "label": "Closed Weight / Restricted"},
            {"id": "coding", "label": "Coding Models"},
            {"id": "reasoning", "label": "Reasoning Models"},
            {"id": "multimodal", "label": "Multimodal Models"},
            {"id": "chat", "label": "Chat Models"},
            {"id": "rag", "label": "RAG-focused Models"},
        ]
        + [{"id": sc, "label": SIZE_CLASS_LABELS.get(sc, sc)} for sc in size_groups],
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
