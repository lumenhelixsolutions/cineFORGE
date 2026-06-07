"""Generate API.md from OpenAPI JSON."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    spec_path = Path(__file__).with_name("openapi.json")
    out_path = Path(__file__).with_name("API.md")
    with open(spec_path) as f:
        spec = json.load(f)

    lines: list[str] = ["# CineForge API Reference\n"]
    info = spec.get("info", {})
    lines.append(
        f"Generated from OpenAPI `{spec.get('openapi', 'unknown')}` — "
        f"**{info.get('title', 'CineForge')}** v{info.get('version', '0.1.0')}\n"
    )

    paths = spec.get("paths", {})
    for path, methods in sorted(paths.items()):
        for method, details in sorted(methods.items()):
            if method == "parameters":
                continue
            summary = details.get("summary", "")
            desc = details.get("description", "")
            lines.append(f"## {method.upper()} {path}\n")
            if summary:
                lines.append(f"**Summary:** {summary}\n")
            if desc:
                lines.append(f"{desc}\n")
            params = details.get("parameters", [])
            if params:
                lines.append("### Parameters\n")
                for p in params:
                    req = " **required**" if p.get("required") else ""
                    lines.append(
                        f"- `{p['name']}` ({p.get('in', 'query')}) — {p.get('schema', {}).get('type', 'any')}{req}\n"
                    )
                lines.append("\n")
            req_body = details.get("requestBody", {})
            if req_body:
                content = req_body.get("content", {})
                for ct, ctdetails in content.items():
                    schema = ctdetails.get("schema", {})
                    lines.append(f"### Request Body (`{ct}`)\n")
                    lines.append(f"```json\n{json.dumps(schema, indent=2)}\n```\n")
            responses = details.get("responses", {})
            if responses:
                lines.append("### Responses\n")
                for code, resp in sorted(responses.items(), key=lambda x: int(x[0]) if x[0].isdigit() else x[0]):
                    lines.append(f"- **{code}** — {resp.get('description', '')}\n")
                lines.append("\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("".join(lines))
    print("API.md generated")


if __name__ == "__main__":
    main()
