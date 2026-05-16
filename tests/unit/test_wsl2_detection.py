import subprocess
from pathlib import Path

import pytest

from relaylm.agents import detector
from relaylm.agents.detector import (
    _detect_claude_code,
    _detect_opencode,
    _wsl2_windows_home,
)


@pytest.fixture
def linux_home(tmp_path, monkeypatch):
    linux_home = tmp_path / "home" / "ubuntu"
    linux_home.mkdir(parents=True)
    monkeypatch.setattr(detector.Path, "home", lambda: linux_home)
    monkeypatch.setattr(detector.shutil, "which", lambda _: None)
    monkeypatch.setattr(detector.sys, "platform", "linux")
    monkeypatch.setattr(detector, "_executable_version", lambda _: None)
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    return linux_home


def _make_subprocess_run(mapping):
    """Build a stub for subprocess.run that returns canned stdout per first-arg.

    mapping: dict keyed by argv[0] -> stdout string (or Exception to raise).
    """

    def stub(argv, **kwargs):
        key = argv[0]
        if key == "wslpath" and len(argv) >= 3:
            key = (argv[0], argv[2])
        result = mapping.get(key)
        if isinstance(result, BaseException):
            raise result
        if result is None:
            raise FileNotFoundError(argv[0])
        return subprocess.CompletedProcess(
            args=argv, returncode=0, stdout=result, stderr=""
        )

    return stub


class TestWsl2WindowsHome:
    def test_returns_none_when_not_wsl2(self, monkeypatch):
        monkeypatch.setattr(detector, "is_wsl2", lambda: False)
        assert _wsl2_windows_home() is None

    def test_uses_userprofile_env_when_set(self, tmp_path, monkeypatch):
        monkeypatch.setattr(detector, "is_wsl2", lambda: True)
        win_home_wsl = tmp_path / "mnt" / "c" / "Users" / "alice"
        win_home_wsl.mkdir(parents=True)
        monkeypatch.setenv("USERPROFILE", r"C:\Users\alice")
        monkeypatch.setattr(
            detector.subprocess,
            "run",
            _make_subprocess_run(
                {("wslpath", r"C:\Users\alice"): str(win_home_wsl) + "\n"}
            ),
        )
        assert _wsl2_windows_home() == win_home_wsl

    def test_falls_back_to_cmd_exe(self, tmp_path, monkeypatch):
        monkeypatch.setattr(detector, "is_wsl2", lambda: True)
        win_home_wsl = tmp_path / "mnt" / "c" / "Users" / "bob"
        win_home_wsl.mkdir(parents=True)
        monkeypatch.delenv("USERPROFILE", raising=False)
        monkeypatch.setattr(
            detector.subprocess,
            "run",
            _make_subprocess_run(
                {
                    "cmd.exe": "C:\\Users\\bob\n",
                    ("wslpath", "C:\\Users\\bob"): str(win_home_wsl) + "\n",
                }
            ),
        )
        assert _wsl2_windows_home() == win_home_wsl

    def test_returns_none_when_userprofile_path_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(detector, "is_wsl2", lambda: True)
        monkeypatch.setenv("USERPROFILE", r"C:\Users\ghost")
        monkeypatch.delenv("APPDATA", raising=False)
        ghost_path = tmp_path / "mnt" / "c" / "Users" / "ghost"  # never created
        monkeypatch.setattr(
            detector.subprocess,
            "run",
            _make_subprocess_run(
                {
                    ("wslpath", r"C:\Users\ghost"): str(ghost_path) + "\n",
                    "cmd.exe": "",
                }
            ),
        )
        assert _wsl2_windows_home() is None

    def test_returns_none_when_subprocess_fails(self, monkeypatch):
        monkeypatch.setattr(detector, "is_wsl2", lambda: True)
        monkeypatch.delenv("USERPROFILE", raising=False)
        monkeypatch.setattr(
            detector.subprocess,
            "run",
            _make_subprocess_run({"cmd.exe": FileNotFoundError("cmd.exe")}),
        )
        assert _wsl2_windows_home() is None


