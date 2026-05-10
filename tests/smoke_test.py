"""Smoke test to verify the built package works before publishing."""


def test_cli_import() -> None:
    from relaylm.cli.app import app

    assert app is not None


def test_config_import() -> None:
    from relaylm.config.loader import load_config

    assert load_config is not None


def test_cli_help() -> None:
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "relaylm", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "setup" in result.stdout
    assert "providers" in result.stdout
    assert "agents" in result.stdout
    assert "config" in result.stdout
