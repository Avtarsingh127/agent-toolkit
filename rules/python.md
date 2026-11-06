---
description: Python style, config, GCP clients and tests
globs:
  - "**/*.py"
---

# Python rules
- Python 3.11+ idioms: type hints on public functions, `pathlib`, f-strings, dataclasses/pydantic for structured config.
- Configuration comes from a typed settings object (env vars / YAML / CLI flags), loaded once at the entry point and passed down. No module-level constants holding project IDs, regions, URLs, or credentials.
- GCP clients: use Application Default Credentials; never read key files. Create clients once and inject them so tests can fake them.
- Errors: catch specific exceptions, add context, re-raise; no bare `except`. Use `logging` (structured where the repo does), not `print`, outside CLIs.
- Tests: pytest, fixtures over setup methods, no network or real GCP calls in unit tests; mark integration tests.
- `ruff` is the formatter and linter of record; don't hand-format around it.
