from pathlib import Path
from typing import Any

from pydantic import BaseModel


class CodingAgent(BaseModel):
    name: str
    display_name: str
    detected: bool
    version: str | None = None
    install_path: str | None = None
    detected_via: str | None = None


class ConfigChange(BaseModel):
    path: str
    operation: str
    value: Any


class ConfigBackup(BaseModel):
    file_path: Path | None = None
    timestamp: str | None = None
    reason: str = "autoconfig-pre-write"


class AutoconfigResult(BaseModel):
    agents: list[CodingAgent]
    changes: list[ConfigChange] = []
    backup: ConfigBackup | None = None
    summary: str = ""


class RevertResult(BaseModel):
    success: bool
    backup_timestamp: str | None = None
    message: str = ""
