from typing import Any

from relaylm.hardware.detector import HardwareProfile

# (name, min_ram_gb, min_vram_gb)
SMALL_MODELS: list[tuple[str, float, float | None]] = [
    ("Qwen/Qwen3-0.6B", 2.0, 1.0),
    ("Qwen/Qwen3-1.5B", 4.0, 2.0),
    ("gemma-3-1b-it-Q4_K_M", 2.0, 1.0),
]

MEDIUM_MODELS: list[tuple[str, float, float | None]] = [
    ("Qwen/Qwen3-4B", 8.0, 4.0),
    ("mistral-7b-v0.3", 14.0, 4.0),
    ("llama-3.1-8b", 16.0, 5.0),
]

LARGE_MODELS: list[tuple[str, float, float | None]] = [
    ("Qwen/Qwen3-14B", 28.0, 8.0),
    ("codellama-13b", 26.0, 7.0),
    ("mixtral-8x7b", 48.0, 16.0),
]


def _fits_in_ram(model: tuple[str, float, float | None], ram_gb: float) -> bool:
    return model[1] <= ram_gb


def _fits_in_vram(model: tuple[str, float, float | None], vram_gb: float) -> bool:
    vram_needed = model[2]
    return vram_needed is None or vram_needed <= vram_gb


def select_models(
    hardware: HardwareProfile, max_models: int = 2
) -> list[dict[str, Any]]:
    models: list[tuple[str, float, float | None]] = []

    if hardware.gpu_vram_gb:
        vram = max(hardware.gpu_vram_gb)
        candidates = LARGE_MODELS + MEDIUM_MODELS + SMALL_MODELS
        for m in candidates:
            if _fits_in_vram(m, vram) and _fits_in_ram(m, hardware.ram_gb):
                models.append(m)
    else:
        candidates = SMALL_MODELS + MEDIUM_MODELS + LARGE_MODELS
        for m in candidates:
            if _fits_in_ram(m, hardware.ram_gb):
                models.append(m)

    if not models:
        models = SMALL_MODELS[:1]

    result: list[dict[str, Any]] = []
    for name, _, _ in models[:max_models]:
        result.append(
            {"name": name, "source": "huggingface", "gpu_index": None, "args": {}}
        )
    return result


def validate_models(model_ids: list[str]) -> list[str]:
    invalid: list[str] = []
    for model_id in model_ids:
        model_id = model_id.strip()
        if not model_id or "/" not in model_id:
            invalid.append(model_id)
    return invalid
