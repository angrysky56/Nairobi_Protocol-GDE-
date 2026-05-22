"""GDE sparse-file key-value store with collision detection.

The ``GDEStore`` combines three components:

1. **Hasher** — deterministic DCT-II hash → byte offset
2. **Sparse file** — 100 GB virtual file (only allocated blocks use disk)
3. **SQLite manifest** — tracks all keys, enables search, detects collisions

Security notes
--------------
- File paths are resolved and validated before I/O.
- SQLite uses parameterized queries (via :class:`Manifest`).
- No user-supplied data is used in file path construction.
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any

from gde.hasher import (
    DEFAULT_ADDRESS_SPACE,
    DEFAULT_SLOT_SIZE,
    coordinate_to_offset,
    universal_geometric_hash,
)
from gde.manifest import Manifest, ManifestEntry

logger = logging.getLogger(__name__)

# Maximum number of linear probes before giving up on collision resolution.
_MAX_PROBE_COUNT: int = 16


class CollisionError(Exception):
    """Raised when a key collision cannot be resolved."""


class GDEStore:
    """Sparse-file-backed deterministic key-value store.

    Parameters
    ----------
    store_dir:
        Directory containing the store files. Created if it doesn't exist.
    address_space:
        Total virtual address space in bytes (default: 100 GB).
    slot_size:
        Slot alignment size in bytes (default: 4096).
    """

    STORE_FILENAME = "knowledge_store.bin"
    MANIFEST_FILENAME = "manifest.db"

    def __init__(
        self,
        store_dir: Path | str,
        address_space: int = DEFAULT_ADDRESS_SPACE,
        slot_size: int = DEFAULT_SLOT_SIZE,
    ) -> None:
        self._store_dir = Path(store_dir).resolve()
        self._store_dir.mkdir(parents=True, exist_ok=True)

        self._address_space = address_space
        self._slot_size = slot_size

        self._bin_path = self._store_dir / self.STORE_FILENAME
        self._manifest = Manifest(self._store_dir / self.MANIFEST_FILENAME)

        self._ensure_sparse_file()

    def _ensure_sparse_file(self) -> None:
        """Create the sparse binary file if it doesn't exist."""
        if not self._bin_path.exists():
            # Create a sparse file by seeking to the end and writing nothing.
            with open(self._bin_path, "wb") as f:
                f.seek(self._address_space - 1)
                f.write(b"\x00")
            logger.info(
                "Created sparse store: %s (%d GB virtual)",
                self._bin_path,
                self._address_space // (1024**3),
            )

    # ----- Core operations -----

    def store(
        self,
        key: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ManifestEntry:
        """Store content at the deterministic address of ``key``.

        If the computed offset is already occupied by a different key,
        linear probing is used to find the next available slot (up to
        ``_MAX_PROBE_COUNT`` probes).

        Parameters
        ----------
        key:
            The storage key (any string).
        content:
            The content to store.
        metadata:
            Optional metadata dict to associate with this entry.

        Returns
        -------
        ManifestEntry
            The manifest entry for the stored content.

        Raises
        ------
        CollisionError
            If collision resolution fails after ``_MAX_PROBE_COUNT`` probes.
        ValueError
            If content exceeds the slot size.
        """
        content_bytes = content.encode("utf-8")
        if len(content_bytes) > self._slot_size:
            raise ValueError(
                f"Content ({len(content_bytes)} bytes) exceeds slot size "
                f"({self._slot_size} bytes). Use store_chunked() for large content."
            )

        # Check if key already exists — update in place.
        existing = self._manifest.get(key)
        if existing is not None:
            offset = existing.offset
        else:
            # Compute offset and handle collisions.
            vector = universal_geometric_hash(key)
            base_offset = coordinate_to_offset(
                vector,
                address_space=self._address_space,
                slot_size=self._slot_size,
            )
            offset = self._resolve_offset(key, base_offset)

        # Write content to the sparse file (padded to slot size).
        padded = content_bytes.ljust(self._slot_size, b"\x00")
        with open(self._bin_path, "r+b") as f:
            f.seek(offset)
            f.write(padded)

        # Record in manifest.
        content_hash = hashlib.sha256(content_bytes).hexdigest()
        entry = ManifestEntry(
            key=key,
            offset=offset,
            slot_size=self._slot_size,
            content_hash=content_hash,
            created_at=Manifest.now_iso(),
            metadata=metadata or {},
        )
        self._manifest.put(entry)
        return entry

    def retrieve(self, key: str) -> str | None:
        """Retrieve content by exact key.

        Parameters
        ----------
        key:
            The key to look up.

        Returns
        -------
        str or None
            The stored content, or ``None`` if the key is not found.
        """
        entry = self._manifest.get(key)
        if entry is None:
            return None

        with open(self._bin_path, "rb") as f:
            f.seek(entry.offset)
            raw = f.read(entry.slot_size)

        # Strip null padding.
        return raw.rstrip(b"\x00").decode("utf-8", errors="replace")

    def delete(self, key: str) -> bool:
        """Delete a key and zero its slot.

        Parameters
        ----------
        key:
            The key to delete.

        Returns
        -------
        bool
            True if the key existed and was deleted.
        """
        entry = self._manifest.get(key)
        if entry is None:
            return False

        # Zero the slot in the sparse file.
        with open(self._bin_path, "r+b") as f:
            f.seek(entry.offset)
            f.write(b"\x00" * entry.slot_size)

        return self._manifest.delete(key)

    def list_keys(
        self, prefix: str | None = None, limit: int = 100
    ) -> list[ManifestEntry]:
        """List stored keys, optionally filtered by prefix.

        Parameters
        ----------
        prefix:
            If provided, only return keys starting with this prefix.
        limit:
            Maximum number of results.

        Returns
        -------
        list[ManifestEntry]
        """
        return self._manifest.list_keys(prefix=prefix, limit=limit)

    def search(self, query: str, limit: int = 20) -> list[ManifestEntry]:
        """Full-text search over stored keys.

        This is the bridge between fuzzy LLM queries and exact GDE keys.

        Parameters
        ----------
        query:
            Natural language search query.
        limit:
            Maximum number of results.

        Returns
        -------
        list[ManifestEntry]
        """
        return self._manifest.search(query, limit=limit)

    def stats(self) -> dict[str, Any]:
        """Return store statistics.

        Returns
        -------
        dict
            Keys: ``entry_count``, ``store_size_bytes``,
            ``virtual_size_bytes``, ``slot_size``, ``manifest``.
        """
        actual_size = (
            self._bin_path.stat().st_size if self._bin_path.exists() else 0
        )
        # On Linux, st_blocks * 512 gives the actual disk usage for sparse files.
        try:
            disk_usage = os.stat(self._bin_path).st_blocks * 512
        except (AttributeError, OSError):
            disk_usage = actual_size

        return {
            "entry_count": self._manifest.count(),
            "virtual_size_bytes": self._address_space,
            "actual_disk_bytes": disk_usage,
            "slot_size": self._slot_size,
            "store_path": str(self._bin_path),
            "manifest": self._manifest.stats(),
        }

    # ----- Collision resolution -----

    def _resolve_offset(self, key: str, base_offset: int) -> int:
        """Find an available slot via linear probing.

        Parameters
        ----------
        key:
            The key being stored.
        base_offset:
            The initially computed offset.

        Returns
        -------
        int
            An available slot offset.

        Raises
        ------
        CollisionError
            If all probe slots are occupied by different keys.
        """
        for probe in range(_MAX_PROBE_COUNT):
            candidate = (base_offset + probe * self._slot_size) % self._address_space
            occupant = self._manifest.get_by_offset(candidate)
            if occupant is None:
                if probe > 0:
                    logger.warning(
                        "Collision resolved for key %r after %d probes "
                        "(base=%d, actual=%d)",
                        key,
                        probe,
                        base_offset,
                        candidate,
                    )
                return candidate
            if occupant.key == key:
                # Same key — overwrite is fine.
                return candidate
        raise CollisionError(
            f"Could not resolve collision for key {key!r} after "
            f"{_MAX_PROBE_COUNT} probes from offset {base_offset}"
        )

    # ----- Context manager -----

    def close(self) -> None:
        """Close the manifest database connection."""
        self._manifest.close()

    def __enter__(self) -> GDEStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
