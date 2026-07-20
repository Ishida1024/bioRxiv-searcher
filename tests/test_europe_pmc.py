from datetime import date

import pytest

from biorxiv_search.infrastructure.europe_pmc import EuropePmcClient, build_search_query


def test_build_search_query_escapes_terms_and_filters():
    query = build_search_query(
        'cell "atlas"',
        title_only=True,
        author="Doe",
        date_from=date(2025, 1, 1),
        date_to=date(2025, 12, 31),
    )
    assert query == (
        'PUBLISHER:"bioRxiv" AND TITLE:("cell" "atlas") AND AUTH:"Doe" '
        'AND FIRST_PDATE:[2025-01-01 TO 2025-12-31]'
    )


def test_build_search_query_uses_keyword_conjunction_for_unquoted_terms():
    assert build_search_query("AlphaFold protein folding") == (
        'PUBLISHER:"bioRxiv" AND TITLE_ABS:("AlphaFold" "protein" "folding")'
    )


def test_build_search_query_supports_only_explicit_boolean_tokens():
    assert build_search_query("AlphaFold OR protein folding") == (
        'PUBLISHER:"bioRxiv" AND (TITLE_ABS:("AlphaFold") OR TITLE_ABS:("protein" "folding"))'
    )


def test_build_search_query_quotes_search_syntax_as_data():
    query = build_search_query("title:BRCA1 (draft) *")
    assert query == 'PUBLISHER:"bioRxiv" AND TITLE_ABS:("title:BRCA1" "(draft)" "*")'


class FakeHttp:
    def __init__(self, payload):
        self.payload = payload
        self.args = None

    async def request_json(self, *args, **kwargs):
        self.args = (args, kwargs)
        return self.payload


@pytest.mark.asyncio
async def test_search_maps_europe_pmc_result():
    http = FakeHttp(
        {
            "hitCount": 1,
            "nextCursorMark": "AoI=",
            "resultList": {
                "result": [
                    {
                        "id": "123",
                        "source": "BIOPR",
                        "doi": "10.1101/2026.01.01.123456",
                        "title": "A <i>title</i>",
                        "abstractText": "<h4>Abstract</h4> An abstract",
                        "authorList": {"author": [{"fullName": "Jane Doe"}]},
                        "firstPublicationDate": "2026-01-02",
                    }
                ]
            },
        }
    )
    page = await EuropePmcClient(http).search("title")
    assert page.total == 1
    assert page.items[0].title == "A title"
    assert page.items[0].authors == ("Jane Doe",)
    assert page.items[0].abstract == "Abstract An abstract"
    assert page.items[0].version is None
    assert page.items[0].latest_version_only is True
    assert page.next_cursor == "AoI="
    assert http.args[1]["params"]["resultType"] == "core"
