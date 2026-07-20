from datetime import date

import pytest

from biorxiv_search.application import PreprintSearchService
from biorxiv_search.domain import InvalidInputError


class FakeSearch:
    async def search(self, *args, **kwargs):
        raise AssertionError("should not be called")


class FakeDetail:
    async def get_by_doi(self, *args, **kwargs):
        raise AssertionError("should not be called")


@pytest.mark.asyncio
async def test_search_validates_input_before_provider_call():
    service = PreprintSearchService(FakeSearch(), FakeDetail())
    with pytest.raises(InvalidInputError):
        await service.search_preprints("", limit=20)
    with pytest.raises(InvalidInputError):
        await service.search_preprints("query", date_from=date(2026, 2, 1), date_to=date(2026, 1, 1))
