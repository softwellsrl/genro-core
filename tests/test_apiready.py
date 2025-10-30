"""Tests for @apiready decorator."""

from genro_core.decorators import apiready


class MockBackend:
    """Mock backend for testing @apiready decorator."""

    @apiready
    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read file as text."""
        return f"content of {path}"

    @apiready
    def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to file."""
        pass

    @apiready(method="POST")
    def get_metadata(self, path: str) -> dict:
        """Get file metadata (explicitly POST)."""
        return {"path": path, "size": 100}


def test_apiready_basic():
    """Test that @apiready preserves function behavior."""
    backend = MockBackend()
    result = backend.read_text("/test.txt")
    assert result == "content of /test.txt"


def test_apiready_metadata_present():
    """Test that @apiready adds _api_metadata attribute."""
    assert hasattr(MockBackend.read_text, "_api_metadata")
    assert hasattr(MockBackend.write_bytes, "_api_metadata")


def test_apiready_http_method_inference():
    """Test HTTP method inference from function name."""
    # read* should infer GET
    metadata = MockBackend.read_text._api_metadata
    assert metadata["http_method"] == "GET"

    # write* should infer POST
    metadata = MockBackend.write_bytes._api_metadata
    assert metadata["http_method"] == "POST"


def test_apiready_explicit_method():
    """Test explicit HTTP method override."""
    # Explicitly set to POST even though name starts with 'get'
    metadata = MockBackend.get_metadata._api_metadata
    assert metadata["http_method"] == "POST"


def test_apiready_request_fields():
    """Test request field extraction."""
    metadata = MockBackend.read_text._api_metadata
    fields = metadata["request_fields"]

    # Should have 'path' (required) and 'encoding' (optional with default)
    assert "path" in fields
    assert "encoding" in fields

    # Check required vs optional
    assert fields["path"] == (str, ...)  # Required (no default)
    assert fields["encoding"] == (str, "utf-8")  # Optional with default


def test_apiready_return_type():
    """Test return type extraction."""
    # read_text returns str
    metadata = MockBackend.read_text._api_metadata
    assert metadata["return_type"] == str

    # write_bytes returns None
    metadata = MockBackend.write_bytes._api_metadata
    assert metadata["return_type"] is type(None)

    # get_metadata returns dict
    metadata = MockBackend.get_metadata._api_metadata
    assert metadata["return_type"] == dict


def test_apiready_endpoint_name():
    """Test endpoint name is function name."""
    metadata = MockBackend.read_text._api_metadata
    assert metadata["endpoint_name"] == "read_text"


def test_apiready_docstring():
    """Test docstring is captured."""
    metadata = MockBackend.read_text._api_metadata
    assert metadata["docstring"] == "Read file as text."
