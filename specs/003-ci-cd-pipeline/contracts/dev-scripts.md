# Contract: Dev Scripts for CI/CD

## Python Scripts

### `scripts/check-version.py`
- **Purpose**: Verify that the current version in pyproject.toml has not been published to PyPI
- **Exit code**: 0 if version is new (not published), 1 if version already exists or error
- **Output to stdout**: `VERSION=<version>` and `STATUS=new|exists|error`
- **Output to stderr**: Error messages
- **Timeout**: 15 seconds for PyPI API call
- **Env vars**: 
  - `PYPI_TIMEOUT` (optional, default 15)
- **Dependencies**: stdlib only (urllib.request + json + tomllib (3.11+))

### `scripts/check-docs-sync.py`
- **Purpose**: Verify that CLI commands and flags documented in markdown files match `relaylm --help` output
- **Exit code**: 0 if docs are in sync, 1 if discrepancies found
- **Output**: Lists each discrepancy with file path, line number, and description
- **Args**:
  - Positional: doc files to check (e.g., `docs/guide.md docs/config.md README.md`)
- **Dependencies**: stdlib only (re, subprocess for running relaylm --help)

## Shell Scripts

### `scripts/setup-branch-protection.sh`
- **Purpose**: Configure branch protection on main branch using `gh` CLI
- **Exit code**: 0 on success, 1 on failure
- **Behavior**:
  - Dry-run mode with `--dry-run` flag (reports what would change without applying)
  - Interactive confirmation before applying changes unless `--yes` flag is passed
  - Detects existing settings and reports changes
- **Required tools**: `gh` (GitHub CLI), `jq` (JSON processor)
- **Env vars**:
  - `GITHUB_REPOSITORY` (optional, default detected from `gh repo view`)
