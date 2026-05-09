---

description: "Task list for AI Router Environment Setup"

---

# Tasks: AI Router Environment Setup

**Input**: Design documents from `specs/001-ai-router-setup/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Per constitution Principle I (Test-First Development), tests are MANDATORY and MUST be written before implementation. Tests MUST fail initially (Red-Green-Refactor).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Single project at repository root: `src/`, `tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure, pyproject.toml, and src/relaylm/ package skeleton
- [ ] T002 [P] Configure ruff, mypy, and pytest in pyproject.toml
- [ ] T003 [P] Create all module `__init__.py` files under src/relaylm/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Implement config loader (read/write/validate YAML) in src/relaylm/config/loader.py
- [ ] T005 [P] Implement config backup manager in src/relaylm/config/backup.py
- [ ] T006 [P] Implement keychain wrapper (system keychain + file fallback) in src/relaylm/providers/keychain.py
- [ ] T007 Implement hardware detector (RAM, CPU, GPU) in src/relaylm/hardware/detector.py
- [ ] T008 Implement container runtime detector and wrapper in src/relaylm/container/runtime.py
- [ ] T009 [P] Implement model selector (hardware-based selection logic) in src/relaylm/models/selector.py
- [ ] T010 [P] Implement Hugging Face model source in src/relaylm/models/source.py
- [ ] T011 Implement CLI app skeleton (typer app, --help) in src/relaylm/cli/app.py

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Single-Command Environment Bootstrap (Priority: P1) 🎯 MVP

**Goal**: Developer runs `relaylm setup` and gets a working local router with vLLM running auto-selected models.

**Independent Test**: Developer on 16 GB RAM Linux can run `relaylm setup --yes` and get a working `localhost:8000/v1/chat/completions` endpoint in under 10 minutes.

### Tests for User Story 1 (MANDATORY - TDD per constitution) 🔴

- [ ] T012 [P] [US1] Contract test for `relaylm setup` CLI in tests/contract/test_cli_setup.py
- [ ] T013 [P] [US1] Unit test for hardware detector in tests/unit/test_hardware_detector.py
- [ ] T014 [P] [US1] Unit test for model selector in tests/unit/test_model_selector.py
- [ ] T015 [P] [US1] Unit test for config loader in tests/unit/test_config_loader.py
- [ ] T016 [P] [US1] Integration test for container runtime detection in tests/integration/test_container_runtime.py
- [ ] T017 [US1] Integration test for vLLM container lifecycle in tests/integration/test_vllm_lifecycle.py

### Implementation for User Story 1

- [ ] T018 [P] [US1] Implement vLLM container manager in src/relaylm/container/vllm.py
- [ ] T019 [P] [US1] Implement `relaylm config` CLI subcommands (show, restore, path) in src/relaylm/cli/config.py
- [ ] T020 [US1] Implement `relaylm setup` CLI command in src/relaylm/cli/setup.py
- [ ] T021 [US1] Wire setup flow (detect → select → deploy → configure) in src/relaylm/cli/app.py
- [ ] T022 [US1] Implement `--yes`/`--non-interactive` flag support in setup flow

**Checkpoint**: At this point, `relaylm setup` produces a working local LLM endpoint

---

## Phase 4: User Story 2 - Configure External AI Providers (Priority: P2)

**Goal**: Developer runs `relaylm providers add openai --key sk-...` and the router can proxy requests to cloud providers.

**Independent Test**: After `relaylm providers add openai --key <key>`, the config file contains provider settings and the key is stored in the system keychain.

### Tests for User Story 2 (MANDATORY - TDD per constitution) 🔴

- [ ] T023 [P] [US2] Contract test for `relaylm providers add` CLI in tests/contract/test_cli_providers.py
- [ ] T024 [P] [US2] Unit test for keychain wrapper in tests/unit/test_keychain.py
- [ ] T025 [P] [US2] Unit test for provider manager in tests/unit/test_provider_manager.py
- [ ] T026 [US2] Integration test for provider config persistence in tests/integration/test_providers.py

