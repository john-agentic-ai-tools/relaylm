import pytest
from typer.testing import CliRunner

from relaylm.cli.app import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    config_dir = tmp_path / ".config" / "relaylm"
    config_path = config_dir / "config.yml"
    backup_dir = config_dir / "backups"
    monkeypatch.setattr("relaylm.config.loader.CONFIG_DIR", config_dir)
    monkeypatch.setattr("relaylm.config.loader.CONFIG_PATH", config_path)
    monkeypatch.setattr("relaylm.config.backup.CONFIG_DIR", config_dir)
    monkeypatch.setattr("relaylm.config.backup.CONFIG_PATH", config_path)
    monkeypatch.setattr("relaylm.config.backup.BACKUP_DIR", backup_dir)
    monkeypatch.setattr("relaylm.agents.detector.Path.home", lambda: tmp_path)
    monkeypatch.setattr("relaylm.agents.detector.shutil.which", lambda _: None)
    monkeypatch.setattr("relaylm.agents.detector.is_wsl2", lambda: False)
    monkeypatch.setattr(
        "relaylm.agents.detector._executable_version", lambda _: None
    )
    monkeypatch.setattr(
        "relaylm.agents.detector._windows_native_version", lambda _: None
    )


class TestAutoconfigCli:
    def test_autoconfig_help(self):
        result = runner.invoke(app, ["autoconfig", "--help"])
        assert result.exit_code == 0
        assert "autoconfig" in result.stdout.lower()

    def test_autoconfig_dry_run(self):
        result = runner.invoke(app, ["autoconfig", "--dry-run"])
        assert result.exit_code == 0

    def test_autoconfig_no_agents_message(self):
        result = runner.invoke(app, ["autoconfig"])
        assert result.exit_code == 0

    def test_autoconfig_mentions_supported_tools(self):
        result = runner.invoke(app, ["autoconfig"])
        assert result.exit_code == 0
        assert "OpenCode" in result.stdout
        assert "Claude Code" in result.stdout

    def test_autoconfig_revert_help(self):
        result = runner.invoke(app, ["autoconfig", "revert", "--help"])
        assert result.exit_code == 0
        assert "revert" in result.stdout.lower()

    def test_autoconfig_revert_runs(self):
        result = runner.invoke(app, ["autoconfig", "revert"])
        assert result.exit_code in (0, 1)
        assert "backup" in result.stdout.lower() or "backup" in result.stderr.lower()


class TestVersion:
    def test_version_long_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "relaylm v" in result.stdout

    def test_version_short_flag(self):
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert "relaylm v" in result.stdout

    def test_version_contains_semver(self):
        result = runner.invoke(app, ["--version"])
        version_part = result.stdout.strip().replace("relaylm v", "").split()[0]
        parts = version_part.split(".")
        assert len(parts) >= 2
        assert all(p.isdigit() for p in parts[:2])


class TestInfo:
    def test_info_prints_required_fields(self):
        result = runner.invoke(app, ["info"])
        assert result.exit_code == 0
        for label in ("version", "package", "python", "platform", "git"):
            assert label in result.stdout
