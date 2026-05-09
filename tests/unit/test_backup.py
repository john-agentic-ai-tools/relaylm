from pathlib import Path

from relaylm.config.backup import (
    BACKUP_DIR,
    create_backup,
    list_backups,
    restore_backup,
)


class TestBackup:
    def test_create_backup_returns_path(self) -> None:
        result = create_backup()
        assert result is None or result.exists()

    def test_create_backup_creates_file(self, tmp_path: Path) -> None:
        config_path = BACKUP_DIR.parent / "config.yml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("version: 1\n")
        result = create_backup()
        assert result is not None
        assert result.exists()
        assert result.suffix == ".yml"
        assert "config-" in result.name

    def test_list_backups_returns_list(self) -> None:
        backups = list_backups()
        assert isinstance(backups, list)

    def test_list_backups_after_creating(self, tmp_path: Path) -> None:
        config_path = BACKUP_DIR.parent / "config.yml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("version: 1\n")
        create_backup()
        backups = list_backups()
        assert len(backups) >= 1
        assert "timestamp" in backups[0]
        assert "path" in backups[0]

    def test_restore_backup_returns_none_for_missing(self) -> None:
        assert restore_backup("nonexistent") is None

    def test_restore_backup_restores_content(self, tmp_path: Path) -> None:
        config_path = BACKUP_DIR.parent / "config.yml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("version: 1\nmodels: []\n")
        backup_path = create_backup()
        assert backup_path is not None

        config_path.write_text("version: 2\nmodels: [test]\n")
        restore_backup(backup_path.stem.replace("config-", ""))
        assert "version: 1" in config_path.read_text()
