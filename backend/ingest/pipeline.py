"""Document ingestion: PDF / MD / URL / TXT → normalized markdown SourceDoc."""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def ingest_document(raw_path: Path, normalized_path: Path, kind: str) -> str:
    """Extract text from raw file and write normalized markdown."""
    if kind == "pdf":
        text = _extract_pdf(raw_path)
    elif kind == "md":
        text = raw_path.read_text(encoding="utf-8")
    elif kind == "url":
        text = await _extract_url(raw_path)
    else:
        text = raw_path.read_text(encoding="utf-8")

    # Normalize: strip excessive whitespace, ensure markdown
    normalized = _normalize(text)
    normalized_path.write_text(normalized, encoding="utf-8")
    return normalized


def _extract_pdf(path: Path) -> str:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(path))
        parts = []
        for page in doc:
            parts.append(page.get_text())
        return "\n\n".join(parts)
    except ImportError:
        raise RuntimeError("PyMuPDF not installed")


async def _extract_url(path: Path) -> str:
    import httpx
    from bs4 import BeautifulSoup
    from markdownify import markdownify as md

    url = path.read_text(encoding="utf-8").strip()
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove script/style
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        html = str(soup.find("article") or soup.find("main") or soup.find("body") or soup)
        return md(html, heading_style="ATX")


def _normalize(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    # Collapse multiple blank lines
    cleaned = []
    prev_blank = False
    for line in lines:
        blank = not line
        if blank and prev_blank:
            continue
        cleaned.append(line)
        prev_blank = blank
    return "\n".join(cleaned)
