# Quick Start

## Prerequisites

- Python 3.11 or later
- Podman or Docker installed and running

## Install

```bash
pip install relaylm
```

Or with uv:

```bash
uv tool install relaylm
```

## Setup

Run the setup command to auto-detect your hardware, select appropriate models, and start a local AI router:

```bash
relaylm setup --yes
```

This will:
1. Detect your hardware (RAM, CPU, GPU)
2. Select suitable models for your system
3. Start a vLLM container with the selected models
4. Save the configuration

After setup completes, the router is available at `http://127.0.0.1:8000/v1`.

## Next Steps

- Configure cloud providers: `relaylm providers add anthropic --key sk-...`
- Auto-configure coding agents: `relaylm agents`
- View configuration: `relaylm config show`
- See the [User Guide](guide.md) for detailed instructions
