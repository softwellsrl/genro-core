# Claude Code Instructions - Genro Core

**Parent Document**: This project follows all policies from the central [genro-next-generation CLAUDE.md](https://github.com/genropy/genro-next-generation/blob/main/CLAUDE.md)

## Project-Specific Context

### Current Status
- Development Status: Alpha (0.1.0)
- Has Implementation: Yes

### Purpose

Genro Core is the shared utilities and decorators package for the entire Genro framework. Any reusable functionality discovered in other Genro projects should be moved here following the principle:

**"Ogni volta che troviamo qualcosa di riusabile lo mettiamo in genro-core"**
(Whenever we find something reusable, we put it in genro-core)

### Current Features

1. **@apiready decorator** (`genro_core/decorators/api.py`)
   - Marks methods as API-ready for automatic endpoint generation
   - Auto-generates Pydantic request/response models from type hints
   - Infers HTTP method from function name (read*/get*/list*/exists*/is_*/has_* → GET, else POST)
   - Supports optional explicit method override: `@apiready(method='POST')`
   - Stores metadata in `func._api_metadata` for consumption by API frameworks

### Project-Specific Guidelines

1. **Zero Dependencies Philosophy**: Keep dependencies minimal. Currently only requires Pydantic (already a standard in the Genro ecosystem).

2. **Type-Safety First**: All utilities must leverage type hints and be fully typed.

3. **Documentation**: Every public function/class must have comprehensive docstrings with examples.

4. **Test Coverage**: Maintain 100% test coverage for all code.

5. **DRY Principle**: This package IS the single source of truth for shared utilities. Avoid duplication across Genro projects.

### Adding New Utilities

When adding new reusable functionality:

1. Determine the appropriate module structure (e.g., `decorators/`, `utils/`, etc.)
2. Create the implementation with full type hints
3. Add comprehensive tests
4. Update README.md with usage examples
5. Export from `genro_core/__init__.py` if it's a primary feature
6. Update this CLAUDE.md with a brief description

### Known Dependencies

- **pydantic>=2.0.0**: Required for type validation and model generation in @apiready

---

**All general policies are inherited from the parent document.**
