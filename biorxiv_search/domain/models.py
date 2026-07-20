from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Funding:
    name: str | None
    identifier: str | None
    identifier_type: str | None
    award: str | None


@dataclass(frozen=True)
class PreprintSummary:
    doi: str
    title: str
    authors: tuple[str, ...]
    abstract: str | None
    posted_date: date | None
    version: int | None
    source: str
    source_record_id: str
    source_url: str
    latest_version_only: bool


@dataclass(frozen=True)
class SearchPage:
    items: tuple[PreprintSummary, ...]
    total: int
    limit: int
    cursor: str | None
    next_cursor: str | None


@dataclass(frozen=True)
class PreprintDetail:
    doi: str
    title: str
    authors: tuple[str, ...]
    corresponding_author: str | None
    corresponding_institution: str | None
    posted_date: date
    version: int
    document_type: str | None
    license: str | None
    category: str | None
    abstract: str
    funding: tuple[Funding, ...]
    published_doi: str | None
    jats_xml_url: str | None
    server: str
    source: str
    fetched_at: datetime
