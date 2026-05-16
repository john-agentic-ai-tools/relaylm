import pytest

from relaylm.agents.detector import detect_agents, run_autoconfig
from relaylm.schemas.autoconfig import AutoconfigResult, CodingAgent


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


class TestDetectAgents:
    def test_returns_list_of_agents(self):
        agents = detect_agents()
        assert len(agents) == 2
        assert all(isinstance(a, CodingAgent) for a in agents)

    def test_opencode_agent_has_correct_name(self):
        agents = detect_agents()
        opencode = next(a for a in agents if a.name == "opencode")
        assert opencode.display_name == "OpenCode"

    def test_claude_code_agent_has_correct_name(self):
        agents = detect_agents()
        claude = next(a for a in agents if a.name == "claude-code")
        assert claude.display_name == "Claude Code"


class TestRunAutoconfig:
    def test_returns_autoconfig_result(self):
        result = run_autoconfig()
        assert isinstance(result, AutoconfigResult)

    def test_summary_mentions_supported_tools(self):
        result = run_autoconfig()
        assert "OpenCode" in result.summary or "Autoconfig complete" in result.summary

    def test_agents_or_no_agents(self):
        result = run_autoconfig()
        assert len(result.agents) == 2
        detected = [a for a in result.agents if a.detected]
        assert len(detected) in (0, 1, 2)
