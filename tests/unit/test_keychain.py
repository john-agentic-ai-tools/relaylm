from relaylm.providers.keychain import delete_key, get_key, store_key

TEST_SERVICE = "test-relaylm-unittest"


class TestKeychainWrapper:
    def test_store_and_get_key(self) -> None:
        store_key(TEST_SERVICE, "test-api-key-123")
        result = get_key(TEST_SERVICE)
        assert result == "test-api-key-123"

    def test_get_missing_key(self) -> None:
        result = get_key("nonexistent-service-xyz")
        assert result is None

    def test_delete_key(self) -> None:
        store_key(TEST_SERVICE, "delete-me")
        delete_key(TEST_SERVICE)
        result = get_key(TEST_SERVICE)
        assert result is None

    def test_store_overwrites(self) -> None:
        store_key(TEST_SERVICE, "first-key")
        store_key(TEST_SERVICE, "second-key")
        result = get_key(TEST_SERVICE)
        assert result == "second-key"

    def test_delete_nonexistent_key(self) -> None:
        delete_key("nonexistent-service-xyz")
