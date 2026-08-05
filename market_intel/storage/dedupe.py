from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from threading import Lock


class DedupeIndex:
    """Persistent deduplication index backed by SQLite B-tree indexes."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=NORMAL")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_records (
                fingerprint TEXT PRIMARY KEY,
                tweet_id TEXT,
                first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) WITHOUT ROWID
            """
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_seen_tweet_id ON seen_records(tweet_id)"
        )
        self.connection.commit()
        self._lock = Lock()

    def add_if_new(self, fingerprint: str, tweet_id: str) -> bool:
        """Insert a record only when neither fingerprint nor tweet ID was seen."""

        with self._lock:
            existing = self.connection.execute(
                """
                SELECT 1
                FROM seen_records
                WHERE fingerprint = ? OR (tweet_id <> '' AND tweet_id = ?)
                LIMIT 1
                """,
                (fingerprint, tweet_id),
            ).fetchone()
            if existing:
                return False

            self.connection.execute(
                "INSERT INTO seen_records(fingerprint, tweet_id) VALUES (?, ?)",
                (fingerprint, tweet_id),
            )
            self.connection.commit()
            return True

    def seed_tweet_ids(self, tweet_ids: Iterable[str], batch_size: int = 1_000) -> int:
        """Seed the index from an existing Parquet dataset for resumable runs."""

        inserted = 0
        batch: list[tuple[str, str]] = []

        def flush() -> int:
            if not batch:
                return 0
            before = self.connection.total_changes
            self.connection.executemany(
                "INSERT OR IGNORE INTO seen_records(fingerprint, tweet_id) VALUES (?, ?)",
                batch,
            )
            self.connection.commit()
            changed = self.connection.total_changes - before
            batch.clear()
            return changed

        with self._lock:
            for tweet_id in tweet_ids:
                value = str(tweet_id).strip()
                if not value:
                    continue
                fingerprint = hashlib.sha256(f"id:{value}".encode("utf-8")).hexdigest()
                batch.append((fingerprint, value))
                if len(batch) >= batch_size:
                    inserted += flush()
            inserted += flush()

        return inserted

    def count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) FROM seen_records").fetchone()
        return int(row[0]) if row else 0

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "DedupeIndex":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()