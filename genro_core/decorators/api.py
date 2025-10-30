"""API-ready decorator for automatic API endpoint generation.

This module provides the @apiready decorator that marks methods for automatic
API endpoint generation with Pydantic-based request/response models.

Example:
    class MyBackend:
        @apiready
        def read_file(self, path: str, encoding: str = 'utf-8') -> str:
            '''Read file content.'''
            ...

        @apiready(method='POST')
        def delete_file(self, path: str) -> None:
            '''Delete file.'''
            ...
"""

from __future__ import annotations

import inspect
from functools import wraps
from typing import Any, Callable, get_type_hints


def apiready(func: Callable | None = None, *, method: str | None = None) -> Callable:
    """Decorator to mark methods as API-ready with auto-generated metadata.

    This decorator analyzes the function signature and type hints to automatically
    generate Pydantic request/response models and HTTP method specifications.

    Args:
        func: The function to decorate (when used as @apiready)
        method: Optional HTTP method ('GET' or 'POST'). If not provided, it will
               be inferred from the function name:
               - read*, get*, list*, exists*, is_*, has_* → GET
               - everything else → POST

    Returns:
        Decorated function with _api_metadata attribute containing:
        - request_model: Pydantic model for request parameters
        - response_model: Pydantic model for response
        - http_method: HTTP method (GET or POST)
        - endpoint_name: API endpoint name (function name)
        - docstring: Function documentation

    Usage:
        @apiready                    # Auto-infer HTTP method
        @apiready(method='POST')     # Explicit HTTP method

    The decorated function retains its original behavior while gaining API metadata
    that can be used by API frameworks (FastAPI, etc.) to auto-generate endpoints.
    """

    def decorator(f: Callable) -> Callable:
        # Get function signature and type hints
        sig = inspect.signature(f)
        type_hints = get_type_hints(f)

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

        # Store metadata on the function
        f._api_metadata = {
            "request_fields": request_fields,
            "return_type": return_type,
            "http_method": http_method,
            "endpoint_name": f.__name__,
            "docstring": f.__doc__,
        }

        # Preserve original function behavior
        @wraps(f)
        def wrapper(*args, **kwargs):
            return f(*args, **kwargs)

        # Copy metadata to wrapper
        wrapper._api_metadata = f._api_metadata

        return wrapper

    # Handle both @apiready and @apiready(...) syntax
    if func is None:
        # Called with arguments: @apiready(method='POST')
        return decorator
    else:
        # Called without arguments: @apiready
        return decorator(func)
