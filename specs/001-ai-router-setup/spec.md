# Feature Specification: AI Router Environment Setup

**Feature Branch**: `001-ai-router-setup`
**Created**: 2026-05-09
**Status**: Draft
**Input**: User description: "Easy to use cli that will allow developer to run a single command and configure docker or podman, setup vllm with several models..."

## Clarifications

### Session 2026-05-09

- Q: How are provider API keys stored securely? → A: System keychain (platform-native) with config file fallback + permissions warning.
- Q: Is `relaylm setup` safe to re-run / is it idempotent? → A: Yes, re-runnable as an update; config is backed up before modification to enable restoration of prior versions.
- Q: Where are model weights sourced from for vLLM? → A: Hugging Face by default, with a configurable model source override in the configuration file.
- Q: Which container runtime is preferred when both Docker and Podman are installed? → A: Podman preferred when both installed; Docker used if only Docker present; install Podman if neither exists.
- Q: Should setup support a non-interactive / CI mode? → A: Yes, via `--yes` / `--non-interactive` flag.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Single-Command Environment Bootstrap (Priority: P1)

A developer wants to set up a local AI routing environment on their machine.
They run a single CLI command. The tool automatically detects their hardware
(RAM, CPU cores, GPU presence and VRAM), selects appropriate models that fit
their resources, detects an available container runtime (Docker or Podman),
configures vLLM with the selected models, and produces a working configuration
file. The developer does not need to know about vLLM, container runtimes, or
model sizing — it just works.

**Why this priority**: This is the core value proposition — zero-friction setup
that removes all manual configuration steps. Everything else builds on top of
this foundation.

**Independent Test**: A developer on a machine with at least 16 GB RAM can run
`relaylm setup` and have a working local LLM endpoint within 10 minutes,
verified by sending a test prompt to the router and receiving a response.

**Acceptance Scenarios**:

1. **Given** a machine with Docker or Podman installed, **When** the developer
   runs `relaylm setup`, **Then** the tool detects the container runtime,
   pulls the vLLM image, starts a container with 1-2 auto-selected models,
   and outputs the local endpoint URL.

2. **Given** a machine with an NVIDIA GPU (8 GB+ VRAM), **When** the developer
   runs `relaylm setup`, **Then** the tool detects GPU availability and selects
   GPU-compatible models optimized for the available VRAM.

3. **Given** a machine without Docker or Podman, **When** the developer runs
   `relaylm setup`, **Then** the tool detects no container runtime and
   provides clear installation instructions for Docker.

---

### User Story 2 - Configure External AI Providers (Priority: P2)

A developer wants their local router to fall back to cloud providers when
local models cannot handle a request. The developer provides API keys for
Anthropic and OpenAI through the CLI or config file. The router is configured
to route requests to local models first, with configurable fallback to
external providers.

**Why this priority**: Provider routing unlocks the full value of the router —
local models for speed/privacy and cloud models for capability — but the setup
can still function without it.

**Independent Test**: A developer configures an OpenAI API key, sends a
request to the router, and the router proxies it to OpenAI when no local
model matches. Response from OpenAI is returned transparently.

**Acceptance Scenarios**:

1. **Given** the environment is already set up, **When** the developer runs
   `relaylm providers add --provider openai --key <key>`, **Then** the OpenAI
   provider is configured and the router can proxy requests to OpenAI.

2. **Given** multiple providers configured, **When** a request arrives that
   no local model can serve, **Then** the router tries providers in priority
   order and returns the first successful response.

---

### User Story 3 - Auto-Configure Coding Agents (Priority: P3)

A developer using Claude Code or OpenCode wants these agents to automatically
use the local router as their LLM endpoint. After running the setup command,
the tool detects installed coding agents and configures them to point at the
router without manual intervention.

**Why this priority**: This is a convenience layer that completes the workflow
but is not essential — developers can manually configure their agents.

**Independent Test**: A developer with Claude Code installed runs `relaylm
setup`, inspects their Claude Code config, and confirms it now points to the
local router endpoint.

**Acceptance Scenarios**:

1. **Given** Claude Code is installed, **When** setup completes, **Then** the
   tool detects the Claude Code config file and sets its API base URL to the
   local router endpoint.

2. **Given** OpenCode is installed, **When** setup completes, **Then** the
   tool detects the OpenCode config file and sets its API base URL to the
   local router endpoint.

---

### User Story 4 - Manual Model Override (Priority: P3)

A developer has specific model requirements or wants to override the
auto-selected models. They provide a list of models via the command line or
config file, and the tool uses their list instead of auto-detecting.

**Why this priority**: Auto-detection covers most users; manual override is
for advanced users who know exactly what they need.

**Independent Test**: A developer runs `relaylm setup --models
"llama3-8b,mistral-7b"` and only those models are deployed, regardless of
what auto-detection would have selected.

**Acceptance Scenarios**:

1. **Given** a developer provides `--models "llama3-8b,mistral-7b"`,
   **When** setup runs, **Then** only the specified models are deployed to
   vLLM.

2. **Given** a developer provides an empty or invalid model name,
   **When** setup validates the model list, **Then** the tool displays an
   error listing the invalid models and exits.

---

### Edge Cases

- What happens when the machine has insufficient RAM or VRAM for even the
  smallest registered model? Resolved: setup exits with a clear "no local
  model fits your available VRAM" message and points the user at
  `relaylm providers add anthropic|openai` for cloud-only mode.
- How does the system handle multiple GPU configurations (e.g., 2 GPUs with
  different VRAM)?
