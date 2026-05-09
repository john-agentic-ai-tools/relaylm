import json
from pathlib import Path

from relaylm.agents.detector import (
    _configure_claude_code,
    _configure_opencode,
    _detect_claude_code,
    _detect_opencode,
    detect_and_configure_agents,
)


class TestDetectClaudeCode:
    def test_returns_path_or_none(self) -> None:
        result = _detect_claude_code()
        assert result is None or result.name == "settings.json"


class TestDetectOpenCode:
    def test_no_opencode_config_returns_none(self) -> None:
        assert _detect_opencode() is None


class TestConfigureClaudeCode:
    def test_sets_api_provider_and_url(self, tmp_path: Path) -> None:
        config_path = tmp_path / "settings.json"
        config_path.write_text(json.dumps({"model": "claude-sonnet-4-20250514"}))
        _configure_claude_code(config_path, "http://localhost:8000/v1", dry_run=False)
        content = json.loads(config_path.read_text())
        assert content["apiProvider"] == "anthropic"
        assert content["customApiUrl"] == "http://localhost:8000/v1"

    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        config_path = tmp_path / "settings.json"
        original = json.dumps({"model": "claude-sonnet-4-20250514"})
        config_path.write_text(original)
        _configure_claude_code(config_path, "http://localhost:8000/v1", dry_run=True)
        assert config_path.read_text() == original

    def test_creates_content_if_file_missing(self, tmp_path: Path) -> None:
        config_path = tmp_path / "nonexistent.json"
        _configure_claude_code(config_path, "http://localhost:8000/v1", dry_run=False)
        content = json.loads(config_path.read_text())
        assert content["apiProvider"] == "anthropic"

    def test_handles_invalid_json(self, tmp_path: Path) -> None:
        config_path = tmp_path / "bad.json"
        config_path.write_text("not json")
        _configure_claude_code(config_path, "http://localhost:8000/v1", dry_run=False)
        content = json.loads(config_path.read_text())
        assert content["apiProvider"] == "anthropic"


class TestConfigureOpenCode:
    def test_sets_model_endpoint(self, tmp_path: Path) -> None:
        config_path = tmp_path / "opencode.json"
        config_path.write_text(json.dumps({}))
        _configure_opencode(config_path, "http://localhost:8000/v1", dry_run=False)
        content = json.loads(config_path.read_text())
        assert content["model"] == "http://localhost:8000/v1/chat/completions"

    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        config_path = tmp_path / "opencode.json"
        original = json.dumps({"model": "old-model"})
        config_path.write_text(original)
        _configure_opencode(config_path, "http://localhost:8000/v1", dry_run=True)
        assert config_path.read_text() == original

    def test_handles_invalid_json(self, tmp_path: Path) -> None:
        config_path = tmp_path / "bad.json"
        config_path.write_text("not json")
        _configure_opencode(config_path, "http://localhost:8000/v1", dry_run=False)
        content = json.loads(config_path.read_text())
        assert "chat/completions" in content["model"]

    def test_strips_trailing_slash(self, tmp_path: Path) -> None:
        config_path = tmp_path / "opencode.json"
        config_path.write_text(json.dumps({}))
        _configure_opencode(config_path, "http://localhost:8000/v1/", dry_run=False)
        content = json.loads(config_path.read_text())
        assert "//v1/chat" not in content["model"]


class TestDetectAndConfigureAgents:
    def test_returns_results_when_no_agents_found(self) -> None:
        results = detect_and_configure_agents("http://localhost:8000/v1", dry_run=True)
        assert len(results) >= 2
        agent_names = [r["agent"] for r in results]
        assert "claude-code" in agent_names
        assert "opencode" in agent_names
