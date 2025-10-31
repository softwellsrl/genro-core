# @apiready Architecture and Design

**Status:** Design Document
**Version:** 1.0
**Date:** 2025-01-30
**Project:** genro-core

---

## Table of Contents

1. [Overview](#overview)
2. [Core Philosophy](#core-philosophy)
3. [Architecture Layers](#architecture-layers)
4. [The @apiready Decorator](#the-apiready-decorator)
5. [Lazy Hierarchical Navigation](#lazy-hierarchical-navigation)
6. [Dual Interface Pattern](#dual-interface-pattern)
7. [Design Decisions](#design-decisions)
8. [Usage Examples](#usage-examples)
9. [Comparison with Other Approaches](#comparison-with-other-approaches)
10. [Best Practices](#best-practices)
11. [Implementation Guide](#implementation-guide)
12. [Future Considerations](#future-considerations)

---

## Overview

The `@apiready` decorator system is a metadata-driven architecture for automatically generating web APIs from Python business logic libraries. It enables a clean separation of concerns where business logic remains completely decoupled from web frameworks while still being able to expose rich, discoverable APIs.

### Key Features

- **Zero Coupling**: Business logic libraries have no dependencies on web frameworks
- **Passive Metadata**: The decorator only adds metadata, never alters behavior
- **Lazy Discovery**: API structure is discovered incrementally as needed
- **Dual Interface**: Single metadata source generates both human UI and machine API
- **Universal Pattern**: Works with any Python library, not tied to specific domains
- **Type-Driven**: Leverages Python type hints and Pydantic for schema generation

### The Problem It Solves

Traditional web framework approaches force coupling between business logic and presentation:

```python
# Traditional approach - business logic coupled to FastAPI
from fastapi import FastAPI, HTTPException

class StorageManager:
    def read_file(self, path: str) -> str:
        # Business logic mixed with web concerns
        if not self.exists(path):
            raise HTTPException(status_code=404, detail="File not found")
        return self._read_file(path)

# Now this library MUST have FastAPI as a dependency
```

The `@apiready` pattern solves this:

```python
# @apiready approach - pure business logic
from genro_core.decorators.api import apiready

@apiready(path="/storage")
class StorageManager:
    @apiready
    def read_file(self, path: str) -> str:
        """Read a file from storage."""
        # Pure business logic, no web framework concerns
        return self._read_file(path)

# Library has NO web framework dependencies
# Metadata is extracted elsewhere by publisher
```

---

## Core Philosophy

### 1. Separation of Concerns

The architecture maintains strict separation between three concerns:

- **Business Logic**: What the system does (domain logic)
- **Metadata**: What can be exposed via APIs (API contracts)
- **Presentation**: How APIs are exposed (web frameworks)

### 2. Metadata as Contract

The decorator defines a **contract** between business logic and its consumers:

- What methods can be called remotely
- What parameters they accept
- What types they return
- How they should be documented

This contract is **passive** - it doesn't change behavior, only describes capabilities.

### 3. Lazy Discovery

Rather than generating a complete API specification upfront, the system discovers structure incrementally:

- First call: Get top-level structure
- Subsequent calls: Drill down into specific paths
- Efficient: Only loads what's needed
- Scalable: Works with massive APIs

### 4. Universal Applicability

This pattern is not specific to any domain. It can be applied to:

- Storage systems (genro-storage)
- Authentication systems (genro-auth)
- ORM layers (genro-orm)
- Any Python library that needs API exposure

---

## Architecture Layers

The system consists of three distinct layers that communicate through well-defined interfaces:

```
┌─────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                       │
│                                                              │
│  ┌──────────────────┐              ┌────────────────────┐  │
│  │   NiceGUI Admin  │              │  OpenAPI Consumer  │  │
│  │   (Human UI)     │              │  (Machine API)     │  │
│  └────────┬─────────┘              └──────────┬─────────┘  │
│           │                                    │            │
│           └────────────────┬───────────────────┘            │
│                            │                                │
└────────────────────────────┼────────────────────────────────┘
                             │
                             │ Reads Metadata
                             │
┌────────────────────────────▼────────────────────────────────┐
│                      METADATA LAYER                          │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  @apiready Decorators + get_api_structure()         │   │
│  │                                                      │   │
│  │  - Method signatures                                │   │
│  │  - Type hints                                       │   │
│  │  - Docstrings                                       │   │
│  │  - Path hierarchies                                 │   │
│  │  - JSON Schema                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└────────────────────────────┬────────────────────────────────┘
                             │
                             │ No Dependencies
                             │
┌────────────────────────────▼────────────────────────────────┐
│                    BUSINESS LOGIC LAYER                      │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Pure Python Libraries                              │   │
│  │                                                      │   │
│  │  - StorageManager (genro-storage)                   │   │
│  │  - AuthManager (genro-auth)                         │   │
│  │  - ORM Classes (genro-orm)                          │   │
│  │  - Any other business logic                         │   │
│  │                                                      │   │
│  │  NO web framework dependencies                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

#### Business Logic Layer

**Responsibilities:**
- Implement domain logic
- Handle data processing
- Manage state and resources
- Provide clear, typed interfaces

**Does NOT:**
- Import web frameworks
- Handle HTTP concerns
- Parse request data
- Format responses

#### Metadata Layer

**Responsibilities:**
- Store API metadata on methods/classes
- Provide introspection capabilities
- Define API structure and hierarchy
- Expose type information

**Does NOT:**
- Execute business logic
- Handle web requests
- Configure web servers
- Manage routing

#### Presentation Layer (Publisher)

**Responsibilities:**
- Read metadata from business logic
- Configure web framework (FastAPI)
- Generate OpenAPI/Swagger documentation
- Render admin UI (NiceGUI)
- Handle HTTP concerns

**Does NOT:**
- Implement business logic
- Store metadata
- Modify decorated classes

---

## The @apiready Decorator

### Basic Usage

The decorator can be applied to both classes and methods:

```python
from genro_core.decorators.api import apiready

@apiready(path="/storage")
class StorageManager:
    """Storage management system."""

    @apiready
    def read_file(self, path: str, encoding: str = 'utf-8') -> str:
        """Read a file from storage.

        Args:
            path: Path to the file
            encoding: Text encoding to use

        Returns:
            File contents as string
        """
        return self._read_file(path, encoding)

    @apiready
    def list_files(self, directory: str = "/") -> list[str]:
        """List files in a directory.

        Args:
            directory: Directory path to list

        Returns:
            List of file names
        """
        return self._list_directory(directory)
```

### What the Decorator Does

The decorator performs the following actions:

1. **Extracts Type Hints**: Reads parameter and return type annotations
2. **Captures Signature**: Stores method signature for introspection
3. **Preserves Docstrings**: Maintains documentation for API generation
4. **Infers HTTP Method**: Determines appropriate HTTP verb (GET/POST)
5. **Composes Paths**: Combines class base path with method path
6. **Stores Metadata**: Adds `_api_metadata` attribute to methods

### Metadata Structure

Example metadata stored on a method:

```python
{
    "request_fields": {
        "path": (str, ...),  # Required parameter
        "encoding": (str, "utf-8")  # Optional with default
    },
    "return_type": str,
    "http_method": "GET",  # Inferred from method name
    "endpoint_path": "/storage/read_file",
    "docstring": "Read a file from storage.",
    "signature": <Signature object>,
    "class_path": "/storage"
}
```

### HTTP Method Inference

The decorator automatically infers HTTP methods based on method names:

- **GET**: `read_*`, `get_*`, `list_*`, `exists`, `is*`, `has_*`
- **POST**: Everything else (write, delete, create, update, configure, etc.)

This follows RESTful conventions:
- GET for safe, idempotent operations (read-only)
- POST for operations that modify state

---

## Lazy Hierarchical Navigation

### The Problem with Eager Loading

Traditional API discovery loads everything upfront:

```python
# Eager loading - loads ENTIRE API structure
api_spec = get_complete_api_spec()
# Potentially thousands of endpoints loaded
# High memory usage
# Slow startup time
```

### The Lazy Solution

The `@apiready` system uses **lazy hierarchical navigation**:

```python
# First call - top level only
structure = get_api_structure()
# Returns: {
#   "storage": {"path": "/storage", "methods": [...], "children": ["nodes"]},
#   "auth": {"path": "/auth", "methods": [...], "children": ["users", "roles"]}
# }

# Second call - drill into specific path
storage_structure = get_api_structure(path="storage")
# Returns: {
#   "nodes": {"path": "/storage/nodes", "methods": [...]},
#   "mounts": {"path": "/storage/mounts", "methods": [...]}
# }

# Third call - drill deeper
nodes_structure = get_api_structure(path="storage/nodes")
# Returns detailed node operations
```

### Navigation Pattern

The navigation pattern is:

1. **Root Level** (no path): Returns top-level services
2. **Service Level** (path="storage"): Returns service's main classes
3. **Class Level** (path="storage/manager"): Returns class methods
4. **Deep Paths** (path="storage/nodes/operations"): Follows hierarchy

### Path Composition

Paths are composed hierarchically:

```python
@apiready(path="/storage")
class StorageManager:
    # Base path: /storage

    @apiready
    def configure(self, config: dict) -> None:
        # Full path: /storage/configure
        pass

    @apiready
    def get_node(self, mount: str, path: str) -> "StorageNode":
        # Full path: /storage/get_node
        # Returns: object with its own @apiready methods
        pass

@apiready(path="/storage/nodes")
class StorageNode:
    # Base path: /storage/nodes

    @apiready
    def read(self) -> bytes:
        # Full path: /storage/nodes/read
        pass
```

### Benefits of Lazy Loading

1. **Performance**: Only loads what's needed
2. **Scalability**: Works with huge APIs
3. **Memory Efficiency**: Minimal memory footprint
4. **Natural Discovery**: Mirrors user's exploration pattern
5. **Caching Friendly**: Each path can be cached independently

---

## Dual Interface Pattern

The system generates two distinct interfaces from the same metadata:

### 1. Admin UI (NiceGUI)

**Target Audience**: System administrators, developers, operators

**Characteristics:**
- Human-friendly visual interface
- Form-based interaction
- Real-time feedback
- Context-sensitive help
- Visual data exploration

**Example Flow:**
```
User opens NiceGUI admin panel
  ↓
Sees list of available services (storage, auth, etc.)
  ↓
Clicks "Storage" service
  ↓
Sees StorageManager operations
  ↓
Clicks "Read File" operation
  ↓
Fills form: path="/data/file.txt", encoding="utf-8"
  ↓
Clicks "Execute"
  ↓
Sees file contents displayed
```

### 2. Consumer API (OpenAPI/REST)

**Target Audience**: External applications, scripts, integrations

**Characteristics:**
- Machine-readable OpenAPI spec
- RESTful HTTP endpoints
- JSON request/response
- Swagger UI for exploration
- Authentication and rate limiting

**Example API:**
```http
GET /api/storage/read_file?path=/data/file.txt&encoding=utf-8
Authorization: Bearer <token>

Response:
{
  "success": true,
  "data": "file contents here..."
}
```

### Why Dual Interface?

Different consumers have different needs:

| Aspect | Admin UI | Consumer API |
|--------|----------|--------------|
| Users | Humans | Applications |
| Interaction | Visual, exploratory | Programmatic, automated |
| Documentation | Inline help | OpenAPI spec |
| Validation | Form validation | Schema validation |
| Error Handling | User-friendly messages | HTTP status codes + JSON |
| Authentication | Session-based | Token-based (JWT/OAuth) |

### Single Source of Truth

Both interfaces are generated from the **same metadata**:

```python
@apiready
def read_file(self, path: str, encoding: str = 'utf-8') -> str:
    """Read a file from storage."""
    return self._read_file(path, encoding)

# NiceGUI generates:
# - Text input for 'path' (required)
# - Dropdown for 'encoding' with default 'utf-8'
# - Button "Read File"
# - Text area to display results

# FastAPI generates:
# - GET /storage/read_file endpoint
# - Query parameters: path, encoding
# - Response schema: string
# - OpenAPI documentation
```

---

## Design Decisions

### 1. Why Decorators?

**Decision**: Use Python decorators rather than configuration files or DSL.

**Rationale:**
- Keeps metadata close to code
- Type-safe with Python type hints
- IDE support (autocomplete, type checking)
- No context switching between files
- Version controlled with code

**Alternatives Considered:**
- YAML/JSON configuration files (rejected: separated from code)
- Custom DSL (rejected: additional learning curve)
- Code generation (rejected: two sources of truth)

### 2. Why Passive Metadata?

**Decision**: Decorator only adds metadata, never modifies behavior.

**Rationale:**
- Business logic works identically with or without decorator
- Easy to test (test business logic directly)
- No "magic" behavior
- Clear separation of concerns
- Can be removed without breaking code

**Example:**
```python
@apiready
def calculate(self, x: int, y: int) -> int:
    return x + y

# Works identically to:
def calculate(self, x: int, y: int) -> int:
    return x + y

# Decorator only adds _api_metadata attribute
```

### 3. Why Lazy Navigation?

**Decision**: Discover API structure incrementally, not all at once.

**Rationale:**
- Large APIs with thousands of endpoints are common
- Users typically explore small subset
- Reduces initial load time
- Scales to any API size
- Natural exploration pattern

**Alternative Considered:**
- Eager loading (rejected: doesn't scale, slow startup)

### 4. Why Path-Based Hierarchy?

**Decision**: Use URL-like paths to organize API structure.

**Rationale:**
- Familiar to web developers
- Mirrors REST conventions
- Easy to understand
- Natural composition
- Supports deep nesting

**Example:**
```
/storage                      # Root service
/storage/manager              # Manager class
/storage/manager/configure    # Configuration method
/storage/nodes                # Nodes subsystem
/storage/nodes/read           # Node read operation
```

### 5. Why Type Hints Over Schemas?

**Decision**: Use Python type hints as primary source of schema information.

**Rationale:**
- Already present in well-written Python code
- IDE support and static analysis
- Pydantic can generate JSON Schema from types
- Single source of truth
- No duplication

**Enhancement**: Use `typing.Annotated` for additional metadata:

```python
from typing import Annotated

@apiready
def read_file(
    self,
    path: Annotated[str, "Path to file in storage"],
    encoding: Annotated[str, "Text encoding"] = 'utf-8'
) -> Annotated[str, "File contents"]:
    """Read a file from storage."""
    return self._read_file(path, encoding)
```

### 6. Why Separate Publisher?

**Decision**: Keep decorator separate from web framework integration.

**Rationale:**
- Business logic has zero web framework dependencies
- Can support multiple publishers (FastAPI, Flask, Django)
- Publisher can be updated independently
- Testing is simpler
- Clear separation of concerns

**Architecture:**
```
genro-storage         # Business logic + @apiready
  ↓ (depends on)
genro-core            # @apiready decorator
  ↓ (no dependency)
genro-api-publisher   # Reads metadata, configures FastAPI
  ↓ (depends on)
FastAPI, NiceGUI      # Web frameworks
```

---

## Usage Examples

### Example 1: Storage Manager

```python
from genro_core.decorators.api import apiready
from typing import Annotated

@apiready(path="/storage")
class StorageManager:
    """Unified storage management system."""

    @apiready
    def configure(
        self,
        source: Annotated[str | list[dict], "Mount configuration"]
    ) -> None:
        """Configure storage mounts.

        Args:
            source: Either a path to config file or list of mount configs
        """
        self._configure(source)

    @apiready
    def get_node(
        self,
        mount_or_path: Annotated[str, "Mount name or full path"]
    ) -> "StorageNode":
        """Get a storage node.

        Args:
            mount_or_path: Mount name (e.g., 'data') or full path (e.g., 'data://file.txt')

        Returns:
            StorageNode instance for the path
        """
        return self._get_node(mount_or_path)

    @apiready
    def list_mounts(self) -> list[str]:
        """Get list of configured mount names.

        Returns:
            List of mount point names
        """
        return list(self._mounts.keys())
```

### Example 2: Storage Node

```python
from genro_core.decorators.api import apiready
from typing import Annotated

@apiready(path="/storage/nodes")
class StorageNode:
    """Represents a file or directory in storage."""

    @apiready
    def read(
        self,
        mode: Annotated[str, "Read mode: 'text' or 'binary'"] = "text",
        encoding: Annotated[str, "Text encoding"] = "utf-8"
    ) -> str | bytes:
        """Read file contents.

        Args:
            mode: Read mode ('text' or 'binary')
            encoding: Text encoding (if mode='text')

        Returns:
            File contents as string or bytes
        """
        return self._read(mode, encoding)

    @apiready
    def write(
        self,
        data: Annotated[str | bytes, "Data to write"],
        mode: Annotated[str, "Write mode"] = "text"
    ) -> None:
        """Write data to file.

        Args:
            data: Data to write
            mode: Write mode ('text' or 'binary')
        """
        self._write(data, mode)

    @apiready
    def get_children(self) -> list[dict]:
        """List directory contents.

        Returns:
            List of child nodes with metadata
        """
        return [
            {
                "name": child.name,
                "is_dir": child.is_dir,
                "size": child.size,
                "modified": child.modified_time
            }
            for child in self._list_children()
        ]
```

### Example 3: API Discovery

```python
from genro_core.api import get_api_structure

# Get top-level structure
root = get_api_structure()
print(root.keys())  # ['storage', 'auth', 'orm', ...]

# Get storage service structure
storage = get_api_structure(path="storage")
print(storage)
# {
#     "manager": {
#         "path": "/storage",
#         "methods": [
#             {
#                 "name": "configure",
#                 "http_method": "POST",
#                 "params": {"source": (str | list[dict], ...)},
#                 "returns": None,
#                 "doc": "Configure storage mounts."
#             },
#             {
#                 "name": "get_node",
#                 "http_method": "GET",
#                 "params": {"mount_or_path": (str, ...)},
#                 "returns": StorageNode,
#                 "doc": "Get a storage node."
#             }
#         ],
#         "children": ["nodes"]
#     }
# }

# Get nodes structure
nodes = get_api_structure(path="storage/nodes")
print(nodes)
# {
#     "path": "/storage/nodes",
#     "methods": [
#         {"name": "read", ...},
#         {"name": "write", ...},
#         {"name": "get_children", ...}
#     ]
# }
```

---

## Comparison with Other Approaches

### vs. FastAPI Direct Integration

**FastAPI Approach:**
```python
from fastapi import FastAPI, HTTPException

app = FastAPI()

class StorageManager:
    @app.get("/storage/read")
    def read_file(self, path: str) -> str:
        # Business logic coupled to FastAPI
        if not self.exists(path):
            raise HTTPException(status_code=404)
        return self._read(path)
```

**Problems:**
- Business logic depends on FastAPI
- Can't use StorageManager without web framework
- Testing requires FastAPI test client
- Tied to single web framework

**@apiready Approach:**
```python
from genro_core.decorators.api import apiready

@apiready(path="/storage")
class StorageManager:
    @apiready
    def read_file(self, path: str) -> str:
        # Pure business logic
        return self._read(path)

# Publisher separately configures FastAPI
# StorageManager has NO web framework dependency
```

**Benefits:**
- Business logic is framework-independent
- Can be tested directly without web layer
- Can publish to multiple frameworks
- Clean separation of concerns

**Rating**: @apiready is significantly better (9/10 vs 5/10)

### vs. GraphQL

**GraphQL Approach:**
```python
import strawberry

@strawberry.type
class Storage:
    @strawberry.field
    def read_file(self, path: str) -> str:
        return self._read(path)

schema = strawberry.Schema(query=Storage)
```

**Problems:**
- Still couples business logic to GraphQL
- Forces GraphQL schema design
- Single query/mutation endpoint
- Complex for simple CRUD operations

**@apiready Advantages:**
- RESTful by default (easier for most clients)
- No GraphQL schema complexity
- Supports both REST and potential GraphQL publishing
- More flexible for different use cases

**Rating**: @apiready is better for REST APIs, GraphQL better for complex queries (8/10 vs 7/10)

### vs. Django REST Framework

**Django REST Approach:**
```python
from rest_framework import serializers, viewsets

class FileSerializer(serializers.Serializer):
    path = serializers.CharField()
    content = serializers.CharField()

class StorageViewSet(viewsets.ViewSet):
    def retrieve(self, request, path=None):
        # Business logic mixed with view logic
        content = self._read(path)
        return Response({"content": content})
```

**Problems:**
- Requires Django framework
- Business logic in viewsets
- Lots of boilerplate
- Serializers separate from models

**@apiready Advantages:**
- No framework dependency
- Type hints replace serializers
- Less boilerplate
- Business logic remains pure

**Rating**: @apiready is cleaner (8/10 vs 6/10)

### Unique Value of @apiready

The `@apiready` pattern offers unique value:

1. **Zero Coupling**: Unlike all competitors, business logic has ZERO web framework dependencies
2. **Lazy Discovery**: Unique hierarchical API discovery pattern
3. **Dual Interface**: Single metadata generates both human UI and machine API
4. **Universal**: Works with any Python library, any domain
5. **Type-Driven**: Leverages Python's type system, no separate schema language

**Overall Rating: 9.5/10**

The only missing piece is the publisher implementation, which is straightforward.

---

## Best Practices

### 1. Use Type Hints Everywhere

Always provide complete type hints:

```python
# Good
@apiready
def read_file(self, path: str, encoding: str = 'utf-8') -> str:
    return self._read(path, encoding)

# Bad - missing return type
@apiready
def read_file(self, path: str, encoding: str = 'utf-8'):
    return self._read(path, encoding)
```

### 2. Use Annotated for Documentation

Provide parameter descriptions using `Annotated`:

```python
from typing import Annotated

@apiready
def read_file(
    self,
    path: Annotated[str, "Path to the file to read"],
    encoding: Annotated[str, "Text encoding to use"] = 'utf-8'
) -> Annotated[str, "File contents as string"]:
    """Read a file from storage."""
    return self._read(path, encoding)
```

### 3. Write Clear Docstrings

Docstrings appear in API documentation:

```python
@apiready
def read_file(self, path: str, encoding: str = 'utf-8') -> str:
    """Read a file from storage.

    This method reads the entire file into memory. For large files,
    consider using read_stream() instead.

    Args:
        path: Path to the file relative to mount point
        encoding: Character encoding (default: utf-8)

    Returns:
        Complete file contents as string

    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file is not readable
    """
    return self._read(path, encoding)
```

### 4. Organize with Path Hierarchies

Use logical path hierarchies:

```python
@apiready(path="/storage")           # Top level
class StorageManager:
    pass

@apiready(path="/storage/nodes")     # Subsystem
class StorageNode:
    pass

@apiready(path="/storage/mounts")    # Another subsystem
class MountManager:
    pass
```

### 5. Keep Business Logic Pure

Don't mix web concerns into business logic:

```python
# Good - pure business logic
@apiready
def read_file(self, path: str) -> str:
    if not self._exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    return self._read(path)

# Bad - web concerns in business logic
@apiready
def read_file(self, path: str) -> dict:
    if not self._exists(path):
        return {"error": "Not found", "status": 404}
    return {"data": self._read(path), "status": 200}
```

### 6. Use Appropriate Return Types

Return domain objects, not HTTP responses:

```python
# Good - return domain object
@apiready
def get_node(self, path: str) -> StorageNode:
    return self._get_node(path)

# Good - return data structures
@apiready
def list_files(self, directory: str) -> list[dict]:
    return [{"name": f.name, "size": f.size} for f in self._list(directory)]

# Bad - return HTTP response
@apiready
def get_node(self, path: str) -> JSONResponse:
    node = self._get_node(path)
    return JSONResponse(content=node.to_dict())
```

### 7. Test Business Logic Directly

Test business logic without web layer:

```python
def test_read_file():
    # Test business logic directly, no web framework
    manager = StorageManager()
    manager.configure({"data": "/path/to/data"})

    content = manager.read_file("data://test.txt")
    assert content == "expected content"

    # No HTTP, no web framework, just business logic
```

### 8. Support Method Chaining

Design APIs that support natural workflows:

```python
@apiready(path="/storage")
class StorageManager:
    @apiready
    def get_node(self, path: str) -> StorageNode:
        """Get a node to work with."""
        return self._get_node(path)

@apiready(path="/storage/nodes")
class StorageNode:
    @apiready
    def read(self) -> str:
        """Read this node's contents."""
        return self._read()

    @apiready
    def get_child(self, name: str) -> "StorageNode":
        """Get a child node."""
        return self._get_child(name)

# Usage:
node = manager.get_node("data://")
child = node.get_child("subdir")
content = child.get_child("file.txt").read()
```

### 9. Provide Sensible Defaults

Use defaults for common parameter values:

```python
@apiready
def read_file(
    self,
    path: str,
    encoding: str = 'utf-8',          # Common default
    errors: str = 'strict',            # Common default
    max_size: int | None = None        # No limit by default
) -> str:
    """Read a file with sensible defaults."""
    return self._read(path, encoding, errors, max_size)
```

### 10. Document Capabilities

Use docstrings to document what's supported:

```python
@apiready
def copy_to(
    self,
    destination: str,
    overwrite: bool = False
) -> None:
    """Copy this file to another location.

    Supports:
    - Copy within same mount: Fast server-side copy
    - Copy across mounts: Streams data through client
    - Copy to different backend types: Automatic conversion

    Args:
        destination: Target path (mount://path format)
        overwrite: Whether to overwrite existing file
    """
    self._copy_to(destination, overwrite)
```

---

## Implementation Guide

### Step 1: Add @apiready to Your Library

Install genro-core and add decorators:

```python
# your_library.py
from genro_core.decorators.api import apiready
from typing import Annotated

@apiready(path="/myservice")
class MyService:
    """Your service description."""

    @apiready
    def my_method(
        self,
        param: Annotated[str, "Parameter description"]
    ) -> Annotated[str, "Return value description"]:
        """Method description."""
        return self._do_something(param)
```

### Step 2: Implement get_api_structure()

Create a utility function in genro-core:

```python
# genro_core/api/discovery.py
def get_api_structure(path: str | None = None) -> dict:
    """Get API structure for a given path.

    Args:
        path: Path to explore (None for root level)

    Returns:
        Dictionary describing API structure at that path
    """
    if path is None:
        # Return top-level services
        return {
            "storage": {
                "path": "/storage",
                "class": StorageManager,
                "methods": _get_methods(StorageManager),
                "children": ["nodes", "mounts"]
            },
            # ... other services
        }

    # Parse path and drill down
    parts = path.split("/")
    # ... navigation logic
```

### Step 3: Create Publisher

Implement publisher that reads metadata:

```python
# genro_api_publisher/publisher.py
from fastapi import FastAPI
from genro_core.api.discovery import get_api_structure

def create_api(services: list) -> FastAPI:
    """Create FastAPI app from @apiready services."""
    app = FastAPI()

    # Discover structure
    structure = get_api_structure()

    # Generate routes
    for service_name, service_info in structure.items():
        for method_info in service_info["methods"]:
            _create_route(app, service_info["class"], method_info)

    return app

def _create_route(app: FastAPI, cls, method_info: dict):
    """Create a FastAPI route from method metadata."""
    # Extract metadata
    path = method_info["endpoint_path"]
    http_method = method_info["http_method"]
    func = getattr(cls, method_info["name"])

    # Create route
    if http_method == "GET":
        app.get(path)(func)
    else:
        app.post(path)(func)
```

### Step 4: Deploy

Run your published API:

```python
# main.py
from genro_api_publisher import create_api
from genro_storage import StorageManager

# Create instances
storage = StorageManager()
storage.configure({"data": "/path/to/data"})

# Publish as API
app = create_api([storage])

# Run
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Future Considerations

### 1. WebSocket Support

Consider adding real-time capabilities:

```python
@apiready(protocol="websocket")
def watch_file(self, path: str) -> AsyncIterator[str]:
    """Watch file for changes and stream updates."""
    async for change in self._watch(path):
        yield change
```

### 2. Batch Operations

Support batching for efficiency:

```python
@apiready(batch=True)
def read_files(self, paths: list[str]) -> dict[str, str]:
    """Read multiple files in one request."""
    return {path: self._read(path) for path in paths}
```

### 3. Rate Limiting Metadata

Add rate limiting hints:

```python
@apiready(rate_limit="100/hour")
def expensive_operation(self, data: str) -> str:
    """Expensive operation with rate limiting."""
    return self._process(data)
```

### 4. Caching Hints

Provide caching guidance:

```python
@apiready(cache_ttl=300)  # Cache for 5 minutes
def get_statistics(self) -> dict:
    """Get statistics (expensive, cacheable)."""
    return self._calculate_stats()
```

### 5. Versioning Support

Support API versioning:

```python
@apiready(path="/storage/v2")
class StorageManagerV2:
    """Version 2 of storage API with breaking changes."""
    pass
```

### 6. GraphQL Publishing

Add GraphQL publisher alongside REST:

```python
# Publish same metadata as GraphQL
from genro_api_publisher.graphql import create_graphql_api
graphql_app = create_graphql_api([storage])
```

### 7. OpenTelemetry Integration

Auto-instrument with observability:

```python
@apiready(trace=True)
def critical_operation(self, data: str) -> str:
    """Automatically traced operation."""
    return self._process(data)
```

---

## Conclusion

The `@apiready` architecture provides a clean, scalable, and framework-independent way to expose Python business logic as web APIs. By maintaining strict separation between business logic, metadata, and presentation, it enables:

- **Clean code**: Business logic stays pure and testable
- **Flexibility**: Support multiple presentation layers from one source
- **Scalability**: Lazy discovery works with APIs of any size
- **Developer experience**: Type hints and decorators provide excellent IDE support
- **Maintainability**: Single source of truth, no duplication

This architecture is applicable to any Python library and provides a solid foundation for building modern, API-first applications.

---

**Document Version:** 1.0
**Last Updated:** 2025-01-30
**Maintained By:** Genropy Team
**GitHub:** https://github.com/genropy/genro-core
