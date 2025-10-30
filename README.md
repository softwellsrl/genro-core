# Genro Core

Core utilities and decorators for the Genro framework.

## Status

**Development Status:** Alpha
This package contains shared utilities and decorators used across Genro projects.

## Features

- **API Decorators**: Auto-generate API endpoints with `@apiready` decorator
- **Type-safe**: Leverages Pydantic for automatic validation and schema generation
- **DRY Principle**: Declare once, use everywhere

## Installation

```bash
pip install genro-core
```

## Usage

### @apiready Decorator

Mark methods as API-ready for automatic endpoint generation:

```python
from genro_core.decorators import apiready

class MyBackend:
    @apiready
    def read_file(self, path: str, encoding: str = 'utf-8') -> str:
        """Read file content."""
        ...

    @apiready(method='POST')
    def delete_file(self, path: str) -> None:
        """Delete file."""
        ...
```

The decorator auto-generates:
- Pydantic request/response models from type hints
- HTTP method detection (GET for read-only, POST for mutations)
- OpenAPI/Swagger documentation
- Input validation

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black genro_core tests

# Lint
ruff genro_core tests
```

## License

MIT License - see LICENSE file for details.

## Links

- [Documentation](https://github.com/genropy/genro-core)
- [Issues](https://github.com/genropy/genro-core/issues)
- [Genro Project](https://github.com/genropy/genro-next-generation)