class TestOpencodeWsl2Detection:
    def test_detects_windows_host_opencode_on_wsl2(
        self, tmp_path, linux_home, monkeypatch
    ):
        win_home_wsl = tmp_path / "mnt" / "c" / "Users" / "alice"
        cfg = win_home_wsl / "AppData" / "Roaming" / "opencode" / "opencode.json"
        cfg.parent.mkdir(parents=True)
        cfg.write_text("{}")
        monkeypatch.setattr(detector, "_wsl2_windows_home", lambda: win_home_wsl)
        agent = _detect_opencode()
        assert agent.detected
        assert agent.detected_via == "wsl-windows-host"
        assert agent.install_path == str(cfg)

    def test_linux_install_preferred_over_windows_host(
        self, tmp_path, linux_home, monkeypatch
    ):
        linux_cfg = linux_home / ".config" / "opencode" / "opencode.json"
        linux_cfg.parent.mkdir(parents=True)
        linux_cfg.write_text("{}")
        win_home_wsl = tmp_path / "mnt" / "c" / "Users" / "alice"
        win_cfg = win_home_wsl / "AppData" / "Roaming" / "opencode" / "opencode.json"
        win_cfg.parent.mkdir(parents=True)
        win_cfg.write_text("{}")
        monkeypatch.setattr(detector, "_wsl2_windows_home", lambda: win_home_wsl)
        agent = _detect_opencode()
        assert agent.detected_via == "config"
        assert agent.install_path == str(linux_cfg)


class TestClaudeCodeWsl2Detection:
    def test_detects_windows_host_claude_on_wsl2(
        self, tmp_path, linux_home, monkeypatch
    ):
        win_home_wsl = tmp_path / "mnt" / "c" / "Users" / "alice"
        cfg = win_home_wsl / ".claude" / "settings.json"
        cfg.parent.mkdir(parents=True)
        cfg.write_text("{}")
        monkeypatch.setattr(detector, "_wsl2_windows_home", lambda: win_home_wsl)
        agent = _detect_claude_code()
        assert agent.detected
        assert agent.detected_via == "wsl-windows-host"
        assert agent.install_path == str(cfg)

    def test_linux_install_preferred_over_windows_host(
        self, tmp_path, linux_home, monkeypatch
    ):
        linux_cfg = linux_home / ".claude" / "settings.json"
        linux_cfg.parent.mkdir(parents=True)
        linux_cfg.write_text("{}")
        win_home_wsl = tmp_path / "mnt" / "c" / "Users" / "alice"
        win_cfg = win_home_wsl / ".claude" / "settings.json"
        win_cfg.parent.mkdir(parents=True)
        win_cfg.write_text("{}")
        monkeypatch.setattr(detector, "_wsl2_windows_home", lambda: win_home_wsl)
        agent = _detect_claude_code()
        assert agent.detected_via == "config"
        assert agent.install_path == str(linux_cfg)

    def test_no_windows_host_returns_not_detected(self, linux_home, monkeypatch):
        monkeypatch.setattr(detector, "_wsl2_windows_home", lambda: None)
        agent = _detect_claude_code()
        assert not agent.detected

    def test_detects_npm_shim_when_no_settings_file(
        self, tmp_path, linux_home, monkeypatch
    ):
        win_home_wsl = tmp_path / "mnt" / "c" / "Users" / "alice"
        shim = win_home_wsl / "AppData" / "Roaming" / "npm" / "claude.cmd"
        shim.parent.mkdir(parents=True)
        shim.write_text("@echo off\n")
        monkeypatch.setattr(detector, "_wsl2_windows_home", lambda: win_home_wsl)
        agent = _detect_claude_code()
        assert agent.detected
        assert agent.detected_via == "wsl-windows-host"
        assert agent.install_path == str(shim)


class TestOpencodeNpmShimDetection:
    def test_detects_npm_shim_when_no_config(
        self, tmp_path, linux_home, monkeypatch
    ):
        win_home_wsl = tmp_path / "mnt" / "c" / "Users" / "alice"
        shim = win_home_wsl / "AppData" / "Roaming" / "npm" / "opencode.cmd"
        shim.parent.mkdir(parents=True)
        shim.write_text("@echo off\n")
        monkeypatch.setattr(detector, "_wsl2_windows_home", lambda: win_home_wsl)
        agent = _detect_opencode()
        assert agent.detected
        assert agent.detected_via == "wsl-windows-host"
        assert agent.install_path == str(shim)

    def test_config_preferred_over_npm_shim(
        self, tmp_path, linux_home, monkeypatch
    ):
        win_home_wsl = tmp_path / "mnt" / "c" / "Users" / "alice"
        cfg = win_home_wsl / "AppData" / "Roaming" / "opencode" / "opencode.json"
        cfg.parent.mkdir(parents=True)
        cfg.write_text("{}")
        shim = win_home_wsl / "AppData" / "Roaming" / "npm" / "opencode.cmd"
        shim.parent.mkdir(parents=True)
        shim.write_text("@echo off\n")
        monkeypatch.setattr(detector, "_wsl2_windows_home", lambda: win_home_wsl)
        agent = _detect_opencode()
        assert agent.install_path == str(cfg)
