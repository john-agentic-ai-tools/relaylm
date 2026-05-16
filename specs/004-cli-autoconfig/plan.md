# Implementation Plan: CLI Autoconfig

**Branch**: `005-cli-autoconfig` | **Date**: 2026-05-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-cli-autoconfig/spec.md`

## Summary

Add a `relaylm autoconfig` command that scans the machine for installed coding
agents (OpenCode, Claude Code), creates a timestamped backup of relaylm's own
config, registers detected agents in relaylm's config, displays a change
summary with testing instructions, and provides a revert path via the existing
`relaylm config restore` command. This is a relaylm-only config change — agent
config files are never modified.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: typer (CLI), pyyaml (config), pydantic (data models)

**Storage**: Filesystem — `~/.config/relaylm/config.yml` (YAML), backups in
`~/.config/relaylm/backups/`

**Testing**: pytest with pytest-cov

**Target Platform**: Windows, macOS, Linux (cross-platform)

**Project Type**: CLI tool (Python package, pip-installable)

**Performance Goals**: Full autoconfig completes in under 5 seconds per SC-001

**Constraints**:
- Detection must work on Windows (PATH + known install dirs), macOS, and Linux
- Config backup must happen BEFORE any write
- Zero modification of agent-owned config files (FR-006)
- Exit code 0 for success, 1 for errors, 2 for bad args

**Scale/Scope**: Single-user CLI; no network calls, no server component

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Justification |
|-----------|--------|---------------|
| I. Test-First (NON-NEGOTIABLE) | PASS | All user stories have acceptance scenarios that map to test cases; TDD workflow applies |
| II. Python Best Practices | PASS | PEP 8, type hints, ruff, mypy all enforced by project config |
| III. UX Packaging | PASS | Feature is a pip-installable CLI command via typer entry point; text I/O for all output |
| IV. Simplicity (YAGNI) | PASS | Detection is two known agents; backup reuses existing module; revert reuses existing command |
| V. Quality & Observability | PASS | Text I/O for results, errors to stderr, structured logging for diagnostics |

**Result: ALL GATES PASS** — no violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/004-cli-autoconfig/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/relaylm/
├── cli/
│   └── app.py              # Add `autoconfig` command
├── agents/
│   └── detector.py          # Refactor: separate detection from config writing
├── config/
│   ├── backup.py            # Reuse as-is
│   └── loader.py            # Reuse as-is
└── schemas/
    └── autoconfig.py        # NEW: pydantic models for AutoconfigResult, etc.

tests/
├── unit/
│   ├── test_agent_detection.py
│   └── test_autoconfig_result.py
└── integration/
    └── test_autoconfig_cli.py
```

**Structure Decision**: Single Python package (existing pattern). New modules
only where separation of concerns demands it: `schemas/autoconfig.py` for
pydantic models, extended `cli/app.py` for the command, refactored
`agents/detector.py` for detection logic.

## Complexity Tracking

No constitution violations — this section is intentionally left blank.
