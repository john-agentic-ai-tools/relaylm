"""Memory-aware model selection.

Picks the largest registry entry that fits in the detected free VRAM at
a usable minimum context, leaving a safety margin for measurement drift.
"""

from typing import Any

from relaylm.hardware.detector import HardwareProfile
from relaylm.models.registry import REGISTRY, ModelSpec, find, heuristic_spec

# Cover for short-term VRAM fluctuations between measurement and launch.
SAFETY_MARGIN = 0.90
# A model isn't useful as a chat/agent backend below this context length.
MIN_CONTEXT_TOKENS = 2048


def select_model(
    hardware: HardwareProfile,
    *,
    min_context: int = MIN_CONTEXT_TOKENS,
    safety_margin: float = SAFETY_MARGIN,
) -> ModelSpec | None:
    """Return the largest registry model that fits the hardware, or None."""
    free_vram_gb = hardware.max_gpu_vram_free_gb
    if free_vram_gb <= 0:
        return None

    budget_gb = free_vram_gb * safety_margin
    candidates = sorted(REGISTRY, key=lambda s: s.params_b, reverse=True)
    for spec in candidates:
        if spec.min_ram_gb > hardware.ram_gb:
            continue
        if spec.min_runtime_gb(min_context) <= budget_gb:
            return spec
    return None


def resolve_specs(model_ids: list[str]) -> list[ModelSpec]:
    """Resolve user-supplied HF ids to ModelSpec, falling back to heuristic."""
    out: list[ModelSpec] = []
    for raw in model_ids:
        name = raw.strip()
        if not name:
            continue
        match = find(name)
        out.append(match if match is not None else heuristic_spec(name))
    return out


def spec_to_config_entry(spec: ModelSpec) -> dict[str, Any]:
    """Render a ModelSpec for storage in `~/.config/relaylm/config.yml`."""
    return {
        "name": spec.name,
        "source": "huggingface",
        "gpu_index": None,
        "args": {},
    }


def validate_models(model_ids: list[str]) -> list[str]:
    invalid: list[str] = []
    for model_id in model_ids:
        model_id = model_id.strip()
        if not model_id or "/" not in model_id:
            invalid.append(model_id)
    return invalid
