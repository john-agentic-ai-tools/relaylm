# Data Model: Project Documentation

## Document Entities

### README.md
| Field | Type | Description |
|-------|------|-------------|
| path | string | `/README.md` |
| format | string | Markdown (CommonMark) |
| audience | string | New users, evaluators |
| purpose | string | Project introduction, install, quick start, navigation |

**Required sections**: Title, description, prerequisites, install, quick start, links to docs

### LICENSE
| Field | Type | Description |
|-------|------|-------------|
| path | string | `/LICENSE` |
| format | string | Plain text |
| license_type | string | MIT |

### CODE_OF_CONDUCT.md
| Field | Type | Description |
|-------|------|-------------|
| path | string | `/CODE_OF_CONDUCT.md` |
| format | string | Markdown (CommonMark) |
| template | string | Contributor Covenant v2.1 |

### CONTRIBUTING.md
| Field | Type | Description |
|-------|------|-------------|
| path | string | `/CONTRIBUTING.md` |
| format | string | Markdown (CommonMark) |
| audience | string | Developers, contributors |
| purpose | string | Development setup, testing, standards, PR process |

**Required sections**: Development setup, running tests, coding standards, PR process

### docs/guide.md
| Field | Type | Description |
|-------|------|-------------|
| path | string | `/docs/guide.md` |
| format | string | Markdown (CommonMark) |
| audience | string | Users installing and configuring RelayLM |
| purpose | string | Step-by-step installation and configuration guide |

**Required sections**: Hardware requirements, installation, container runtime setup, basic setup, provider configuration, agent configuration, configuration management, troubleshooting
**Supporting documents**: Cross-links to `/docs/config.md` and other supporting docs for complex topics

### docs/config.md (supporting)
| Field | Type | Description |
|-------|------|-------------|
| path | string | `/docs/config.md` |
| format | string | Markdown (CommonMark) |
| audience | string | Users configuring RelayLM |
| purpose | string | Detailed configuration reference |

## Document Relationships

```text
README.md (entry point)
├── Links to ──> docs/guide.md (detailed guide)
├── Links to ──> CONTRIBUTING.md (for contributors)
└── Links to ──> CODE_OF_CONDUCT.md (for community)

docs/guide.md (main guide)
└── Cross-links ──> docs/*.md (supporting documents for complex topics)
```

## Validation Rules

- All CLI commands and flags referenced in docs must exist in the actual tool
- All internal links between documents must resolve
- All code blocks must use correct language tags
- No broken markdown formatting
- Consistent terminology across all documents
