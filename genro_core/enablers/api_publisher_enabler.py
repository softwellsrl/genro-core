# Copyright (c) 2025 Softwell Srl, Milano, Italy
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""API-ready decorator and PublisherBridge for automatic API endpoint generation.

This module provides:
1. @apiready decorator: Marks classes and methods for automatic API endpoint generation
2. PublisherBridge class: Introspects @apiready decorated classes to extract API metadata

Example:
    @apiready(path="/books")
    class BookTable(Table):
        @apiready
        def add(self, **kwargs) -> dict:
            '''Add a new book.'''
            ...

    app = Library()
    app.bridge = PublisherBridge(app)
    structure = app.bridge.get_api_structure(BookTable)
"""

from __future__ import annotations

import inspect
import json
import sys
from functools import wraps
from typing import Any, Callable, get_type_hints, get_origin, get_args


def apiready(
    target: Callable | None = None,
    *,
    path: str | None = None,
    method: str | None = None,
    additem: str | None = None,
    delitem: str | None = None,
    transaction: bool = False
) -> Callable:
    """Decorator to mark classes and methods as API-ready.

    Can be applied to:
    1. Classes: @apiready(path="/books") - marks class as API-ready with base path
    2. Methods: @apiready or @apiready(path="/custom") - marks method for API exposure

    For classes:
        Sets _api_base_path attribute used by methods to build full endpoint paths.

    For methods:
        Analyzes function signature and type hints to automatically generate
        Pydantic request/response models and HTTP method specifications.

    Args:
        target: The class or function to decorate
        path: API path (required for classes, optional for methods)
        method: Optional HTTP method for methods ('GET' or 'POST'). If not provided,
               inferred from function name (read*/get*/list* → GET, else POST)
        additem: Optional name of the method that adds items (for CRUD interfaces)
        delitem: Optional name of the method that deletes items (for CRUD interfaces)
        transaction: If True, method will be executed within a database transaction
                    (default: False). Mutations (POST) typically need transaction=True.

    Returns:
        For classes: Class with _api_base_path attribute set
        For methods: Decorated function with _api_metadata attribute containing:
            - request_fields: Parameter types and defaults
            - return_type: Return type
            - http_method: HTTP method (GET or POST)
            - endpoint_path: Relative path (defaults to function name)
            - docstring: Function documentation
            - transaction: Whether to run in a transaction

    Usage:
        @apiready(path="/books")
        class BookTable:
            @apiready
            def list(self) -> list[dict]: ...

            @apiready(transaction=True)
            def add(self, title: str, author: str) -> dict: ...
    """

    def class_decorator(cls: type) -> type:
        """Decorator for classes - sets _api_base_path and CRUD metadata."""
        if path is None:
            raise ValueError(
                f"@apiready on class {cls.__name__} requires path parameter: "
                f"@apiready(path='/your-path')"
            )
        cls._api_base_path = path

        # Store CRUD metadata if provided
        if additem is not None:
            cls._api_additem = additem
        if delitem is not None:
            cls._api_delitem = delitem

        return cls

    def method_decorator(f: Callable) -> Callable:
        """Decorator for methods - creates API metadata."""
        # Get function signature and type hints
        sig = inspect.signature(f)
        try:
            type_hints = get_type_hints(f, include_extras=True)
        except NameError:
            # Forward references can't be resolved yet, use raw annotations
            type_hints = f.__annotations__.copy() if hasattr(f, '__annotations__') else {}

        # Extract return type
        return_type = type_hints.get("return", Any)

        # Build request fields from parameters (skip 'self' and 'cls')
        request_fields = {}
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            # Get type from type hints, default to Any if not specified
            param_type = type_hints.get(param_name, Any)

            # Handle default values
            if param.default is inspect.Parameter.empty:
                # Required parameter
                request_fields[param_name] = (param_type, ...)
            else:
                # Optional parameter with default
                request_fields[param_name] = (param_type, param.default)

        # Infer HTTP method if not provided
        http_method = method
        if http_method is None:
            func_name = f.__name__
            # GET for read-only operations
            if any(
                func_name.startswith(prefix)
                for prefix in ["read", "get", "list", "exists", "is_", "has_"]
            ):
                http_method = "GET"
            else:
                # POST for mutations
                http_method = "POST"

        # Determine endpoint path (relative to class base path)
        endpoint_path = path if path is not None else f"/{f.__name__}"
        if not endpoint_path.startswith("/"):
            endpoint_path = f"/{endpoint_path}"

        # Store metadata on the function
        f._api_metadata = {
            "request_fields": request_fields,
            "return_type": return_type,
            "http_method": http_method,
            "endpoint_path": endpoint_path,
            "docstring": f.__doc__,
            "transaction": transaction,
        }

        # Preserve original function behavior
        @wraps(f)
        def wrapper(*args, **kwargs):
            return f(*args, **kwargs)

        # Copy metadata to wrapper
        wrapper._api_metadata = f._api_metadata

        return wrapper

    # Determine if decorating a class or a method/function
    if target is None:
        # Called with arguments: @apiready(path="/books") or @apiready(method='POST')
        def deferred_decorator(actual_target):
            if inspect.isclass(actual_target):
                return class_decorator(actual_target)
            else:
                return method_decorator(actual_target)
        return deferred_decorator
    else:
        # Called without arguments: @apiready
        if inspect.isclass(target):
            return class_decorator(target)
        else:
            return method_decorator(target)


class PublisherBridge:
    """Bridge for API publishers to access introspection capabilities.

    This class provides methods to introspect @apiready decorated classes
    and extract API metadata for automatic endpoint generation.

    Usage:
        app = Library()
        app.bridge = PublisherBridge(app)
        structure = app.bridge.get_api_structure(BookTable)
        structure_multi = app.bridge.get_api_structure_multi([BookTable, ShelfTable])
    """

    def __init__(self, app):
        """Initialize PublisherBridge with app reference.

        Args:
            app: Application instance (e.g., Library, GenroMicroApplication)
        """
        self.app = app

    def get_api_structure(
        self,
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
            API structure as JSON string, YAML string, Markdown string, HTML string, or dict

        Example:
            structure = app.bridge.get_api_structure(BookTable, mode="json")
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

        # Add CRUD metadata if available
        if hasattr(target, '_api_additem'):
            structure["additem"] = target._api_additem
        if hasattr(target, '_api_delitem'):
            structure["delitem"] = target._api_delitem

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
            parameters = self._extract_parameter_info(metadata["request_fields"])

            # Extract return type information
            return_info = self._extract_type_info(metadata["return_type"])

            # Build endpoint entry
            endpoint = {
                "path": metadata["endpoint_path"],
                "method": metadata["http_method"],
                "function_name": name,
                "parameters": parameters,
                "return_type": return_info,
                "transaction": metadata.get("transaction", False)
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
            seen_classes = set()

            # 1. Instance attributes (manager pattern)
            if instance is not None:
                for name in dir(instance):
                    if name.startswith('_'):
                        continue
                    try:
                        attr = getattr(instance, name)
                        if hasattr(attr, '__class__') and hasattr(attr.__class__, '_api_base_path'):
                            child_structure = self.get_api_structure(attr, eager=True, mode="dict")
                            class_name = child_structure["class_name"]
                            if class_name not in seen_classes:
                                children.append(child_structure)
                                seen_classes.add(class_name)
                    except:
                        continue

            # 2. Module-level @apiready classes (automatic discovery)
            try:
                module = sys.modules.get(target.__module__)
                if module:
                    for name, obj in vars(module).items():
                        if (inspect.isclass(obj) and
                            hasattr(obj, '_api_base_path') and
                            obj != target):
                            class_name = obj.__name__
                            if class_name not in seen_classes:
                                child_structure = self.get_api_structure(obj, eager=False, mode="dict")
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
            return self._format_as_markdown(structure)
        elif mode.lower() == "html":
            return self._format_as_html(structure)
        else:
            # Return raw dict if mode not recognized
            return structure

    def get_api_structure_multi(
        self,
        targets: list[type | object],
        *,
        eager: bool = True,
        mode: str = "json"
    ) -> str | list[dict]:
        """Extract API structure from multiple @apiready decorated classes.

        Args:
            targets: List of classes or instances to introspect
            eager: If True, recursively collect all API metadata (default: True)
            mode: Output format - "json" (default), "yaml", "markdown", or "html"

        Returns:
            Combined API structures as JSON string, YAML string, or list of dicts

        Example:
            structure = app.bridge.get_api_structure_multi([BookTable, ShelfTable])
        """
        structures = []

        for target in targets:
            structure = self.get_api_structure(target, eager=eager, mode="dict")
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
            return self._format_as_markdown_multi(structures)
        elif mode.lower() == "html":
            return self._format_as_html_multi(structures)
        else:
            # Return raw list if mode not recognized
            return structures

    def _extract_parameter_info(self, request_fields: dict[str, tuple]) -> dict[str, dict]:
        """Extract detailed parameter information from request fields."""
        parameters = {}

        for param_name, (param_type, default_value) in request_fields.items():
            param_info = self._extract_type_info(param_type)
            param_info["required"] = default_value is ...

            if default_value is not ...:
                param_info["default"] = default_value

            parameters[param_name] = param_info

        return parameters

    def _extract_type_info(self, type_hint: Any) -> dict[str, Any]:
        """Extract information from a type hint."""
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
                    actual_type = args[0]
                    info.update(self._extract_type_info(actual_type))

                    if len(args) > 1:
                        for metadata in args[1:]:
                            if isinstance(metadata, str):
                                info["description"] = metadata
                                break
                    return info

            # Handle Union types
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

    def _format_as_markdown(self, structure: dict) -> str:
        """Format API structure as compact Markdown list."""
        lines = []

        lines.append(f"### {structure['class_name']} [{structure['base_path']}]")
        lines.append("")

        for endpoint in structure["endpoints"]:
            method = endpoint['method']
            path = endpoint['path']
            func = endpoint['function_name']
            return_type = endpoint.get("return_type", {})
            return_type_str = return_type.get("type", "None")

            full_path = structure['base_path'] + path

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

            lines.append(
                f"**{func}**<br>"
                f"&nbsp;&nbsp;{method} {full_path} -> {return_type_str}"
                f"{param_line}"
            )
            lines.append("")

        return "\n".join(lines)

    def _format_as_html(self, structure: dict) -> str:
        """Format API structure as HTML."""
        lines = []

        lines.append("<!DOCTYPE html>")
        lines.append("<html>")
        lines.append("<head>")
        lines.append(f"<title>{structure['class_name']} API</title>")
        lines.append("<style>")
        lines.append("body { font-family: monospace; margin: 20px; }")
        lines.append("h3 { color: #333; font-size: 1.5em; font-weight: bold; margin-top: 20px; border-bottom: 2px solid #333; padding-bottom: 5px; }")
        lines.append(".endpoint { margin-bottom: 20px; }")
        lines.append(".name { font-weight: bold; }")
        lines.append(".command { margin-left: 20px; line-height: 1.2; }")
        lines.append(".params { margin-left: 20px; line-height: 1.2; }")
        lines.append("</style>")
        lines.append("</head>")
        lines.append("<body>")

        lines.append(f"<h3>{structure['class_name']} [{structure['base_path']}]</h3>")

        for endpoint in structure["endpoints"]:
            method = endpoint['method']
            path = endpoint['path']
            func = endpoint['function_name']
            return_type = endpoint.get("return_type", {})
            return_type_str = return_type.get("type", "None")

            full_path = structure['base_path'] + path

            lines.append('<div class="endpoint">')
            lines.append(f'  <div class="name">{func}</div>')
            lines.append(f'  <div class="command">{method} {full_path} -&gt; {return_type_str}</div>')

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

        lines.append("</body>")
        lines.append("</html>")

        return "\n".join(lines)

    def _format_as_markdown_multi(self, structures: list[dict]) -> str:
        """Format multiple API structures as combined Markdown document."""
        lines = []

        lines.append("## API Documentation")
        lines.append("")

        for structure in structures:
            lines.append(f"### {structure['class_name']} [{structure['base_path']}]")
            lines.append("")

            for endpoint in structure["endpoints"]:
                method = endpoint['method']
                path = endpoint['path']
                func = endpoint['function_name']
                return_type = endpoint.get("return_type", {})
                return_type_str = return_type.get("type", "None")

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

                lines.append(
                    f"**{func}**<br>"
                    f"&nbsp;&nbsp;{method} {path} -> {return_type_str}"
                    f"{param_line}"
                )
                lines.append("")

            lines.append("")

        return "\n".join(lines)

    def _format_as_html_multi(self, structures: list[dict]) -> str:
        """Format multiple API structures as combined HTML document."""
        lines = []

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

        lines.append("<h2>API Documentation</h2>")

        for structure in structures:
            lines.append('<div class="class-section">')
            lines.append(f"<h3>{structure['class_name']} [{structure['base_path']}]</h3>")

            for endpoint in structure["endpoints"]:
                method = endpoint['method']
                path = endpoint['path']
                func = endpoint['function_name']
                return_type = endpoint.get("return_type", {})
                return_type_str = return_type.get("type", "None")

                lines.append('<div class="endpoint">')
                lines.append(f'  <div class="name">{func}</div>')
                lines.append(f'  <div class="command">{method} {path} -&gt; {return_type_str}</div>')

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

        lines.append("</body>")
        lines.append("</html>")

        return "\n".join(lines)
