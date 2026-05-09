# CLI Commands Contract

## `relaylm setup`

Single-command environment bootstrap.

```
relaylm setup [OPTIONS]

Options:
  --models TEXT              Comma-separated model list (overrides auto-detection)
  --yes / --non-interactive  Auto-accept all prompts
  --runtime TEXT             Force container runtime: "podman" | "docker"
  --port INT                 Router port (default: 8000)
  --help                     Show this help
```

**Exit codes**: 0 = success, 1 = error, 2 = validation error

**Output**: Writes config to `~/.config/relaylm/config.yml`, creates backup of
prior config if present, prints router endpoint URL.

## `relaylm providers add`

Configure an external AI provider.

```
relaylm providers add <name> [OPTIONS]

Arguments:
  name                     "anthropic" | "openai"

Options:
  --key TEXT               API key (prompts securely if omitted)
  --base-url TEXT          API base URL (defaults to provider standard)
  --yes                    Skip confirmation prompt
  --help                   Show this help
```

**Behavior**: Stores API key in system keychain via `keyring` library. Writes
non-secret provider config to `config.yml`.

## `relaylm config`

Configuration management.

```
relaylm config [COMMAND]

Commands:
  show                     Print current config (secrets masked)
  restore --list           List available backups
  restore <timestamp>      Restore config from backup
  path                     Print config file path
```

## `relaylm agents detect`

Scan and optionally configure coding agents.

```
relaylm agents detect [OPTIONS]

Options:
  --dry-run                Show what would be changed without writing
  --yes                    Apply changes without confirmation
  --help                   Show this help
```
