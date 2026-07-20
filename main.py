import argparse
import asyncio
import json
import sys

from biorxiv_search.application import PreprintSearchService
from biorxiv_search.domain.errors import SearcherError
from biorxiv_search.infrastructure.biorxiv import BiorxivClient
from biorxiv_search.infrastructure.cache import SQLiteCache
from biorxiv_search.infrastructure.europe_pmc import EuropePmcClient
from biorxiv_search.infrastructure.http import PoliteHttpClient


def build_service(cache_path: str) -> tuple[PreprintSearchService, PoliteHttpClient, SQLiteCache]:
    http = PoliteHttpClient(user_agent="biorxiv-searcher/0.1 (local research tool)")
    cache = SQLiteCache(cache_path)
    return PreprintSearchService(EuropePmcClient(http), BiorxivClient(http), cache), http, cache


async def run(args: argparse.Namespace) -> None:
    service, http, cache = build_service(args.cache)
    try:
        if args.command == "search":
            result = await service.search_preprints(args.query, limit=args.limit)
        else:
            result = await service.get_preprint(args.doi)
        print(json.dumps(_jsonable(result), ensure_ascii=False, indent=2))
    finally:
        await http.aclose()
        cache.close()


def _jsonable(value):
    from dataclasses import asdict
    from datetime import date, datetime

    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if hasattr(value, "__dataclass_fields__"):
        return _jsonable(asdict(value))
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Search bioRxiv metadata")
    subparsers = parser.add_subparsers(dest="command", required=True)
    search = subparsers.add_parser("search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=20)
    search.add_argument("--cache", default=".biorxiv-searcher.sqlite3")
    detail = subparsers.add_parser("detail")
    detail.add_argument("doi")
    detail.add_argument("--cache", default=".biorxiv-searcher.sqlite3")
    try:
        asyncio.run(run(parser.parse_args()))
    except SearcherError as exc:
        print(
            json.dumps(
                {"error": {"code": exc.code, "message": exc.message, "retryable": exc.retryable}},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