### Implementation for User Story 2

- [ ] T027 [P] [US2] Implement provider manager CRUD in src/relaylm/providers/manager.py
- [ ] T028 [US2] Implement `relaylm providers add` CLI in src/relaylm/cli/app.py
- [ ] T029 [US2] Wire provider keychain storage and config write into setup flow

**Checkpoint**: At this point, both local and cloud providers can be configured

---

## Phase 5: User Story 3 - Auto-Configure Coding Agents (Priority: P3)

**Goal**: After setup, Claude Code and OpenCode are automatically configured to use the local router.

**Independent Test**: Developer with Claude Code installed runs `relaylm setup` then checks `~/.claude/settings.json` — the `customApiUrl` points at `http://localhost:8000`.

### Tests for User Story 3 (MANDATORY - TDD per constitution) 🔴

- [ ] T030 [P] [US3] Unit test for Claude Code config detection in tests/unit/test_agent_detector.py
- [ ] T031 [P] [US3] Unit test for OpenCode config detection in tests/unit/test_agent_detector.py

### Implementation for User Story 3

- [ ] T032 [P] [US3] Implement agent detector (Claude Code + OpenCode) in src/relaylm/agents/detector.py
- [ ] T033 [US3] Wire agent auto-configuration into the setup flow in src/relaylm/cli/setup.py

**Checkpoint**: Coding agents automatically use the local router

---

## Phase 6: User Story 4 - Manual Model Override (Priority: P3)

**Goal**: Developer can provide `--models "llama3-8b,mistral-7b"` to override auto-detected models.

**Independent Test**: Developer runs `relaylm setup --models "llama3-8b,mistral-7b" --yes` and only those models are deployed.

### Tests for User Story 4 (MANDATORY - TDD per constitution) 🔴

- [ ] T034 [P] [US4] Unit test for model override validation in tests/unit/test_model_selector.py
- [ ] T035 [US4] Contract test for `--models` flag in tests/contract/test_cli_setup.py

### Implementation for User Story 4

- [ ] T036 [P] [US4] Add `--models` CLI option parsing in src/relaylm/cli/setup.py
- [ ] T037 [US4] Wire model override through selector to skip auto-detection path

**Checkpoint**: All user stories complete and independently testable

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T038 Run quickstart.md validation end-to-end
- [ ] T039 [P] Add comprehensive `--help` text and docstrings across all modules
- [ ] T040 [P] Add structured logging to all modules per constitution Principle V
- [ ] T041 Run full test suite and fix all failures
- [ ] T042 Finalize pyproject.toml metadata for PyPI publishing
- [ ] T043 Remove all placeholder comments and TODO markers from source files

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 (Phase 3) → US2 (Phase 4) (US2 builds on US1's config)
  - US3 (Phase 5) depends on US1 (needs running router)
  - US4 (Phase 6) depends on US1 (modifies bootstrap flow)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Core modules before CLI wiring
- Story complete before moving to next priority

### Parallel Opportunities

- All Phase 1 tasks marked [P] can run in parallel
- All Phase 2 tasks marked [P] can run in parallel
- Within each story: tests marked [P] can run in parallel
- Within each story: implementation tasks marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for relaylm setup CLI in tests/contract/test_cli_setup.py"
Task: "Unit test for hardware detector in tests/unit/test_hardware_detector.py"
Task: "Unit test for model selector in tests/unit/test_model_selector.py"
Task: "Unit test for config loader in tests/unit/test_config_loader.py"
Task: "Integration test for container runtime detection in tests/integration/test_container_runtime.py"

# Launch all parallel implementation tasks:
Task: "Implement vLLM container manager in src/relaylm/container/vllm.py"
Task: "Implement relaylm config CLI subcommands in src/relaylm/cli/config.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test US1 independently — `relaylm setup` produces working endpoint
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (MVP) → Test independently → Working local router
3. Add US2 (providers) → Cloud fallback works
4. Add US3 (agents) → Coding agents auto-configured
5. Add US4 (model override) → Advanced customization
