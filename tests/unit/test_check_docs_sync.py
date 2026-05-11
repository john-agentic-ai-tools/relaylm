

import sys
from unittest.mock import patch

from scripts.check_docs_sync import (
    check_doc_file,
    extract_cli_commands,
    find_flag_references,
    main,
)


def test_extract_cli_commands_typical() -> None:
    help_text = """\
 Usage: relaylm [OPTIONS] COMMAND [ARGS]...

╭─ Commands ───────────────────────╮
│ setup      Bootstrap the env.    │
│ agents     Configure agents.     │
│ providers  Manage providers      │
│ config     Manage config         │
╰──────────────────────────────────╯
"""
    commands = extract_cli_commands(help_text)
    assert commands == {"setup", "agents", "providers", "config"}


def test_extract_cli_commands_empty() -> None:
    commands = extract_cli_commands("No commands here")
    assert commands == set()


def test_find_flag_references_no_flags() -> None:
    content = "This is a simple document with no CLI references."
    refs = find_flag_references("test.md", content)
    assert refs == []


def test_find_flag_references_with_command() -> None:
    content = "Run `relaylm setup` to bootstrap."
    refs = find_flag_references("test.md", content)
    assert len(refs) == 1
    assert refs[0].command == "setup"


def test_find_flag_references_with_option() -> None:
    content = "Use `--help` to see options."
    refs = find_flag_references("test.md", content)
    assert len(refs) == 1
    assert refs[0].command is None
    assert refs[0].flag == "--help"


def test_find_flag_references_multiple() -> None:
    content = "Run `relaylm setup --yes` or `relaylm --help`."
    refs = find_flag_references("test.md", content)
    assert len(refs) >= 2


def test_find_flag_references_empty_file() -> None:
    refs = find_flag_references("empty.md", "")
    assert refs == []


def test_check_doc_file_not_found() -> None:
    errors = check_doc_file("missing.md", {"setup"})
    assert len(errors) == 1
    assert "File not found" in errors[0]


def test_check_doc_file_unknown_command(tmp_path) -> None:
    doc = tmp_path / "doc.md"
    doc.write_text("Run `relaylm unknown-cmd`.")
    errors = check_doc_file(str(doc), {"setup"})
    assert len(errors) == 1
    assert "Unknown command" in errors[0]


def test_main_no_args(capsys) -> None:
    with patch.object(sys, "argv", ["check_docs_sync.py"]):
        result = main()
    assert result == 1
    captured = capsys.readouterr()
    assert "Usage" in captured.err


def test_main_with_valid_docs(tmp_path) -> None:
    doc = tmp_path / "doc.md"
    doc.write_text("Run `relaylm setup`.")
    with patch.object(sys, "argv", ["check_docs_sync.py", str(doc)]):
        with patch(
            "scripts.check_docs_sync.get_cli_help",
            return_value="│ setup      Bootstrap      │",
        ):
            result = main()
    assert result == 0


def test_main_with_unknown_command(tmp_path, capsys) -> None:
    doc = tmp_path / "doc.md"
    doc.write_text("Run `relaylm unknown-cmd`.")
    with patch.object(sys, "argv", ["check_docs_sync.py", str(doc)]):
        with patch(
            "scripts.check_docs_sync.get_cli_help",
            return_value="│ setup      Bootstrap      │",
        ):
            result = main()
    assert result == 1
    captured = capsys.readouterr()
    assert "Unknown command" in captured.err


def test_main_cli_help_failure(capsys) -> None:
    with patch.object(sys, "argv", ["check_docs_sync.py", "doc.md"]):
        with patch(
            "scripts.check_docs_sync.get_cli_help",
            side_effect=FileNotFoundError("no module"),
        ):
            result = main()
    assert result == 1
    captured = capsys.readouterr()
    assert "Failed to get CLI help" in captured.err
