import functools
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from relaylm.config.backup import create_backup, list_backups, restore_backup
from relaylm.config.loader import load_config, save_config
from relaylm.platform import is_wsl2
from relaylm.schemas.autoconfig import (
    AutoconfigResult,
    CodingAgent,
    ConfigBackup,
    ConfigChange,
    RevertResult,
)


def _wslpath_to_unix(win_path: str) -> Path | None:
    try:
        result = subprocess.run(
            ["wslpath", "-u", win_path],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    converted = result.stdout.strip()
    return Path(converted) if converted else None


_VERSION_RE = re.compile(r"\d+\.\d+(?:\.\d+)?(?:[-+][\w.\-]+)?")


@functools.lru_cache(maxsize=8)
def _executable_version(executable: str) -> str | None:
    try:
        result = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    text = f"{result.stdout or ''} {result.stderr or ''}".strip()
    match = _VERSION_RE.search(text)
    return match.group(0) if match else None


def _agent_version(bin_name: str, install_path: str | None) -> str | None:
    if install_path:
        p = Path(install_path)
        if p.suffix.lower() in {".cmd", ".exe", ".bat", ""} and p.is_file():
            v = _executable_version(str(p))
            if v:
                return v
    found = shutil.which(bin_name)
    if found:
        v = _executable_version(found)
        if v:
            return v
    win_home = _wsl2_windows_home()
    if win_home is not None:
        npm_globals = win_home / "AppData" / "Roaming" / "npm"
        for cand in (npm_globals / f"{bin_name}.cmd", npm_globals / bin_name):
            if cand.is_file():
                v = _executable_version(str(cand))
                if v:
                    return v
    return None


def _wsl2_windows_home() -> Path | None:
    if not is_wsl2():
        return None
    win_userprofile = os.environ.get("USERPROFILE")
    if win_userprofile:
        path = _wslpath_to_unix(win_userprofile)
        if path is not None and path.exists():
            return path
    try:
        result = subprocess.run(
            ["cmd.exe", "/c", "echo %USERPROFILE%"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    win_path = result.stdout.strip()
    if not win_path:
        return None
    path = _wslpath_to_unix(win_path)
    if path is not None and path.exists():
        return path
    return None


def _detect_claude_code() -> CodingAgent:
    settings = Path.home() / ".claude" / "settings.json"
    if settings.exists():
        path = str(settings)
        return CodingAgent(
            name="claude-code",
            display_name="Claude Code",
            detected=True,
            detected_via="config",
            install_path=path,
            version=_agent_version("claude", path),
        )
    shim = shutil.which("claude")
    if shim:
        return CodingAgent(
            name="claude-code",
            display_name="Claude Code",
            detected=True,
            detected_via="path",
            install_path=shim,
            version=_agent_version("claude", shim),
        )
    win_home = _wsl2_windows_home()
    if win_home is not None:
        npm_globals = win_home / "AppData" / "Roaming" / "npm"
        for win_path in (
            win_home / ".claude" / "settings.json",
            npm_globals / "claude.cmd",
            npm_globals / "claude",
        ):
            if win_path.exists():
                path = str(win_path)
                return CodingAgent(
                    name="claude-code",
                    display_name="Claude Code",
                    detected=True,
                    detected_via="wsl-windows-host",
                    install_path=path,
                    version=_agent_version("claude", path),
                )
    return CodingAgent(
        name="claude-code",
        display_name="Claude Code",
        detected=False,
    )


def _opencode_config_candidates() -> list[Path]:
    home = Path.home()
    if sys.platform == "win32":
        appdata_env = os.environ.get("APPDATA")
        appdata = Path(appdata_env) if appdata_env else home / "AppData" / "Roaming"
        return [appdata / "opencode" / "opencode.json"]
    if sys.platform == "darwin":
        return [
            home / "Library" / "Application Support" / "opencode" / "opencode.json",
            home / ".config" / "opencode" / "opencode.json",
        ]
    xdg_env = os.environ.get("XDG_CONFIG_HOME")
    xdg_base = Path(xdg_env) if xdg_env else home / ".config"
    return [xdg_base / "opencode" / "opencode.json"]


def _detect_opencode() -> CodingAgent:
    for candidate in _opencode_config_candidates():
        if candidate.exists():
            path = str(candidate)
            return CodingAgent(
                name="opencode",
                display_name="OpenCode",
                detected=True,
                detected_via="config",
                install_path=path,
                version=_agent_version("opencode", path),
            )
    shim = shutil.which("opencode")
    if shim:
        return CodingAgent(
            name="opencode",
            display_name="OpenCode",
            detected=True,
            detected_via="path",
            install_path=shim,
            version=_agent_version("opencode", shim),
        )
    win_home = _wsl2_windows_home()
    if win_home is not None:
        appdata = win_home / "AppData" / "Roaming"
        npm_globals = appdata / "npm"
        for win_path in (
            appdata / "opencode" / "opencode.json",
            npm_globals / "opencode.cmd",
            npm_globals / "opencode",
        ):
            if win_path.exists():
                path = str(win_path)
                return CodingAgent(
                    name="opencode",
                    display_name="OpenCode",
                    detected=True,
                    detected_via="wsl-windows-host",
                    install_path=path,
                    version=_agent_version("opencode", path),
                )
    return CodingAgent(
        name="opencode",
        display_name="OpenCode",
        detected=False,
    )


def detect_agents() -> list[CodingAgent]:
    return [_detect_opencode(), _detect_claude_code()]


def _build_changes(detected: list[CodingAgent], timestamp: str) -> list[ConfigChange]:
    changes: list[ConfigChange] = []
    for agent in detected:
        if not agent.detected:
            continue
        changes.append(
            ConfigChange(
                path=f"agents.{agent.name}",
                operation="added",
                value={
                    "detected": True,
                    "version": agent.version,
                    "install_path": agent.install_path,
                    "detected_via": agent.detected_via,
                    "configured_at": timestamp,
                },
            )
        )
    return changes


_AGENT_HELP_URLS = {
    "opencode": "https://opencode.ai",
    "claude-code": "https://docs.anthropic.com/en/docs/claude-code/overview",
}


def run_autoconfig(dry_run: bool = False) -> AutoconfigResult:
    """Detect supported coding agents and record them under ``agents.<name>``
    in ``~/.config/relaylm/config.yml``. Re-running clobbers any hand-edits to
    those keys; use ``relaylm autoconfig revert`` to restore the prior config.
    """
    agents = detect_agents()
    detected = [a for a in agents if a.detected]

    if not detected:
        summary = (
            "No supported coding agents detected.\n\n"
            "RelayLM currently supports:\n"
        )
        for a in agents:
            url = _AGENT_HELP_URLS.get(a.name, "")
            summary += f"  \u2022 {a.display_name}  \u2014  {url}\n"
        summary += (
            "\nInstall one of these agents and re-run `relaylm autoconfig`.\n"
            "No changes were made to your configuration."
        )
        return AutoconfigResult(agents=agents, summary=summary)

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    changes = _build_changes(detected, timestamp)

    backup = None
    backup_path = None
    if not dry_run:
        backup_path = create_backup()
        if backup_path:
            backup = ConfigBackup(
                file_path=backup_path,
                timestamp=timestamp,
                reason="autoconfig-pre-write",
            )

        config = load_config()
        agents_config = config.setdefault("agents", {})
        for change in changes:
            agents_config[change.path.split(".", 1)[1]] = change.value
        save_config(config)

    detected_lines = "\n".join(
        f"  \u2705 {a.display_name}"
        + (f" ({a.version})" if a.version else "")
        + (f" \u2014  {a.install_path}" if a.install_path else "")
        for a in detected
    )
    change_lines = "\n".join(
        f"  + {c.path} = {c.value}" for c in changes
    )

    if dry_run:
        header = "Dry run \u2014 no changes applied."
        backup_line = (
            "\nA backup of ~/.config/relaylm/config.yml would be created "
            "before writing."
        )
        changes_label = "Changes that would be made to relaylm config:"
        footer = "\nRe-run without --dry-run to apply these changes."
    else:
        header = "Autoconfig complete."
        backup_line = (
            f"\nBackup saved: {backup_path}" if backup_path
            else "\nNo backup needed (new config created)."
        )
        changes_label = "Changes made to relaylm config:"
        footer = (
            "\nTo test:\n"
            "  relaylm providers list\n\n"
            "To revert:\n"
            "  relaylm autoconfig revert"
        )

    summary = (
        f"{header}\n\n"
        f"Detected agents:\n{detected_lines}\n\n"
        f"{changes_label}\n{change_lines}"
        f"{backup_line}\n"
        f"{footer}"
    )

    return AutoconfigResult(
        agents=agents,
        changes=changes,
        backup=backup,
        summary=summary,
    )


def revert_autoconfig() -> RevertResult:
    backups = list_backups()
    if not backups:
        return RevertResult(
            success=False,
            message=(
                "No backup found. "
                "Run `relaylm autoconfig` first to create a backup."
            ),
        )

    latest = backups[0]
    timestamp = latest["timestamp"]
    restored = restore_backup(timestamp)
    if restored is None:
        return RevertResult(
            success=False,
            backup_timestamp=timestamp,
            message=f"Backup '{timestamp}' could not be restored.",
        )

    return RevertResult(
        success=True,
        backup_timestamp=timestamp,
        message=f"Configuration restored from backup '{timestamp}'.",
    )
