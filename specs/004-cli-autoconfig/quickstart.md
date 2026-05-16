# Quickstart: CLI Autoconfig

## Usage

```bash
# Auto-detect and configure coding agents
relaylm autoconfig

# Preview changes without applying
relaylm autoconfig --dry-run

# Skip confirmation
relaylm autoconfig --yes
```

## What It Does

1. Scans your machine for OpenCode and Claude Code
2. Backs up your existing relaylm config (if any)
3. Updates relaylm's config with detected agent info
4. Shows a summary of changes with testing instructions
5. Never modifies agent config files — only relaylm's own config

## Reverting

```bash
# List available backups
relaylm config restore --list

# Restore from a specific backup
relaylm config restore 20260515T103000
```

## Testing

```bash
# Verify agents were registered
relaylm config show | grep agents

# Verify the CLI still works after autoconfig
relaylm --help
relaylm providers list
```
