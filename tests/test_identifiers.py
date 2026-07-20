import pytest

from biorxiv_search.domain import InvalidInputError, normalize_doi


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("10.1101/2026.01.01.123456", "10.1101/2026.01.01.123456"),
        ("doi:10.1101/2026.01.01.123456", "10.1101/2026.01.01.123456"),
        ("https://doi.org/10.1101/2026.01.01.123456", "10.1101/2026.01.01.123456"),
        ("10.64898/2026.07.07.736950", "10.64898/2026.07.07.736950"),
        ("  10.1101/2026.01.01.123456  ", "10.1101/2026.01.01.123456"),
    ],
)
def test_normalize_doi(value, expected):
    assert normalize_doi(value) == expected


@pytest.mark.parametrize("value", ["", "https://example.com/10.1101/x", "10.123/x", "10.1101/"])
def test_normalize_doi_rejects_invalid_values(value):
    with pytest.raises(InvalidInputError):
        normalize_doi(value)
