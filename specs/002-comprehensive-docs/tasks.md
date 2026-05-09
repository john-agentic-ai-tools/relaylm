---

description: "Task list for Comprehensive Project Documentation"

---

# Tasks: Comprehensive Project Documentation

**Input**: Design documents from `specs/002-comprehensive-docs/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL for this feature (documentation-only — no code changes). The spec does not include explicit test tasks.

**Organization**: Tasks are grouped by user story to enable independent implementation and validation of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Single project at repository root: `README.md`, `LICENSE`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `docs/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the documentation environment and verify CLI accuracy

- [X] T001 Create `docs/` directory at repository root
- [X] T002 [P] Run CLI verification against research.md — confirm all commands and flags documented in research.md match actual `relaylm` output
- [ ] T003 [P] Install and configure markdownlint for documentation validation
- [ ] T004 [P] Install and configure spell checker for documentation validation

**Checkpoint**: Environment ready — documentation writing can begin

---

## Phase 2: User Story 1 - Quick Start via README (Priority: P1) 🎯 MVP

**Goal**: A developer discovering RelayLM can read the README and immediately understand what the project does, how to install it, and how to run the basic `relaylm setup` command.

**Independent Test**: A developer unfamiliar with the project can read the README and successfully run `relaylm --help` and `relaylm setup --help` without referring to any other documentation.

### Implementation for User Story 1

- [X] T005 [P] [US1] Create README.md with project name, description, and key benefits at repository root
- [X] T006 [P] [US1] Add installation prerequisites section to README.md (Python 3.11+, Podman/Docker)
- [X] T007 [P] [US1] Add install commands section to README.md (pip, uv tool install, from source)
- [X] T008 [P] [US1] Add quick start example to README.md with `relaylm setup --yes` and expected output
- [X] T009 [US1] Add next steps section to README.md linking to user guide, providers, and agents docs
- [X] T010 [US1] Add badge row to README.md (Python version, license, CI status)

**Checkpoint**: README.md is complete and can serve as the project's primary entry point

---

## Phase 3: User Story 2 - Detailed Installation & User Guide (Priority: P1)

**Goal**: A developer can follow a step-by-step guide covering installation through all configuration options.

**Independent Test**: A developer following the guide can go from a clean system to a fully configured local AI router with a cloud provider fallback and auto-configured coding agents.

### Implementation for User Story 2

- [X] T011 [P] [US2] Create docs/guide.md with table of contents and hardware requirements section
- [X] T012 [P] [US2] Add installation section to docs/guide.md covering all install methods with commands
- [X] T013 [P] [US2] Add container runtime section to docs/guide.md with Podman and Docker installation for Linux and macOS
- [X] T014 [P] [US2] Add basic setup walkthrough to docs/guide.md covering `relaylm setup` with all options (`--models`, `--runtime`, `--port`, `--yes`)
- [X] T015 [P] [US2] Add provider configuration section to docs/guide.md covering `relaylm providers add` with interactive and non-interactive usage
- [X] T016 [P] [US2] Add agent configuration section to docs/guide.md explaining how `relaylm agents` auto-detects and configures Claude Code and OpenCode
- [X] T017 [P] [US2] Add configuration management section to docs/guide.md covering `relaylm config show`, `config path`, and `config restore`
- [X] T018 [P] [US2] Add troubleshooting section to docs/guide.md covering common issues (container runtime not found, GPU not detected, API key errors, port conflicts)
- [X] T019 [P] [US2] Create docs/config.md as supporting configuration reference document
- [X] T020 [US2] Add cross-links between docs/guide.md and supporting docs (docs/config.md)

**Checkpoint**: docs/guide.md is complete with cross-linked supporting documents

---

## Phase 4: User Story 3 - Contribution Guide (Priority: P2)

**Goal**: A developer who wants to contribute can read a CONTRIBUTING guide explaining the development workflow, testing requirements, coding standards, and PR process.

**Independent Test**: A new contributor can set up a development environment, run the full test suite, and submit a pull request following the guide.

### Implementation for User Story 3

