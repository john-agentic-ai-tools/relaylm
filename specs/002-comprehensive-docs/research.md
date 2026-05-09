# Research: Comprehensive Project Documentation

## CLI Verification

All commands and flags verified against the actual `relaylm` tool:

| Command | Flag | Type | Notes |
|---------|------|------|-------|
| `relaylm` | `--help` | built-in | Shows commands: setup, agents, providers, config |
| `relaylm setup` | `--models TEXT` | optional | Comma-separated model list |
| `relaylm setup` | `--yes / --non-interactive` | flag | Auto-accept all prompts |
| `relaylm setup` | `--runtime TEXT` | optional | Force container runtime: podman or docker |
| `relaylm setup` | `--port INTEGER` | optional | Router port (default: 8000) |
| `relaylm providers add` | `NAME` | required arg | Provider name: anthropic or openai |
| `relaylm providers add` | `--key TEXT` | optional | API key (prompts if omitted) |
| `relaylm providers add` | `--base-url TEXT` | optional | API base URL |
| `relaylm providers add` | `--yes` | flag | Skip confirmation |
| `relaylm providers list-cmd` | — | — | Lists configured providers |
| `relaylm agents` | `--dry-run` | flag | Show changes without writing |
| `relaylm agents` | `--yes` | flag | Apply changes without confirmation |
| `relaylm config show` | — | — | Print current config (secrets masked) |
| `relaylm config path` | — | — | Print config file path |
| `relaylm config restore` | `TIMESTAMP` | optional arg | Backup timestamp to restore |
| `relaylm config restore` | `--list` | flag | List available backups |

## Product Information

**Install methods**:
- `pip install relaylm` (PyPI)
- `uv tool install relaylm` (uv)
- `pip install git+https://github.com/anomalyco/relaylm.git` (from source)

**Prerequisites**:
- Python 3.11+
- Podman or Docker (container runtime)
- Optional: NVIDIA GPU with nvidia-smi, AMD GPU with ROCm

**Config file**: `~/.config/relaylm/config.yml`
**Backups**: `~/.config/relaylm/backups/config-{timestamp}.yml`

## Documentation Best Practices

- **README.md**: GitHub stars, badges, one-paragraph intro, install, quick start, links to docs
- **CONTRIBUTING.md**: Pre-commit hooks, test commands, PR template reference, code review process
- **CODE_OF_CONDUCT.md**: Contributor Covenant v2.1 is the industry standard
- **LICENSE**: MIT license (already chosen in pyproject.toml)
- **docs/guide.md**: Include table of contents, numbered steps, code blocks, troubleshooting FAQ

## Existing Documentation Audit

Current state:
- `pyproject.toml`: Has license = "MIT", project description, and script entry points
- No README.md, LICENSE, CODE_OF_CONDUCT, or CONTRIBUTING files exist
- Source code modules have docstrings but no user-facing documentation
- `specs/001-ai-router-setup/` contains internal development documents
- `AGENTS.md` exists for agent context
- No docs/ directory exists yet

## Key Decisions

- **README.md** at repository root: Entry point with badges, description, install, quick start
- **LICENSE** at repository root: MIT license text
- **CODE_OF_CONDUCT.md** at repository root: Contributor Covenant v2.1
- **CONTRIBUTING.md** at repository root: Development workflow and PR process
- **docs/guide.md**: Main user guide with TOC and step-by-step instructions
- **docs/config.md**: Supporting doc for configuration reference (cross-linked from guide.md)
