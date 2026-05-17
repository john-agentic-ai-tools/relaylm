"""Diagnostic info — version, git SHA, install location.

Used by ``relaylm --version`` and ``relaylm info``. All subprocess and lookup
failures return sentinel values so this module is safe to call from CLI
startup paths.
"""

import functools
import subprocess
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path


def package_path() -> Path:
    import relaylm

    return Path(relaylm.__file__).resolve().parent


def package_version() -> str:
    try:
        return _pkg_version("relaylm")
    except PackageNotFoundError:
        return "unknown"


@functools.lru_cache(maxsize=1)
def git_info() -> tuple[str, bool] | None:
    """Return ``(short_sha, dirty)`` when the package lives inside a git
    working tree, else ``None``.
    """
    pkg_dir = str(package_path())
    try:
        sha = subprocess.run(
            ["git", "-C", pkg_dir, "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", pkg_dir, "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    if not sha:
        return None
    return sha, bool(status)


def version_string() -> str:
    base = f"relaylm v{package_version()}"
    info = git_info()
    if info is None:
        return base
    sha, dirty = info
    return f"{base} ({sha}{'+dirty' if dirty else ''})"


def runtime_info() -> dict[str, str]:
    from relaylm.platform import is_wsl2, wsl_distro_name

    info: dict[str, str] = {
        "version": package_version(),
        "package": str(package_path()),
        "python": f"{sys.executable} ({sys.version.split()[0]})",
        "platform": sys.platform,
    }
    if is_wsl2():
        info["wsl"] = wsl_distro_name() or "wsl2"
    g = git_info()
    info["git"] = (
        f"{g[0]} ({'dirty' if g[1] else 'clean'})"
        if g is not None
        else "not in a git working tree"
    )
    return info
