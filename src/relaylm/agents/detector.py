import json
from pathlib import Path
from typing import Any


def _detect_claude_code() -> Path | None:
    claude_settings = Path.home() / ".claude" / "settings.json"
    if claude_settings.exists():
        return claude_settings
    return None


def _detect_opencode() -> Path | None:
    opencode_config = Path.home() / ".config" / "opencode" / "opencode.json"
    if opencode_config.exists():
        return opencode_config
    return None


def _configure_claude_code(config_path: Path, endpoint_url: str, dry_run: bool) -> bool:
    try:
        content = json.loads(config_path.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        content = {}

    content["apiProvider"] = "anthropic"
    content["customApiUrl"] = endpoint_url

    if dry_run:
        return True

    config_path.write_text(json.dumps(content, indent=2))
    return True


def _configure_opencode(config_path: Path, endpoint_url: str, dry_run: bool) -> bool:
    try:
        content = json.loads(config_path.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        content = {}

    content["model"] = endpoint_url.rstrip("/") + "/chat/completions"

    if dry_run:
        return True

    config_path.write_text(json.dumps(content, indent=2))
    return True


def detect_and_configure_agents(
    endpoint_url: str, dry_run: bool = False
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    claude_config = _detect_claude_code()
    if claude_config:
        _configure_claude_code(claude_config, endpoint_url, dry_run)
        action = "Would configure" if dry_run else "Configured"
        results.append(
            {
                "agent": "claude-code",
                "config_path": str(claude_config),
                "action": action,
            }
        )
    else:
        results.append(
            {"agent": "claude-code", "config_path": None, "action": "Not found"}
        )

    opencode_config = _detect_opencode()
    if opencode_config:
        _configure_opencode(opencode_config, endpoint_url, dry_run)
        action = "Would configure" if dry_run else "Configured"
        results.append(
            {
                "agent": "opencode",
                "config_path": str(opencode_config),
                "action": action,
            }
        )
    else:
        results.append(
            {"agent": "opencode", "config_path": None, "action": "Not found"}
        )

    return results
