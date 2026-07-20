import asyncio
from datetime import date, datetime, timedelta, timezone
import hashlib
import json

from ..domain.errors import InvalidInputError
from ..domain.identifiers import normalize_doi
from ..domain.models import PreprintDetail, SearchPage
from ..infrastructure.biorxiv import BiorxivClient
from ..infrastructure.cache import SQLiteCache
from ..infrastructure.europe_pmc import EuropePmcClient


class PreprintSearchService:
    def __init__(
        self,
        search_provider: EuropePmcClient,
        detail_provider: BiorxivClient,
        cache: SQLiteCache | None = None,
    ) -> None:
        self._search_provider = search_provider
        self._detail_provider = detail_provider
        self._cache = cache
        self._inflight: dict[str, asyncio.Task] = {}

    async def search_preprints(
        self,
        query: str,
        *,
        title_only: bool = False,
        author: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> SearchPage:
        _validate_search(query, author, date_from, date_to, limit, cursor)
        key = _key("search", query, title_only, author, date_from, date_to, limit, cursor)
        if self._cache:
            cached = self._cache.get(key)
            if cached:
                return _search_page_from_json(cached.payload)
        page = await self._coalesced(
            key,
            lambda: self._search_provider.search(
                query,
                title_only=title_only,
                author=author,
                date_from=date_from,
                date_to=date_to,
                limit=limit,
                cursor=cursor,
            ),
        )
        if self._cache:
            now = datetime.now(timezone.utc)
            self._cache.set(key, "europe_pmc", _jsonable(page), now + timedelta(minutes=30))
        return page

    async def get_preprint(self, doi: str, *, version: int | None = None, refresh: bool = False) -> PreprintDetail:
        normalized = normalize_doi(doi)
        if version is not None and (not isinstance(version, int) or version < 1):
            raise InvalidInputError("version must be a positive integer")
        key = _key("detail", normalized, version)
        if self._cache and not refresh:
            cached = self._cache.get(key)
            if cached:
                return _detail_from_json(cached.payload)
        detail = await self._coalesced(
            key,
            lambda: self._detail_provider.get_by_doi(normalized, version=version),
        )
        if self._cache:
            now = datetime.now(timezone.utc)
            self._cache.set(key, "biorxiv_api", _jsonable(detail), now + timedelta(hours=12))
        return detail

    async def _coalesced(self, key: str, operation):
        task = self._inflight.get(key)
        if task is None:
            task = asyncio.create_task(operation())
            self._inflight[key] = task
        try:
            return await asyncio.shield(task)
        finally:
            if task.done() and self._inflight.get(key) is task:
                del self._inflight[key]


def _validate_search(
    query: str,
    author: str | None,
    date_from: date | None,
    date_to: date | None,
    limit: int,
    cursor: str | None,
) -> None:
    if not isinstance(query, str) or not query.strip() or len(query) > 500:
        raise InvalidInputError("query must contain 1 to 500 characters")
    if author is not None and (not isinstance(author, str) or len(author) > 200):
        raise InvalidInputError("author must contain at most 200 characters")
    if not 1 <= limit <= 50:
        raise InvalidInputError("limit must be between 1 and 50")
    if cursor is not None and (not isinstance(cursor, str) or len(cursor) > 1000):
        raise InvalidInputError("cursor must contain at most 1000 characters")
    if date_from is not None and not isinstance(date_from, date):
        raise InvalidInputError("date_from must be a date")
    if date_to is not None and not isinstance(date_to, date):
        raise InvalidInputError("date_to must be a date")
    if date_from and date_to and date_from > date_to:
        raise InvalidInputError("date_from must not be later than date_to")


def _key(*parts: object) -> str:
    raw = json.dumps([str(part) for part in parts], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def _jsonable(value: object) -> dict:
    from dataclasses import asdict
    from datetime import date, datetime

    def convert(item: object) -> object:
        if isinstance(item, (date, datetime)):
            return item.isoformat()
        if isinstance(item, tuple):
            return [convert(part) for part in item]
        if isinstance(item, list):
            return [convert(part) for part in item]
        if isinstance(item, dict):
            return {key: convert(part) for key, part in item.items()}
        return item

    return convert(asdict(value))  # type: ignore[arg-type]


def _search_page_from_json(data: dict) -> SearchPage:
    from datetime import date
    from ..domain.models import PreprintSummary

    items = tuple(
        PreprintSummary(
            **{
                **item,
                "authors": tuple(item["authors"]),
                "posted_date": date.fromisoformat(item["posted_date"]) if item["posted_date"] else None,
            }
        )
        for item in data["items"]
    )
    return SearchPage(items, data["total"], data["limit"], data["cursor"], data["next_cursor"])


def _detail_from_json(data: dict) -> PreprintDetail:
    from datetime import date, datetime
    from ..domain.models import Funding

    data = dict(data)
    data["posted_date"] = date.fromisoformat(data["posted_date"])
    data["fetched_at"] = datetime.fromisoformat(data["fetched_at"])
    data["authors"] = tuple(data["authors"])
    data["funding"] = tuple(Funding(**item) for item in data["funding"])
    return PreprintDetail(**data)
