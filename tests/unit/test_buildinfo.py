import subprocess

import pytest

from relaylm import _buildinfo


@pytest.fixture(autouse=True)
def _clear_git_cache():
    _buildinfo.git_info.cache_clear()
    yield
    _buildinfo.git_info.cache_clear()


def _stub_git(sha: str | None, dirty: bool, raises=None):
    def run(argv, **kw):
        if raises is not None:
            raise raises
        sub = argv[3]  # ["git", "-C", "<dir>", "<subcmd>", ...]
        if sub == "rev-parse":
            return subprocess.CompletedProcess(argv, 0, stdout=(sha or "") + "\n", stderr="")
        if sub == "status":
            return subprocess.CompletedProcess(
                argv, 0, stdout=" M foo.py\n" if dirty else "", stderr=""
            )
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    return run


class TestGitInfo:
    def test_returns_sha_and_dirty_flag(self, monkeypatch):
        monkeypatch.setattr(
            _buildinfo.subprocess, "run", _stub_git(sha="8c1699b", dirty=False)
        )
        assert _buildinfo.git_info() == ("8c1699b", False)

    def test_reports_dirty_when_status_nonempty(self, monkeypatch):
        monkeypatch.setattr(
            _buildinfo.subprocess, "run", _stub_git(sha="8c1699b", dirty=True)
        )
        assert _buildinfo.git_info() == ("8c1699b", True)

    def test_returns_none_when_git_missing(self, monkeypatch):
        monkeypatch.setattr(
            _buildinfo.subprocess,
            "run",
            _stub_git(sha=None, dirty=False, raises=FileNotFoundError("git")),
        )
        assert _buildinfo.git_info() is None

    def test_returns_none_when_not_a_git_repo(self, monkeypatch):
        monkeypatch.setattr(
            _buildinfo.subprocess,
            "run",
            _stub_git(
                sha=None,
                dirty=False,
                raises=subprocess.CalledProcessError(128, "git"),
            ),
        )
        assert _buildinfo.git_info() is None


class TestVersionString:
    def test_includes_sha_when_clean(self, monkeypatch):
        monkeypatch.setattr(_buildinfo, "package_version", lambda: "1.2.3")
        monkeypatch.setattr(_buildinfo, "git_info", lambda: ("abc1234", False))
        assert _buildinfo.version_string() == "relaylm v1.2.3 (abc1234)"

    def test_marks_dirty(self, monkeypatch):
        monkeypatch.setattr(_buildinfo, "package_version", lambda: "1.2.3")
        monkeypatch.setattr(_buildinfo, "git_info", lambda: ("abc1234", True))
        assert _buildinfo.version_string() == "relaylm v1.2.3 (abc1234+dirty)"

    def test_omits_suffix_when_not_in_repo(self, monkeypatch):
        monkeypatch.setattr(_buildinfo, "package_version", lambda: "1.2.3")
        monkeypatch.setattr(_buildinfo, "git_info", lambda: None)
        assert _buildinfo.version_string() == "relaylm v1.2.3"


class TestRuntimeInfo:
    def test_contains_required_keys(self, monkeypatch):
        monkeypatch.setattr(_buildinfo, "git_info", lambda: ("abc1234", False))
        info = _buildinfo.runtime_info()
        for key in ("version", "package", "python", "platform", "git"):
            assert key in info
        assert info["git"] == "abc1234 (clean)"

    def test_reports_no_git_when_outside_repo(self, monkeypatch):
        monkeypatch.setattr(_buildinfo, "git_info", lambda: None)
        info = _buildinfo.runtime_info()
        assert info["git"] == "not in a git working tree"
