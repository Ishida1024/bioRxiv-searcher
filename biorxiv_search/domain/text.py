import html
import re

_HTML_TAG = re.compile(r"<[^>]*>")
_WHITESPACE = re.compile(r"\s+")


def clean_external_text(value: object) -> str | None:
    """Return readable text while treating upstream markup as data."""
    if value is None:
        return None
    text = html.unescape(str(value))
    text = _HTML_TAG.sub(" ", text)
    text = _WHITESPACE.sub(" ", text).strip()
    return text or None
