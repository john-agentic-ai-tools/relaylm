<!--
  Sync Impact Report
  Version change: template → 1.0.0
  Principles created (all 5):
    - I. Test-First Development (NON-NEGOTIABLE)
    - II. Python Best Practices
    - III. UX Packaging
    - IV. Simplicity (YAGNI)
    - V. Quality & Observability
  Sections added: Technology Stack, Development Workflow
  Sections removed: None
  Templates updated:
    - ✅ .specify/templates/plan-template.md (Constitution Check gates)
    - ✅ .specify/templates/tasks-template.md (tests MANDATORY, updated headers)
    - ✅ .opencode/command/speckit.tasks.md (tests MANDATORY)
    - ✅ .specify/templates/spec-template.md (reviewed - no changes needed)
    - ✅ Command files (reviewed - no outdated references)
  Deferred items: None
-->

# RelayLM Constitution

## Core Principles

### I. Test-First Development (NON-NEGOTIABLE)

TDD is mandatory for all features. Tests MUST be written before implementation
code, MUST fail initially (Red phase), and MUST pass only after implementation
(Green phase). Refactoring is permitted only after tests pass. No code is
considered complete without corresponding tests. This applies to all layers:
unit, contract, and integration tests.

### II. Python Best Practices

All development MUST follow PEP 8, use type hints for all public APIs, and
adopt modern Python packaging via pyproject.toml. Prefer the standard library
when possible. Dependencies MUST be declared explicitly in pyproject.toml with
pinned or range-constrained versions. Use ruff for linting and mypy for type
checking.

### III. UX Packaging

Features MUST be delivered as pip-installable Python packages with CLI entry
points defined in pyproject.toml. Every package MUST expose its functionality
through a well-defined CLI interface using text I/O: stdin/args for input,
stdout for structured output, stderr for diagnostics. Sensible defaults and
clear help text are required — users should not need to read documentation
for basic usage.

### IV. Simplicity (YAGNI)

Start simple and avoid premature abstraction. Every component, layer, or
dependency MUST justify its existence. Favor flat over nested, explicit over
implicit, and concrete over generic. If a feature or abstraction is not needed
now, do not add it. Complexity MUST be documented and justified in the
implementation plan's Complexity Tracking section.

### V. Quality & Observability

Text I/O ensures debuggability by design. Structured logging MUST be used for
all production-adjacent code. All errors MUST go to stderr with descriptive
messages. Linting (ruff) and type checking (mypy) MUST pass before any code
is merged. Integration tests are required for contract changes and inter-
service communication.

## Technology Stack

- Language: Python 3.11+
- Testing: pytest with coverage
- Packaging: pyproject.toml (setuptools or hatchling)
- Linting: ruff
- Type Checking: mypy
- CI: GitHub Actions (or equivalent) enforcing lint, type, and test gates

## Development Workflow

All development MUST start from a feature branch. Commits MUST be granular and
atomic. Tests MUST pass on CI before merge. Pull requests MUST include test
evidence (test output showing Red before implementation, Green after). The
Constitution Check in the implementation plan MUST be evaluated at both the
start and end of the design phase.

## Governance

This Constitution supersedes all other development practices. Amendments
MUST be proposed as a change to this document with:
1. Rationale for the change
2. Impact analysis on existing principles
3. Migration plan for any affected artifacts

Versioning follows semver:
- MAJOR: Backward incompatible governance/principle removals or redefinitions
- MINOR: New principle/section added or materially expanded guidance
- PATCH: Clarifications, wording, typo fixes, non-semantic refinements

All pull requests and reviews MUST verify compliance with this Constitution.
Complexity MUST be justified per Principle IV. Use `AGENTS.md` for runtime
development guidance.

**Version**: 1.0.0 | **Ratified**: 2026-05-09 | **Last Amended**: 2026-05-09
