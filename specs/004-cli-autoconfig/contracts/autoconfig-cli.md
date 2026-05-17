# CLI Contract: `relaylm autoconfig`

## Command Signature

```
relaylm autoconfig [OPTIONS]
```

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--dry-run` | `bool` | `False` | Scan and report what would change without writing anything |
| `--yes` / `--non-interactive` | `bool` | `False` | Skip confirmation prompt, apply changes immediately |

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Autoconfig completed successfully (agents found OR none found) |
| `1` | Error during detection or config write |
| `2` | Invalid arguments |

## Stdout (Success — Agents Found)

```
Autoconfig complete.

Detected agents:
  ✅ OpenCode (v0.x) — /home/user/.local/bin/opencode
  ✅ Claude Code (via npx)

Changes made to ~/.config/relaylm/config.yml:
  + agents.opencode = {"detected": true, ...}
  + agents.claude-code = {"detected": true, ...}

Backup saved: ~/.config/relaylm/backups/config-20260515T103000.yml

To test:
  relaylm providers list

To revert:
  relaylm config restore 20260515T103000
```

## Stdout (Success — No Agents Found)

```
Autoconfig complete.

No supported coding agents detected.

RelayLM currently supports:
  • OpenCode   — https://opencode.ai
  • Claude Code — https://docs.anthropic.com/en/docs/claude-code/overview

Install one of these agents and re-run `relaylm autoconfig`.
No changes were made to your configuration.
```

## Stderr (Error)

All error messages go to stderr with descriptive text. Example:

```
Error: Could not write config to ~/.config/relaylm/config.yml: Permission denied
```

## Config Contract (Agents Section)

When agents are detected, the following section is added to `~/.config/relaylm/config.yml`:

```yaml
agents:
  opencode:
    detected: true
    version: "0.x"
    install_path: /home/user/.local/bin/opencode
    configured_at: "2026-05-15T10:30:00"
  claude-code:
    detected: true
    version: "latest"
    detected_via: npx
    configured_at: "2026-05-15T10:30:00"
```

## Dry-Run Contract

When `--dry-run` is specified:
- Detection runs normally
- No backup is created
- No config is written
- Output shows what WOULD have been changed
- Exit code is always `0` (detection itself succeeded)