- What happens if Docker daemon is installed but not running?
- How does the tool handle Podman rootless vs rootful mode?
- What if both Docker and Podman are installed? Resolved: prefer Podman when both present; use Docker if only Docker is installed; install Podman if neither exists.
- How are API keys stored securely? Resolved: system keychain (platform-native) with config file fallback; config file gets restricted permissions (0600) and a warning.
- In non-interactive mode (`--yes`), how are destructive operations (model
  downloads, container pulls) handled? All proceed with defaults; errors
  fail with exit code and stderr message.
- How can a developer restore a previous configuration after a bad update?
  Tool keeps timestamped backups in `~/.config/relaylm/backups/` and
  supports `relaylm config restore --list` and `--restore <timestamp>`.
- What if a coding agent's config file is in a non-standard location?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: CLI MUST provide a single `setup` command that performs all
  bootstrap steps, with a `--yes` / `--non-interactive` flag to auto-accept
  defaults in unattended/CI environments.
- **FR-002**: CLI MUST detect available RAM, CPU core count, and GPU
  presence with VRAM.
- **FR-003**: CLI MUST select appropriate models based on detected hardware
  using predefined sizing rules.
- **FR-004**: CLI MUST detect available container runtimes and select
  Podman over Docker when both are present; install Podman if neither
  exists.
- **FR-005**: CLI MUST configure vLLM with the selected models inside the
  detected container runtime.
- **FR-006**: CLI MUST generate a configuration file at a standard location
  (e.g., `~/.config/relaylm/config.yml`).
- **FR-007**: CLI MUST support a `providers add` subcommand to configure
  external AI providers (Anthropic, OpenAI) with API keys.
- **FR-008**: CLI MUST detect installed coding agents (Claude Code,
  OpenCode) and configure them to use the local router as their API
  endpoint.
- **FR-009**: CLI MUST support `--models` flag to override auto-detected
  model selection.
- **FR-010**: Configuration file MUST support defining fallback order
  (local models first, then provider chain).
- **FR-011**: CLI MUST validate that all configured models and providers
  are reachable before marking setup complete.
- **FR-012**: CLI MUST output clear error messages with suggested fixes
  when any step fails (missing runtime, insufficient RAM, invalid model
  name, etc.).
- **FR-013**: CLI MUST store provider API keys using the platform-native
  system keychain by default, with config file storage as a warned fallback.
- **FR-014**: CLI MUST create a timestamped backup of the configuration
  file before any modification, enabling restore of prior versions.
- **FR-015**: CLI MUST source models from Hugging Face by default, with a
  configurable model source override in the configuration file.
- **FR-016**: CLI MUST offer to install Podman automatically when no
  container runtime is detected, with a clear explanation before
  proceeding.

### Key Entities

- **Hardware Profile**: Detected system capabilities (RAM, CPU cores, GPU
  model/VRAM, container runtime availability).
- **Model Selection**: List of models chosen for deployment, either
  auto-selected from hardware or user-specified. Auto-selection is
  **memory-aware** — it consults a curated registry of model
  architectural numbers (parameter count, hidden size, layer count,
  dtype) and the host's measured **free** GPU VRAM, picking the largest
  registered model whose weights + activations + KV cache at a 2048-token
  minimum context fit within a safety margin of available VRAM. vLLM
  runtime flags (`--gpu-memory-utilization`, `--max-model-len`,
  `--max-num-seqs`) are computed from the same inputs; users may
  override them via CLI flags for advanced tuning.
- **Configuration File**: Persistent YAML/TOML file storing all settings:
  models, providers, fallback order, container runtime preference.
  Timestamped backups kept in `~/.config/relaylm/backups/` before each
  modification.
- **Provider Config**: External AI provider credentials (Anthropic, OpenAI)
  with API keys (stored in system keychain by default), base URLs, and
  priority for fallback routing.
- **Agent Config**: Detected coding agent (Claude Code, OpenCode) with its
  config file path and current API endpoint settings.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer on a standard Linux workstation (16 GB RAM, no GPU)
  can complete setup and send their first local LLM request in under 10
  minutes.
- **SC-002**: A developer with an NVIDIA GPU (8 GB+ VRAM) has GPU-accelerated
  models deployed automatically without any manual configuration.
- **SC-003**: Developers can configure up to 3 external providers in under
  2 minutes using CLI commands.
- **SC-004**: 90% of developers with Claude Code or OpenCode installed have
  their agent auto-configured to use the local router on first setup.
- **SC-005**: All error conditions (missing runtime, insufficient RAM,
  invalid model, no local model fits the available VRAM) produce
  actionable error messages that let the developer resolve the issue
  without external documentation. The "no model fits" case explicitly
  surfaces the cloud-provider fallback command.

## Out of Scope

- The router runtime (RelayLM proxy/server) — this tool only configures it
- Model training, fine-tuning, or custom model development
- Native Windows Python support (WSL2 is the supported path on Windows)
- GUI or web dashboard — CLI only
- Cloud deployment or remote server orchestration
- Multi-node / cluster / Kubernetes setups
- Monitoring dashboards or usage analytics
- User management or multi-tenant isolation

## Assumptions

- Developers are on Linux, macOS, or Windows via WSL2.
- Developers have sudo or equivalent access for container runtime setup.
- Developers have an internet connection for pulling container images and
  model weights on first run.
- At least 8 GB of free RAM is available to run the smallest local model.
- Docker or Podman is either already installed or the developer is willing
  to install one.
- Developers using external providers (Anthropic, OpenAI) already have API
  keys from those services.
- Claude Code and OpenCode follow standard config file conventions for the
  user's platform.
- The "router" component is part of the RelayLM project and will expose a
  standard OpenAI-compatible API endpoint for agents to connect to.
