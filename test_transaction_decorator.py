"""Test transaction parameter in @apiready decorator."""

from genro_core.enablers import apiready


@apiready(path="/test")
class TestTable:
    """Test table with transaction-decorated methods."""

    @apiready
    def read_method(self) -> dict:
        """This is a read method (GET)."""
        return {}

    @apiready(transaction=True)
    def write_method(self, data: str) -> dict:
        """This is a write method with transaction (POST)."""
        return {}

    @apiready(transaction=False)
    def no_transaction_method(self, data: str) -> dict:
        """This is a write method without transaction (POST)."""
        return {}


def test_transaction_metadata():
    """Test that transaction flag is properly stored in metadata."""

    print("=" * 60)
    print("TESTING TRANSACTION PARAMETER")
    print("=" * 60)

    # Test read_method (default transaction=False)
    print("\n1. Testing read_method (default)...")
    metadata = TestTable.read_method._api_metadata
    assert "transaction" in metadata, "transaction key missing from metadata"
    assert metadata["transaction"] == False, f"Expected False, got {metadata['transaction']}"
    print(f"   ✓ read_method: transaction={metadata['transaction']}")

    # Test write_method (explicit transaction=True)
    print("\n2. Testing write_method (transaction=True)...")
    metadata = TestTable.write_method._api_metadata
    assert "transaction" in metadata, "transaction key missing from metadata"
    assert metadata["transaction"] == True, f"Expected True, got {metadata['transaction']}"
    print(f"   ✓ write_method: transaction={metadata['transaction']}")

    # Test no_transaction_method (explicit transaction=False)
    print("\n3. Testing no_transaction_method (transaction=False)...")
    metadata = TestTable.no_transaction_method._api_metadata
    assert "transaction" in metadata, "transaction key missing from metadata"
    assert metadata["transaction"] == False, f"Expected False, got {metadata['transaction']}"
    print(f"   ✓ no_transaction_method: transaction={metadata['transaction']}")

    print("\n" + "=" * 60)
    print("✓ ALL TRANSACTION TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    test_transaction_metadata()
