import subprocess

import pytest

from relaylm.agents import detector
from relaylm.agents.detector import _agent_version, _executable_version


@pytest.fixture(autouse=True)
def _clear_version_cache():
    _executable_version.cache_clear()
    detector._windows_native_version.cache_clear()
    yield
    _executable_version.cache_clear()
    detector._windows_native_version.cache_clear()


def _stub_subprocess(stdout: str = "", stderr: str = "", raises=None):
    def run(argv, **kw):
        if raises is not None:
            raise raises
        return subprocess.CompletedProcess(
            args=argv, returncode=0, stdout=stdout, stderr=stderr
        )

    return run


class TestVersionInvocation:
    def test_plain_argv_on_non_wsl2(self, monkeypatch):
        monkeypatch.setattr(detector, "is_wsl2", lambda: False)
        argv = detector._version_invocation("/usr/bin/claude")
        assert argv == ["/usr/bin/claude", "--version"]

    def test_plain_argv_for_exe_on_wsl2(self, monkeypatch):
        monkeypatch.setattr(detector, "is_wsl2", lambda: True)
        argv = detector._version_invocation("/mnt/c/Windows/System32/where.exe")
        assert argv == ["/mnt/c/Windows/System32/where.exe", "--version"]

    def test_wraps_cmd_through_cmd_exe_on_wsl2(self, monkeypatch):
        monkeypatch.setattr(detector, "is_wsl2", lambda: True)
        monkeypatch.setattr(
            detector,
            "_wslpath_to_windows",
            lambda p: r"C:\Users\Admin\AppData\Roaming\npm\opencode.cmd",
        )
        argv = detector._version_invocation(
            "/mnt/c/Users/Admin/AppData/Roaming/npm/opencode.cmd"
        )
        assert argv == [
            "cmd.exe",
            "/c",
            r"C:\Users\Admin\AppData\Roaming\npm\opencode.cmd",
            "--version",
        ]

    def test_returns_none_when_wslpath_fails(self, monkeypatch):
        monkeypatch.setattr(detector, "is_wsl2", lambda: True)
        monkeypatch.setattr(detector, "_wslpath_to_windows", lambda _: None)
        argv = detector._version_invocation("/mnt/c/foo/opencode.cmd")
        assert argv is None


class TestExecutableVersion:
    def test_parses_plain_semver(self, monkeypatch):
        monkeypatch.setattr(
            detector.subprocess, "run", _stub_subprocess(stdout="1.2.3\n")
        )
        assert _executable_version("/usr/bin/claude") == "1.2.3"

    def test_parses_prefixed_output(self, monkeypatch):
        monkeypatch.setattr(
            detector.subprocess,
            "run",
            _stub_subprocess(stdout="claude-code v0.5.12 (build abc)\n"),
        )
        assert _executable_version("/usr/bin/claude") == "0.5.12"

    def test_parses_prerelease_suffix(self, monkeypatch):
        monkeypatch.setattr(
            detector.subprocess,
            "run",
            _stub_subprocess(stdout="opencode 1.0.0-beta.3\n"),
        )
        assert _executable_version("/usr/bin/opencode") == "1.0.0-beta.3"

    def test_falls_back_to_stderr(self, monkeypatch):
        monkeypatch.setattr(
            detector.subprocess,
            "run",
            _stub_subprocess(stdout="", stderr="version 2.0\n"),
        )
        assert _executable_version("/usr/bin/x") == "2.0"

    def test_returns_none_when_no_version_token(self, monkeypatch):
        monkeypatch.setattr(
            detector.subprocess, "run", _stub_subprocess(stdout="no version here\n")
        )
        assert _executable_version("/usr/bin/x") is None

    def test_returns_none_on_subprocess_failure(self, monkeypatch):
        monkeypatch.setattr(
            detector.subprocess,
            "run",
            _stub_subprocess(raises=FileNotFoundError("missing")),
        )
        assert _executable_version("/usr/bin/missing") is None

    def test_returns_none_on_timeout(self, monkeypatch):
        monkeypatch.setattr(
            detector.subprocess,
            "run",
            _stub_subprocess(raises=subprocess.TimeoutExpired("x", 3)),
        )
        assert _executable_version("/usr/bin/slow") is None

    def test_results_are_cached(self, monkeypatch):
        calls = []

        def counting_run(argv, **kw):
            calls.append(argv[0])
            return subprocess.CompletedProcess(argv, 0, stdout="1.0.0", stderr="")

        monkeypatch.setattr(detector.subprocess, "run", counting_run)
        _executable_version("/usr/bin/cached") == "1.0.0"
        _executable_version("/usr/bin/cached") == "1.0.0"
        assert calls == ["/usr/bin/cached"]


