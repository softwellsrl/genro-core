"""API structure introspection utilities.

This module provides utilities to extract API metadata from classes decorated
with @apiready, supporting JSON, YAML, HTML, and Markdown output formats.
"""

from __future__ import annotations

import inspect
import json
import sys
from typing import Any, get_type_hints, get_origin, get_args


def get_api_structure(
    target: type | object,
    *,
    eager: bool = True,
    mode: str = "json"
) -> str | dict:
    """Extract API structure from an @apiready decorated class.

    Args:
        target: Class or instance to introspect
        eager: If True, recursively collect all API metadata (default: True)
        mode: Output format - "json" (default), "yaml", "markdown"/"md", or "html"

    Returns:
        API structure as JSON string, YAML string, Markdown string, HTML string, or dict (if mode not recognized)

    Example:
        >>> from genro_storage import StorageManager
        >>> structure = get_api_structure(StorageManager, mode="json")
        >>> print(structure)
    """
    # Keep reference to instance for eager mode
    instance = None if inspect.isclass(target) else target

    # Get the class if instance was passed
    if not inspect.isclass(target):
        target = target.__class__

    # Check if class is decorated with @apiready
    if not hasattr(target, '_api_base_path'):
        raise ValueError(
            f"Class {target.__name__} is not decorated with @apiready. "
            "Only @apiready decorated classes can be introspected."
        )

    # Collect structure
    structure = {
        "class_name": target.__name__,
        "base_path": target._api_base_path,
        "endpoints": []
    }

    # Add class docstring if available
    if target.__doc__:
        structure["docstring"] = inspect.cleandoc(target.__doc__)

    # Iterate through class members to find decorated methods
    for name, method in inspect.getmembers(target, inspect.isfunction):
        # Check if method has API metadata
        if not hasattr(method, '_api_metadata'):
            continue

        metadata = method._api_metadata

        # Extract parameter information
        parameters = _extract_parameter_info(metadata["request_fields"])

        # Extract return type information
        return_info = _extract_type_info(metadata["return_type"])

        # Build endpoint entry
        # Note: path is just the endpoint_path (e.g., "/list_shelves")
        # The Publisher will add the base_path prefix via APIRouter
        endpoint = {
            "path": metadata["endpoint_path"],
            "method": metadata["http_method"],
            "function_name": name,
            "parameters": parameters,
            "return_type": return_info
        }

        # Add docstring if available
        if metadata.get("docstring"):
            endpoint["docstring"] = inspect.cleandoc(metadata["docstring"])

        structure["endpoints"].append(endpoint)

    # Sort endpoints by path for consistent output
    structure["endpoints"].sort(key=lambda x: x["path"])

    # If eager mode, look for @apiready attributes and classes
    if eager:
        children = []
        seen_classes = set()  # Track class names to avoid duplicates

        # 1. Instance attributes (manager pattern)
        if instance is not None:
            # Iterate through instance attributes to find nested @apiready objects
            for name in dir(instance):
                if name.startswith('_'):
                    continue
                try:
                    attr = getattr(instance, name)
                    # Check if attribute has _api_base_path (is @apiready)
                    if hasattr(attr, '__class__') and hasattr(attr.__class__, '_api_base_path'):
                        # Recursively collect structure
                        child_structure = get_api_structure(attr, eager=True, mode="dict")
                        class_name = child_structure["class_name"]
                        if class_name not in seen_classes:
                            children.append(child_structure)
                            seen_classes.add(class_name)
                except:
                    continue

        # 2. Module-level @apiready classes (automatic discovery)
        try:
            # Get module where the class is defined
            module = sys.modules.get(target.__module__)
            if module:
                # Search module namespace for @apiready classes
                for name, obj in vars(module).items():
                    if (inspect.isclass(obj) and
                        hasattr(obj, '_api_base_path') and
                        obj != target):  # Don't include self
                        class_name = obj.__name__
                        # Skip if already added as instance attribute
                        if class_name not in seen_classes:
                            # Recursively collect structure (non-eager for classes)
                            child_structure = get_api_structure(obj, eager=False, mode="dict")
                            children.append(child_structure)
                            seen_classes.add(class_name)
        except:
            pass

        if children:
            structure["children"] = children

    # Format output according to mode
    if mode.lower() == "json":
        return json.dumps(structure, indent=2, default=str)
    elif mode.lower() == "yaml":
        try:
            import yaml
            return yaml.dump(structure, default_flow_style=False, sort_keys=False)
        except ImportError:
            raise ImportError(
                "PyYAML is required for YAML output. "
                "Install it with: pip install pyyaml"
            )
    elif mode.lower() in ("markdown", "md"):
        return _format_as_markdown(structure)
    elif mode.lower() == "html":
        return _format_as_html(structure)
    else:
        # Return raw dict if mode not recognized
        return structure


