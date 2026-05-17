from pathlib import Path

import pytest

from relaylm.agents import detector
from relaylm.agents.detector import _detect_opencode, _opencode_config_candidates


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(detector.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(detector.shutil, "which", lambda _: None)
    monkeypatch.setattr(detector, "is_wsl2", lambda: False)
    monkeypatch.setattr(detector, "_executable_version", lambda _: None)
    monkeypatch.setattr(detector, "_windows_native_version", lambda _: None)


class TestOpencodeConfigCandidates:
    def test_linux_uses_xdg_default(self, tmp_path, monkeypatch):
        monkeypatch.setattr(detector.sys, "platform", "linux")
        candidates = _opencode_config_candidates()
        assert candidates == [tmp_path / ".config" / "opencode" / "opencode.json"]

    def test_linux_respects_xdg_config_home(self, tmp_path, monkeypatch):
        monkeypatch.setattr(detector.sys, "platform", "linux")
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "custom"))
        candidates = _opencode_config_candidates()
        assert candidates == [tmp_path / "custom" / "opencode" / "opencode.json"]

    def test_macos_prefers_application_support_then_xdg(self, tmp_path, monkeypatch):
        monkeypatch.setattr(detector.sys, "platform", "darwin")
        candidates = _opencode_config_candidates()
        assert candidates == [
            tmp_path / "Library" / "Application Support" / "opencode" / "opencode.json",
            tmp_path / ".config" / "opencode" / "opencode.json",
        ]

    def test_windows_uses_appdata(self, tmp_path, monkeypatch):
        monkeypatch.setattr(detector.sys, "platform", "win32")
        monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
        candidates = _opencode_config_candidates()
        assert candidates == [tmp_path / "Roaming" / "opencode" / "opencode.json"]

    def test_windows_falls_back_to_home_appdata_roaming(self, tmp_path, monkeypatch):
        monkeypatch.setattr(detector.sys, "platform", "win32")
        candidates = _opencode_config_candidates()
        assert candidates == [
            tmp_path / "AppData" / "Roaming" / "opencode" / "opencode.json"
        ]


class TestDetectOpencode:
    def _write_config(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}")

    def test_detects_config_on_linux(self, tmp_path, monkeypatch):
        monkeypatch.setattr(detector.sys, "platform", "linux")
        cfg = tmp_path / ".config" / "opencode" / "opencode.json"
        self._write_config(cfg)
        agent = _detect_opencode()
        assert agent.detected
        assert agent.detected_via == "config"
        assert agent.install_path == str(cfg)

    def test_detects_config_on_macos(self, tmp_path, monkeypatch):
        monkeypatch.setattr(detector.sys, "platform", "darwin")
        cfg = (
            tmp_path / "Library" / "Application Support" / "opencode" / "opencode.json"
        )
        self._write_config(cfg)
        agent = _detect_opencode()
        assert agent.detected
        assert agent.detected_via == "config"
        assert agent.install_path == str(cfg)

    def test_detects_config_on_windows(self, tmp_path, monkeypatch):
        monkeypatch.setattr(detector.sys, "platform", "win32")
        monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
        cfg = tmp_path / "Roaming" / "opencode" / "opencode.json"
        self._write_config(cfg)
        agent = _detect_opencode()
        assert agent.detected
        assert agent.detected_via == "config"
        assert agent.install_path == str(cfg)

    def test_falls_back_to_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr(detector.sys, "platform", "linux")
        monkeypatch.setattr(
            detector.shutil, "which", lambda name: "/usr/bin/opencode"
        )
        agent = _detect_opencode()
        assert agent.detected
        assert agent.detected_via == "path"
        assert agent.install_path == "/usr/bin/opencode"

    def test_not_detected_when_nothing_present(self, tmp_path, monkeypatch):
        monkeypatch.setattr(detector.sys, "platform", "linux")
        agent = _detect_opencode()
        assert not agent.detected
        assert agent.install_path is None
        assert agent.detected_via is None
