import os
import stat
from pathlib import Path

try:
    import keyring as _keyring_module

    _has_keyring = True
except ImportError:
    _keyring_module = None  # type: ignore[assignment]
    _has_keyring = False

KEYCHAIN_FALLBACK_DIR = Path.home() / ".config" / "relaylm" / "secrets"


def _ensure_fallback_dir() -> None:
    KEYCHAIN_FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(KEYCHAIN_FALLBACK_DIR, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)


def store_key(service: str, key: str) -> None:
    if _keyring_module is not None:
        try:
            _keyring_module.set_password(service, "api_key", key)
            return
        except Exception:
            pass
    _ensure_fallback_dir()
    key_path = KEYCHAIN_FALLBACK_DIR / service
    key_path.write_text(key)
    os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)
    print(
        f"Warning: API key stored in plaintext at {key_path}. "
        f"Install 'keyring' for secure system keychain storage.",
        file=__import__("sys").stderr,
    )


def get_key(service: str) -> str | None:
    if _keyring_module is not None:
        try:
            result = _keyring_module.get_password(service, "api_key")
            if result is not None:
                return result
        except Exception:
            pass
    key_path = KEYCHAIN_FALLBACK_DIR / service
    if key_path.exists():
        return key_path.read_text().strip()
    return None


def delete_key(service: str) -> None:
    if _keyring_module is not None:
        try:
            _keyring_module.delete_password(service, "api_key")
        except Exception:
            pass
    key_path = KEYCHAIN_FALLBACK_DIR / service
    if key_path.exists():
        key_path.unlink()
