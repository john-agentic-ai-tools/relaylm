# Research: AI Router Environment Setup

## vLLM Docker Deployment

**Decision**: Use official `vllm/vllm-openai:latest` Docker image for NVIDIA GPU
systems, `vllm/vllm-openai-rocm:latest` for AMD ROCm.

**Rationale**: vLLM provides official, well-maintained Docker images for both
CUDA and ROCm that expose an OpenAI-compatible API server. Images include CUDA
forward-compatibility libraries for older drivers.

**Key commands**:

- NVIDIA: `docker run --runtime nvidia --gpus all -p 8000:8000 --ipc=host
  vllm/vllm-openai:latest --model <model>`
- Podman: `podman run --device nvidia.com/gpu=all -p 8000:8000 --ipc=host
  docker.io/vllm/vllm-openai:latest --model <model>`
- AMD ROCm: `docker run --group-add=video --device /dev/kfd --device /dev/dri
  -p 8000:8000 --ipc=host vllm/vllm-openai-rocm:latest --model <model>`

**Alternatives considered**: Building vLLM from source (too slow, unnecessary),
CPU-only vLLM (limited performance, only for small models).

---

## Container Runtime Abstraction

**Decision**: Use Python subprocess to invoke `podman` or `docker` CLI directly,
with a wrapper that normalizes flags across both runtimes.

**Rationale**: Both Docker and Podman share nearly identical CLI interfaces for
the flags we need (`run`, `pull`, `ps`, `stop`, `rm`). The primary differences
are GPU passthrough (`--gpus all` vs `--device nvidia.com/gpu=all`) and image
references (Docker uses bare names, Podman may need `docker.io/` prefix). A thin
wrapper handles these differences.

**Key findings**:
- Podman is daemonless and rootless by default — more secure
- Docker has wider ecosystem adoption and documentation
- Both support `docker compose` (Podman via `podman-compose` or `--compat`)
- vLLM official docs provide both `docker run` and `podman run` examples

---

## System Keychain Access

**Decision**: Use the `keyring` Python library for cross-platform keychain access.

**Rationale**: `keyring` provides a unified API across macOS Keychain, Linux
Freedesktop Secret Service (libsecret), and Windows Credential Locker. It
auto-selects the appropriate backend per platform.

**Backend details**:
- **macOS**: Uses native Keychain via `keyring.backends.macOS.Keyring`
- **Linux**: Uses Freedesktop Secret Service via `secretstorage` (requires D-Bus)
- **Linux fallback**: Encrypted file backend via `keyrings.alt` if no D-Bus
- **Windows**: Uses Windows Credential Locker

---

## Claude Code Configuration

**Decision**: Modify `~/.claude/settings.json` or `.claude/settings.local.json`
to set `apiProvider` and `customApiUrl` pointing at the local router.

**Key findings**:
- User config: `~/.claude/settings.json` (global, user-owned)
- Project config: `.claude/settings.json` (shared via git)
- Local config: `.claude/settings.local.json` (gitignored, per-project)
- Key settings: `apiProvider` (string), `customApiUrl` (string)
- Also supports `ANTHROPIC_BASE_URL` env var as override
- Claude Code v2.1+ uses JSON settings files

---

## OpenCode Configuration

**Decision**: Modify `~/.config/opencode/opencode.json` to set provider config
pointing at the local router as the model endpoint.

**Key findings**:
- Global config: `~/.config/opencode/opencode.json`
- Project config: `opencode.json` in project root
- Custom path via `OPENCODE_CONFIG` env var
- Auth/credentials stored in `~/.local/share/opencode/auth.json`
- OpenCode supports `model` field with `provider/model-name` format
- API keys can be set as env vars or in auth.json

---

## Hugging Face Model Discovery

**Decision**: Use `huggingface-hub` library `HfApi.list_models()` with filters
for task (`text-generation`), library (`vllm`), and hardware constraints.

**Rationale**: Hugging Face provides a searchable model API. Models can be
filtered by task, library compatibility, and popularity. The `safetensors`
format is preferred for vLLM compatibility.

**Model sizing heuristic** (approximate VRAM/RAM needs):
- 1B params: ~2 GB (quantized: ~0.8 GB)
- 3B params: ~6 GB (quantized: ~2 GB)
- 7B params: ~14 GB (quantized: ~4 GB)
- 8B params: ~16 GB (quantized: ~5 GB)
- 13B params: ~26 GB (quantized: ~7 GB)
- 70B params: ~140 GB (quantized: ~35 GB)
