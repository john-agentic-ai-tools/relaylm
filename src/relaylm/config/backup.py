from datetime import datetime
from pathlib import Path

from relaylm.config.loader import CONFIG_DIR, CONFIG_PATH

BACKUP_DIR = CONFIG_DIR / "backups"


def _unique_path(base: Path) -> Path:
    if not base.exists():
        return base
    stem = base.stem
    suffix_num = 1
    while True:
        candidate = base.with_name(f"{stem}_{suffix_num:03d}{base.suffix}")
        if not candidate.exists():
            return candidate
        suffix_num += 1


def create_backup() -> Path | None:
    if not CONFIG_PATH.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_path = _unique_path(BACKUP_DIR / f"config-{timestamp}.yml")
    content = CONFIG_PATH.read_bytes()
    try:
        backup_path.write_bytes(content)
    except PermissionError:
        return None
    return backup_path


def list_backups() -> list[dict[str, str]]:
    if not BACKUP_DIR.exists():
        return []
    backups = []
    for p in sorted(BACKUP_DIR.iterdir(), reverse=True):
        if p.suffix == ".yml":
            backups.append({"timestamp": p.stem.replace("config-", ""), "path": str(p)})
    return backups


def restore_backup(timestamp: str) -> Path | None:
    backup_path = BACKUP_DIR / f"config-{timestamp}.yml"
    if not backup_path.exists():
        return None
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = backup_path.read_bytes()
    CONFIG_PATH.write_bytes(content)
    return CONFIG_PATH
