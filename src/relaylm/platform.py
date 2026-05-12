"""WSL2 detection helpers.

Stdlib-only. Safe to import from any layer.
"""

import os
from functools import lru_cache
from pathlib import Path

_PROC_VERSION = Path("/proc/version")
_RUN_WSL = Path("/run/WSL")


@lru_cache(maxsize=1)
def is_wsl2() -> bool:
    """Return True when running inside a WSL2 distro.

    WSL2 exposes /run/WSL (absent on WSL1). As a secondary signal we look for
    "microsoft" in /proc/version, which both WSL1 and WSL2 set — gated by
    WSL_INTEROP to exclude WSL1.
    """
    if _RUN_WSL.is_dir():
        return True
    if os.environ.get("WSL_INTEROP") and _proc_version_mentions_microsoft():
        return True
    return False


def wsl_distro_name() -> str | None:
    """Return the WSL distro name (e.g. "Ubuntu-22.04") if set."""
    name = os.environ.get("WSL_DISTRO_NAME")
    return name or None


def _proc_version_mentions_microsoft() -> bool:
    try:
        content = _PROC_VERSION.read_text()
    except (FileNotFoundError, PermissionError, OSError):
        return False
    return "microsoft" in content.lower()
