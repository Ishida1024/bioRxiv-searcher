import pytest

from biorxiv_search.infrastructure.biorxiv import BiorxivClient


class FakeHttp:
    async def request_json(self, *args, **kwargs):
        return {
            "collection": [
                {
                    "doi": "10.1101/2026.01.01.123456",
                    "title": "A title",
                    "authors": "Jane Doe; John Doe",
                    "author_corresponding": "Jane Doe",
                    "date": "2026-01-02",
                    "version": 1,
                    "type": "new results",
                    "license": "cc_by",
                    "category": "Genomics",
                    "abstract": "<h4>Abstract</h4> An abstract",
                    "funding": [{"name": "NIH", "id": "1", "id-type": "grant", "award": "A"}],
                    "published": "",
                    "jats xml path": "https://example.org/article.xml",
                    "server": "biorxiv",
                }
            ]
        }


@pytest.mark.asyncio
async def test_get_by_doi_maps_detail():
    detail = await BiorxivClient(FakeHttp()).get_by_doi("doi:10.1101/2026.01.01.123456", version=1)
    assert detail.version == 1
    assert detail.authors == ("Jane Doe", "John Doe")
    assert detail.funding[0].identifier == "1"
    assert detail.abstract == "Abstract An abstract"
