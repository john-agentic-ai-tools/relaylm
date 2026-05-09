# Document Format Contract

## Markdown Conventions

All documentation files MUST follow these conventions:

1. **Line length**: Maximum 88 characters per line (consistent with code style)
2. **Headings**: ATX-style (`#`, `##`, `###`) with space after `#`
3. **Code blocks**: Fenced with triple backticks and language tag
4. **Emphasis**: Use `**bold**` and `*italic*` (not underscores)
5. **Lists**: Use `-` for unordered, `1.` for ordered
6. **Links**: Inline format `[text](url)`
7. **Tables**: GitHub-flavored markdown with pipes and dashes

## CLI Reference Format

When documenting CLI commands, use this format:

````markdown
### Command Name

Description of what the command does.

```bash
relaylm command [OPTIONS] [ARGS]
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| NAME | Yes | Description of argument |

**Options**:
| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--flag` | TEXT | default | Description |
````

## Cross-Reference Contract

- Internal links use relative paths: `[text](../path/to/file.md)`
- Section anchors use `[text](#section-name)` matching GitHub's auto-generated anchors
- Supporting docs from guide.md use `[See detailed guide](config.md)` format
