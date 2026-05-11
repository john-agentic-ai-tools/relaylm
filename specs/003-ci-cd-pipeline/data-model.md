# Data Model: CI/CD Pipeline

**Date**: 2026-05-09
**Feature**: specs/003-ci-cd-pipeline/spec.md

## Entities

### 1. GitHub Actions Workflow
```
Workflow
├── name: string                    # Human-readable name
├── on: Event[]                     # Trigger events (push, pull_request, workflow_dispatch)
├── concurrency: ConcurrencyGroup   # Prevent parallel runs
├── jobs: Job[]                     # Collection of jobs
└── defaults: RunDefaults           # Shell, working-directory
```

### 2. Job (Quality Gate)
```
Job
├── name: string                    # Display name (appears in PR checks)
├── runs-on: string                 # Runner label (ubuntu-latest)
├── needs: string[]                 # Dependencies on other jobs
├── if: expression                  # Conditional execution
├── steps: Step[]                   # Collection of steps
└── outputs: Map<string,string>     # Job outputs consumed by dependents
```

### 3. Step
```
Step
├── name: string
├── uses: string                    # Action reference (or null for run)
├── run: string                     # Inline script (or null for uses)
├── with: Map<string,string>        # Action inputs
├── env: Map<string,string>         # Environment variables
└── continue-on-error: boolean      # Allow step failure without failing job
```

### 4. Quality Gate
```
QualityGate
├── name: "lint" | "security" | "deps" | "tests" | "docs"
├── tool: string                    # Tool used (ruff, semgrep, pytest, etc.)
├── command: string                 # CLI command to run
├── config_path: string             # Path to configuration file
├── expected_exit_code: 0|1         # 0 = pass, 1 = fail
└── parallel_group: string          # Group for parallel execution
```

### 5. Version Check
```
VersionCheck
├── local_version: string           # From pyproject.toml
├── pypi_latest: string|null        # From pypi.org JSON API (null if not published)
├── is_new: boolean                 # local_version > pypi_latest
├── pypi_url: string                # API endpoint for version check
└── check_timeout_seconds: 15       # Timeout for PyPI API call
```

### 6. Branch Protection Rule
```
BranchProtection
├── branch: "main"
├── required_status_checks: string[] # Gate names that must pass
├── requires_pull_request_reviews: true
├── required_approving_review_count: 1
├── requires_linear_history: true
├── dismisses_stale_reviews: true
└── lock_branch: false
```

### 7. Concurrency Group
```
ConcurrencyGroup
├── group: string                   # Unique group identifier
├── cancel-in-progress: boolean     # Cancel running if new trigger arrives
└── scope: "workflow" | "branch"
```

## Relationships

```
Repository
├── has_many: Workflow (.github/workflows/*.yml)
├── has_many: QualityGate (defined in workflows)
├── has_many: SemgrepRule (.semgrep/*.yml)
└── has_one: BranchProtection (applied to main branch)

Workflow
├── triggers_on: Event (push, pull_request, release)
├── contains: Job[]
│   └── Job
│       └── represents: QualityGate
└── respects: ConcurrencyGroup

Release Pipeline
├── depends_on: VersionCheck (pre-flight)
├── requires: QualityGate[] (all must pass)
└── produces: PyPIRelease (pypi.org publish)
```

## File Locations

| Artifact | Path |
|----------|------|
| CI workflow | `.github/workflows/ci.yml` |
| Release workflow | `.github/workflows/release.yml` |
| Semgrep rules dir | `.semgrep/` |
| Version check script | `scripts/check-version.py` |
| Docs sync checker | `scripts/check-docs-sync.py` |
| Branch protection script | `scripts/setup-branch-protection.sh` |
