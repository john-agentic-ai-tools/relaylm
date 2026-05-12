# Contributing to RelayLM

Thank you for your interest in contributing to RelayLM! This guide will help you get started.

## Development Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/anomalyco/relaylm.git
   cd relaylm
   ```

2. **Create a virtual environment**:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install in development mode**:

   ```bash
   pip install -e ".[dev]"
   ```

4. **Verify the setup**:

   ```bash
   relaylm --help
   ```

### Developing on Windows (WSL2)

Use a WSL2 Ubuntu (or compatible) distro. Clone the repo into the Linux
filesystem (`~/code/relaylm`) — not under `/mnt/c/...` — to avoid slow
cross-filesystem I/O. From there the `uv`, `pytest`, `ruff`, and `mypy`
commands below work exactly as on Linux. See
[Running on Windows (WSL2)](docs/guide.md#windows-wsl2) for prerequisite
setup.

## Running Tests

```bash
# Run the full test suite
pytest

# Run with coverage
pytest --cov=relaylm

# Run specific test file
pytest tests/unit/test_model_selector.py
```

## Linting and Type Checking

```bash
# Lint check
ruff check src/ tests/

# Auto-fix lint issues
ruff check --fix src/ tests/

# Format check
ruff format --check src/ tests/

# Auto-format
ruff format src/ tests/

# Type check
mypy src/
```

## Coding Standards

- **PEP 8**: Follow Python's style guide
- **Type hints**: Required for all public APIs
- **TDD**: Test-First Development per the [project constitution](.specify/memory/constitution.md)
  - Tests MUST be written before implementation code
  - Tests MUST fail initially (Red phase)
  - Tests MUST pass after implementation (Green phase)
- **Dependencies**: Declare explicitly in `pyproject.toml` with version constraints

## Pull Request Process

1. Create a feature branch from `main`:

   ```bash
   git checkout -b my-feature-branch
   ```

2. Make your changes with granular, atomic commits

3. Run the full quality gate before submitting:

   ```bash
   ruff check src/ tests/
   mypy src/
   pytest
   ```

4. Push your branch and open a pull request

5. In your PR description, include:
   - What the change does
   - Why it's needed
   - Test evidence (output showing Red before implementation, Green after for TDD)

6. Your PR will be reviewed by maintainers. Address any feedback and update as needed.

## Questions?

Open an issue on GitHub or reach out to the maintainers.
