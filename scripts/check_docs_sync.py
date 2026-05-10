"""Verify that CLI commands/flags in docs match actual relaylm --help output."""

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DocReference:
    file: str
    line: int
    command: str | None
    flag: str | None
    text: str

    def __repr__(self) -> str:
        loc = f"{self.file}:{self.line}"
        if self.command:
            return f"{loc}: command `{self.command}`"
        if self.flag:
            return f"{loc}: flag `{self.flag}`"
        return f"{loc}: {self.text}"


def extract_cli_commands(help_text: str) -> set[str]:
    commands: set[str] = set()
    for line in help_text.splitlines():
        m = re.match(r"│\s+(\S+)\s+", line)
        if m:
            cmd = m.group(1)
            if cmd not in ("╭─", "╰─"):
                commands.add(cmd)
    return commands


def get_cli_help() -> str:
    result = subprocess.run(
        [sys.executable, "-m", "relaylm", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout


def find_flag_references(filepath: str, content: str) -> list[DocReference]:
    refs: list[DocReference] = []
    for i, line in enumerate(content.splitlines(), 1):
        for m in re.finditer(r"`([^`]+)`", line):
            text = m.group(1)
            if text.startswith("--"):
                refs.append(DocReference(filepath, i, None, text, line.strip()))
            elif text.startswith("relaylm "):
                parts = text.split()
                if len(parts) >= 2:
                    refs.append(DocReference(filepath, i, parts[1], None, line.strip()))
    return refs


def check_doc_file(filepath: str, known_commands: set[str]) -> list[str]:
    path = Path(filepath)
    if not path.exists():
        return [f"File not found: {filepath}"]

    content = path.read_text()
    errors: list[str] = []

    refs = find_flag_references(filepath, content)
    for ref in refs:
        if ref.command and ref.command not in known_commands:
            msg = f"{ref.file}:{ref.line}: Unknown command `{ref.command}`"
            errors.append(msg)

    return errors


def main() -> int:
    doc_files = sys.argv[1:]
    if not doc_files:
        print("Usage: check-docs-sync.py <doc-file> [doc-file ...]", file=sys.stderr)
        return 1

    try:
        help_text = get_cli_help()
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"Failed to get CLI help: {e}", file=sys.stderr)
        return 1

    known_commands = extract_cli_commands(help_text)

    all_errors: list[str] = []
    for doc_file in doc_files:
        errors = check_doc_file(doc_file, known_commands)
        all_errors.extend(errors)

    if all_errors:
        for error in all_errors:
            print(error, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
