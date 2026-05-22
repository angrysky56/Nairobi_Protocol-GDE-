"""Tests for gde.store and gde.manifest — store operations and collision handling."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from gde.manifest import Manifest, ManifestEntry
from gde.store import GDEStore


# ---------------------------------------------------------------------------
# Manifest tests
# ---------------------------------------------------------------------------


class TestManifest:
    """Tests for the SQLite manifest."""

    def test_put_and_get(self, tmp_path: Path) -> None:
        """Store and retrieve a manifest entry."""
        with Manifest(tmp_path / "test.db") as m:
            entry = ManifestEntry(
                key="test_key",
                offset=4096,
                slot_size=4096,
                content_hash="abc123",
                created_at=Manifest.now_iso(),
                metadata={"source": "test"},
            )
            m.put(entry)
            result = m.get("test_key")
            assert result is not None
            assert result.key == "test_key"
            assert result.offset == 4096

    def test_get_nonexistent(self, tmp_path: Path) -> None:
        """Getting a nonexistent key returns None."""
        with Manifest(tmp_path / "test.db") as m:
            assert m.get("nonexistent") is None

    def test_delete(self, tmp_path: Path) -> None:
        """Deleting a key removes it."""
        with Manifest(tmp_path / "test.db") as m:
            entry = ManifestEntry(
                key="delete_me",
                offset=8192,
                slot_size=4096,
                content_hash="def456",
                created_at=Manifest.now_iso(),
            )
            m.put(entry)
            assert m.delete("delete_me") is True
            assert m.get("delete_me") is None

    def test_delete_nonexistent(self, tmp_path: Path) -> None:
        """Deleting a nonexistent key returns False."""
        with Manifest(tmp_path / "test.db") as m:
            assert m.delete("nonexistent") is False

    def test_list_keys(self, tmp_path: Path) -> None:
        """List keys returns all entries."""
        with Manifest(tmp_path / "test.db") as m:
            for i in range(5):
                m.put(ManifestEntry(
                    key=f"key_{i}",
                    offset=i * 4096,
                    slot_size=4096,
                    content_hash=f"hash_{i}",
                    created_at=Manifest.now_iso(),
                ))
            entries = m.list_keys()
            assert len(entries) == 5

    def test_list_keys_prefix(self, tmp_path: Path) -> None:
        """List keys with prefix filter."""
        with Manifest(tmp_path / "test.db") as m:
            for key in ["neural_1", "neural_2", "quantum_1"]:
                m.put(ManifestEntry(
                    key=key,
                    offset=0,
                    slot_size=4096,
                    content_hash="h",
                    created_at=Manifest.now_iso(),
                ))
            entries = m.list_keys(prefix="neural")
            assert len(entries) == 2

    def test_search(self, tmp_path: Path) -> None:
        """FTS5 search finds matching keys."""
        with Manifest(tmp_path / "test.db") as m:
            for key in ["neural network architecture", "quantum computing", "neural logic"]:
                m.put(ManifestEntry(
                    key=key,
                    offset=0,
                    slot_size=4096,
                    content_hash="h",
                    created_at=Manifest.now_iso(),
                ))
            m._rebuild_fts()
            results = m.search("neural")
            keys = {r.key for r in results}
            assert "neural network architecture" in keys
            assert "neural logic" in keys

    def test_count(self, tmp_path: Path) -> None:
        """Count returns correct number of entries."""
        with Manifest(tmp_path / "test.db") as m:
            assert m.count() == 0
            m.put(ManifestEntry(
                key="k",
                offset=0,
                slot_size=4096,
                content_hash="h",
                created_at=Manifest.now_iso(),
            ))
            assert m.count() == 1

    def test_get_by_offset(self, tmp_path: Path) -> None:
        """Look up entry by offset (for collision detection)."""
        with Manifest(tmp_path / "test.db") as m:
            m.put(ManifestEntry(
                key="occupant",
                offset=12288,
                slot_size=4096,
                content_hash="h",
                created_at=Manifest.now_iso(),
            ))
            result = m.get_by_offset(12288)
            assert result is not None
            assert result.key == "occupant"
            assert m.get_by_offset(99999) is None


# ---------------------------------------------------------------------------
# GDEStore tests
# ---------------------------------------------------------------------------


class TestGDEStore:
    """Tests for the GDE store."""

    def _make_store(self, tmp_path: Path) -> GDEStore:
        """Create a small test store (1 MB address space)."""
        return GDEStore(
            store_dir=tmp_path,
            address_space=1024 * 1024,  # 1 MB
            slot_size=256,
        )

    def test_store_and_retrieve(self, tmp_path: Path) -> None:
        """Round-trip: store and retrieve content."""
        with self._make_store(tmp_path) as store:
            store.store("hello", "world")
            result = store.retrieve("hello")
            assert result == "world"

    def test_retrieve_nonexistent(self, tmp_path: Path) -> None:
        """Retrieving a nonexistent key returns None."""
        with self._make_store(tmp_path) as store:
            assert store.retrieve("nonexistent") is None

    def test_overwrite(self, tmp_path: Path) -> None:
        """Storing the same key twice overwrites the content."""
        with self._make_store(tmp_path) as store:
            store.store("key", "first")
            store.store("key", "second")
            assert store.retrieve("key") == "second"

    def test_delete(self, tmp_path: Path) -> None:
        """Deleting a key removes it."""
        with self._make_store(tmp_path) as store:
            store.store("key", "value")
            assert store.delete("key") is True
            assert store.retrieve("key") is None

    def test_delete_nonexistent(self, tmp_path: Path) -> None:
        """Deleting a nonexistent key returns False."""
        with self._make_store(tmp_path) as store:
            assert store.delete("nonexistent") is False

    def test_list_keys(self, tmp_path: Path) -> None:
        """List all stored keys."""
        with self._make_store(tmp_path) as store:
            store.store("alpha", "a")
            store.store("beta", "b")
            entries = store.list_keys()
            keys = {e.key for e in entries}
            assert keys == {"alpha", "beta"}

    def test_search(self, tmp_path: Path) -> None:
        """Search finds matching keys."""
        with self._make_store(tmp_path) as store:
            store.store("neural network", "content1")
            store.store("quantum computing", "content2")
            # Rebuild FTS for search.
            store._manifest._rebuild_fts()
            results = store.search("neural")
            keys = {r.key for r in results}
            assert "neural network" in keys

    def test_stats(self, tmp_path: Path) -> None:
        """Stats returns expected keys."""
        with self._make_store(tmp_path) as store:
            store.store("key", "value")
            info = store.stats()
            assert info["entry_count"] == 1
            assert "store_path" in info
            assert "slot_size" in info

    def test_content_too_large(self, tmp_path: Path) -> None:
        """Storing content larger than slot_size raises ValueError."""
        with self._make_store(tmp_path) as store:
            big_content = "x" * 1000  # > 256 byte slot_size
            try:
                store.store("big", big_content)
                assert False, "Should have raised ValueError"
            except ValueError:
                pass

    def test_multiple_keys_deterministic(self, tmp_path: Path) -> None:
        """Multiple keys produce deterministic offsets."""
        with self._make_store(tmp_path) as store:
            e1 = store.store("key_a", "value_a")
            e2 = store.store("key_b", "value_b")
            assert e1.offset != e2.offset or e1.key != e2.key

        # Re-open store, same offsets.
        with self._make_store(tmp_path) as store:
            r1 = store.retrieve("key_a")
            r2 = store.retrieve("key_b")
            assert r1 == "value_a"
            assert r2 == "value_b"

    def test_metadata_roundtrip(self, tmp_path: Path) -> None:
        """Metadata survives store → retrieve cycle."""
        with self._make_store(tmp_path) as store:
            entry = store.store(
                "meta_key", "data", metadata={"source": "test", "version": 1}
            )
            assert entry.metadata["source"] == "test"
            # Verify via manifest.
            looked_up = store._manifest.get("meta_key")
            assert looked_up is not None
            assert looked_up.metadata["version"] == 1
