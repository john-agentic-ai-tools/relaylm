# Data Model: CLI Autoconfig

## Entities

### CodingAgent

Represents a detected coding agent on the system.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `str` | Yes | Agent identifier: `"opencode"` or `"claude-code"` |
| `display_name` | `str` | Yes | Human-readable name: `"OpenCode"` or `"Claude Code"` |
| `detected` | `bool` | Yes | Whether the agent was found on the system |
| `version` | `str \| None` | No | Detected version string, if available |
| `install_path` | `str \| None` | No | Path to the agent executable or config |
| `detected_via` | `str \| None` | No | How it was detected: `"path"`, `"config"`, `"npx"`, etc. |

### ConfigBackup

Represents a backup of the CLI config (reuses existing `config/backup.py` model).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file_path` | `Path \| None` | No | Full path to backup YAML file, or None if no backup was made |
| `timestamp` | `str \| None` | No | ISO-style timestamp string (e.g. `"20260515T103000"`) |
| `reason` | `str` | Yes | Why the backup was created: `"autoconfig-pre-write"` |

### ConfigChange

A single change made to the CLI config.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | `str` | Yes | Dot-notation path in config (e.g. `"agents.opencode"`) |
| `operation` | `str` | Yes | `"added"`, `"modified"`, or `"removed"` |
| `value` | `Any` | Yes | New value or old value depending on context |

### AutoconfigResult

The top-level result of an autoconfig run.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agents` | `list[CodingAgent]` | Yes | All agents that were checked |
| `changes` | `list[ConfigChange]` | Yes | Config changes applied (empty if no agents found) |
| `backup` | `ConfigBackup \| None` | No | Backup reference if config was modified |
| `summary` | `str` | Yes | Human-readable summary for display |

### RevertResult

Result of a revert operation (reuses existing `restore_backup`).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `success` | `bool` | Yes | Whether the revert succeeded |
| `backup_timestamp` | `str \| None` | No | Which backup was used |
| `message` | `str` | Yes | Human-readable outcome |

## State Transitions

```
[User runs autoconfig]
         │
         ▼
  Scan for agents ──→ No agents found ──→ Print friendly message
         │                                    (no config changes)
         ▼
  Agents detected
         │
         ▼
  Backup existing config (if exists)
         │
         ▼
  Update relaylm config with agent entries
         │
         ▼
  Print change summary + testing instructions
```

## Validation Rules

- `CodingAgent.name` MUST be one of `"opencode"` or `"claude-code"`
- `CodingAgent.detected` MUST reflect actual filesystem/PATH check — never assumed
- `ConfigChange.path` MUST use dot notation for nested keys
- `AutoconfigResult.backup` MUST be `None` only when no config modification occurred
- If config file does not exist and agents are detected, a new config is created (no backup needed)
