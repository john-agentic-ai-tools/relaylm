import pytest

from relaylm.providers.keychain import delete_key, get_key
from relaylm.providers.manager import SUPPORTED_PROVIDERS, ProviderManager


class TestProviderManager:
    def test_list_providers_empty_initially(self) -> None:
        mgr = ProviderManager()
        providers = mgr.list_providers()
        assert isinstance(providers, list)

    def test_supported_providers(self) -> None:
        assert "anthropic" in SUPPORTED_PROVIDERS
        assert "openai" in SUPPORTED_PROVIDERS
        assert len(SUPPORTED_PROVIDERS) == 2

    def test_add_provider_unsupported_raises(self) -> None:
        mgr = ProviderManager()
        with pytest.raises(ValueError, match="Unsupported provider"):
            mgr.add_provider("unknown", "sk-test")

    def test_add_provider_returns_status(self) -> None:
        mgr = ProviderManager()
        result = mgr.add_provider("openai", "sk-test-key")
        assert result["name"] == "openai"
        assert result["status"] == "configured"

    def test_add_provider_stores_key(self) -> None:
        mgr = ProviderManager()
        mgr.add_provider("anthropic", "sk-anthropic-test")
        stored = get_key("relaylm-anthropic")
        assert stored == "sk-anthropic-test"
        delete_key("relaylm-anthropic")

    def test_remove_provider_unsupported_raises(self) -> None:
        mgr = ProviderManager()
        with pytest.raises(ValueError, match="Unsupported provider"):
            mgr.remove_provider("unknown")

    def test_remove_provider_returns_status(self) -> None:
        mgr = ProviderManager()
        mgr.add_provider("openai", "sk-to-remove")
        result = mgr.remove_provider("openai")
        assert result["name"] == "openai"
        assert result["status"] == "removed"

    def test_add_provider_uses_custom_base_url(self) -> None:
        mgr = ProviderManager()
        mgr.add_provider("openai", "sk-test", base_url="https://custom.example.com/v1")
        providers = mgr.list_providers()
        matching = [p for p in providers if p["name"] == "openai"]
        assert len(matching) > 0
        delete_key("relaylm-openai")
