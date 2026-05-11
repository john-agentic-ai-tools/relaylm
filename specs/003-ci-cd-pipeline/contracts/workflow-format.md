# Contract: GitHub Actions Workflow Format

## CI Workflow (`.github/workflows/ci.yml`)

### Trigger Events
- `push` on all branches
- `pull_request` targeting `main`
- `workflow_dispatch` (manual trigger)

### Jobs (run in parallel)
All gate jobs run in parallel with no dependencies between them:

1. **lint** — `ruff check src/ tests/`
2. **security** — `semgrep --config=.semgrep/ src/`
3. **deps** — dependency validation
4. **tests** — `pytest --cov=src/ --cov-report=term-missing`
5. **docs** — markdownlint + spell check + docs-sync check

### Pass/Fail Behavior
- Each gate reports independent status to PR
- Workflow fails if any gate fails
- All gates must pass for PR to be mergeable (enforced by branch protection)

## Release Workflow (`.github/workflows/release.yml`)

### Trigger Events
- `workflow_dispatch` only (manual trigger by maintainer)
- Optional: `push` on tags like `v*`

### Pre-flight (Phase 1)
1. **version-check** job runs first
   - Runs `scripts/check-version.py`
   - Fails fast if version already exists on PyPI
   - Outputs version status for downstream jobs

### Quality Gates (Phase 2)
- Same gates as CI workflow, but gated on version-check passing
- Run in parallel after version-check

### Publishing (Phase 3)
- Only runs if all quality gates pass
- Uses `pypa/gh-action-pypi-publish@release/v1`
- Requires `PYPI_API_TOKEN` secret

### Concurrency
- `group: release-${{ github.ref }}`
- `cancel-in-progress: false` (don't cancel a running release)

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Workflow file | kebab-case | `ci.yml`, `release.yml` |
| Job ID | snake_case | `run-lint`, `security-scan` |
| Job name | Title Case with gate prefix | `Gate: Lint`, `Gate: Security` |
| Step name | Imperative sentence | `Run ruff linting` |
| Status check name | `Gate: <Name>` | `Gate: Lint`, `Gate: Security` |

This naming convention is required because branch protection references status checks by name.