- [X] T021 [P] [US3] Create CONTRIBUTING.md with development setup instructions (clone, venv, install dev deps)
- [X] T022 [P] [US3] Add testing instructions to CONTRIBUTING.md (run pytest, ruff check, mypy)
- [X] T023 [P] [US3] Add coding standards section to CONTRIBUTING.md (PEP 8, type hints, TDD per constitution)
- [X] T024 [US3] Add pull request process section to CONTRIBUTING.md (submission steps, PR description, review process)

**Checkpoint**: CONTRIBUTING.md is complete and enables new contributors

---

## Phase 5: User Story 4 - License & Code of Conduct (Priority: P3)

**Goal**: The project includes a LICENSE file with MIT license and a CODE_OF_CONDUCT file establishing community standards.

**Independent Test**: A user can open the LICENSE file and understand the terms under which the project is distributed.

### Implementation for User Story 4

- [X] T025 [P] [US4] Create LICENSE file with MIT license text at repository root
- [X] T026 [P] [US4] Create CODE_OF_CONDUCT.md with Contributor Covenant v2.1 at repository root

**Checkpoint**: Legal and community documents are in place

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Quality assurance and consistency checks across all documents

- [ ] T027 [P] Run markdownlint on all documentation files and fix any formatting issues
- [ ] T028 [P] Run spell check on all documentation files and fix any spelling errors
- [ ] T029 [P] Verify all internal cross-links between documents resolve correctly
- [ ] T030 [P] Verify all CLI commands and flags referenced in documentation exist in the actual tool (cross-reference with research.md)
- [ ] T031 [P] Verify consistent terminology and formatting across all documents (per FR-018 and document-format.md contract)
- [X] T032 Run full quality gate: ruff check, mypy, pytest — confirm no regressions from documentation changes
- [X] T033 Update AGENTS.md to reference completed documentation artifacts

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **User Story 1 (Phase 2)**: Depends on Setup (T002 CLI verification)
- **User Story 2 (Phase 3)**: Depends on Setup (T002 CLI verification). Independent from US1 but can be validated together
- **User Story 3 (Phase 4)**: Depends on Setup. Reference project constitution and existing tooling — independent
- **User Story 4 (Phase 5)**: No dependencies — can be done anytime. Standard boilerplate documents
- **Polish (Phase 6)**: Depends on all user stories (Phases 2-5)

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories — can start after Phase 1
- **User Story 2 (P1)**: No dependencies on other stories — can start after Phase 1
- **User Story 3 (P2)**: No dependencies on other stories — can start after Phase 1
- **User Story 4 (P3)**: No dependencies — can be done in parallel with any phase

### Within Each User Story

- Documents within a story marked [P] can be created in parallel
- Content sections within a document should flow logically
- Cross-linking between stories should reference already-created files

### Parallel Opportunities

- All Phase 1 tasks marked [P] can run in parallel
- All user story documents marked [P] can run in parallel
- US4 (LICENSE + CODE_OF_CONDUCT) can run at any time since they require no context

---

## Parallel Example: User Stories 1 + 2 + 4

```bash
# Launch all independent documents together:
Task: "Create README.md with project description and install instructions"
Task: "Create docs/guide.md with table of contents and hardware requirements"
Task: "Create LICENSE with MIT license text"
Task: "Create CODE_OF_CONDUCT.md with Contributor Covenant v2.1"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: User Story 1 (README)
3. **STOP and VALIDATE**: Test US1 independently — README covers install + quick start
4. Deploy/demo if ready

### Incremental Delivery

1. Setup + US1 (README) → README exists as project entry point
2. Add US3 (CONTRIBUTING) → Contributors have guidance
3. Add US4 (LICENSE + CODE_OF_CONDUCT) → Legal and community standards in place
4. Add US2 (User Guide) → Production-quality documentation complete
5. Polish pass → Quality verified

### Parallel Team Strategy

1. Developer A: US1 (README)
2. Developer B: US2 (User Guide)
3. Developer C: US3 (CONTRIBUTING) + US4 (LICENSE/CODE_OF_CONDUCT)
4. All documents written in parallel, then cross-linked and polished

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- All CLI commands must be verified against the actual tool (FR-017)
- Documents must follow the format contract in contracts/document-format.md
- No code changes are required — this is a documentation-only feature
