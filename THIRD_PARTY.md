# Third-Party Licenses

## Runtime dependencies

| Package | License | Usage |
|---------|---------|-------|
| FastAPI | MIT | HTTP API framework |
| SQLAlchemy | MIT | ORM and database abstraction |
| Alembic | MIT | Database migrations |
| Pydantic | MIT | Data validation and serialization |
| httpx | BSD-3-Clause | Async HTTP client |
| LiteLLM | MIT | LLM gateway and provider abstraction |
| txtai | Apache-2.0 | Semantic search and embeddings index |
| sentence-transformers | Apache-2.0 | Local embedding models |
| MoviePy | MIT | Video editing and compositing |
| PyMuPDF | AGPL-3.0 (commercial license available) | PDF text extraction |
| markdownify | MIT | HTML to Markdown conversion |
| BeautifulSoup4 | MIT | HTML parsing |
| PyYAML | MIT | YAML configuration files |
| pytest | MIT | Testing framework |
| hypothesis | MPL-2.0 | Property-based testing |
| mypy | MIT | Static type checking |

## System dependencies

| Package | License | Usage |
|---------|---------|-------|
| FFmpeg | LGPL-2.1+ / GPL-2.0+ (with --enable-gpl) | Video encoding, decoding, filtering |
| Tauri | MIT / Apache-2.0 | Desktop application shell |
| SolidJS | MIT | Frontend UI framework |
| Tailwind CSS | MIT | Utility-first CSS framework |

## Model and API providers

- **Google Vertex AI / Veo**: Subject to Google Cloud Terms of Service
- **fal.ai**: Subject to fal.ai Terms of Service
- **Anthropic Claude**: Subject to Anthropic Terms of Service
- **OpenAI GPT**: Subject to OpenAI Terms of Service

## Note on FFmpeg

CineForge uses FFmpeg features covered by the LGPL build. If you compile FFmpeg with `--enable-gpl` or `--enable-nonfree`, you are responsible for compliance with the GPL or respective commercial licenses.
