# Research: CI/CD Pipeline

**Date**: 2026-05-09
**Feature**: specs/003-ci-cd-pipeline/spec.md
**Purpose**: Gather project-specific details needed for CI/CD pipeline implementation

## Project Inventory

### Build & Packaging
- **Build system**: setuptools (pyproject.toml)
- **Package name**: relaylm
- **Current version**: 0.1.0
- **Python**: >=3.11
- **Entry point**: `relaylm = "relaylm.cli.app:app"`
- **Source layout**: src/relaylm/ (flat under src/)
- **Optional deps**: dev = [pytest>=8.0, pytest-cov>=5.0, ruff>=0.5, mypy>=1.10]

### Code Quality Tooling
| Tool    | Config                            | Status      |
|---------|-----------------------------------|-------------|
| ruff    | pyproject.toml, target py311, 88 cols, select E/F/I/N/W/UP | Clean: all checks pass |
| mypy    | pyproject.toml, strict=true, files=src | Clean: no issues |
| pytest  | pyproject.toml, testpaths=tests   | 53 tests pass |
| semgrep | Not yet configured                | Needs setup |

### CLI Surface (extracted from relaylm --help)
- Commands: `setup`, `agents`, `providers`, `config`
- Global options: `--install-completion`, `--show-completion`, `--help`
- Subcommands (verify as needed for docs-sync checker)

### Project Structure
```
.
├── .github/              # CI/CD workflows go here (currently empty)
├── .semgrep/             # Semgrep rules (not yet created)
├── src/relaylm/          # Application source
├── tests/                # Test suite (unit/, integration/, contract/)
├── docs/                 # Documentation
│   ├── guide.md
│   └── config.md
├── scripts/              # Scripts directory (not yet created)
├── pyproject.toml        # Build config + tool configs
└── README.md
```

### PyPI
- Package: relaylm on pypi.org
- Version check URL: https://pypi.org/pypi/relaylm/json

### GitHub Actions Environment
- Runner: ubuntu-latest (standard)
- Python: Setup via actions/setup-python@v5
- Actions needed:
  - actions/checkout@v4
  - actions/setup-python@v5
  - pypa/gh-action-pypi-publish@release/v1 (for PyPI publishing)
  - semgrep/semgrep-action@v1 (or pip install semgrep)

### Existing Scripts
- No `scripts/` directory exists yet
- No existing CI/CD configuration
- No pre-commit hooks configured

### Branch Protection
- Requires GitHub CLI (`gh`) with admin permissions
- API endpoint: `repos/{owner}/{repo}/branches/main/protection`
- Required checks: lint (ruff), security (semgrep), deps, tests, docs
- Settings: require PR review, require status checks, linear history

## Key Design Decisions

1. **Semgrep**: Use `semgrep/semgrep-action@v1` action with `.semgrep/` rules directory
2. **Dependency validation**: Use `pip-audit` or manual `pip install` check
3. **Docs sync checker**: Python script in `scripts/` that compares CLI --help output against docs
4. **Version check**: Python script that queries PyPI JSON API
5. **Branch protection**: Shell script using `gh api` commands
6. **Workflow concurrency**: GitHub Actions concurrency groups to prevent concurrent releases