def _extract_parameter_info(request_fields: dict[str, tuple]) -> dict[str, dict]:
    """Extract detailed parameter information from request fields.

    Args:
        request_fields: Dictionary mapping parameter names to (type, default) tuples

    Returns:
        Dictionary with detailed parameter information
    """
    parameters = {}

    for param_name, (param_type, default_value) in request_fields.items():
        param_info = _extract_type_info(param_type)

        # Determine if parameter is required (no default value)
        param_info["required"] = default_value is ...

        # Add default value if present
        if default_value is not ...:
            param_info["default"] = default_value

        parameters[param_name] = param_info

    return parameters


def _extract_type_info(type_hint: Any) -> dict[str, Any]:
    """Extract information from a type hint.

    Handles:
    - Simple types (str, int, bool, etc.)
    - Union types (str | int)
    - Generic types (list[str], dict[str, int])
    - Annotated types with descriptions
    - Forward references ("ClassName")

    Args:
        type_hint: The type hint to analyze

    Returns:
        Dictionary with type information
    """
    info = {}

    # Handle None type
    if type_hint is type(None):
        info["type"] = "None"
        return info

    # Handle string forward references
    if isinstance(type_hint, str):
        info["type"] = type_hint
        return info

    # Check if it's an Annotated type with description
    origin = get_origin(type_hint)

    if origin is not None:
        # Handle typing.Annotated
        if hasattr(origin, '__name__') and origin.__name__ == 'Annotated':
            args = get_args(type_hint)
            if args:
                # First arg is the actual type
                actual_type = args[0]
                info.update(_extract_type_info(actual_type))

                # Additional args are metadata (usually descriptions)
                if len(args) > 1:
                    for metadata in args[1:]:
                        if isinstance(metadata, str):
                            info["description"] = metadata
                            break
                return info

        # Handle Union types (including | syntax in Python 3.10+)
        if origin is type(None) or (hasattr(origin, '__name__') and 'Union' in origin.__name__):
            args = get_args(type_hint)
            if args:
                type_names = []
                for arg in args:
                    if arg is type(None):
                        type_names.append("None")
                    elif hasattr(arg, '__name__'):
                        type_names.append(arg.__name__)
                    else:
                        type_names.append(str(arg))
                info["type"] = " | ".join(type_names)
                return info

        # Handle generic types (list, dict, etc.)
        if hasattr(origin, '__name__'):
            args = get_args(type_hint)
            if args:
                arg_names = []
                for arg in args:
                    if hasattr(arg, '__name__'):
                        arg_names.append(arg.__name__)
                    else:
                        arg_names.append(str(arg))
                info["type"] = f"{origin.__name__}[{', '.join(arg_names)}]"
            else:
                info["type"] = origin.__name__
            return info

    # Handle simple types with __name__
    if hasattr(type_hint, '__name__'):
        info["type"] = type_hint.__name__
        return info

    # Fallback: convert to string
    info["type"] = str(type_hint)
    return info


