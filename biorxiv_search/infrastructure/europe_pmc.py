from datetime import date
from urllib.parse import quote

from .http import PoliteHttpClient
from ..domain.errors import UpstreamProtocolError
from ..domain.models import PreprintSummary, SearchPage

BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def _escape_query(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_search_query(
    query: str,
    *,
    title_only: bool = False,
    author: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> str:
    field = "TITLE" if title_only else "TITLE_ABS"
    parts = [f'PUBLISHER:"bioRxiv"', f'{field}:"{_escape_query(query)}"']
    if author:
        parts.append(f'AUTH:"{_escape_query(author)}"')
    if date_from or date_to:
        start = date_from.isoformat() if date_from else "*"
        end = date_to.isoformat() if date_to else "*"
        parts.append(f"FIRST_PDATE:[{start} TO {end}]")
    return " AND ".join(parts)


class EuropePmcClient:
    provider = "europe_pmc"

    def __init__(self, http: PoliteHttpClient) -> None:
        self._http = http

    async def search(
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
        params = {
            "query": build_search_query(
                query,
                title_only=title_only,
                author=author,
                date_from=date_from,
                date_to=date_to,
            ),
            "format": "json",
            "resultType": "core",
            "pageSize": str(limit),
        }
        if cursor:
            params["cursorMark"] = cursor
        payload = await self._http.request_json("GET", BASE_URL, params=params)
        result_list = payload.get("resultList", {})
        if not isinstance(result_list, dict):
            raise UpstreamProtocolError("Europe PMC resultList has an invalid shape", provider=self.provider)
        results = result_list.get("result", [])
        if not isinstance(results, list):
            raise UpstreamProtocolError("Europe PMC result list has an invalid shape", provider=self.provider)
        items = tuple(self._summary(item) for item in results if isinstance(item, dict))
        next_cursor = payload.get("nextCursorMark")
        if next_cursor is not None and not isinstance(next_cursor, str):
            raise UpstreamProtocolError("Europe PMC cursor has an invalid shape", provider=self.provider)
        hit_count = payload.get("hitCount", len(items))
        if not isinstance(hit_count, int):
            raise UpstreamProtocolError("Europe PMC hitCount has an invalid shape", provider=self.provider)
        return SearchPage(items, hit_count, limit, cursor, next_cursor)

    @staticmethod
    def _summary(item: dict) -> PreprintSummary:
        doi = item.get("doi")
        if not isinstance(doi, str) or not doi:
            raise UpstreamProtocolError("Europe PMC result has no DOI", provider="europe_pmc")
        authors = item.get("authorString") or ""
        author_list = item.get("authorList", {}).get("author", [])
        if isinstance(author_list, list):
            names = tuple(
                author.get("fullName", "").strip()
                for author in author_list
                if isinstance(author, dict) and author.get("fullName")
            )
        else:
            names = tuple(part.strip() for part in authors.split(",") if part.strip())
        posted_date = None
        raw_date = item.get("firstPublicationDate") or item.get("firstIndexDate")
        if isinstance(raw_date, str):
            try:
                posted_date = date.fromisoformat(raw_date[:10])
            except ValueError:
                posted_date = None
        return PreprintSummary(
            doi=doi,
            title=str(item.get("title", "")),
            authors=names,
            abstract=item.get("abstractText"),
            posted_date=posted_date,
            version=item.get("version") if isinstance(item.get("version"), int) else None,
            source="europe_pmc",
            source_record_id=str(item.get("id", "")),
            source_url=f"https://europepmc.org/article/{item.get('source', 'MED')}/{item.get('id', '')}",
            latest_version_only=True,
        )
