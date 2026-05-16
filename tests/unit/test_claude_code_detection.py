import pytest

from relaylm.agents import detector
from relaylm.agents.detector import _detect_claude_code


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setattr(detector.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(detector.shutil, "which", lambda _: None)
    monkeypatch.setattr(detector, "is_wsl2", lambda: False)
    monkeypatch.setattr(detector, "_executable_version", lambda _: None)


class TestDetectClaudeCode:
    def test_detects_config(self, tmp_path):
        cfg = tmp_path / ".claude" / "settings.json"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text("{}")
        agent = _detect_claude_code()
        assert agent.detected
        assert agent.detected_via == "config"
        assert agent.install_path == str(cfg)

    def test_falls_back_to_path(self, monkeypatch):
        monkeypatch.setattr(
            detector.shutil, "which", lambda name: "/usr/local/bin/claude"
        )
        agent = _detect_claude_code()
        assert agent.detected
        assert agent.detected_via == "path"
        assert agent.install_path == "/usr/local/bin/claude"

    def test_not_detected_when_nothing_present(self):
        agent = _detect_claude_code()
        assert not agent.detected
        assert agent.install_path is None
        assert agent.detected_via is None

    def test_config_preferred_over_path(self, tmp_path, monkeypatch):
        cfg = tmp_path / ".claude" / "settings.json"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text("{}")
        monkeypatch.setattr(
            detector.shutil, "which", lambda name: "/usr/local/bin/claude"
        )
        agent = _detect_claude_code()
        assert agent.detected_via == "config"
        assert agent.install_path == str(cfg)
