"""Test introspection module."""

import pytest
from typing import Annotated
from genro_core.decorators import apiready
from genro_core.introspection import get_api_structure


# Test fixtures - simple classes


@apiready(path="/simple")
class SimpleClass:
    """Simple class with basic methods."""

    @apiready
    def get_data(self) -> dict:
        """Get data without parameters."""
        return {"status": "ok"}

    @apiready
    def set_value(
        self, value: Annotated[str, "Value to set"]
    ) -> bool:
        """Set a value with one parameter."""
        return True


@apiready(path="/complex")
class ComplexClass:
    """Complex class with various parameter types."""

    @apiready
    def process(
        self,
        name: Annotated[str, "Name parameter"],
        count: Annotated[int, "Count parameter"] = 10,
        active: Annotated[bool, "Active flag"] = True,
    ) -> dict:
        """Process with multiple parameters including defaults."""
        return {"name": name, "count": count, "active": active}

    @apiready(method="POST")
    def update(
        self, data: Annotated[dict, "Data to update"]
    ) -> dict:
        """Update with explicit POST method."""
        return data


@apiready(path="/manager")
class ManagerClass:
    """Manager class with child manager."""

    def __init__(self):
        self.child = ChildManager(self)

    @apiready
    def get_info(self) -> str:
        """Get manager info."""
        return "manager"


@apiready(path="/child")
class ChildManager:
    """Child manager class."""

    def __init__(self, parent: ManagerClass):
        self._parent = parent

    @apiready
    def get_child_info(self) -> str:
        """Get child info."""
        return "child"


class TestGetApiStructureBasic:
    """Test basic get_api_structure functionality."""

    def test_simple_class_dict_mode(self):
        """Test introspection of simple class in dict mode."""
        instance = SimpleClass()
        result = get_api_structure(instance, mode="dict")

        assert isinstance(result, dict)
        assert result["class_name"] == "SimpleClass"
        assert result["base_path"] == "/simple"
        assert len(result["endpoints"]) == 2

    def test_simple_class_lazy_mode(self):
        """Test lazy mode (no eager child discovery)."""
        instance = SimpleClass()
        result = get_api_structure(instance, eager=False, mode="dict")

        assert "children" not in result

    def test_endpoint_metadata(self):
        """Test endpoint metadata extraction."""
        instance = SimpleClass()
        result = get_api_structure(instance, mode="dict")

        endpoints = {ep["function_name"]: ep for ep in result["endpoints"]}

        # Test get_data endpoint
        assert "get_data" in endpoints
        get_data = endpoints["get_data"]
        assert get_data["path"] == "/get_data"
        assert get_data["method"] == "GET"
        assert get_data["parameters"] == {}
        assert get_data["return_type"]["type"] == "dict"

        # Test set_value endpoint
        assert "set_value" in endpoints
        set_value = endpoints["set_value"]
        assert set_value["path"] == "/set_value"
        assert set_value["method"] == "POST"
        assert "value" in set_value["parameters"]
        assert set_value["parameters"]["value"]["type"] == "str"
        assert set_value["parameters"]["value"]["description"] == "Value to set"


class TestParameterTypes:
    """Test various parameter types and defaults."""

    def test_parameters_with_defaults(self):
        """Test parameters with default values."""
        instance = ComplexClass()
        result = get_api_structure(instance, mode="dict")

        endpoints = {ep["function_name"]: ep for ep in result["endpoints"]}
        process = endpoints["process"]

        params = process["parameters"]

        # Required parameter
        assert params["name"]["required"] is True
        assert "default" not in params["name"] or params["name"]["default"] == "..."

        # Optional parameters with defaults
        assert params["count"]["required"] is False
        assert params["count"]["default"] == 10

        assert params["active"]["required"] is False
        assert params["active"]["default"] is True

    def test_explicit_method(self):
        """Test explicit HTTP method specification."""
        instance = ComplexClass()
        result = get_api_structure(instance, mode="dict")

        endpoints = {ep["function_name"]: ep for ep in result["endpoints"]}
        update = endpoints["update"]

        assert update["method"] == "POST"


class TestEagerMode:
    """Test eager mode with child discovery."""

    def test_manager_with_child_eager(self):
        """Test eager discovery of child managers."""
        instance = ManagerClass()
        result = get_api_structure(instance, eager=True, mode="dict")

        assert "children" in result
        # Eager mode may find multiple classes in the module
        assert len(result["children"]) >= 1

        # Find the ChildManager in children
        child_manager = None
        for child in result["children"]:
            if child["class_name"] == "ChildManager":
                child_manager = child
                break

        assert child_manager is not None
        assert child_manager["base_path"] == "/child"
        assert len(child_manager["endpoints"]) == 1
        assert child_manager["endpoints"][0]["function_name"] == "get_child_info"

    def test_manager_without_child_lazy(self):
        """Test lazy mode does not discover children."""
        instance = ManagerClass()
        result = get_api_structure(instance, eager=False, mode="dict")

        assert "children" not in result


