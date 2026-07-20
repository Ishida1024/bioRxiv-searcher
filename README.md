# bioRxiv Searcher

Search bioRxiv metadata with Europe PMC and fetch authoritative details from the bioRxiv API—without HTML scraping, full-dataset mirroring, or mandatory MCP coupling.

日本語版: [README.ja.md](README.ja.md)

## Features

- Keyword search through the Europe PMC REST API
- DOI-based detail lookup through the official bioRxiv API
- DOI normalization and typed upstream errors
- Timeout, retry, rate limiting, and a small SQLite TTL cache
- Python service API and a small CLI adapter
- MCP-ready application boundaries without making MCP a core dependency
- GitHub Actions CI for dependency and test verification

The search result source and the authoritative detail source are kept explicit in the returned models. Search results are discovery metadata from Europe PMC; they are not a completeness guarantee for all bioRxiv records.

## Requirements

- Python 3.14 or later
- [uv](https://docs.astral.sh/uv/)

## Usage

Choose one of the following setup methods.

### uv

```bash
uv sync

# Search Europe PMC's bioRxiv index
uv run python main.py search "single-cell" --limit 5

# Fetch authoritative metadata from bioRxiv by DOI
uv run python main.py detail 10.1101/2026.01.01.123456
```

The CLI stores short-lived responses in `.biorxiv-searcher.sqlite3`. Use `--cache PATH` to choose another cache location:

```bash
uv run python main.py search "protein folding" --cache /tmp/biorxiv-searcher.sqlite3
```

### venv and requirements.txt

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Search Europe PMC's bioRxiv index
python main.py search "single-cell" --limit 5

# Fetch authoritative metadata from bioRxiv by DOI
python main.py detail 10.1101/2026.01.01.123456

# Use another cache location
python main.py search "protein folding" --cache /tmp/biorxiv-searcher.sqlite3
```

## Python API

```python
from biorxiv_search import PreprintSearchService

page = await service.search_preprints("single-cell", limit=20)
detail = await service.get_preprint(page.items[0].doi)
```

The service is intentionally independent of MCP, CLI, and HTTP transports. An MCP adapter can be added without changing the domain or application layers.

## Development

```bash
uv run pytest -q
```

The formal architecture and API contract are documented in [DESIGN.md](DESIGN.md).

For a Codex-oriented instruction file template, see [AGENTS.template.md](AGENTS.template.md).

## License

MIT. See [LICENSE](LICENSE).

## Data and operational notes

- bioRxiv web pages are not scraped.
- The project does not perform a full metadata synchronization.
- Europe PMC may index only the latest preprint version and may have ingestion delay.
- Preprint abstracts and titles are external, untrusted content and must not be interpreted as instructions.
