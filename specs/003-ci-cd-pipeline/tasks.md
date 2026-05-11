---

description: "Task list for CI/CD Pipeline"

---

# Tasks: CI/CD Pipeline

**Input**: Design documents from `specs/003-ci-cd-pipeline/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED for Python helper scripts (check-version.py, check-docs-sync.py). Tests MUST be written BEFORE implementation (TDD per constitution).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Workflows: `.github/workflows/`
- Semgrep rules: `.semgrep/`
- Helper scripts: `scripts/`
- Tests: `tests/unit/`

---

## Phase 1: Directory Structure & Foundation

**Purpose**: Create directories and foundational config files that don't need tests

- [ ] T001 Create `.github/workflows/` directory
- [ ] T002 Create `.semgrep/` directory
- [ ] T003 Create `scripts/` directory
- [ ] T004 [P] Create `.semgrep/semgrep.yml` with Python security rules (insecure subprocess, eval, request without timeout, hardcoded secrets, SQL injection, pickle deserialization, yaml load without loader, tmpfile races, assert usage, debug=True in production)

**Checkpoint**: Directory structure ready, semgrep rules in place

---

## Phase 2: CI Workflow (User Story 1)

**Goal**: CI pipeline runs all five quality gates in parallel on PR/push

**Independent Test**: Push a branch and open a PR — five status checks appear within 5 minutes.

- [ ] T005 [P] [US1] Create `.github/workflows/ci.yml` with trigger events (push, pull_request, workflow_dispatch)
- [ ] T006 [P] [US1] Add `lint` job: checkout, setup Python, pip install .[dev], run `ruff check src/ tests/`
- [ ] T007 [P] [US1] Add `security` job: checkout, setup Python, pip install semgrep, run `semgrep --config=.semgrep/ src/`
- [ ] T008 [P] [US1] Add `deps` job: checkout, setup Python, pip install .[dev], run `pip-audit` on installed packages
- [ ] T009 [P] [US1] Add `tests` job: checkout, setup Python, pip install .[dev], run `pytest --cov=src/ --cov-report=term-missing`
- [ ] T010 [P] [US1] Add `docs` job: checkout, setup Python, install markdownlint-cli and codespell, run lint + spell + docs-sync checks
- [ ] T011 [US1] Wire all five jobs in parallel with no `needs` dependencies — each reports independent status

**Checkpoint**: CI workflow complete — pushing a branch triggers all five gates

---

## Phase 3: Helper Scripts with Tests (User Stories 2 & 3) — TDD REQUIRED

**Goal**: Python scripts for version checking and docs sync, written test-first

### Script: check-version.py (US2)

- [ ] T012 [US2] Write tests for `scripts/check-version.py` in `tests/unit/test_check_version.py`:
  - Test with new version (not on PyPI) — mock API returns 404
  - Test with existing version (already published) — mock API returns matching version
  - Test with PyPI API unreachable — mock raises timeout/connection error
  - Test with malformed pyproject.toml
  - Test stdout format: `VERSION=x.y.z` and `STATUS=new|exists|error`
- [ ] T013 [US2] Implement `scripts/check-version.py`:
  - Parse pyproject.toml using `tomllib` (stdlib in 3.11+)
  - Query PyPI JSON API at `https://pypi.org/pypi/{package}/json`
  - Compare versions, output status, exit 0 if new / 1 if exists or error
  - Support `PYPI_TIMEOUT` env var, default 15s

### Script: check-docs-sync.py (US3)

- [ ] T014 [US3] Write tests for `scripts/check-docs-sync.py` in `tests/unit/test_check_docs_sync.py`:
  - Test with docs matching CLI output — should pass
  - Test with non-existent flag in docs — should fail
  - Test with missing command reference — should fail
  - Test with empty/whitespace files
  - Test with no doc files specified (should error gracefully)
- [ ] T015 [US3] Implement `scripts/check-docs-sync.py`:
  - Run `relaylm --help` via subprocess, parse command names and option flags
  - Accept doc file paths as positional arguments
  - Search for CLI command/flag references in markdown using regex
  - Report each discrepancy with file path and line number
  - Exit 0 if all docs match CLI, 1 otherwise

**Checkpoint**: Helper scripts implemented with passing tests

---

## Phase 4: Release Workflow (User Story 2)

**Goal**: Release pipeline checks version, runs gates, publishes if all pass

