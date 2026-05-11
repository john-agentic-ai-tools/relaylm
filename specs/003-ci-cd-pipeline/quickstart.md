# Quick Start: CI/CD Pipeline

## Prerequisites

- Repository is hosted on GitHub
- Maintainer has admin permissions on the repository
- GitHub CLI (`gh`) is installed and authenticated
- PyPI API token is stored as `PYPI_API_TOKEN` repository secret

## Setup

### 1. Configure Branch Protection

```bash
./scripts/setup-branch-protection.sh --dry-run   # Preview changes
./scripts/setup-branch-protection.sh --yes       # Apply changes
```

### 2. Verify CI Pipeline

Push a branch and open a PR. Within 5 minutes, five status checks appear:
- `Gate: Lint` — ruff
- `Gate: Security` — semgrep
- `Gate: Dependencies` — pip-audit / dep check
- `Gate: Tests` — pytest
- `Gate: Docs` — markdownlint + spell check + docs sync

### 3. Trigger a Release

```bash
gh workflow run release.yml
```

The release pipeline:
1. Checks version against PyPI (fails fast if duplicate)
2. Runs all quality gates
3. Publishes to PyPI if all pass

## Key Files

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | CI pipeline (PRs, pushes) |
| `.github/workflows/release.yml` | Release pipeline (manual) |
| `.semgrep/` | Semgrep security rules |
| `scripts/check-version.py` | PyPI version check |
| `scripts/check-docs-sync.py` | Docs/CLI sync checker |
| `scripts/setup-branch-protection.sh` | Branch protection automation |