def get_api_structure_multi(
    *targets: type | object,
    eager: bool = True,
    mode: str = "json"
) -> str | list[dict]:
    """Extract API structure from multiple @apiready decorated classes.

    Args:
        *targets: Classes or instances to introspect
        eager: If True, recursively collect all API metadata (default: True)
        mode: Output format - "json" (default) or "yaml"

    Returns:
        API structures as JSON string, YAML string, or list of dicts

    Example:
        >>> from genro_storage import StorageManager
        >>> from genro_storage.node import StorageNode
        >>> structure = get_api_structure_multi(
        ...     StorageManager, StorageNode, mode="json"
        ... )
    """
    structures = []

    for target in targets:
        # Get structure as dict
        structure = get_api_structure(target, eager=eager, mode="dict")
        structures.append(structure)

    # Format output according to mode
    if mode.lower() == "json":
        return json.dumps(structures, indent=2, default=str)
    elif mode.lower() == "yaml":
        try:
            import yaml
            return yaml.dump(structures, default_flow_style=False, sort_keys=False)
        except ImportError:
            raise ImportError(
                "PyYAML is required for YAML output. "
                "Install it with: pip install pyyaml"
            )
    elif mode.lower() in ("markdown", "md"):
        return _format_as_markdown_multi(structures)
    elif mode.lower() == "html":
        return _format_as_html_multi(structures)
    else:
        # Return raw list if mode not recognized
        return structures


def _format_as_html(structure: dict) -> str:
    """Format API structure as HTML.

    Args:
        structure: API structure dictionary

    Returns:
        HTML-formatted string
    """
    lines = []

    # HTML header with minimal CSS
    lines.append("<!DOCTYPE html>")
    lines.append("<html>")
    lines.append("<head>")
    lines.append(f"<title>{structure['class_name']} API</title>")
    lines.append("<style>")
    lines.append("body { font-family: monospace; margin: 20px; }")
    lines.append("h3 { color: #333; font-size: 1.5em; font-weight: bold; margin-top: 20px; border-bottom: 2px solid #333; padding-bottom: 5px; }")
    lines.append("h4 { color: #555; font-size: 1.2em; font-weight: bold; margin-top: 15px; border-bottom: 1px solid #999; padding-bottom: 3px; }")
    lines.append(".endpoint { margin-bottom: 20px; }")
    lines.append(".child { margin-left: 20px; padding-left: 20px; border-left: 3px solid #ccc; }")
    lines.append(".child .endpoint { margin-left: 20px; }")
    lines.append(".name { font-weight: bold; }")
    lines.append(".command { margin-left: 20px; line-height: 1.2; }")
    lines.append(".params { margin-left: 20px; line-height: 1.2; }")
    lines.append(".child .name { margin-left: 20px; }")
    lines.append(".child .command { margin-left: 40px; }")
    lines.append(".child .params { margin-left: 40px; }")
    lines.append("</style>")
    lines.append("</head>")
    lines.append("<body>")

    # Title
    lines.append(f"<h3>{structure['class_name']} [{structure['base_path']}]</h3>")

    # Endpoints
    for endpoint in structure["endpoints"]:
        method = endpoint['method']
        path = endpoint['path']
        func = endpoint['function_name']
        return_type = endpoint.get("return_type", {})
        return_type_str = return_type.get("type", "None")

        # Construct full path for display (base_path + endpoint path)
        full_path = structure['base_path'] + path

        lines.append('<div class="endpoint">')
        lines.append(f'  <div class="name">{func}</div>')
        lines.append(f'  <div class="command">{method} {full_path} -&gt; {return_type_str}</div>')

        # Parameters
        params = endpoint.get("parameters", {})
        if params:
            param_list = []
            for param_name, param_info in params.items():
                param_type = param_info.get("type", "Any")
                required = param_info.get("required", False)
                default = param_info.get("default", "")

                if required:
                    param_list.append(f"{param_name} {param_type}")
                else:
                    if default == "":
                        default_str = ""
                    elif default is None:
                        default_str = "None"
                    else:
                        default_str = str(default)
                    param_list.append(f"{param_name} {param_type}={default_str}")

            lines.append(f'  <div class="params">Parameters: {", ".join(param_list)}</div>')

        lines.append('</div>')

    # Render children if present
    if "children" in structure:
        for child in structure["children"]:
            lines.append('<div class="child">')
            lines.append(f"<h4>{child['class_name']} [{child['base_path']}]</h4>")

            # Child endpoints
            for endpoint in child["endpoints"]:
                method = endpoint['method']
                path = endpoint['path']
                func = endpoint['function_name']
                return_type = endpoint.get("return_type", {})
                return_type_str = return_type.get("type", "None")

                # Construct full path for display (child's base_path + endpoint path)
                full_path = child['base_path'] + path

                lines.append('<div class="endpoint">')
                lines.append(f'  <div class="name">{func}</div>')
                lines.append(f'  <div class="command">{method} {full_path} -&gt; {return_type_str}</div>')

                # Parameters
                params = endpoint.get("parameters", {})
                if params:
                    param_list = []
                    for param_name, param_info in params.items():
                        param_type = param_info.get("type", "Any")
                        required = param_info.get("required", False)
                        default = param_info.get("default", "")

                        if required:
                            param_list.append(f"{param_name} {param_type}")
                        else:
                            if default == "":
                                default_str = ""
                            elif default is None:
                                default_str = "None"
                            else:
                                default_str = str(default)
                            param_list.append(f"{param_name} {param_type}={default_str}")

                    lines.append(f'  <div class="params">Parameters: {", ".join(param_list)}</div>')

                lines.append('</div>')

            lines.append('</div>')

    # HTML footer
    lines.append("</body>")
    lines.append("</html>")

    return "\n".join(lines)


