# Configuration File Schema

**Location**: `~/.config/relaylm/config.yml`
**Format**: YAML
**Backups**: `~/.config/relaylm/backups/config-<ISO_TIMESTAMP>.yml`

## Schema (v1)

```yaml
version: 1                            # Schema version (int, required)
container_runtime: podman             # "podman" | "docker" (string, required)
models:                               # List of deployed models (array)
  - name: Qwen/Qwen3-0.6B             #   Model ID / name (string, required)
    source: huggingface                #   "huggingface" | custom URL (string)
    gpu_index: ~                       #   GPU device index or null for CPU
    args: {}                          #   Extra vLLM args (dict, optional)
providers:                            # External provider configs (dict)
  anthropic:                          #   Provider key name
    enabled: false                    #   Active flag (bool, required)
    base_url: https://api.anthropic.com/v1  # API endpoint (string)
    keychain_service: relaylm-anthropic     # Keyring service name (string)
  openai:                             #   Same structure
    enabled: false
    base_url: https://api.openai.com/v1
    keychain_service: relaylm-openai
fallback:                             # Fallback routing config (dict)
  order: [local, anthropic, openai]   #   Priority-ordered list (array)
  timeout_seconds: 30                 #   Per-provider timeout (int)
router:                               # Router bind config (dict)
  host: 127.0.0.1                     #   Bind address (string)
  port: 8000                          #   Bind port (int)
```

## Validation Rules

- `version` MUST be present and match the expected schema version
- `container_runtime` MUST be "podman" or "docker"
- `models` MUST contain at least one entry (or be empty for cloud-only)
- Each model `name` MUST be non-empty
- `fallback.order` MUST include at least one entry
- Unknown keys MUST be preserved (forward compatibility)

## Migration

When `version` changes on write:
1. Create backup of old config with current timestamp
2. Write new config with incremented version
3. On read, if version differs: warn user, suggest `config restore`
