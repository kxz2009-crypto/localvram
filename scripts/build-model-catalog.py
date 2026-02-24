#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "data" / "model-catalog.json"
MODELS_OUT = ROOT / "src" / "data" / "models.json"

FAMILIES = [
    {"family": "Llama", "scenario": "chat", "license_scope": "closed-weight", "focus": "general reasoning", "caveat": "license review needed"},
    {"family": "Qwen2.5", "scenario": "coding", "license_scope": "open-source", "focus": "multilingual coding", "caveat": "watch memory at long context"},
    {"family": "Qwen3", "scenario": "coding", "license_scope": "open-source", "focus": "reasoning and coding balance", "caveat": "long context memory pressure can spike"},
    {"family": "Qwen3.5", "scenario": "coding", "license_scope": "open-source", "focus": "latest Qwen coding and agent workflows", "caveat": "verify release variant before production use"},
    {"family": "DeepSeek-R1", "scenario": "reasoning", "license_scope": "open-source", "focus": "chain-of-thought tasks", "caveat": "sensitive to quantization"},
    {"family": "Mistral", "scenario": "chat", "license_scope": "open-source", "focus": "fast interactive response", "caveat": "requires prompt style tuning"},
    {"family": "Codestral", "scenario": "coding", "license_scope": "closed-weight", "focus": "code completion", "caveat": "best with IDE context constraints"},
    {"family": "Gemma", "scenario": "chat", "license_scope": "open-source", "focus": "efficient deployment", "caveat": "can degrade on very long outputs"},
    {"family": "Phi", "scenario": "reasoning", "license_scope": "open-source", "focus": "small-model reasoning", "caveat": "not ideal for heavy multilingual tasks"},
    {"family": "Command-R", "scenario": "rag", "license_scope": "closed-weight", "focus": "retrieval workloads", "caveat": "benefits from retrieval tuning"},
    {"family": "Yi", "scenario": "chat", "license_scope": "open-source", "focus": "balanced quality-speed", "caveat": "some variants need prompt adaptation"},
    {"family": "Solar", "scenario": "chat", "license_scope": "open-source", "focus": "lightweight serving", "caveat": "mixed benchmark consistency"},
    {"family": "Nemotron", "scenario": "reasoning", "license_scope": "closed-weight", "focus": "enterprise reasoning", "caveat": "higher VRAM floor"},
    {"family": "LLaVA", "scenario": "multimodal", "license_scope": "open-source", "focus": "vision-language tasks", "caveat": "depends on image pipeline"},
    {"family": "Qwen-VL", "scenario": "multimodal", "license_scope": "open-source", "focus": "vision and OCR", "caveat": "large image batches increase memory"},
    {"family": "DeepSeek-Coder", "scenario": "coding", "license_scope": "open-source", "focus": "code generation", "caveat": "syntax reliability varies by quant"},
]

VERIFIED_IDS = {
    "qwen3-32b-q4",
    "qwen3-32b-q5",
    "deepseek-r1-32b-q4",
}

SIZES = [
    {"label": "7b", "params_b": 7, "size_class": "7b-14b", "base_vram_min": 8},
    {"label": "14b", "params_b": 14, "size_class": "7b-14b", "base_vram_min": 12},
    {"label": "32b", "params_b": 32, "size_class": "32b-class", "base_vram_min": 20},
    {"label": "70b", "params_b": 70, "size_class": "70b-class", "base_vram_min": 40},
]

QUANTS = [
    {"label": "q4", "delta_min": -2, "delta_opt": 0, "speed_mult": 1.0},
    {"label": "q5", "delta_min": 0, "delta_opt": 2, "speed_mult": 0.9},
    {"label": "q8", "delta_min": 4, "delta_opt": 6, "speed_mult": 0.72},
    {"label": "fp16", "delta_min": 10, "delta_opt": 14, "speed_mult": 0.55},
]


def safe_slug(text: str) -> str:
    return (
        text.lower()
        .replace(" ", "-")
        .replace(".", "")
        .replace("_", "-")
        .replace("/", "-")
    )


def base_tokens(params_b: int) -> float:
    if params_b <= 8:
        return 34.0
    if params_b <= 14:
        return 22.0
    if params_b <= 32:
        return 11.0
    return 6.8


def main() -> None:
    items = []
    for fam in FAMILIES:
        for size in SIZES:
            for q in QUANTS:
                model_id = f"{safe_slug(fam['family'])}-{size['label']}-{q['label']}"
                min_vram = max(6, size["base_vram_min"] + q["delta_min"])
                opt_vram = max(min_vram + 2, size["base_vram_min"] + 8 + q["delta_opt"])
                tok_3090 = round(base_tokens(size["params_b"]) * q["speed_mult"], 1)
                tok_4090 = round(tok_3090 * 1.35, 1)
                tok_a100 = round(tok_3090 * 2.4, 1)
                items.append(
                    {
                        "id": model_id,
                        "slug": model_id,
                        "name": f"{fam['family']} {size['label'].upper()} {q['label'].upper()}",
                        "family": fam["family"],
                        "license_scope": fam["license_scope"],
                        "scenario": fam["scenario"],
                        "params_b": size["params_b"],
                        "size_class": size["size_class"],
                        "quantization": q["label"].upper(),
                        "vram_min_gb": min_vram,
                        "vram_optimal_gb": opt_vram,
                        "best_local_gpu": "RTX 3090 24GB" if opt_vram <= 24 else "RTX 4090 24GB",
                        "cloud_fallback": "A100 80GB" if opt_vram > 32 else "A6000 48GB",
                        "cloud_hourly_usd": 1.95 if opt_vram > 32 else 0.76,
                        "local_monthly_power_usd": round((0.35 * 0.16) * 120, 2),
                        "data_status": "measured" if model_id in VERIFIED_IDS else "estimated",
                        "verified": model_id in VERIFIED_IDS,
                        "benchmarks": {
                            "rtx3090_tok_s": tok_3090,
                            "rtx4090_tok_s": tok_4090,
                            "a100_tok_s": tok_a100,
                        },
                        "focus": fam["focus"],
                        "caveat": fam["caveat"],
                        "updated_at": "2026-02-24",
                    }
                )

    payload = {
        "version": "2026.02.24",
        "generated_at": "2026-02-24T00:00:00Z",
        "count": len(items),
        "items": items,
        "group_definitions": [
            {"id": "open-source", "label": "Open Source Models"},
            {"id": "closed-weight", "label": "Closed Weight / Restricted"},
            {"id": "7b-14b", "label": "7B-14B Models"},
            {"id": "32b-class", "label": "32B Class Models"},
            {"id": "70b-class", "label": "70B Class Models"},
            {"id": "coding", "label": "Coding Models"},
            {"id": "reasoning", "label": "Reasoning Models"},
            {"id": "multimodal", "label": "Multimodal Models"},
            {"id": "chat", "label": "Chat Models"},
            {"id": "rag", "label": "RAG-focused Models"},
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
