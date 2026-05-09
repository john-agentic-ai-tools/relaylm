from relaylm.hardware.detector import HardwareProfile
from relaylm.models.selector import select_models, validate_models


class TestSelectModels:
    def test_selects_small_models_for_low_ram(self) -> None:
        hp = HardwareProfile(ram_gb=2.0, cpu_cores=2)
        result = select_models(hp, max_models=2)
        assert len(result) <= 2
        for m in result:
            assert isinstance(m, dict)
            assert "name" in m

    def test_selects_larger_models_with_gpu(self) -> None:
        hp = HardwareProfile(
            ram_gb=64.0, cpu_cores=16, has_nvidia_gpu=True, gpu_vram_gb=[24.0]
        )
        result = select_models(hp)
        assert len(result) > 0
        names = [m["name"] for m in result]
        assert any("14B" in n or "13b" in n or "13B" in n or "8" in n for n in names)

    def test_selects_medium_models_with_moderate_ram(self) -> None:
        hp = HardwareProfile(ram_gb=16.0, cpu_cores=8)
        result = select_models(hp, max_models=1)
        assert len(result) == 1

    def test_respects_max_models(self) -> None:
        hp = HardwareProfile(ram_gb=128.0, cpu_cores=32)
        result = select_models(hp, max_models=3)
        assert len(result) <= 3

    def test_fallback_when_nothing_fits(self) -> None:
        hp = HardwareProfile(ram_gb=0.5, cpu_cores=1)
        result = select_models(hp)
        assert len(result) > 0

    def test_result_structure(self) -> None:
        hp = HardwareProfile(ram_gb=16.0, cpu_cores=8)
        result = select_models(hp, max_models=1)
        assert len(result) == 1
        m = result[0]
        assert "name" in m
        assert m["source"] == "huggingface"
        assert "gpu_index" in m
        assert "args" in m


class TestValidateModels:
    def test_valid_models_pass(self) -> None:
        invalid = validate_models(["Qwen/Qwen3-0.6B", "mistralai/Mistral-7B"])
        assert invalid == []

    def test_invalid_models_are_reported(self) -> None:
        invalid = validate_models(["not-a-model", "also-bad", "", "Qwen/Qwen3-0.6B"])
        assert "not-a-model" in invalid
        assert "also-bad" in invalid
        assert "" in invalid
        assert "Qwen/Qwen3-0.6B" not in invalid

    def test_empty_model_list(self) -> None:
        assert validate_models([]) == []
