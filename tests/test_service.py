from datetime import date

import pytest

from biorxiv_search.application import PreprintSearchService
from biorxiv_search.domain import InvalidInputError
from biorxiv_search.infrastructure.cache import SQLiteCache
from biorxiv_search.domain.models import PreprintSummary, SearchPage


class FakeSearch:
    async def search(self, *args, **kwargs):
        raise AssertionError("should not be called")


class FakeDetail:
    async def get_by_doi(self, *args, **kwargs):
        raise AssertionError("should not be called")


class SearchResult:
    def __init__(self):
        self.calls = 0

    async def search(self, *args, **kwargs):
        self.calls += 1
        return SearchPage(
            items=(PreprintSummary("10.1101/x", "Title", (), None, None, None, "europe_pmc", "1", "url", True),),
            total=1,
            limit=20,
            cursor=None,
            next_cursor=None,
        )


@pytest.mark.asyncio
async def test_search_validates_input_before_provider_call():
    service = PreprintSearchService(FakeSearch(), FakeDetail())
    with pytest.raises(InvalidInputError):
        await service.search_preprints("", limit=20)
    with pytest.raises(InvalidInputError):
        await service.search_preprints("query", date_from=date(2026, 2, 1), date_to=date(2026, 1, 1))


@pytest.mark.asyncio
async def test_search_round_trips_through_cache():
    provider = SearchResult()
    service = PreprintSearchService(provider, FakeDetail(), SQLiteCache())
    first = await service.search_preprints("query")
    second = await service.search_preprints("query")
    assert first == second
    assert provider.calls == 1
