# Implementation Plan: CI/CD Pipeline

**Branch**: `003-ci-cd-pipeline` | **Date**: 2026-05-09 | **Spec**: specs/003-ci-cd-pipeline/spec.md
**Input**: Feature specification from specs/003-ci-cd-pipeline/spec.md

## Summary

Create a complete CI/CD pipeline for RelayLM using GitHub Actions with five parallel quality gates (lint, security, deps, tests, docs), a release pipeline with PyPI version safety checks, documentation sync validation, and a branch protection setup script. All gates run in parallel on PRs; the release pipeline gates publishing on all gates passing plus version uniqueness.

## Technical Context

**Language/Version**: YAML (GitHub Actions), Python 3.11+ (helper scripts), Shell (setup script)
**Primary Dependencies**: GitHub Actions (CI/CD platform), semgrep (security scanning), ruff/pytest/mypy (existing)
**Storage**: `.github/workflows/` (workflows), `.semgrep/` (rules), `scripts/` (helper scripts)
**Testing**: pytest for Python helper scripts; manual verification of workflows via GitHub
**Target Platform**: GitHub Actions (ubuntu-latest)
**Project Type**: CI/CD configuration + utility scripts
**Performance Goals**: CI completes in under 5 minutes; release completes in under 10 minutes
**Constraints**: All gates must run in parallel on CI; release must fail fast on duplicate version; docs must match actual CLI output
**Scale/Scope**: 2 workflow files, 3-5 helper scripts, ~10 semgrep rules, 1 branch protection script

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **TDD Compliance**: REQUIRED. Helper Python scripts (check-version.py, check-docs-sync.py) MUST have tests written BEFORE implementation. Workflow YAML and shell scripts are tested via integration/CI, not unit tests.
- **Simplicity Review**: Workflow files follow standard GitHub Actions patterns. Helper scripts are single-purpose with stdlib dependencies only. No framework or abstraction added.
- **Python Standards**: Helper scripts use Python 3.11+ stdlib only, with type hints and docstrings. No external dependencies needed.
- **Packaging Ready**: Helper scripts are standalone, not part of the pip package. They live in `scripts/` alongside the project, not in `src/`.
- **Quality Gates**: The pipeline IS the quality gate system. All gates must pass before merge.

**Gate Status**: PASS

## Project Structure

### CI/CD Artifacts (this feature)

```text
.github/workflows/
├── ci.yml                  # US1: CI pipeline on PR/push
└── release.yml             # US2: Release pipeline with version safety

.semgrep/
├── semgrep.yml             # US1: Default semgrep ruleset

scripts/
├── check-version.py        # US2: PyPI version check (TDD: tests/)
├── check-docs-sync.py      # US3: Docs vs CLI sync check (TDD: tests/)
└── setup-branch-protection.sh  # US4: Branch protection automation

tests/
├── unit/
│   ├── test_check_version.py   # Tests for check-version.py
│   └── test_check_docs_sync.py # Tests for check-docs-sync.py
└── integration/
    └── test_ci_workflow.py     # Optional: validate workflow YAML structure
```

### Spec Directory

```text
specs/003-ci-cd-pipeline/
├── plan.md              # This file
├── research.md          # Phase 0 - Project inventory and decisions
├── data-model.md        # Phase 1 - Entities and relationships
├── contracts/           # Phase 1 - Dev scripts and workflow format contracts
│   ├── dev-scripts.md
│   └── workflow-format.md
├── quickstart.md        # Phase 1 - Quick reference
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 - Task breakdown
```

**Structure Decision**: Standard GitHub Actions layout with `.github/workflows/` for workflow files, `.semgrep/` for Semgrep rules, and `scripts/` for helper scripts. This follows GitHub conventions and keeps infrastructure separate from application code.

## Complexity Tracking

> **TDD mandate**: Two Python scripts require unit tests written first. This is tracked in tasks with explicit test-first ordering.
> **No constitution violations**: All scripts are single-purpose, stdlib-only, and follow existing project conventions.

## Implementation Order

1. Phase 1: Create directory structure and Semgrep rules (no tests needed)
2. Phase 2: Write CI workflow (ci.yml) — all quality gates
3. Phase 3: Write helper scripts with tests (TDD: tests first)
4. Phase 4: Write release workflow (release.yml) with version check
5. Phase 5: Write branch protection script
6. Phase 6: Final integration and quality gate verification
