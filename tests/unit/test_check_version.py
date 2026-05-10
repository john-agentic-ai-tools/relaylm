import json
import tomllib
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from scripts.check_version import (
    check_pypi_version,
    load_local_version,
    parse_pypi_response,
)


def test_load_local_version_found(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "0.2.0"\n')
    result = load_local_version(pyproject)
    assert result == "0.2.0"


def test_load_local_version_missing_field(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "foo"\n')
    with pytest.raises(KeyError):
        load_local_version(pyproject)


def test_load_local_version_malformed_toml(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("not valid toml {{{")
    with pytest.raises(tomllib.TOMLDecodeError):
        load_local_version(pyproject)


def test_parse_pypi_response_version_found() -> None:
    data = {"info": {"version": "0.1.0"}}
    result = parse_pypi_response(json.dumps(data))
    assert result == "0.1.0"


def test_parse_pypi_response_no_info() -> None:
    data = {}
    result = parse_pypi_response(json.dumps(data))
    assert result is None


def test_check_pypi_version_new_version() -> None:
    from http.client import HTTPMessage

    http_error = urllib.error.HTTPError(
        url="https://pypi.org/pypi/relaylm/json",
        code=404,
        msg="Not Found",
        hdrs=HTTPMessage(),
        fp=None,
    )
    with patch("urllib.request.urlopen", side_effect=http_error):
        status, msg = check_pypi_version("0.2.0", "relaylm")
    assert status == "new"


def test_check_pypi_version_exists() -> None:
    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.status = 200
    mock_response.read.return_value = json.dumps(
        {"info": {"version": "0.1.0"}}
    ).encode()
    with patch("urllib.request.urlopen", return_value=mock_response):
        status, msg = check_pypi_version("0.1.0", "relaylm")
    assert status == "exists"


def test_check_pypi_version_network_error() -> None:
    with patch("urllib.request.urlopen", side_effect=OSError("Connection refused")):
        status, msg = check_pypi_version("0.2.0", "relaylm")
    assert status == "error"
    assert "Connection refused" in msg


def test_check_pypi_version_timeout() -> None:
    with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
        status, msg = check_pypi_version("0.2.0", "relaylm")
    assert status == "error"
    assert "timed out" in msg


def test_check_pypi_version_none_pypi_version() -> None:
    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.status = 200
    mock_response.read.return_value = json.dumps({"info": {}}).encode()
    with patch("urllib.request.urlopen", return_value=mock_response):
        status, msg = check_pypi_version("0.2.0", "relaylm")
    assert status == "new"
    assert "differs from PyPI None" in msg
