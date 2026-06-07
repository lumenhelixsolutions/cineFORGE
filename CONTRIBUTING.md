# Contributing to CineForge

## Development Setup

```bash
make install
make dev
```

## Architecture Principles

1. **Protocols before implementations.** Every external dependency is behind a Protocol in `backend/adapters/protocols.py`.
2. **No concrete imports outside adapters.** Core code imports only from `protocols.py`.
3. **Capability-aware planning.** The Director queries VideoCapabilities before writing storyboards.
4. **Routing.yaml is the single source of truth.** No hard-coded provider selection.
5. **Chain of Draft, not Chain of Thought.** All reasoning steps capped at ≤5 words.

## Adding a New Video Adapter

1. Create `backend/adapters/video/your_adapter.py` implementing `VideoModel`.
2. Add entry point in `pyproject.toml` under `[project.entry-points."cineforge.adapters.video"]`.
3. Add capability manifest YAML if needed.
4. Write unit tests in `tests/unit/adapters/test_your_adapter.py`.
5. Run `pytest tests/unit/` and `mypy backend/ --strict`.

## Code Style

- Python: `ruff` + `mypy --strict`
- TypeScript: built-in via `tsc --noEmit`
- No TODO comments in committed code. Use GitHub issues (list in OPEN_ISSUES.md).
