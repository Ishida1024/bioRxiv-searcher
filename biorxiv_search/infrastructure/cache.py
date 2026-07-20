import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class CacheEntry:
    payload: dict
    expires_at: datetime


class SQLiteCache:
    def __init__(self, path: str | Path = ":memory:") -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path)
        self._connection.execute("PRAGMA busy_timeout = 5000")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute(
            """CREATE TABLE IF NOT EXISTS http_cache (
                cache_key TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                response_json TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                schema_version INTEGER NOT NULL
            )"""
        )
        self._connection.commit()

    def get(self, key: str, *, now: datetime | None = None) -> CacheEntry | None:
        current = now or datetime.now(timezone.utc)
        row = self._connection.execute(
            "SELECT response_json, expires_at FROM http_cache WHERE cache_key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        try:
            expires_at = datetime.fromisoformat(row[1])
            payload = json.loads(row[0])
        except (ValueError, TypeError, json.JSONDecodeError):
            self.delete(key)
            return None
        if expires_at <= current:
            self.delete(key)
            return None
        if not isinstance(payload, dict):
            self.delete(key)
            return None
        return CacheEntry(payload, expires_at)

    def set(
        self,
        key: str,
        provider: str,
        payload: dict,
        expires_at: datetime,
        *,
        schema_version: int = 1,
        now: datetime | None = None,
    ) -> None:
        fetched_at = now or datetime.now(timezone.utc)
        self._connection.execute(
            """INSERT INTO http_cache
               (cache_key, provider, response_json, fetched_at, expires_at, schema_version)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(cache_key) DO UPDATE SET
                 provider=excluded.provider,
                 response_json=excluded.response_json,
                 fetched_at=excluded.fetched_at,
                 expires_at=excluded.expires_at,
                 schema_version=excluded.schema_version""",
            (key, provider, json.dumps(payload), fetched_at.isoformat(), expires_at.isoformat(), schema_version),
        )
        self._connection.commit()

    def delete(self, key: str) -> None:
        self._connection.execute("DELETE FROM http_cache WHERE cache_key = ?", (key,))
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()
