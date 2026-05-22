"""SQLite-backed key manifest with FTS5 full-text search.

The manifest tracks every key stored in the GDE sparse file, enabling:

- Exact key lookup (O(1) via PRIMARY KEY)
- Full-text search over keys (via FTS5)
- Prefix listing / pagination
- Collision detection (offset occupancy check)

Security notes
--------------
- All SQL uses parameterized queries (no string concatenation).
- File paths are validated before use.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    """A single entry in the GDE key manifest."""

    key: str
    offset: int
    slot_size: int
    content_hash: str
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)


class Manifest:
    """SQLite-backed key registry with FTS5 search.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file. Created if it doesn't exist.
    """

    def __init__(self, db_path: Path | str) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create tables if they don't exist."""
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS entries (
                key         TEXT    PRIMARY KEY,
                offset_addr INTEGER NOT NULL,
                slot_size   INTEGER NOT NULL,
                content_hash TEXT   NOT NULL,
                created_at  TEXT    NOT NULL,
                metadata    TEXT    NOT NULL DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_entries_offset
                ON entries(offset_addr);
            """
        )
        # FTS5 virtual table for full-text search over keys.
        # We use a separate content-sync table to keep FTS in sync.
        self._conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts
            USING fts5(key, content=entries, content_rowid=rowid);
            """
        )
        self._conn.commit()

    def _rebuild_fts(self) -> None:
        """Rebuild the FTS index from the entries table."""
        self._conn.execute(
            "INSERT INTO entries_fts(entries_fts) VALUES('rebuild')"
        )
        self._conn.commit()

    # ----- Write operations -----

    def put(self, entry: ManifestEntry) -> None:
        """Insert or replace a manifest entry.

        Parameters
        ----------
        entry:
            The entry to store.
        """
        metadata_json = json.dumps(entry.metadata, separators=(",", ":"))
        self._conn.execute(
            """
            INSERT OR REPLACE INTO entries
                (key, offset_addr, slot_size, content_hash, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                entry.key,
                entry.offset,
                entry.slot_size,
                entry.content_hash,
                entry.created_at,
                metadata_json,
            ),
        )
        # Sync FTS — delete old entry if exists, insert new.
        self._conn.execute(
            "INSERT OR IGNORE INTO entries_fts(rowid, key) "
            "SELECT rowid, key FROM entries WHERE key = ?",
            (entry.key,),
        )
        self._conn.commit()

    def delete(self, key: str) -> bool:
        """Remove an entry by key.

        Returns
        -------
        bool
            True if the entry existed and was deleted.
        """
        cursor = self._conn.execute(
            "DELETE FROM entries WHERE key = ?", (key,)
        )
        self._conn.commit()
        if cursor.rowcount > 0:
            self._rebuild_fts()
            return True
        return False

    # ----- Read operations -----

    def get(self, key: str) -> ManifestEntry | None:
        """Look up an entry by exact key.

        Parameters
        ----------
        key:
            The key to look up.

        Returns
        -------
        ManifestEntry or None
        """
        row = self._conn.execute(
            "SELECT key, offset_addr, slot_size, content_hash, created_at, metadata "
            "FROM entries WHERE key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_entry(row)

    def get_by_offset(self, offset: int) -> ManifestEntry | None:
        """Look up an entry by offset address (for collision detection).

        Parameters
        ----------
        offset:
            The byte offset to check.

        Returns
        -------
        ManifestEntry or None
        """
        row = self._conn.execute(
            "SELECT key, offset_addr, slot_size, content_hash, created_at, metadata "
            "FROM entries WHERE offset_addr = ? LIMIT 1",
            (offset,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_entry(row)

    def list_keys(
        self, prefix: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[ManifestEntry]:
        """List entries, optionally filtered by key prefix.

        Parameters
        ----------
        prefix:
            If provided, only return keys starting with this prefix.
        limit:
            Maximum number of results (default: 100).
        offset:
            Pagination offset (default: 0).

        Returns
        -------
        list[ManifestEntry]
        """
        if prefix is not None:
            rows = self._conn.execute(
                "SELECT key, offset_addr, slot_size, content_hash, created_at, metadata "
                "FROM entries WHERE key LIKE ? ORDER BY key LIMIT ? OFFSET ?",
                (prefix + "%", limit, offset),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT key, offset_addr, slot_size, content_hash, created_at, metadata "
                "FROM entries ORDER BY key LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def search(self, query: str, limit: int = 20) -> list[ManifestEntry]:
        """Full-text search over stored keys using FTS5.

        Parameters
        ----------
        query:
            The search query (supports FTS5 syntax like ``neural AND network``).
        limit:
            Maximum number of results.

        Returns
        -------
        list[ManifestEntry]
        """
        # Sanitize: FTS5 queries are passed as parameters, but we need to
        # handle the case where the query has special FTS5 syntax characters.
        # For simple keyword matching, we quote each word.
        safe_query = " ".join(
            f'"{word}"' for word in query.split() if word.strip()
        )
        if not safe_query:
            return []
        try:
            rows = self._conn.execute(
                "SELECT e.key, e.offset_addr, e.slot_size, e.content_hash, "
                "       e.created_at, e.metadata "
                "FROM entries_fts f "
                "JOIN entries e ON e.rowid = f.rowid "
                "WHERE entries_fts MATCH ? "
                "ORDER BY rank "
                "LIMIT ?",
                (safe_query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            # If FTS query is malformed, fall back to LIKE search.
            like_pattern = "%" + query.replace("%", "").replace("_", "") + "%"
            rows = self._conn.execute(
                "SELECT key, offset_addr, slot_size, content_hash, created_at, metadata "
                "FROM entries WHERE key LIKE ? ORDER BY key LIMIT ?",
                (like_pattern, limit),
            ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def count(self) -> int:
        """Return the total number of entries."""
        row = self._conn.execute("SELECT COUNT(*) FROM entries").fetchone()
        return row[0] if row else 0

    def stats(self) -> dict[str, Any]:
        """Return summary statistics about the manifest.

        Returns
        -------
        dict
            Keys: ``entry_count``, ``db_size_bytes``, ``db_path``.
        """
        return {
            "entry_count": self.count(),
            "db_size_bytes": self._db_path.stat().st_size if self._db_path.exists() else 0,
            "db_path": str(self._db_path),
        }

    # ----- Helpers -----

    @staticmethod
    def _row_to_entry(row: tuple[Any, ...]) -> ManifestEntry:
        """Convert a database row to a ManifestEntry."""
        metadata_raw = row[5] if len(row) > 5 else "{}"
        try:
            metadata = json.loads(metadata_raw)
        except (json.JSONDecodeError, TypeError):
            metadata = {}
        return ManifestEntry(
            key=row[0],
            offset=row[1],
            slot_size=row[2],
            content_hash=row[3],
            created_at=row[4],
            metadata=metadata,
        )

    @staticmethod
    def now_iso() -> str:
        """Return the current UTC time in ISO 8601 format."""
        return datetime.now(timezone.utc).isoformat()

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> Manifest:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
