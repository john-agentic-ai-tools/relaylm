# Quickstart: AI Router Environment Setup

## Prerequisites

- Linux or macOS (WSL2 on Windows)
- Python 3.11+
- Internet connection (first run)
- At least 8 GB free RAM

## Installation

```bash
pip install relaylm
```

## Single-Command Setup

```bash
relaylm setup
```

The tool will:
1. Detect your hardware (RAM, CPU, GPU)
2. Select appropriate models for your hardware
3. Detect Podman or Docker
4. Pull and start vLLM with selected models
5. Generate `~/.config/relaylm/config.yml`
6. Print the router endpoint URL

## Add External Providers

```bash
relaylm providers add openai --key sk-...
relaylm providers add anthropic --key sk-ant-...
```

## Verify

```bash
curl http://localhost:8000/v1/models
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen3-0.6B","messages":[{"role":"user","content":"Hello"}]}'
```

## Agent Auto-Configuration

After setup, Claude Code and OpenCode will be detected and configured
to use the local router as their LLM endpoint automatically.

## Configuration Restore

```bash
relaylm config restore --list      # List backups
relaylm config restore 20260509T120000  # Restore specific backup
```

## Non-Interactive Mode

```bash
relaylm setup --yes                 # Auto-accept all defaults
relaylm setup --models "llama3-8b,mistral-7b" --yes  # Custom models, non-interactive
```