def _format_as_markdown(structure: dict) -> str:
    """Format API structure as compact Markdown list.

    Args:
        structure: API structure dictionary

    Returns:
        Markdown-formatted string (compact, no docstrings)
    """
    lines = []

    # Title: ClassName [/base_path]
    lines.append(f"### {structure['class_name']} [{structure['base_path']}]")
    lines.append("")

    for endpoint in structure["endpoints"]:
        method = endpoint['method']
        path = endpoint['path']
        func = endpoint['function_name']
        return_type = endpoint.get("return_type", {})
        return_type_str = return_type.get("type", "None")

        # Construct full path for display (base_path + endpoint path)
        full_path = structure['base_path'] + path

        # Parameters (compact, one line)
        params = endpoint.get("parameters", {})
        param_line = ""
        if params:
            param_list = []
            for param_name, param_info in params.items():
                param_type = param_info.get("type", "Any")
                required = param_info.get("required", False)
                default = param_info.get("default", "")

                if required:
                    param_list.append(f"{param_name} {param_type}")
                else:
                    if default == "":
                        default_str = ""
                    elif default is None:
                        default_str = "None"
                    else:
                        default_str = str(default)
                    param_list.append(f"{param_name} {param_type}={default_str}")

            param_line = f"<br>&nbsp;&nbsp;Parameters: {', '.join(param_list)}"

        # Use HTML for tight control: name, command, params (tight), then space
        lines.append(
            f"**{func}**<br>"
            f"&nbsp;&nbsp;{method} {full_path} -> {return_type_str}"
            f"{param_line}"
        )
        lines.append("")

    return "\n".join(lines)


