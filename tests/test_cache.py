from datetime import datetime, timedelta, timezone

from biorxiv_search.infrastructure.cache import SQLiteCache


def test_sqlite_cache_expires_entries():
    cache = SQLiteCache()
    now = datetime(2026, 7, 20, tzinfo=timezone.utc)
    cache.set("key", "test", {"value": 1}, now + timedelta(minutes=1), now=now)
    assert cache.get("key", now=now).payload == {"value": 1}
    assert cache.get("key", now=now + timedelta(minutes=2)) is None


def test_sqlite_cache_creates_parent_directory(tmp_path):
    cache = SQLiteCache(tmp_path / "nested" / "cache.sqlite3")
    cache.set("key", "test", {"value": 1}, datetime.now(timezone.utc) + timedelta(minutes=1))
    assert cache.get("key") is not None


def test_sqlite_cache_discards_corrupt_entries():
    cache = SQLiteCache()
    now = datetime.now(timezone.utc)
    cache._connection.execute(
        "INSERT INTO http_cache VALUES (?, ?, ?, ?, ?, ?)",
        ("bad", "test", "not-json", now.isoformat(), (now + timedelta(minutes=1)).isoformat(), 1),
    )
    cache._connection.commit()
    assert cache.get("bad") is None
