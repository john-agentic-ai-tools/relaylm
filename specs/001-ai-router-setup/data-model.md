# Data Model: AI Router Configuration

## Config Schema (YAML)

The master configuration file at `~/.config/relaylm/config.yml`.

```yaml
# RelayLM Configuration
version: 1
container_runtime: podman     # "podman" | "docker" — auto-detected
models:
  - name: Qwen/Qwen3-0.6B    # Hugging Face model ID
    source: huggingface       # "huggingface" | custom URL
    gpu_index: 0              # GPU device index (null for CPU)
    args:                     # Extra vLLM serve arguments
      max_model_len: 4096
providers:
  anthropic:
    enabled: false
    base_url: https://api.anthropic.com/v1
    keychain_service: relaylm-anthropic  # keychain service name
  openai:
    enabled: false
    base_url: https://api.openai.com/v1
    keychain_service: relaylm-openai
fallback:
  order:                      # Priority order for routing
    - local                   # Try local models first
    - anthropic               # Then cloud providers in order
    - openai
  timeout_seconds: 30         # Per-provider timeout
router:
  host: 127.0.0.1
  port: 8000
```

## Entities

### HardwareProfile
| Field | Type | Description |
|-------|------|-------------|
| ram_gb | float | Total system RAM in GB |
| cpu_cores | int | Logical CPU core count |
| has_nvidia_gpu | bool | NVIDIA GPU detected |
| gpu_vram_gb | float[] | VRAM per GPU device |
| has_amd_gpu | bool | AMD ROCm-capable GPU detected |
| container_runtime | str | "podman" \| "docker" \| null |

### ModelSelection
| Field | Type | Description |
|-------|------|-------------|
| model_id | str | Hugging Face model ID (e.g. "Qwen/Qwen3-0.6B") |
| source | str | "huggingface" \| custom URL |
| required_ram_gb | float | Estimated RAM needed |
| required_vram_gb | float | Estimated VRAM needed (null for CPU) |
| gpu_index | int \| null | Assigned GPU device (null = CPU) |
| args | dict | Extra vLLM serve arguments |

### ProviderConfig
| Field | Type | Description |
|-------|------|-------------|
| name | str | "anthropic" \| "openai" |
| enabled | bool | Whether provider is active |
| base_url | str | API endpoint URL |
| keychain_service | str | Keyring service name for API key |

### AgentConfig
| Field | Type | Description |
|-------|------|-------------|
| name | str | "claude-code" \| "opencode" |
| config_path | str | Detected config file path |
| configured | bool | Whether agent was modified |

### ConfigBackup
| Field | Type | Description |
|-------|------|-------------|
| timestamp | str | ISO 8601 timestamp of backup |
| path | str | Path to backup file |
| version | int | Config schema version at backup time |

## State Transitions

```
INITIAL → HARDWARE_DETECTED → MODELS_SELECTED → CONTAINER_STARTED
  → VLLM_DEPLOYED → PROVIDERS_CONFIGURED → AGENTS_CONFIGURED → READY

Any step → FAILED (with recovery instructions)
READY → RE-RUN (backup, then update) → UPDATED
UPDATED → RE-RUN → UPDATED (re-runnable cycle)
```
