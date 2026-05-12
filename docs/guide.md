# RelayLM User Guide

## Table of Contents

- [Hardware Requirements](#hardware-requirements)
- [Installation](#installation)
- [Container Runtime](#container-runtime)
- [Basic Setup](#basic-setup)
- [Provider Configuration](#provider-configuration)
- [Agent Configuration](#agent-configuration)
- [Configuration Management](#configuration-management)
- [Troubleshooting](#troubleshooting)

---

## Hardware Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| RAM | 8 GB (16 GB recommended for larger models) |
| CPU | 4 cores |
| Disk | 10 GB free for model storage |
| Container Runtime | Podman or Docker |

### GPU Recommendations

GPU acceleration is optional but recommended for better performance:

- **NVIDIA**: Any CUDA-compatible GPU with 4 GB+ VRAM
- **AMD**: ROCm-compatible GPU

RelayLM auto-detects your GPU during `relaylm setup` and selects appropriate models based on available VRAM.

### Checking Your System

```bash
# Check RAM (Linux)
grep MemTotal /proc/meminfo

# Check CPU cores
nproc

# Check NVIDIA GPU memory
nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits

# Check AMD GPU
rocm-smi
```

On WSL2, use the same Linux commands inside the distro. `nvidia-smi` works
when the Windows-side NVIDIA CUDA on WSL driver is installed.

---

## Installation

### Via pip (recommended)

```bash
pip install relaylm
```

### Via uv

```bash
uv tool install relaylm
```

### From source

```bash
pip install git+https://github.com/anomalyco/relaylm.git
```

### Verify installation

```bash
relaylm --help
```

You should see the list of available commands: `setup`, `agents`, `providers`, `config`.

### Windows (WSL2)

Native Windows Python is not supported. Install and run RelayLM inside a WSL2
Linux distro on Windows 10 22H2+ or Windows 11.

1. **Enable WSL2 and install Ubuntu** (Windows PowerShell, as administrator):

   ```powershell
   wsl --install -d Ubuntu
   ```

   Restart when prompted, then finish the Ubuntu first-run setup.

2. **Install a container runtime**:

   - *Recommended*: install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
     on Windows and enable WSL integration for your distro
     (Settings → Resources → WSL Integration).
   - *Alternative*: install Podman inside the distro: `sudo apt install podman`.

3. **Install RelayLM inside the distro**:

   ```bash
   pip install relaylm
   ```

4. **GPU passthrough (optional)**: install the
   [NVIDIA CUDA on WSL driver](https://developer.nvidia.com/cuda/wsl) **on the
   Windows host** — do not install the Linux NVIDIA driver inside the distro.
   Verify with `nvidia-smi` inside the distro.

5. **Performance**: clone repositories into the Linux filesystem
   (e.g. `~/code`), not under `/mnt/c/...` — cross-filesystem I/O is 5–10x
   slower.

---

## Container Runtime

RelayLM uses a container runtime (Podman or Docker) to run the vLLM inference server.

### Installing Podman

**Linux (Ubuntu/Debian)**:

```bash
sudo apt update
sudo apt install podman
```

**Linux (Fedora)**:

```bash
sudo dnf install podman
```

**macOS**:

```bash
brew install podman
podman machine init
podman machine start
```

### Installing Docker

**Linux (Ubuntu/Debian)**:

```bash
sudo apt update
sudo apt install docker.io
sudo systemctl enable --now docker
```

**Linux (Fedora)**:

```bash
sudo dnf install docker
sudo systemctl enable --now docker
```

**macOS**: Download Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop/)

### Verify the Runtime

```bash
podman info
```

or

```bash
docker info
```

RelayLM auto-detects the available runtime. Podman is preferred when both are present.

---

## Basic Setup

### Default Setup

```bash
relaylm setup --yes
```

This runs in non-interactive mode and:

1. Detects your hardware (RAM, CPU, GPU)
2. Selects models appropriate for your system
3. Pulls the vLLM Docker image
4. Starts a vLLM container with the selected models
5. Saves configuration to `~/.config/relaylm/config.yml`

After completion, your router is available at `http://127.0.0.1:8000/v1`.

### Setup Options

```bash
relaylm setup [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--models TEXT` | Comma-separated model list (overrides auto-detection) |
| `--yes` / `--non-interactive` | Auto-accept all prompts |
| `--runtime TEXT` | Force container runtime: `podman` or `docker` |
| `--port INTEGER` | Router port (default: 8000) |

#### Override Model Selection

```bash
relaylm setup --models "Qwen/Qwen3-0.6B,mistralai/Mistral-7B-Instruct-v0.3"
```

#### Force a Specific Runtime

```bash
relaylm setup --runtime docker
```

#### Custom Port

```bash
relaylm setup --port 8080
```

---

## Provider Configuration

RelayLM supports external AI providers as fallback or primary inference sources. You can configure Anthropic and OpenAI.

### Adding a Provider

```bash
relaylm providers add anthropic --key sk-ant-...
```

Or for OpenAI:

```bash
relaylm providers add openai --key sk-...
```

### Interactive Mode

If you omit `--key`, you will be prompted securely:

```bash
relaylm providers add anthropic
Enter anthropic API key:
```

### Custom API Base URL

```bash
relaylm providers add openai --key sk-... --base-url https://custom.example.com/v1
```

### Skip Confirmation

```bash
relaylm providers add anthropic --key sk-ant-... --yes
```

### Listing Providers

```bash
relaylm providers list-cmd
```

Example output:

```text
anthropic: enabled=True, key set
openai: enabled=True, no key
```

### How Provider Fallback Works

When configured, the router uses the local vLLM instance as the primary inference target. If the local model is unavailable or a request specifies a model not loaded locally, the router falls back to the configured cloud provider. The provider order is specified in the configuration file.

---

## Agent Configuration

RelayLM can auto-detect and configure coding agents to use the local router as their inference endpoint.

### Claude Code

If you have Claude Code installed (`~/.claude/settings.json` exists), running:

```bash
relaylm agents
```

will update your Claude configuration to point at the local router:

```json
{
  "apiProvider": "anthropic",
  "customApiUrl": "http://127.0.0.1:8000/v1"
}
```

### OpenCode

If you have OpenCode installed (`~/.config/opencode/opencode.json` exists), RelayLM will configure it to use the local endpoint as its model.

### Dry Run

To see what would be changed without writing:

```bash
relaylm agents --dry-run
```

---

## Configuration Management

### View Configuration

```bash
relaylm config show
```

This prints your current configuration with secrets masked.

### Configuration File Location

```bash
relaylm config path
```

Example output:

```text
/home/you/.config/relaylm/config.yml
```

### Backups

RelayLM automatically creates timestamped backups before modifying the configuration. Backups are stored in:

```text
~/.config/relaylm/backups/config-{timestamp}.yml
```

### Listing Backups

```bash
relaylm config restore --list
```

### Restoring a Backup

```bash
relaylm config restore 20260509T172321
```

---

See the [Configuration Reference](config.md) for a complete description of all configuration file fields.

---

## Troubleshooting

### Container Runtime Not Found

**Error**: `No container runtime found (install Podman or Docker)`

**Solution**: Install Podman or Docker (see [Container Runtime](#container-runtime) above) and ensure it's running.

```bash
# Verify runtime is running
podman info
```

### GPU Not Detected

**Error**: No GPU detected when one is installed.

**NVIDIA**:

```bash
# Verify NVIDIA drivers are installed
nvidia-smi
```

If `nvidia-smi` is not found, install NVIDIA drivers and the CUDA toolkit.

**AMD**:

```bash
# Verify ROCm is installed
rocm-smi
```

### API Key Errors

**Error**: Authentication errors when using provider fallback.

**Solution**: Verify your API key is stored:

```bash
relaylm providers list-cmd
```

If a provider shows "no key", re-add it:

```bash
relaylm providers add anthropic --key sk-ant-...
```

### Port Already in Use

**Error**: `address already in use` or similar port conflict.

**Solution**: Specify a different port:

```bash
relaylm setup --port 8080
```

### vLLM Container Fails to Start

**Error**: `Failed to start vLLM container` or container exits immediately.

**Possible causes**:

- Insufficient disk space for model download
- Insufficient RAM/VRAM for the selected model
- Container runtime permission issues

**Solutions**:

- Free up disk space
- Use `--models` to select a smaller model
- Run setup with `--runtime podman` or `--runtime docker` explicitly
