<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://img.shields.io/badge/python-3.11+-blue?style=flat&logo=python&logoColor=white&labelColor=333">
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11+-blue?style=flat&logo=python&logoColor=white&labelColor=333">
</picture>

![MIT License](https://img.shields.io/badge/license-MIT-green?style=flat)
[![Ruff](https://img.shields.io/badge/code_style-ruff-000000?style=flat)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue?style=flat)](https://github.com/python/mypy)

# RelayLM

**Local AI routing infrastructure — one command to bootstrap your environment.**

RelayLM auto-detects your hardware (RAM, CPU, GPU), selects appropriate models from Hugging Face, starts a vLLM inference server via Podman or Docker, and configures cloud provider fallback and coding agents — all with a single command.

## Prerequisites

- **Python 3.11** or later
- **Podman** or **Docker** (container runtime)

## Install

```bash
pip install relaylm
```

Or with uv:

```bash
uv tool install relaylm
```

Or from source:

```bash
pip install git+https://github.com/anomalyco/relaylm.git
```

## Quick Start

```bash
relaylm setup --yes
```

This will:

1. Detect your hardware (RAM, CPU cores, GPU)
2. Select models appropriate for your system
3. Pull and start a vLLM container with the selected models
4. Save configuration to `~/.config/relaylm/config.yml`

After setup, your local AI router is available at `http://127.0.0.1:8000/v1`.

## Next Steps

- [User Guide](docs/guide.md) — Detailed installation and configuration instructions
- [Provider Configuration](docs/guide.md#provider-configuration) — Add Anthropic or OpenAI as cloud fallback
- [Agent Setup](docs/guide.md#agent-configuration) — Auto-configure Claude Code and OpenCode
- [Contributing](CONTRIBUTING.md) — Development workflow and how to contribute

## Commands

| Command | Description |
|---------|-------------|
| `relaylm setup` | Bootstrap the local AI routing environment |
| `relaylm providers add` | Configure an external AI provider |
| `relaylm providers list-cmd` | List configured providers |
| `relaylm agents` | Detect and configure coding agents |
| `relaylm config show` | Print current configuration |
| `relaylm config path` | Print configuration file path |
| `relaylm config restore` | Restore configuration from a backup |

## License

MIT — see [LICENSE](LICENSE) for details.
