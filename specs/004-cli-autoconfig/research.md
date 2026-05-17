# Research: CLI Autoconfig

## 1. Agent Detection Strategies

### OpenCode Detection

- **Decision**: Check known config path `~/.config/opencode/opencode.json` + scan `PATH` for `opencode` executable
- **Rationale**: OpenCode stores its config at `~/.config/opencode/opencode.json` on all platforms. The binary may be at different locations depending on install method (pipx, brew, manual), so PATH scanning confirms installation
- **Alternatives considered**: Checking a hardcoded list of install directories is fragile across OS and versions

### Claude Code Detection

- **Decision**: Check known config path `~/.claude/settings.json` + check if `npx @anthropic-ai/claude-code` is available
- **Rationale**: Claude Code stores settings at `~/.claude/settings.json`. Some installs do not add a PATH entry, so `npx` availability is a reliable fallback
- **Alternatives considered**: Checking `which claude` is unreliable because Claude Code is often used via npx

### Cross-Platform Concerns

- **Windows**: Use `$env:APPDATA` and `$env:LOCALAPPDATA` for additional detection paths; `where.exe` in place of `which`
- **macOS/Linux**: `shutil.which()` from stdlib provides unified PATH scanning
- **Decision**: Use `shutil.which()` for PATH-based detection (stdlib, cross-platform), supplemented by known config file checks

## 2. Config Format for Agent Registration

### Current Config Structure
```yaml
version: 1
container_runtime: docker
models:
  - name: Qwen/Qwen2.5-7B-Instruct
    source: huggingface
    gpu_index: null
    args: {}
fallback:
  order:
    - local
    - anthropic
  timeout_seconds: 30
router:
  host: 127.0.0.1
  port: 8000
```

### Proposed Addition
```yaml
agents:
  opencode:
    detected: true
    version: "0.x"
    install_path: /home/user/.local/bin/opencode
    configured_at: "2026-05-15T10:30:00"
  claude-code:
    detected: true
    version: "latest"
    detected_via: npx
    configured_at: "2026-05-15T10:30:00"
```

- **Decision**: Add an `agents` section to config tracking detection metadata
- **Rationale**: Keeps agent registration in the existing config file, no new files needed
- **Alternatives considered**: Separate agents config file — adds complexity without benefit

## 3. Backup Integration

- **Decision**: Reuse `config/backup.py` as-is — `create_backup()` already does timestamped YAML backup
- **Rationale**: Existing restore command (`relaylm config restore`) already works with these backups
- **Edge cases**:
  - No existing config: skip backup, create fresh config with agent settings
  - Backup directory unwritable: hard error, no changes made

## 4. UX Pattern

- **Decision**: Follow the existing `relaylm setup` UX pattern — typer CLI, `typer.echo()` for output, `err=True` for errors
- **Rationale**: Consistency with the rest of the CLI; users already familiar with the style
- **Summary display format**:
  ```
  Autoconfig complete.

  Detected agents:
    ✅ OpenCode (v0.x) — /home/user/.local/bin/opencode
    ✅ Claude Code (via npx)

  Changes made to ~/.config/relaylm/config.yml:
    + agents.opencode = {"detected": true, ...}
    + agents.claude-code = {"detected": true, ...}
    + fallback.order[2] = "opencode"

  Backup saved: ~/.config/relaylm/backups/config-20260515T103000.yml

  To test:
    relaylm chat              # Verify OpenCode integration
    relaylm providers list    # Verify provider configuration

  To revert:
    relaylm config restore 20260515T103000
  ```

## 5. No-Agent Scenario

- **Decision**: Detect nothing → print friendly message listing OpenCode and Claude Code, no config changes, no backup
- **Rationale**: Matches US-2 acceptance criteria; no side effects when no agents found