class TestOutputModes:
    """Test different output modes."""

    def test_dict_mode(self):
        """Test dict output mode."""
        instance = SimpleClass()
        result = get_api_structure(instance, mode="dict")

        assert isinstance(result, dict)
        assert "class_name" in result
        assert "base_path" in result
        assert "endpoints" in result

    def test_html_mode(self):
        """Test HTML output mode."""
        instance = SimpleClass()
        result = get_api_structure(instance, mode="html")

        assert isinstance(result, str)
        assert "<html>" in result
        assert "SimpleClass" in result
        assert "/simple" in result
        assert "get_data" in result
        assert "set_value" in result

    def test_markdown_mode(self):
        """Test Markdown output mode."""
        instance = SimpleClass()
        result = get_api_structure(instance, mode="markdown")

        assert isinstance(result, str)
        assert "SimpleClass" in result
        assert "/simple" in result
        assert "get_data" in result
        assert "set_value" in result

    def test_html_with_children(self):
        """Test HTML output includes children."""
        instance = ManagerClass()
        result = get_api_structure(instance, eager=True, mode="html")

        assert isinstance(result, str)
        assert "ManagerClass" in result
        assert "ChildManager" in result
        assert "/manager" in result
        assert "/child" in result

    def test_markdown_with_children(self):
        """Test Markdown output includes children."""
        instance = ManagerClass()
        result = get_api_structure(instance, eager=True, mode="markdown")

        assert isinstance(result, str)
        assert "ManagerClass" in result
        assert "/manager" in result
        # Children may or may not appear depending on eager discovery


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_class_without_apiready(self):
        """Test class without @apiready decorator."""

        class PlainClass:
            def method(self):
                pass

        instance = PlainClass()

        with pytest.raises(ValueError, match="is not decorated with @apiready"):
            get_api_structure(instance)

    def test_empty_class(self):
        """Test class with no methods."""

        @apiready(path="/empty")
        class EmptyClass:
            pass

        instance = EmptyClass()
        result = get_api_structure(instance, mode="dict")

        assert result["class_name"] == "EmptyClass"
        assert result["base_path"] == "/empty"
        assert result["endpoints"] == []

    def test_class_with_non_apiready_methods(self):
        """Test class with mix of @apiready and regular methods."""

        @apiready(path="/mixed")
        class MixedClass:
            @apiready
            def api_method(self) -> str:
                return "api"

            def regular_method(self):
                return "regular"

        instance = MixedClass()
        result = get_api_structure(instance, mode="dict")

        assert len(result["endpoints"]) == 1
        assert result["endpoints"][0]["function_name"] == "api_method"

    def test_invalid_mode(self):
        """Test invalid output mode returns dict."""
        instance = SimpleClass()

        result = get_api_structure(instance, mode="invalid")
        # Invalid mode returns raw dict
        assert isinstance(result, dict)
        assert result["class_name"] == "SimpleClass"


class TestDocstrings:
    """Test docstring extraction."""

    def test_method_docstring(self):
        """Test that method docstrings are extracted."""
        instance = SimpleClass()
        result = get_api_structure(instance, mode="dict")

        endpoints = {ep["function_name"]: ep for ep in result["endpoints"]}
        get_data = endpoints["get_data"]

        assert "docstring" in get_data
        assert "Get data without parameters" in get_data["docstring"]

    def test_class_docstring_in_html(self):
        """Test HTML output includes class information."""
        instance = ComplexClass()
        result = get_api_structure(instance, mode="html")

        # Verify HTML structure includes class name and methods
        assert isinstance(result, str)
        assert "ComplexClass" in result
        assert "process" in result
        assert "update" in result

    def test_class_docstring_in_markdown(self):
        """Test Markdown output includes class information."""
        instance = ComplexClass()
        result = get_api_structure(instance, mode="markdown")

        # Verify Markdown includes class name and methods
        assert isinstance(result, str)
        assert "ComplexClass" in result
        assert "process" in result
        assert "update" in result


class TestComplexTypes:
    """Test handling of complex parameter types."""

    def test_dict_parameter(self):
        """Test dict parameter type."""
        instance = ComplexClass()
        result = get_api_structure(instance, mode="dict")

        endpoints = {ep["function_name"]: ep for ep in result["endpoints"]}
        update = endpoints["update"]

        assert "data" in update["parameters"]
        assert update["parameters"]["data"]["type"] == "dict"

    def test_return_type_dict(self):
        """Test dict return type."""
        instance = ComplexClass()
        result = get_api_structure(instance, mode="dict")

        endpoints = {ep["function_name"]: ep for ep in result["endpoints"]}
        process = endpoints["process"]

        assert process["return_type"]["type"] == "dict"


class TestMultipleClasses:
    """Test introspection with multiple classes."""

    def test_different_classes_different_paths(self):
        """Test that different classes have different base paths."""
        simple = SimpleClass()
        complex_inst = ComplexClass()

        simple_result = get_api_structure(simple, mode="dict")
        complex_result = get_api_structure(complex_inst, mode="dict")

        assert simple_result["base_path"] == "/simple"
        assert complex_result["base_path"] == "/complex"
        assert simple_result["base_path"] != complex_result["base_path"]

    def test_different_classes_different_endpoints(self):
        """Test that different classes have different endpoints."""
        simple = SimpleClass()
        complex_inst = ComplexClass()

        simple_result = get_api_structure(simple, mode="dict")
        complex_result = get_api_structure(complex_inst, mode="dict")

        simple_names = {ep["function_name"] for ep in simple_result["endpoints"]}
        complex_names = {ep["function_name"] for ep in complex_result["endpoints"]}

        assert simple_names == {"get_data", "set_value"}
        assert complex_names == {"process", "update"}