**Independent Test**: Trigger release with existing version — fails fast in under 30s with clear message.

- [ ] T016 [P] [US2] Create `.github/workflows/release.yml` with trigger (workflow_dispatch)
- [ ] T017 [P] [US2] Add `version-check` job: checkout, run `scripts/check-version.py`, fail fast if version exists
- [ ] T018 [P] [US2] Add lint, security, deps, tests, docs jobs (reuse same pattern from ci.yml) — all `needs: [version-check]`
- [ ] T019 [P] [US2] Add `publish` job: `needs: [lint, security, deps, tests, docs]`, uses `pypa/gh-action-pypi-publish@release/v1`, requires `PYPI_API_TOKEN`
- [ ] T020 [P] [US2] Add concurrency group to prevent concurrent releases
- [ ] T021 [US2] Add condition to only publish on `github.ref == 'refs/heads/main'`

**Checkpoint**: Release workflow complete — full pipeline from version check to publish

---

## Phase 5: Branch Protection Script (User Story 4)

**Goal**: Script to automate branch protection setup via GitHub CLI

**Independent Test**: Run `scripts/setup-branch-protection.sh --dry-run` on a repo and see what would change.

- [ ] T022 [US4] Create `scripts/setup-branch-protection.sh`:
  - Detect current protection settings via `gh api repos/{owner}/{repo}/branches/main/protection`
  - Define expected settings (PR reviews required, status checks required, linear history)
  - Dry-run mode (`--dry-run`) that compares current vs expected and reports differences
  - Interactive confirmation before applying (`--yes` to skip)
  - Apply settings via `gh api -X PUT repos/{owner}/{repo}/branches/main/protection`

**Checkpoint**: Branch protection script complete and tested manually

---

## Phase 6: Integration & Final Polish

**Purpose**: Verify everything works end-to-end and update project references

- [ ] T023 [P] Verify all workflow files pass GitHub Actions schema validation (no syntax errors)
- [ ] T024 [P] Run full quality gate: ruff check, mypy, pytest — confirm no regressions
- [ ] T025 Update AGENTS.md to reference completed CI/CD artifacts
- [ ] T026 Update README.md with CI/CD badges (CI status, Python version, license)

**Checkpoint**: All CI/CD artifacts in place, documentation updated, quality gate passes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundation (Phase 1)**: No dependencies — directories and semgrep rules
- **CI Workflow (Phase 2)**: Depends on Phase 1 (directories exist)
- **Helper Scripts (Phase 3)**: Independent of Phase 2 — tests can be written first
- **Release Workflow (Phase 4)**: Depends on Phase 2 (reuses gate patterns) and Phase 3 (check-version.py script)
- **Branch Protection (Phase 5)**: No dependencies — standalone shell script
- **Integration (Phase 6)**: Depends on all prior phases

### Parallel Opportunities

- T001-T004 (Phase 1) — all independent
- T005-T011 (Phase 2) — sequential within phase (jobs added to one file)
- T012-T013 + T014-T015 (Phase 3) — two script/test pairs can run in parallel
- T016-T021 (Phase 4) — sequential within phase
- T022 (Phase 5) — standalone
- T023-T026 (Phase 6) — can run in parallel

### TDD Ordering

For T013 and T015:
1. Write test file first (T012, T014)
2. Run tests — they should fail (no implementation yet)
3. Implement script (T013, T015)
4. Run tests — they should pass

---

## Implementation Strategy

### Incremental Delivery

1. **Phase 1**: Foundation — directories and semgrep rules
2. **Phase 2**: CI workflow — all five gates on PR/push (core value)
3. **Phase 3**: Helper scripts with tests (TDD)
4. **Phase 4**: Release workflow — version safety + publish
5. **Phase 5**: Branch protection — one-time setup
6. **Phase 6**: Polish — badges, AGENTS.md, final verification

### Parallel Team Strategy

1. Developer A: Phase 2 (CI workflow)
2. Developer B: Phase 3 (helper scripts with tests)
3. Developer C: Phase 5 (branch protection script)
4. All merge into Phase 4 (release workflow)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Python scripts MUST use stdlib only (no external deps) — they run in CI without project install
- Semgrep rules should cover OWASP Top 10 Python patterns
- Branch protection script requires `gh` CLI and `jq` — document prerequisites
- The `docs` gate in CI runs markdownlint, codespell, AND check-docs-sync.py
