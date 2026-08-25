"""SQLite cache for page ad counts."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from models import PageResult
from utils import DATA_DIR, ensure_dirs

DB_PATH = DATA_DIR / "cache.sqlite"


def _connect(path: Path | None = None) -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS page_cache (
            page_id TEXT NOT NULL,
            country TEXT NOT NULL,
            page_name TEXT,
            active_ads INTEGER,
            payload TEXT NOT NULL,
            last_checked TEXT NOT NULL,
            PRIMARY KEY (page_id, country)
        )
        """
    )
    conn.commit()
    return conn


class PageCache:
    def __init__(self, path: Path | None = None, ttl_hours: float = 12.0):
        self.path = path or DB_PATH
        self.ttl_hours = ttl_hours

    def get(self, page_id: str, country: str) -> PageResult | None:
        with _connect(self.path) as conn:
            row = conn.execute(
                "SELECT payload, last_checked FROM page_cache WHERE page_id = ? AND country = ?",
                (str(page_id), country.upper()),
            ).fetchone()
        if not row:
            return None
        last = datetime.fromisoformat(row["last_checked"])
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - last
        if age > timedelta(hours=self.ttl_hours):
            return None
        data = json.loads(row["payload"])
        result = PageResult.from_dict(data)
        result.from_cache = True
        return result

    def put(self, country: str, result: PageResult) -> None:
        payload = json.dumps(result.to_dict(), ensure_ascii=False)
        checked = result.last_checked or datetime.now(timezone.utc).isoformat()
        with _connect(self.path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO page_cache
                (page_id, country, page_name, active_ads, payload, last_checked)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    result.page_id,
                    country.upper(),
                    result.page_name,
                    result.active_ads_found,
                    payload,
                    checked,
                ),
            )
            conn.commit()

    def delete(self, page_id: str, country: str) -> None:
        with _connect(self.path) as conn:
            conn.execute(
                "DELETE FROM page_cache WHERE page_id = ? AND country = ?",
                (str(page_id), country.upper()),
            )
            conn.commit()

    def stats(self) -> dict[str, Any]:
        with _connect(self.path) as conn:
            n = conn.execute("SELECT COUNT(*) AS n FROM page_cache").fetchone()["n"]
        return {"entries": n, "ttl_hours": self.ttl_hours}
