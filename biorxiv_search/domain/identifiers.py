from urllib.parse import unquote, urlparse

from .errors import InvalidInputError

_MAX_DOI_LENGTH = 500


def normalize_doi(value: str) -> str:
    """Normalize accepted DOI forms without following arbitrary URLs."""
    if not isinstance(value, str):
        raise InvalidInputError("DOI must be a string")

    doi = value.strip()
    if not doi or len(doi) > _MAX_DOI_LENGTH or any(ord(char) < 32 for char in doi):
        raise InvalidInputError("DOI is empty, too long, or contains control characters")

    lowered = doi.lower()
    if lowered.startswith("https://doi.org/") or lowered.startswith("http://doi.org/"):
        parsed = urlparse(doi)
        if parsed.netloc.lower() != "doi.org" or parsed.query or parsed.fragment:
            raise InvalidInputError("DOI URL must use doi.org without query or fragment")
        doi = unquote(parsed.path.lstrip("/"))
    elif lowered.startswith("doi:"):
        doi = doi[4:].strip()

    if not doi.lower().startswith("10.1101/") or len(doi) <= len("10.1101/"):
        raise InvalidInputError("DOI must be a bioRxiv DOI beginning with 10.1101/")
    if any(char.isspace() for char in doi):
        raise InvalidInputError("DOI must not contain whitespace")
    return doi
