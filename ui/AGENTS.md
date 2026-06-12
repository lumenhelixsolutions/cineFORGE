# cineforge UI — Agent Notes

Scope: Tauri webview UI (`ui/`) only. Rust/Python cores are out of scope for UI MCP tooling.

## Stack

- **SolidJS** (not React) — see `ui/package.json`
- Portfolio chat standard is assistant-ui (React); cineforge uses Solid primitives today

## magic-mcp (opt-in, M9)

magic-mcp generates **React** components. Use it only when prototyping ideas to port manually into Solid.

| Step | Action |
|------|--------|
| 1 | Read `D:/projects/docs/MAGIC_MCP.md` |
| 2 | Copy `.cursor/mcp.json.example` → `.cursor/mcp.json` (gitignored) |
| 3 | Add `21ST_MAGIC_API_KEY` in local env — never commit |
| 4 | Run `npx @21st-dev/cli@latest install cursor --api-key <key>` |
| 5 | Port generated React markup to Solid components under `ui/src/` |

**Gate:** magic-mcp is opt-in per developer. No CI dependency. No kernel/runtime coupling.

## Related

- `D:/projects/cineforge/AGENTS.md` — project-wide agents guide
- `D:/projects/docs/MAGIC_MCP.md` — portfolio policy