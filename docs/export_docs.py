"""Export all docs/*.md into a single dark-themed HTML page."""

from __future__ import annotations

import datetime
import re
from pathlib import Path


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline_code(text: str) -> str:
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", text)


def _linkify(text: str) -> str:
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)


def _process_line(line: str) -> str:
    line = _inline_code(line)
    line = _linkify(line)
    return line


def markdown_to_html(md_text: str) -> str:
    """Minimal markdown-to-HTML converter."""
    lines = md_text.splitlines()
    out: list[str] = []
    in_code = False
    code_lang = ""
    code_buffer: list[str] = []

    for line in lines:
        if line.startswith("```"):
            if in_code:
                out.append(f"<pre><code>{_escape_html('\n'.join(code_buffer))}</code></pre>")
                code_buffer = []
                in_code = False
            else:
                in_code = True
                code_lang = line[3:].strip()
                _ = code_lang
            continue

        if in_code:
            code_buffer.append(line)
            continue

        # Headers
        if line.startswith("# "):
            out.append(f"<h1>{_process_line(line[2:])}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{_process_line(line[3:])}</h2>")
        elif line.startswith("### "):
            out.append(f"<h3>{_process_line(line[4:])}</h3>")
        elif line.startswith("#### "):
            out.append(f"<h4>{_process_line(line[5:])}</h4>")
        # Lists
        elif line.startswith("- "):
            out.append(f"<li>{_process_line(line[2:])}</li>")
        # Table rows (simple)
        elif line.startswith("| ") and " | " in line:
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if all(c.replace("-", "") == "" for c in cells):
                continue  # skip separator
            out.append("<tr>" + "".join(f"<td>{_process_line(c)}</td>" for c in cells) + "</tr>")
        # Empty line
        elif line.strip() == "":
            out.append("<br/>")
        else:
            out.append(f"<p>{_process_line(line)}</p>")

    if in_code and code_buffer:
        out.append(f"<pre><code>{_escape_html('\n'.join(code_buffer))}</code></pre>")

    # Wrap consecutive <li> in <ul>
    result: list[str] = []
    in_list = False
    for seg in out:
        if seg.startswith("<li>"):
            if not in_list:
                result.append("<ul>")
                in_list = True
            result.append(seg)
        else:
            if in_list:
                result.append("</ul>")
                in_list = False
            result.append(seg)
    if in_list:
        result.append("</ul>")

    # Wrap consecutive <tr> in <table>
    result2: list[str] = []
    in_table = False
    for seg in result:
        if seg.startswith("<tr>"):
            if not in_table:
                result2.append('<table class="docs-table">')
                in_table = True
            result2.append(seg)
        else:
            if in_table:
                result2.append("</table>")
                in_table = False
            result2.append(seg)
    if in_table:
        result2.append("</table>")

    return "\n".join(result2)


def build_page(sections: dict[str, str]) -> str:
    body_parts: list[str] = []
    for name in sorted(sections):
        html = markdown_to_html(sections[name])
        body_parts.append(f'<section id="{name}">\n{html}\n</section>\n')

    return (
        """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CineForge Documentation</title>
<style>
:root {
  --bg: #0d1117;
  --fg: #c9d1d9;
  --accent: #58a6ff;
  --muted: #8b949e;
  --border: #30363d;
  --code-bg: #161b22;
}
body {
  background: var(--bg);
  color: var(--fg);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  line-height: 1.6;
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem 1rem;
}
h1, h2, h3, h4 { color: #f0f6fc; margin-top: 2rem; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
code {
  background: var(--code-bg);
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-size: 0.9em;
}
pre {
  background: var(--code-bg);
  padding: 1rem;
  border-radius: 8px;
  overflow-x: auto;
  border: 1px solid var(--border);
}
pre code { background: transparent; padding: 0; }
ul { padding-left: 1.5rem; }
.docs-table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
}
.docs-table td, .docs-table th {
  border: 1px solid var(--border);
  padding: 0.5rem;
}
.docs-table th { background: var(--code-bg); }
nav {
  position: sticky;
  top: 0;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  padding: 0.75rem 0;
  margin-bottom: 1rem;
}
nav a { margin-right: 1rem; font-weight: 600; }
</style>
</head>
<body>
<nav>
  <a href="#quickstart">Quickstart</a>
  <a href="#api">API</a>
  <a href="#stack_builder">StackBuilder</a>
  <a href="#troubleshooting">Troubleshooting</a>
</nav>
"""
        + "\n".join(body_parts)
        + """
<footer style="margin-top:3rem; color:var(--muted); font-size:0.85rem;">
  CineForge Docs — generated on """
        + datetime.datetime.now(datetime.timezone.utc).isoformat()
        + """
</footer>
</body>
</html>
"""
    )


def main() -> None:
    docs_dir = Path(__file__).parent
    sections: dict[str, str] = {}
    for md_file in sorted(docs_dir.glob("*.md")):
        key = md_file.stem.lower()
        sections[key] = md_file.read_text(encoding="utf-8")

    html = build_page(sections)
    out_path = docs_dir / "index.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Exported docs to {out_path}")


if __name__ == "__main__":
    main()
