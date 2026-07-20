from datetime import date, datetime, timezone
from urllib.parse import quote

from .http import PoliteHttpClient
from ..domain.errors import NotFoundError, UpstreamProtocolError
from ..domain.identifiers import normalize_doi
from ..domain.models import Funding, PreprintDetail
from ..domain.text import clean_external_text

BASE_URL = "https://api.biorxiv.org"


class BiorxivClient:
    provider = "biorxiv_api"

    def __init__(self, http: PoliteHttpClient) -> None:
        self._http = http

    async def get_by_doi(self, doi: str, *, version: int | None = None) -> PreprintDetail:
        normalized = normalize_doi(doi)
        url = f"{BASE_URL}/details/biorxiv/{quote(normalized, safe='/')}/na/json"
        payload = await self._http.request_json("GET", url)
        collection = payload.get("collection")
        if not isinstance(collection, list) or not collection:
            raise NotFoundError("bioRxiv preprint was not found", provider=self.provider)
        records = [item for item in collection if isinstance(item, dict)]
        if version is not None:
            records = [item for item in records if item.get("version") == version]
        if not records:
            raise NotFoundError("Requested bioRxiv version was not found", provider=self.provider)
        record = max(records, key=lambda item: int(item.get("version", 0)))
        return self._detail(record)

    @staticmethod
    def _detail(item: dict) -> PreprintDetail:
        required = ("doi", "title", "date", "version", "abstract")
        if any(key not in item for key in required):
            raise UpstreamProtocolError("bioRxiv detail response is missing required fields", provider="biorxiv_api")
        raw_date = item["date"]
        try:
            posted_date = date.fromisoformat(str(raw_date)[:10])
            version = int(item["version"])
        except (TypeError, ValueError) as exc:
            raise UpstreamProtocolError("bioRxiv detail response has invalid date or version", provider="biorxiv_api") from exc
        return PreprintDetail(
            doi=str(item["doi"]),
            title=str(item["title"]),
            authors=_authors(item.get("authors")),
            corresponding_author=_optional(item.get("author_corresponding")),
            corresponding_institution=_optional(item.get("author_corresponding_institution")),
            posted_date=posted_date,
            version=version,
            document_type=_optional(item.get("type")),
            license=_optional(item.get("license")),
            category=_optional(item.get("category")),
            abstract=clean_external_text(item["abstract"]) or "",
            funding=_funding(item.get("funding")),
            published_doi=_optional(item.get("published")),
            jats_xml_url=_optional(item.get("jats xml path")),
            server=str(item.get("server", "biorxiv")),
            source="biorxiv_api",
            fetched_at=datetime.now(timezone.utc),
        )


def _optional(value: object) -> str | None:
    return str(value) if value not in (None, "", "NA", "N/A") else None


def _authors(value: object) -> tuple[str, ...]:
    if not isinstance(value, str):
        return ()
    separator = ";" if ";" in value else ","
    return tuple(part.strip() for part in value.split(separator) if part.strip())


def _funding(value: object) -> tuple[Funding, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(
        Funding(
            name=_optional(item.get("name")),
            identifier=_optional(item.get("id")),
            identifier_type=_optional(item.get("id-type")),
            award=_optional(item.get("award")),
        )
        for item in value
        if isinstance(item, dict)
    )
