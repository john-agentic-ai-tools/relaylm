---

description: "Task list for CLI Autoconfig feature"
---

# Tasks: CLI Autoconfig

**Input**: Design documents from `/specs/004-cli-autoconfig/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Test tasks are included per constitution Principle I (TDD is mandatory). Tests MUST be written before implementation and MUST fail initially.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Single project: `src/`, `tests/` at repository root
- CLI tool: commands in `src/relaylm/cli/`, logic in domain modules under `src/relaylm/`

---

## Phase 1: Setup (Dependency Update & Security Audit)

**Purpose**: Update all project dependencies to latest compatible versions and address known vulnerabilities per constitution mandate.

- [X] T001 Update all project dependencies to latest compatible versions in pyproject.toml
- [X] T002 Run `pip-audit` (or equivalent) to identify and fix known security vulnerabilities; document any deferred vulnerabilities with rationale

**Checkpoint**: Dependencies up to date, no unresolved high-severity vulnerabilities.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create shared data models and detection infrastructure that all user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Create pydantic schemas (CodingAgent, AutoconfigResult, ConfigChange) in src/relaylm/schemas/autoconfig.py
- [X] T004 [P] Refactor src/relaylm/agents/detector.py to expose pure detection functions (detect_agents() returning list of agent results) separate from config-writing logic

**Checkpoint**: Foundation ready — data models and detection API available for all user stories.

---

## Phase 3: User Story 1 — Autodiscover and configure detected agents (Priority: P1) 🎯 MVP

**Goal**: User runs `relaylm autoconfig`, CLI scans for agents, backs up config, registers detected agents in relaylm config, and displays a change summary with testing instructions.

**Independent Test**: Run `relaylm autoconfig` on a machine with at least one supported agent (OpenCode or Claude Code) installed; verify relaylm config is updated with agent entries and a timestamped backup exists.

### Tests for User Story 1 (TDD — write first, expect RED)

- [X] T005 [P] [US1] Write unit test for agent detection returning correct CodingAgent results in tests/unit/test_agent_detection.py
- [X] T006 [P] [US1] Write unit test for AutoconfigResult model serialization in tests/unit/test_autoconfig_result.py
- [X] T007 [US1] Write integration test for full autoconfig flow (detection → backup → config update → summary) in tests/integration/test_autoconfig_cli.py

### Implementation for User Story 1

- [X] T008 [US1] Implement detect_agents() in src/relaylm/agents/detector.py that scans for OpenCode and Claude Code using shutil.which() and known config paths
- [X] T009 [US1] Implement autoconfig core orchestration logic (scan → backup → config update → result) in src/relaylm/agents/detector.py
- [X] T010 [US1] Register `relaylm autoconfig` CLI command with --dry-run and --yes options in src/relaylm/cli/app.py
- [X] T011 [US1] Implement change summary display with detected agents, config changes, backup path, and testing instructions in src/relaylm/cli/app.py
- [X] T012 [US1] Add agents section to relaylm config format (detected agent metadata) in src/relaylm/config/loader.py or autoconfig.py

**Checkpoint**: User Story 1 complete — `relaylm autoconfig` finds agents, backs up config, updates relaylm config, and shows summary.

---

## Phase 4: User Story 2 — No supported agents found (Priority: P1)

**Goal**: When no supported agents are detected, the CLI displays a friendly message, lists OpenCode and Claude Code as supported tools, and makes no config changes.

**Independent Test**: Run `relaylm autoconfig` on a machine with no supported agents; verify output lists OpenCode and Claude Code, and verify config is unmodified with no backup created.

### Tests for User Story 2 (TDD — write first, expect RED)

- [X] T013 [P] [US2] Write unit test for no-agent detection path in tests/unit/test_agent_detection.py
- [X] T014 [US2] Write integration test for no-agent scenario (no config change, no backup) in tests/integration/test_autoconfig_cli.py

### Implementation for User Story 2

- [X] T015 [US2] Implement no-agent detection handler in src/relaylm/agents/detector.py that returns empty results with friendly message
- [X] T016 [US2] Wire no-agent handler into CLI output path in src/relaylm/cli/app.py (print supported tools, skip backup, exit 0)

**Checkpoint**: User Story 2 complete — `relaylm autoconfig` gracefully handles machines with no agents.

---

## Phase 5: User Story 3 — Revert autoconfig changes from backup (Priority: P2)

**Goal**: User runs a revert command that restores the pre-autoconfig config from the most recent backup.

**Independent Test**: Run `relaylm autoconfig` to create a backup, then run `relaylm autoconfig revert` and verify the config returns to its original state.

### Tests for User Story 3 (TDD — write first, expect RED)

- [X] T017 [P] [US3] Write unit test for revert finding most recent backup in tests/unit/test_autoconfig_result.py
- [X] T018 [US3] Write integration test for revert flow (backup exists → revert succeeds) in tests/integration/test_autoconfig_cli.py

### Implementation for User Story 3

- [X] T019 [US3] Implement `relaylm autoconfig revert` subcommand that finds and restores the most recent autoconfig backup in src/relaylm/cli/app.py
- [X] T020 [US3] Handle edge cases: no backup exists (print message, exit 0), revert shows which backup was used

**Checkpoint**: User Story 3 complete — users can revert autoconfig changes with a single command.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements, edge cases, and documentation.

- [X] T021 [P] Handle edge case: config file does not exist (create fresh config, no backup needed) in src/relaylm/agents/detector.py
- [X] T022 [P] Handle edge case: malformed agent detection (note agent found but config unreadable, continue) in src/relaylm/agents/detector.py
- [X] T023 [P] Handle edge case: backup directory unwritable (hard error, no changes made) in src/relaylm/config/backup.py
- [X] T024 [P] Handle edge case: duplicate backup timestamps (append suffix _001, _002 for uniqueness) in src/relaylm/config/backup.py
- [X] T025 [P] Run quickstart.md validation — verify all documented commands work end-to-end
- [X] T026 Run ruff linting and mypy type checking on all new/modified code

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - US1 and US2 are independent (can proceed in parallel)
  - US3 slightly builds on US1 (needs backup to exist), but revert logic is independent
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) — Fully independent of US1
- **User Story 3 (P2)**: Can start after US1 completes (backup must exist to test revert) — Standalone revert logic

### Within Each User Story

- Tests MUST be written and FAIL (RED) before implementation
- Pydantic models before services/logic
- Core logic before CLI wiring
- Story complete before moving to next

### Parallel Opportunities

- T003 and T004 can run in parallel (different modules)
- T005, T006, T007 can run in parallel (different test files)
- T010 and T011 can run in parallel (CLI registration vs output formatting)
- US1 and US2 phases can run in parallel after Phase 2 completes
- All Polish tasks marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Write unit test for agent detection in tests/unit/test_agent_detection.py"
Task: "Write unit test for AutoconfigResult model in tests/unit/test_autoconfig_result.py"

# Launch implementation after tests pass:
Task: "Implement detect_agents() in src/relaylm/agents/detector.py"
Task: "Register autoconfig command in src/relaylm/cli/app.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (dependency update + security audit)
2. Complete Phase 2: Foundational (schemas + detection refactor)
3. Complete Phase 3: User Story 1 (the core autoconfig flow)
4. **STOP and VALIDATE**: Run `relaylm autoconfig` end-to-end
5. Demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (autodiscover + configure) → Test independently → MVP!
3. Add User Story 2 (no-agent handling) → Test independently → Deliver
4. Add User Story 3 (revert) → Test independently → Deliver
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (autodiscover + configure)
   - Developer B: User Story 2 (no-agent handling) — fully independent
   - Developer C: Can start on revert helper in parallel
3. User Story 3 can be picked up after US1 creates backup infrastructure

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail (RED) before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Cross-platform agent detection (Windows, macOS, Linux) must be verified
- Constitution Principle I (TDD) is NON-NEGOTIABLE — all implementation tasks MUST have corresponding test tasks