class TestAgentVersion:
    def test_invokes_install_path_when_executable_suffix(self, tmp_path, monkeypatch):
        shim = tmp_path / "claude.cmd"
        shim.write_text("@echo off\n")
        called_with = []

        def fake_exec(path: str) -> str | None:
            called_with.append(path)
            return "1.2.3"

        monkeypatch.setattr(detector, "_executable_version", fake_exec)
        monkeypatch.setattr(detector.shutil, "which", lambda _: None)
        monkeypatch.setattr(detector, "_wsl2_windows_home", lambda: None)
        assert _agent_version("claude", str(shim)) == "1.2.3"
        assert called_with == [str(shim)]

    def test_skips_install_path_for_config_files(self, tmp_path, monkeypatch):
        cfg = tmp_path / "settings.json"
        cfg.write_text("{}")
        called_with = []

        def fake_exec(path: str) -> str | None:
            called_with.append(path)
            return "9.9.9" if path == "/usr/bin/claude" else None

        monkeypatch.setattr(detector, "_executable_version", fake_exec)
        monkeypatch.setattr(detector.shutil, "which", lambda _: "/usr/bin/claude")
        monkeypatch.setattr(detector, "_wsl2_windows_home", lambda: None)
        assert _agent_version("claude", str(cfg)) == "9.9.9"
        assert str(cfg) not in called_with

    def test_falls_back_to_wsl2_windows_npm(self, tmp_path, monkeypatch):
        win_home = tmp_path / "mnt" / "c" / "Users" / "alice"
        shim = win_home / "AppData" / "Roaming" / "npm" / "opencode.cmd"
        shim.parent.mkdir(parents=True)
        shim.write_text("@echo off\n")
        monkeypatch.setattr(
            detector,
            "_executable_version",
            lambda p: "0.7.1" if p == str(shim) else None,
        )
        monkeypatch.setattr(detector.shutil, "which", lambda _: None)
        monkeypatch.setattr(detector, "_wsl2_windows_home", lambda: win_home)
        assert _agent_version("opencode", None) == "0.7.1"

    def test_returns_none_when_nothing_resolves(self, monkeypatch):
        monkeypatch.setattr(detector, "_executable_version", lambda _: None)
        monkeypatch.setattr(detector, "_windows_native_version", lambda _: None)
        monkeypatch.setattr(detector.shutil, "which", lambda _: None)
        monkeypatch.setattr(detector, "_wsl2_windows_home", lambda: None)
        assert _agent_version("claude", None) is None

    def test_falls_back_to_windows_native_when_npm_globals_empty(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(detector, "_executable_version", lambda _: None)
        monkeypatch.setattr(detector.shutil, "which", lambda _: None)
        win_home = tmp_path / "mnt" / "c" / "Users" / "alice"
        win_home.mkdir(parents=True)
        monkeypatch.setattr(detector, "_wsl2_windows_home", lambda: win_home)
        monkeypatch.setattr(
            detector,
            "_windows_native_version",
            lambda name: "2.1.142" if name == "claude" else None,
        )
        assert _agent_version("claude", None) == "2.1.142"


class TestWindowsNativeVersion:
    def test_returns_none_on_non_wsl2(self, monkeypatch):
        monkeypatch.setattr(detector, "is_wsl2", lambda: False)
        assert detector._windows_native_version("claude") is None

    def test_parses_version_from_cmd_exe(self, monkeypatch):
        monkeypatch.setattr(detector, "is_wsl2", lambda: True)
        monkeypatch.setattr(
            detector.subprocess,
            "run",
            _stub_subprocess(stdout="Claude Code 2.1.142\n"),
        )
        assert detector._windows_native_version("claude") == "2.1.142"

    def test_returns_none_on_subprocess_failure(self, monkeypatch):
        monkeypatch.setattr(detector, "is_wsl2", lambda: True)
        monkeypatch.setattr(
            detector.subprocess,
            "run",
            _stub_subprocess(raises=FileNotFoundError("cmd.exe")),
        )
        assert detector._windows_native_version("claude") is None

    def test_returns_none_when_no_version_token(self, monkeypatch):
        monkeypatch.setattr(detector, "is_wsl2", lambda: True)
        monkeypatch.setattr(
            detector.subprocess,
            "run",
            _stub_subprocess(stdout="'claude' is not recognized\n"),
        )
        assert detector._windows_native_version("claude") is None
