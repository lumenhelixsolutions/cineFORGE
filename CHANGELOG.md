# Changelog

## [0.2.0] — 2026-06-11 (Public Beta)

### Added

- lookBOOK shot graph ingest: `POST /projects/{id}/ingest/lookbook`
- Async SQLAlchemy 2.0 DB layer with auth scaffolding
- TTS, transitions, LUT grading, ref-image generation, extend pipeline
- 11 video adapters (8 real + 3 stubs)
- Landing page at `landing/` with GitHub Pages workflow
- Portfolio integration with NOTEtoolsLM vault export and lookBOOK shot JSON

### Changed

- Version aligned across Tauri, Python, and UI packages (0.2.0)
- Release workflow publishes draft prerelease bundles on `v*` tags

### Known limitations (beta)

- Installers are unsigned until EV/Apple certificates are configured (Milestone 11)
- OpenAI Sora 2 API availability uncertain — hybrid routing falls back to Veo 3.1 + Kling 3.0