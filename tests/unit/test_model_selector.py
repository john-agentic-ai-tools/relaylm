from relaylm.hardware.detector import HardwareProfile
from relaylm.models.registry import REGISTRY, ModelSpec
from relaylm.models.selector import (
    resolve_specs,
    select_model,
    validate_models,
)


def _hardware(
    *, free_vram: float, total_vram: float, ram: float = 32.0
) -> HardwareProfile:
    return HardwareProfile(
        ram_gb=ram,
        cpu_cores=8,
        has_nvidia_gpu=True,
        gpu_vram_gb=[total_vram],
        gpu_vram_free_gb=[free_vram],
    )


class TestSelectModel:
    def test_picks_largest_fitting_model_on_24gb_card(self) -> None:
        hp = _hardware(free_vram=22.0, total_vram=24.0, ram=64.0)
        chosen = select_model(hp)
        assert chosen is not None
        # Should pick something in the 7-14B range, not a 0.6B.
        assert chosen.params_b >= 4.0

    def test_picks_small_model_on_8gb_card_with_6gb_free(self) -> None:
        hp = _hardware(free_vram=6.7, total_vram=8.0)
        chosen = select_model(hp)
        assert chosen is not None
        # 14B and 7B don't fit in 6.7 * 0.9 = 6 GB budget.
        assert chosen.params_b < 5.0

    def test_returns_none_when_no_gpu(self) -> None:
        hp = HardwareProfile(ram_gb=16.0, cpu_cores=8)
        assert select_model(hp) is None

    def test_returns_none_when_vram_too_tight(self) -> None:
        hp = _hardware(free_vram=1.0, total_vram=2.0, ram=8.0)
        # Even Qwen3-0.6B needs ~2 GB runtime; 1.0 * 0.9 = 0.9 budget.
        assert select_model(hp) is None

    def test_skips_models_violating_ram_minimum(self) -> None:
        # Plenty of VRAM but tiny RAM → only small-RAM models qualify.
        hp = _hardware(free_vram=24.0, total_vram=24.0, ram=4.0)
        chosen = select_model(hp)
        assert chosen is not None
        assert chosen.min_ram_gb <= 4.0


class TestResolveSpecs:
    def test_resolves_known_name_from_registry(self) -> None:
        out = resolve_specs(["Qwen/Qwen3-0.6B"])
        assert len(out) == 1
        # Same identity as the registry entry.
        assert out[0] in REGISTRY

    def test_falls_back_to_heuristic_for_unknown_name(self) -> None:
        out = resolve_specs(["someone/UnknownModel-7B"])
        assert len(out) == 1
        spec = out[0]
        assert isinstance(spec, ModelSpec)
        assert spec.params_b == 7.0  # parsed from "7B"

    def test_skips_empty_entries(self) -> None:
        out = resolve_specs(["", "  ", "Qwen/Qwen3-0.6B"])
        assert len(out) == 1
        assert out[0].name == "Qwen/Qwen3-0.6B"


class TestValidateModels:
    def test_valid_models_pass(self) -> None:
        assert validate_models(["Qwen/Qwen3-0.6B", "mistralai/Mistral-7B"]) == []

    def test_invalid_models_are_reported(self) -> None:
        invalid = validate_models(["not-a-model", "also-bad", "", "Qwen/Qwen3-0.6B"])
        assert "not-a-model" in invalid
        assert "also-bad" in invalid
        assert "" in invalid
        assert "Qwen/Qwen3-0.6B" not in invalid

    def test_empty_model_list(self) -> None:
        assert validate_models([]) == []
