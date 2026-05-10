"""Check the current version against PyPI before publishing."""

import json
import os
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

PYPI_TIMEOUT = int(os.environ.get("PYPI_TIMEOUT", "15"))
PYPI_URL_TEMPLATE = "https://pypi.org/pypi/{package}/json"


def load_local_version(pyproject_path: Path) -> str:
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)
    version: str = data["project"]["version"]
    return version


def parse_pypi_response(body: str) -> str | None:
    data = json.loads(body)
    info = data.get("info")
    if info is None:
        return None
    version: str | None = info.get("version")
    return version


def check_pypi_version(local_version: str, package: str) -> tuple[str, str]:
    url = PYPI_URL_TEMPLATE.format(package=package)
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=PYPI_TIMEOUT) as response:
            if response.status == 200:
                body = response.read().decode()
                pypi_version = parse_pypi_response(body)
                if pypi_version and pypi_version == local_version:
                    return "exists", f"Version {local_version} already exists on PyPI"
                return (
                    "new",
                    f"Local version {local_version} differs from PyPI {pypi_version}",
                )
            return "error", f"Unexpected HTTP {response.status}"
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return (
                "new",
                f"Package {package} not found on PyPI — version {local_version} is new",
            )
        return "error", f"HTTP error {e.code}: {e.reason}"
    except (OSError, TimeoutError) as e:
        return "error", str(e)


def main() -> int:
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        print("STATUS=error", file=sys.stderr)
        print("pyproject.toml not found", file=sys.stderr)
        return 1

    try:
        local_version = load_local_version(pyproject)
    except (tomllib.TOMLDecodeError, KeyError) as e:
        print("STATUS=error", file=sys.stderr)
        print(f"Failed to parse pyproject.toml: {e}", file=sys.stderr)
        return 1

    package = "relaylm"
    status, message = check_pypi_version(local_version, package)

    print(f"VERSION={local_version}")
    print(f"STATUS={status}")

    if status == "exists":
        print(message, file=sys.stderr)
        return 1
    if status == "error":
        print(message, file=sys.stderr)
        return 1

    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
