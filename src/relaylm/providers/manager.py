from typing import Any

from relaylm.config.backup import create_backup
from relaylm.config.loader import load_config, save_config
from relaylm.providers.keychain import delete_key, get_key, store_key

SUPPORTED_PROVIDERS = ("anthropic", "openai")
DEFAULT_URLS = {
    "anthropic": "https://api.anthropic.com/v1",
    "openai": "https://api.openai.com/v1",
}


class ProviderManager:
    def __init__(self) -> None:
        self.config = load_config()

    def list_providers(self) -> list[dict[str, Any]]:
        providers = self.config.get("providers", {})
        result: list[dict[str, Any]] = []
        for name, cfg in providers.items():
            has_key = (
                get_key(cfg.get("keychain_service", f"relaylm-{name}")) is not None
            )
            result.append(
                {
                    "name": name,
                    "enabled": cfg.get("enabled", False),
                    "base_url": cfg.get("base_url", ""),
                    "has_key": has_key,
                }
            )
        return result

    def add_provider(
        self,
        name: str,
        api_key: str,
        base_url: str | None = None,
    ) -> dict[str, str]:
        if name not in SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported provider: {name}. Supported: {SUPPORTED_PROVIDERS}"
            )

        create_backup()

        keychain_service = f"relaylm-{name}"
        store_key(keychain_service, api_key)

        providers = self.config.setdefault("providers", {})
        providers[name] = {
            "enabled": True,
            "base_url": base_url or DEFAULT_URLS[name],
            "keychain_service": keychain_service,
        }

        fallback = self.config.setdefault(
            "fallback", {"order": ["local"], "timeout_seconds": 30}
        )
        if name not in fallback.get("order", []):
            fallback.setdefault("order", ["local"]).append(name)

        save_config(self.config)
        return {"name": name, "status": "configured"}

    def remove_provider(self, name: str) -> dict[str, str]:
        if name not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {name}")

        create_backup()
        delete_key(f"relaylm-{name}")

        providers = self.config.get("providers", {})
        providers.pop(name, None)
        fallback = self.config.get("fallback", {})
        order = fallback.get("order", [])
        if name in order:
            order.remove(name)

        save_config(self.config)
        return {"name": name, "status": "removed"}
