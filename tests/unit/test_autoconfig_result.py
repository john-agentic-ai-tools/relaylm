from relaylm.schemas.autoconfig import (
    AutoconfigResult,
    CodingAgent,
    ConfigBackup,
    ConfigChange,
    RevertResult,
)


class TestAutoconfigResult:
    def test_default_summary_is_empty_string(self):
        result = AutoconfigResult(agents=[])
        assert result.summary == ""

    def test_with_detected_agents(self):
        agents = [
            CodingAgent(name="opencode", display_name="OpenCode", detected=True),
        ]
        result = AutoconfigResult(agents=agents)
        assert len(result.agents) == 1

    def test_with_backup(self):
        result = AutoconfigResult(
            agents=[],
            backup=ConfigBackup(
                file_path="/tmp/backup.yml",
                timestamp="20260515T120000",
                reason="autoconfig-pre-write",
            ),
        )
        assert result.backup is not None
        assert result.backup.reason == "autoconfig-pre-write"


class TestConfigChange:
    def test_fields(self):
        change = ConfigChange(
            path="agents.opencode", operation="added", value={"key": "val"}
        )
        assert change.path == "agents.opencode"
        assert change.operation == "added"


class TestCodingAgent:
    def test_detected_defaults(self):
        agent = CodingAgent(name="test", display_name="Test", detected=True)
        assert agent.version is None
        assert agent.install_path is None
        assert agent.detected_via is None

    def test_not_detected(self):
        agent = CodingAgent(name="test", display_name="Test", detected=False)
        assert not agent.detected


class TestRevertResult:
    def test_success(self):
        result = RevertResult(success=True, message="Restored")
        assert result.success
        assert result.message == "Restored"

    def test_failure(self):
        result = RevertResult(success=False, message="No backup found")
        assert not result.success
