from relaylm.config.loader import CONFIG_DIR, load_config, save_config, validate_config


class TestSaveAndLoadConfig:
    def test_round_trip(self) -> None:
        config = {"version": 1, "container_runtime": "podman", "models": []}
        save_config(config)
        loaded = load_config()
        assert loaded == config

    def test_load_returns_dict(self) -> None:
        result = load_config()
        assert isinstance(result, dict)

    def test_save_creates_directory(self) -> None:
        config = {"version": 1}
        save_config(config)
        assert CONFIG_DIR.exists()


class TestValidateConfig:
    def test_valid_config(self) -> None:
        config = {
            "version": 1,
            "container_runtime": "podman",
            "models": [{"name": "Qwen/Qwen3-0.6B"}],
            "fallback": {"order": ["local"]},
        }
        assert validate_config(config) == []

    def test_missing_version(self) -> None:
        errors = validate_config({"container_runtime": "podman"})
        assert "Missing required field: version" in errors

    def test_invalid_runtime(self) -> None:
        errors = validate_config({"version": 1, "container_runtime": "containerd"})
        assert any("container_runtime" in e for e in errors)

    def test_model_without_name(self) -> None:
        config = {"version": 1, "models": [{"source": "huggingface"}]}
        errors = validate_config(config)
        assert any("name is required" in e for e in errors)

    def test_invalid_fallback(self) -> None:
        config = {"version": 1, "fallback": {"order": ["nonexistent"]}}
        errors = validate_config(config)
        assert any("fallback.order" in e for e in errors)
