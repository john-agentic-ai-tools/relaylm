from pathlib import Path

import pytest

from relaylm.config import backup as backup_mod
from relaylm.config import loader as loader_mod
from relaylm.config.backup import create_backup, list_backups, restore_backup


@pytest.fixture(autouse=True)
def isolated_config_dir(tmp_path, monkeypatch):
    config_dir = tmp_path / ".config" / "relaylm"
    config_path = config_dir / "config.yml"
    backup_dir = config_dir / "backups"
    monkeypatch.setattr(loader_mod, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(loader_mod, "CONFIG_PATH", config_path)
    monkeypatch.setattr(backup_mod, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(backup_mod, "CONFIG_PATH", config_path)
    monkeypatch.setattr(backup_mod, "BACKUP_DIR", backup_dir)


def _write_config(content: str = "version: 1\n") -> Path:
    loader_mod.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    loader_mod.CONFIG_PATH.write_text(content)
    return loader_mod.CONFIG_PATH


class TestCreateBackup:
    def test_returns_none_when_no_config(self) -> None:
        assert create_backup() is None

    def test_creates_file_when_config_exists(self) -> None:
        _write_config()
        result = create_backup()
        assert result is not None
        assert result.exists()
        assert result.suffix == ".yml"
        assert result.name.startswith("config-")

    def test_collision_suffix_when_same_second(self, monkeypatch) -> None:
        _write_config()
        from relaylm.config.backup import datetime as backup_datetime

        class _FixedNow:
            @staticmethod
            def now():
                return backup_datetime.now().replace(
                    year=2026, month=5, day=15, hour=12, minute=0, second=0
                )

        monkeypatch.setattr(backup_mod, "datetime", _FixedNow)

        first = create_backup()
        second = create_backup()
        third = create_backup()
        assert first is not None and second is not None and third is not None
        assert first.name == "config-20260515T120000.yml"
        assert second.name == "config-20260515T120000_001.yml"
        assert third.name == "config-20260515T120000_002.yml"
        assert first.exists() and second.exists() and third.exists()


class TestListBackups:
    def test_returns_empty_list_when_no_backups(self) -> None:
        assert list_backups() == []

    def test_returns_list_after_create(self) -> None:
        _write_config()
        create_backup()
        backups = list_backups()
        assert len(backups) == 1
        assert "timestamp" in backups[0]
        assert "path" in backups[0]


class TestRestoreBackup:
    def test_returns_none_for_missing(self) -> None:
        assert restore_backup("nonexistent") is None

    def test_restores_content(self) -> None:
        config_path = _write_config("version: 1\nmodels: []\n")
        backup_path = create_backup()
        assert backup_path is not None

        config_path.write_text("version: 2\nmodels: [test]\n")
        timestamp = backup_path.stem.replace("config-", "")
        restored = restore_backup(timestamp)
        assert restored is not None
        assert "version: 1" in config_path.read_text()

    def test_round_trips_collision_suffixed_timestamp(self, monkeypatch) -> None:
        config_path = _write_config("version: 1\n")
        from relaylm.config.backup import datetime as backup_datetime

        class _FixedNow:
            @staticmethod
            def now():
                return backup_datetime.now().replace(
                    year=2026, month=5, day=15, hour=12, minute=0, second=0
                )

        monkeypatch.setattr(backup_mod, "datetime", _FixedNow)

        create_backup()
        second = create_backup()
        assert second is not None and second.name.endswith("_001.yml")

        config_path.write_text("version: 99\n")
        listed = list_backups()
        timestamps = [b["timestamp"] for b in listed]
        assert "20260515T120000_001" in timestamps

        restored = restore_backup("20260515T120000_001")
        assert restored is not None
        assert config_path.read_text() == "version: 1\n"
