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

GPU acceleration is recommended:

- **NVIDIA**: Any CUDA-compatible GPU with 4 GB+ VRAM. More VRAM means
  RelayLM can pick a larger model automatically.
- **AMD**: ROCm-compatible GPU.

You do not need to pre-classify your hardware. At setup time RelayLM
measures **free** GPU memory (not just total), looks up architectural
numbers for each candidate model in its curated registry, and picks the
largest one that fits with a usable context window — see [Auto-Sizing](#auto-sizing).

### Checking Your System

```bash
# Check RAM (Linux)
grep MemTotal /proc/meminfo

# Check CPU cores
nproc

# Check NVIDIA GPU total and free memory
nvidia-smi --query-gpu=memory.total,memory.free --format=csv,noheader,nounits

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
| `--max-model-len INTEGER` | *Advanced.* Override the auto-computed vLLM context length |
| `--max-num-seqs INTEGER` | *Advanced.* Override the default concurrent-sequence cap (1) |
| `--gpu-memory-util FLOAT` | *Advanced.* Override the auto-computed vLLM memory fraction |

The three "advanced" options are explained in
[Advanced Tuning](#advanced-tuning). Most users should not need them —
defaults are auto-computed from your hardware and the selected model.

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

### Auto-Sizing

When you run `relaylm setup` without `--models`, RelayLM picks a model
that actually fits your hardware:

1. **Measures free VRAM** via `nvidia-smi` (not just total — what's
   currently available, after accounting for the desktop session,
   browsers, etc.).
2. **Looks up the curated model registry** at
   `src/relaylm/models/registry.py`. Each entry has real architectural
   numbers (parameter count, hidden size, layer count, dtype) used to
   estimate runtime memory.
3. **Picks the largest model** whose weights + activations + KV cache at
   a 2048-token minimum context fit inside 90% of your free VRAM (a
   small safety margin covers measurement drift).
4. **Computes vLLM flags** from the resolved model + your VRAM:
   `--gpu-memory-utilization` scales with how much VRAM is actually
   free; `--max-model-len` is sized so the KV cache fits in the
   remaining budget (capped at 8192 to avoid over-reservation).

Sample output on an 8 GB card with ~6.7 GB free:

```text
Detected hardware: HardwareProfile(ram=32.0GB, cpu=16 cores, nvidia=True,
  vram_total=[8.0], vram_free=[6.7], amd=False)
Selected models: ['Qwen/Qwen3-1.7B']
  weights: 3.4 GB (1.7B params, fp16)
GPU budget: 6.20 GB (78% of 8.0 GB total, 6.7 GB free)
Runtime allocation: weights 3.4 GB + overhead 1.0 GB + KV cache up to 1.8 GB
Auto-tuned: --max-model-len 8192 --max-num-seqs 1 --gpu-memory-utilization 0.78
```

If no registered model fits, setup exits with a clean error and points
you at [Provider Configuration](#provider-configuration) so you can use
cloud inference instead.

If you pass `--models <hf-id>` for a model **not** in the registry,
RelayLM falls back to heuristic estimates (parameter count parsed from
the name, FP16 assumed) and prints a warning. Auto-sizing will still
work but may be conservative — `--max-model-len` lets you tune.

### Advanced Tuning

You should not normally need these flags. If auto-sizing failed (rare —
report it) or you have a specific workload in mind, you can override:

| Flag | When to reach for it | Example |
|------|---------------------|---------|
| `--max-model-len` | You want longer context than auto-tuning picked (e.g. for long-document tasks) and you have VRAM headroom | `relaylm setup --max-model-len 16384` |
| `--max-num-seqs` | Multiple agents will hit the router concurrently and you want higher throughput | `relaylm setup --max-num-seqs 4` |
| `--gpu-memory-util` | You've freed up VRAM since the last setup and want vLLM to grab more | `relaylm setup --gpu-memory-util 0.92` |

Changing any of these tuning flags recreates the running container
(RelayLM detects the configuration drift and stops + restarts vLLM with
the new flags).

### Hugging Face Token (optional)

vLLM downloads model weights from the Hugging Face Hub. Anonymous downloads
are rate-limited; setting a token enables faster, rate-limit-free downloads
and access to gated models (e.g. some Llama and Mistral releases).

1. **Create a Hugging Face account** at
   [https://huggingface.co/join](https://huggingface.co/join).
2. **Generate an access token**: open
   [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens),
   click "Create new token", choose the **Read** role (sufficient for
   downloads), give it a name (e.g. `relaylm`), and copy the value — it
   starts with `hf_`.
3. **Set the `HF_TOKEN` environment variable** in the shell where you'll
   run `relaylm setup`:

   - **Linux / macOS / WSL2** (bash or zsh):

     ```bash
     export HF_TOKEN=hf_xxx...
     # Persist across shells:
     echo 'export HF_TOKEN=hf_xxx...' >> ~/.bashrc
     ```

   - **Windows PowerShell** (only relevant if you ever run RelayLM
     natively on Windows — currently unsupported, see WSL2 above):

     ```powershell
     $env:HF_TOKEN = "hf_xxx..."
     # Persist (new shells only):
     setx HF_TOKEN "hf_xxx..."
     ```

   On WSL2, set the variable **inside the distro**, not in PowerShell —
   `relaylm setup` runs inside WSL2, and PowerShell env vars do not
   propagate unless `WSLENV` is configured.

4. **Run `relaylm setup`** — the token is forwarded to the vLLM container
   automatically. If you omit `--yes`, you will be prompted interactively
   if the env var is not set.

**Gated models**: for models behind a license agreement (e.g.
`meta-llama/...`), visit the model's page on Hugging Face and accept the
license while signed in. The token alone is not enough.

**Security**: tokens grant read access to your Hugging Face account; treat
them like passwords. The token is exposed in the container's environment
(visible via `docker inspect`), so use a dedicated read-only token rather
than your account's full-access one. Revoke at
[huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
if it leaks.

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
- Container runtime permission issues
- Port already bound by a previous container

**Solutions**:

- Free up disk space
- Run setup with `--runtime podman` or `--runtime docker` explicitly
- Remove any stranded container holding port 8000:
  `docker ps --filter "publish=8000"` then `docker rm -f <id>`

### Container exits with "No available memory for the cache blocks"

This means vLLM loaded the model but had no room left for the KV cache.
First, make sure you're on the current version (auto-sizing computes
both flags from your hardware now). If it still happens:

- Free up VRAM (close GPU-heavy apps on the host) and re-run.
- Try `relaylm setup --max-model-len 2048` to shrink the KV cache.

### Setup Exits with "No local model fits"

**Error**: `No local model fits your available VRAM (X GB free of Y GB
total).`

**Cause**: Your free VRAM is below the minimum any registered model
needs at a usable context length.

**Solutions**:

- Free up VRAM on the host (close other GPU-using apps) and re-run.
- Configure a cloud provider so requests are proxied to Anthropic or
  OpenAI: `relaylm providers add anthropic --key sk-ant-...`.
- If you know your card can handle a specific model, pass it explicitly:
  `relaylm setup --models someone/Foo-7B` (heuristic sizing applies).
