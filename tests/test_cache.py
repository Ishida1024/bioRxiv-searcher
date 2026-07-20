from datetime import datetime, timedelta, timezone

from biorxiv_search.infrastructure.cache import SQLiteCache


def test_sqlite_cache_expires_entries():
    cache = SQLiteCache()
    now = datetime(2026, 7, 20, tzinfo=timezone.utc)
    cache.set("key", "test", {"value": 1}, now + timedelta(minutes=1), now=now)
    assert cache.get("key", now=now).payload == {"value": 1}
    assert cache.get("key", now=now + timedelta(minutes=2)) is None