def _format_as_html_multi(structures: list[dict]) -> str:
    """Format multiple API structures as combined HTML document.

    Args:
        structures: List of API structure dictionaries

    Returns:
        HTML-formatted string with all classes
    """
    lines = []

    # HTML header with minimal CSS
    lines.append("<!DOCTYPE html>")
    lines.append("<html>")
    lines.append("<head>")
    lines.append("<title>API Documentation</title>")
    lines.append("<style>")
    lines.append("body { font-family: monospace; margin: 20px; }")
    lines.append("h2 { color: #333; border-bottom: 2px solid #333; padding-bottom: 5px; }")
    lines.append("h3 { color: #555; }")
    lines.append(".class-section { margin-bottom: 40px; }")
    lines.append(".endpoint { margin-bottom: 20px; }")
    lines.append(".name { font-weight: bold; }")
    lines.append(".command { margin-left: 20px; line-height: 1.2; }")
    lines.append(".params { margin-left: 20px; line-height: 1.2; }")
    lines.append("</style>")
    lines.append("</head>")
    lines.append("<body>")

    # Title
    lines.append("<h2>API Documentation</h2>")

    # Each class section
    for structure in structures:
        lines.append('<div class="class-section">')
        lines.append(f"<h3>{structure['class_name']} [{structure['base_path']}]</h3>")

        # Endpoints
        for endpoint in structure["endpoints"]:
            method = endpoint['method']
            path = endpoint['path']
            func = endpoint['function_name']
            return_type = endpoint.get("return_type", {})
            return_type_str = return_type.get("type", "None")

            lines.append('<div class="endpoint">')
            lines.append(f'  <div class="name">{func}</div>')
            lines.append(f'  <div class="command">{method} {path} -&gt; {return_type_str}</div>')

            # Parameters
            params = endpoint.get("parameters", {})
            if params:
                param_list = []
                for param_name, param_info in params.items():
                    param_type = param_info.get("type", "Any")
                    required = param_info.get("required", False)
                    default = param_info.get("default", "")

                    if required:
                        param_list.append(f"{param_name} {param_type}")
                    else:
                        if default == "":
                            default_str = ""
                        elif default is None:
                            default_str = "None"
                        else:
                            default_str = str(default)
                        param_list.append(f"{param_name} {param_type}={default_str}")

                lines.append(f'  <div class="params">Parameters: {", ".join(param_list)}</div>')

            lines.append('</div>')

        lines.append('</div>')

    # HTML footer
    lines.append("</body>")
    lines.append("</html>")

    return "\n".join(lines)


def _format_as_markdown_multi(structures: list[dict]) -> str:
    """Format multiple API structures as combined Markdown document.

    Args:
        structures: List of API structure dictionaries

    Returns:
        Markdown-formatted string with all classes (compact, no docstrings)
    """
    lines = []

    # Title
    lines.append("## API Documentation")
    lines.append("")

    for structure in structures:
        # Class title: ClassName [/base_path]
        lines.append(f"### {structure['class_name']} [{structure['base_path']}]")
        lines.append("")

        for endpoint in structure["endpoints"]:
            method = endpoint['method']
            path = endpoint['path']
            func = endpoint['function_name']
            return_type = endpoint.get("return_type", {})
            return_type_str = return_type.get("type", "None")

            # Parameters (compact, one line)
            params = endpoint.get("parameters", {})
            param_line = ""
            if params:
                param_list = []
                for param_name, param_info in params.items():
                    param_type = param_info.get("type", "Any")
                    required = param_info.get("required", False)
                    default = param_info.get("default", "")

                    if required:
                        param_list.append(f"{param_name} {param_type}")
                    else:
                        if default == "":
                            default_str = ""
                        elif default is None:
                            default_str = "None"
                        else:
                            default_str = str(default)
                        param_list.append(f"{param_name} {param_type}={default_str}")

                param_line = f"<br>&nbsp;&nbsp;Parameters: {', '.join(param_list)}"

            # Use HTML for tight control: name, command, params (tight), then space
            lines.append(
                f"**{func}**<br>"
                f"&nbsp;&nbsp;{method} {path} -> {return_type_str}"
                f"{param_line}"
            )
            lines.append("")

        lines.append("")  # Extra space between classes

    return "\n".join(lines)
