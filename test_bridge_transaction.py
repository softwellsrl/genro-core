"""Test that PublisherBridge exposes transaction metadata."""

import json
from genro_core.enablers import apiready, PublisherBridge


@apiready(path="/test")
class TestTable:
    """Test table with transaction-decorated methods."""

    @apiready
    def read_method(self) -> dict:
        """Read method (no transaction)."""
        return {}

    @apiready(transaction=True)
    def write_method(self, data: str) -> dict:
        """Write method (with transaction)."""
        return {}


class MockApp:
    """Mock application for testing."""
    pass


def test_bridge_transaction_metadata():
    """Test that PublisherBridge includes transaction flag in API structure."""

    print("=" * 60)
    print("TESTING PUBLISHERBRIDGE TRANSACTION METADATA")
    print("=" * 60)

    # Create bridge
    app = MockApp()
    bridge = PublisherBridge(app)

    # Get API structure
    print("\n1. Getting API structure...")
    structure_json = bridge.get_api_structure(TestTable, mode="json")
    structure = json.loads(structure_json)

    print(f"   ✓ Got structure for {structure['class_name']}")

    # Check endpoints
    print("\n2. Checking endpoints...")
    endpoints = {ep["function_name"]: ep for ep in structure["endpoints"]}

    # Check read_method
    print("\n   a. Checking read_method...")
    assert "read_method" in endpoints, "read_method not found"
    read_ep = endpoints["read_method"]
    assert "transaction" in read_ep, "transaction key missing"
    assert read_ep["transaction"] == False, f"Expected False, got {read_ep['transaction']}"
    print(f"      ✓ read_method: transaction={read_ep['transaction']}")

    # Check write_method
    print("\n   b. Checking write_method...")
    assert "write_method" in endpoints, "write_method not found"
    write_ep = endpoints["write_method"]
    assert "transaction" in write_ep, "transaction key missing"
    assert write_ep["transaction"] == True, f"Expected True, got {write_ep['transaction']}"
    print(f"      ✓ write_method: transaction={write_ep['transaction']}")

    # Print full structure for verification
    print("\n3. Full API structure:")
    print(json.dumps(structure, indent=2))

    print("\n" + "=" * 60)
    print("✓ ALL BRIDGE TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    test_bridge_transaction_metadata()
