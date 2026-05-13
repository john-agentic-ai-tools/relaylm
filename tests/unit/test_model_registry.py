from relaylm.models.registry import (
    REGISTRY,
    ModelSpec,
    find,
    heuristic_spec,
)


class TestModelSpecMath:
    def test_weights_gb_fp16(self) -> None:
        m = ModelSpec(
            name="x", params_b=7.0, hidden_size=4096, num_layers=32, dtype="fp16"
        )
        assert m.weights_gb == 14.0  # 7B * 2 bytes/param

    def test_weights_gb_int4(self) -> None:
        m = ModelSpec(
            name="x", params_b=7.0, hidden_size=4096, num_layers=32, dtype="int4"
        )
        assert m.weights_gb == 3.5

    def test_overhead_scales_with_weights(self) -> None:
        small = ModelSpec(name="s", params_b=0.6, hidden_size=1024, num_layers=24)
        big = ModelSpec(name="b", params_b=14.0, hidden_size=5120, num_layers=40)
        assert big.overhead_gb > small.overhead_gb
        # CUDA context floor.
        assert small.overhead_gb >= 0.5

    def test_kv_bytes_per_token_scales_with_arch(self) -> None:
        small = ModelSpec(name="s", params_b=0.6, hidden_size=1024, num_layers=24)
        big = ModelSpec(name="b", params_b=7.0, hidden_size=4096, num_layers=32)
        # Bigger hidden + more layers = larger KV per token.
        assert big.kv_bytes_per_token > small.kv_bytes_per_token
        # 2 (K+V) * 1024 * 24 * 2 (fp16) = 98304 bytes for the small model.
        assert small.kv_bytes_per_token == 2 * 1024 * 24 * 2

    def test_min_runtime_grows_with_context(self) -> None:
        m = ModelSpec(name="x", params_b=0.6, hidden_size=1024, num_layers=24)
        assert m.min_runtime_gb(2048) < m.min_runtime_gb(8192)

    def test_small_model_min_runtime_fits_8gb(self) -> None:
        m = ModelSpec(name="x", params_b=0.6, hidden_size=1024, num_layers=24)
        # Sanity: at 2048 ctx the 0.6B model should fit in ~3 GB.
        assert m.min_runtime_gb(2048) < 3.5


class TestRegistryEntries:
    def test_registry_is_non_empty(self) -> None:
        assert len(REGISTRY) >= 5

    def test_all_entries_have_realistic_numbers(self) -> None:
        for m in REGISTRY:
            assert m.params_b > 0
            assert m.hidden_size > 0
            assert m.num_layers > 0
            assert m.dtype in {"fp16", "bf16", "int8", "int4", "fp32"}
            assert m.min_ram_gb > 0


class TestFind:
    def test_returns_entry_when_known(self) -> None:
        m = find("Qwen/Qwen3-0.6B")
        assert m is not None
        assert m.params_b == 0.6

    def test_returns_none_when_unknown(self) -> None:
        assert find("nobody/UnknownModel") is None


class TestHeuristicSpec:
    def test_extracts_params_from_7b_suffix(self) -> None:
        m = heuristic_spec("someone/Foo-7B-Chat")
        assert m.params_b == 7.0

    def test_extracts_decimal_params(self) -> None:
        m = heuristic_spec("someone/Foo-0.6B")
        assert m.params_b == 0.6

    def test_defaults_when_no_size_in_name(self) -> None:
        m = heuristic_spec("someone/NoSizeHint")
        assert m.params_b == 1.0

    def test_dtype_defaults_to_fp16(self) -> None:
        m = heuristic_spec("someone/Foo-7B")
        assert m.dtype == "fp16"
