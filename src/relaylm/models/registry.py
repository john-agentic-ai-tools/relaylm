"""Curated catalog of vLLM-compatible models with real architecture
parameters, used to right-size GPU memory at setup time.

Each entry's numbers come from the model's HF `config.json`. To add a
new model, look up `hidden_size`, `num_hidden_layers`, and the
parameter count; FP16 is the assumed dtype unless the upstream model
ships in a different precision.
"""

from dataclasses import dataclass

# Per-element byte sizes for common dtypes (weights and KV cache assume
# the same dtype unless the model card says otherwise).
_BYTES_PER_PARAM: dict[str, float] = {
    "fp32": 4.0,
    "fp16": 2.0,
    "bf16": 2.0,
    "int8": 1.0,
    "int4": 0.5,
}

# vLLM's CUDA context + framework overhead (per-process, model-agnostic).
_CUDA_CONTEXT_GB = 0.5
# Empirical activation/scratch overhead during a profile pass.
_ACTIVATION_OVERHEAD_FRACTION = 0.15


@dataclass(frozen=True)
class ModelSpec:
    """Architectural numbers needed to right-size vLLM at startup."""

    name: str
    params_b: float
    hidden_size: int
    num_layers: int
    dtype: str = "fp16"
    min_ram_gb: float = 8.0

    @property
    def bytes_per_param(self) -> float:
        return _BYTES_PER_PARAM.get(self.dtype, 2.0)

    @property
    def weights_gb(self) -> float:
        return self.params_b * self.bytes_per_param

    @property
    def overhead_gb(self) -> float:
        return _CUDA_CONTEXT_GB + _ACTIVATION_OVERHEAD_FRACTION * self.weights_gb

    @property
    def kv_bytes_per_token(self) -> int:
        # Key + value, full precision of the KV elements (matches model dtype).
        return int(2 * self.hidden_size * self.num_layers * self.bytes_per_param)

    def min_runtime_gb(self, context_tokens: int = 2048) -> float:
        kv_gb = (self.kv_bytes_per_token * context_tokens) / 1e9
        return self.weights_gb + self.overhead_gb + kv_gb


# Curated registry. Numbers verified against published HF config.json
# files. Entries are ordered roughly by size for readability; selection
# logic sorts by params_b descending.
REGISTRY: tuple[ModelSpec, ...] = (
    ModelSpec(
        name="Qwen/Qwen3-0.6B",
        params_b=0.6,
        hidden_size=1024,
        num_layers=28,
        min_ram_gb=4.0,
    ),
    ModelSpec(
        name="Qwen/Qwen3-1.7B",
        params_b=1.7,
        hidden_size=2048,
        num_layers=28,
        min_ram_gb=6.0,
    ),
    ModelSpec(
        name="Qwen/Qwen3-4B",
        params_b=4.0,
        hidden_size=2560,
        num_layers=36,
        min_ram_gb=8.0,
    ),
    ModelSpec(
        name="Qwen/Qwen3-8B",
        params_b=8.2,
        hidden_size=4096,
        num_layers=36,
        min_ram_gb=16.0,
    ),
    ModelSpec(
        name="Qwen/Qwen3-14B",
        params_b=14.8,
        hidden_size=5120,
        num_layers=40,
        min_ram_gb=28.0,
    ),
    ModelSpec(
        name="mistralai/Mistral-7B-Instruct-v0.3",
        params_b=7.25,
        hidden_size=4096,
        num_layers=32,
        min_ram_gb=14.0,
    ),
    ModelSpec(
        name="meta-llama/Llama-3.2-1B-Instruct",
        params_b=1.24,
        hidden_size=2048,
        num_layers=16,
        min_ram_gb=4.0,
    ),
    ModelSpec(
        name="meta-llama/Llama-3.2-3B-Instruct",
        params_b=3.21,
        hidden_size=3072,
        num_layers=28,
        min_ram_gb=8.0,
    ),
    ModelSpec(
        name="google/gemma-3-1b-it",
        params_b=1.0,
        hidden_size=1152,
        num_layers=26,
        min_ram_gb=4.0,
    ),
    ModelSpec(
        name="google/gemma-3-4b-it",
        params_b=4.3,
        hidden_size=2560,
        num_layers=34,
        min_ram_gb=8.0,
    ),
)


def find(name: str) -> ModelSpec | None:
    """Return the registry entry whose `name` matches exactly."""
    for spec in REGISTRY:
        if spec.name == name:
            return spec
    return None


def heuristic_spec(name: str) -> ModelSpec:
    """Best-effort `ModelSpec` for a model not in the registry.

    Used when the user passes `--models <hf-id>` for an unknown model.
    Conservative defaults (assumes FP16, mid-range hidden/layer counts);
    `params_b` is estimated from a number embedded in the model name
    (e.g. "...-7B-..." → 7.0). Defaults to 1.0 if no hint is found.
    """
    params_b = _params_from_name(name)
    # Conservative hidden/layer guesses scale gently with size.
    if params_b < 2:
        hidden, layers = 2048, 24
    elif params_b < 5:
        hidden, layers = 3072, 28
    elif params_b < 10:
        hidden, layers = 4096, 32
    else:
        hidden, layers = 5120, 40
    return ModelSpec(
        name=name,
        params_b=params_b,
        hidden_size=hidden,
        num_layers=layers,
        dtype="fp16",
        min_ram_gb=max(4.0, params_b * 2),
    )


def _params_from_name(name: str) -> float:
    # Find a substring like "7B", "0.6B", "13B" — common across HF ids.
    import re

    m = re.search(r"(\d+(?:\.\d+)?)\s*[Bb]\b", name)
    if m:
        return float(m.group(1))
    return 1.0
