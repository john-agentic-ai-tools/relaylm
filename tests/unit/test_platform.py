from unittest.mock import MagicMock

import pytest

from relaylm import platform


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    platform.is_wsl2.cache_clear()


def _fake_path(is_dir: bool = False, read_text: object = "") -> MagicMock:
    mock = MagicMock()
    mock.is_dir.return_value = is_dir
    if isinstance(read_text, BaseException) or (
        isinstance(read_text, type) and issubclass(read_text, BaseException)
    ):
        mock.read_text.side_effect = read_text
    else:
        mock.read_text.return_value = read_text
    return mock


class TestIsWsl2:
    def test_returns_true_when_run_wsl_dir_exists(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(platform, "_RUN_WSL", _fake_path(is_dir=True))
        assert platform.is_wsl2() is True

    def test_returns_true_when_interop_and_proc_version_mentions_microsoft(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("WSL_INTEROP", "/run/WSL/123_interop")
        monkeypatch.setattr(platform, "_RUN_WSL", _fake_path(is_dir=False))
        monkeypatch.setattr(
            platform,
            "_PROC_VERSION",
            _fake_path(read_text="Linux ... Microsoft ... WSL2"),
        )
        assert platform.is_wsl2() is True

    def test_returns_false_when_no_signals_present(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("WSL_INTEROP", raising=False)
        monkeypatch.setattr(platform, "_RUN_WSL", _fake_path(is_dir=False))
        monkeypatch.setattr(
            platform,
            "_PROC_VERSION",
            _fake_path(read_text="Linux version 6.5.0-generic"),
        )
        assert platform.is_wsl2() is False

    def test_returns_false_when_proc_version_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("WSL_INTEROP", "/run/WSL/123_interop")
        monkeypatch.setattr(platform, "_RUN_WSL", _fake_path(is_dir=False))
        monkeypatch.setattr(
            platform,
            "_PROC_VERSION",
            _fake_path(read_text=FileNotFoundError),
        )
        assert platform.is_wsl2() is False


class TestWslDistroName:
    def test_returns_env_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu-22.04")
        assert platform.wsl_distro_name() == "Ubuntu-22.04"

    def test_returns_none_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
        assert platform.wsl_distro_name() is None
