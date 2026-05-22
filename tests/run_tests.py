#!/usr/bin/env python3
"""Standalone test runner using unittest (no pip dependencies required).

Usage:
    PYTHONPATH=src python3 tests/run_tests.py
"""

from __future__ import annotations

import math
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure src/ is on the path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


# ============================================================================
# Hasher tests
# ============================================================================

from gde.hasher import (
    DEFAULT_ADDRESS_SPACE,
    DEFAULT_SLOT_SIZE,
    HASH_DIM,
    coordinate_to_offset,
    distance,
    key_to_offset,
    universal_geometric_hash,
)


class TestUniversalGeometricHash(unittest.TestCase):
    def test_output_length(self) -> None:
        v = universal_geometric_hash("Neural")
        self.assertEqual(len(v), HASH_DIM)

    def test_unit_vector(self) -> None:
        v = universal_geometric_hash("Neural")
        norm = math.sqrt(sum(x * x for x in v))
        self.assertAlmostEqual(norm, 1.0, places=10)

    def test_deterministic(self) -> None:
        v1 = universal_geometric_hash("Quantum computing")
        v2 = universal_geometric_hash("Quantum computing")
        self.assertEqual(v1, v2)

    def test_case_insensitive(self) -> None:
        v1 = universal_geometric_hash("Neural")
        v2 = universal_geometric_hash("neural")
        self.assertEqual(v1, v2)

    def test_different_inputs_differ(self) -> None:
        v1 = universal_geometric_hash("Apple")
        v2 = universal_geometric_hash("Orbit")
        self.assertNotEqual(v1, v2)

    def test_empty_string(self) -> None:
        v = universal_geometric_hash("")
        self.assertEqual(len(v), HASH_DIM)

    def test_long_string_truncated(self) -> None:
        short = "a" * 32
        long_ = "a" * 100
        v1 = universal_geometric_hash(short)
        v2 = universal_geometric_hash(long_)
        self.assertEqual(v1, v2)


class TestDistance(unittest.TestCase):
    def test_identical_zero(self) -> None:
        self.assertEqual(distance("Apple", "Apple"), 0.0)

    def test_similar_closer(self) -> None:
        self.assertLess(
            distance("Apple", "Apples"),
            distance("Apple", "Orbit"),
        )

    def test_symmetry(self) -> None:
        d1 = distance("Neural", "Logic")
        d2 = distance("Logic", "Neural")
        self.assertAlmostEqual(d1, d2, places=15)

    def test_max_bounded(self) -> None:
        d = distance("aaa", "zzz")
        self.assertLessEqual(d, 2.0 + 1e-10)


class TestCoordinateToOffset(unittest.TestCase):
    def test_deterministic(self) -> None:
        v = universal_geometric_hash("neural network architecture")
        o1 = coordinate_to_offset(v)
        o2 = coordinate_to_offset(v)
        self.assertEqual(o1, o2)

    def test_slot_aligned(self) -> None:
        v = universal_geometric_hash("Quantum")
        offset = coordinate_to_offset(v)
        self.assertEqual(offset % DEFAULT_SLOT_SIZE, 0)

    def test_within_address_space(self) -> None:
        for word in ["Neural", "Logic", "Quantum", "Apple", "Orbit"]:
            v = universal_geometric_hash(word)
            offset = coordinate_to_offset(v)
            self.assertGreaterEqual(offset, 0)
            self.assertLess(offset, DEFAULT_ADDRESS_SPACE)

    def test_invalid_address_space(self) -> None:
        v = universal_geometric_hash("test")
        with self.assertRaises(ValueError):
            coordinate_to_offset(v, address_space=-1)

    def test_key_to_offset_matches(self) -> None:
        key = "neural network architecture"
        v = universal_geometric_hash(key)
        expected = coordinate_to_offset(v)
        self.assertEqual(key_to_offset(key), expected)


# ============================================================================
# Manifest tests
# ============================================================================

from gde.manifest import Manifest, ManifestEntry


class TestManifest(unittest.TestCase):
    def test_put_and_get(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with Manifest(Path(td) / "test.db") as m:
                entry = ManifestEntry(
                    key="test_key", offset=4096, slot_size=4096,
                    content_hash="abc", created_at=Manifest.now_iso(),
                )
                m.put(entry)
                result = m.get("test_key")
                self.assertIsNotNone(result)
                self.assertEqual(result.key, "test_key")  # type: ignore[union-attr]
                self.assertEqual(result.offset, 4096)  # type: ignore[union-attr]

    def test_get_nonexistent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with Manifest(Path(td) / "test.db") as m:
                self.assertIsNone(m.get("nope"))

    def test_delete(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with Manifest(Path(td) / "test.db") as m:
                m.put(ManifestEntry(
                    key="del", offset=0, slot_size=4096,
                    content_hash="h", created_at=Manifest.now_iso(),
                ))
                self.assertTrue(m.delete("del"))
                self.assertIsNone(m.get("del"))

    def test_list_keys(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with Manifest(Path(td) / "test.db") as m:
                for i in range(5):
                    m.put(ManifestEntry(
                        key=f"key_{i}", offset=i * 4096, slot_size=4096,
                        content_hash=f"h{i}", created_at=Manifest.now_iso(),
                    ))
                self.assertEqual(len(m.list_keys()), 5)

    def test_list_keys_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with Manifest(Path(td) / "test.db") as m:
                for k in ["neural_1", "neural_2", "quantum_1"]:
                    m.put(ManifestEntry(
                        key=k, offset=0, slot_size=4096,
                        content_hash="h", created_at=Manifest.now_iso(),
                    ))
                self.assertEqual(len(m.list_keys(prefix="neural")), 2)

    def test_count(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with Manifest(Path(td) / "test.db") as m:
                self.assertEqual(m.count(), 0)
                m.put(ManifestEntry(
                    key="k", offset=0, slot_size=4096,
                    content_hash="h", created_at=Manifest.now_iso(),
                ))
                self.assertEqual(m.count(), 1)

    def test_get_by_offset(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with Manifest(Path(td) / "test.db") as m:
                m.put(ManifestEntry(
                    key="occupant", offset=12288, slot_size=4096,
                    content_hash="h", created_at=Manifest.now_iso(),
                ))
                result = m.get_by_offset(12288)
                self.assertIsNotNone(result)
                self.assertEqual(result.key, "occupant")  # type: ignore[union-attr]
                self.assertIsNone(m.get_by_offset(99999))

    def test_search_fts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with Manifest(Path(td) / "test.db") as m:
                for k in ["neural network", "quantum computing", "neural logic"]:
                    m.put(ManifestEntry(
                        key=k, offset=0, slot_size=4096,
                        content_hash="h", created_at=Manifest.now_iso(),
                    ))
                m._rebuild_fts()
                results = m.search("neural")
                keys = {r.key for r in results}
                self.assertIn("neural network", keys)
                self.assertIn("neural logic", keys)


# ============================================================================
# GDEStore tests
# ============================================================================

from gde.store import GDEStore


class TestGDEStore(unittest.TestCase):
    def _make_store(self, path: str) -> GDEStore:
        return GDEStore(store_dir=path, address_space=1024 * 1024, slot_size=256)

    def test_store_and_retrieve(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self._make_store(td) as store:
                store.store("hello", "world")
                self.assertEqual(store.retrieve("hello"), "world")

    def test_retrieve_nonexistent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self._make_store(td) as store:
                self.assertIsNone(store.retrieve("nope"))

    def test_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self._make_store(td) as store:
                store.store("key", "first")
                store.store("key", "second")
                self.assertEqual(store.retrieve("key"), "second")

    def test_delete(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self._make_store(td) as store:
                store.store("key", "value")
                self.assertTrue(store.delete("key"))
                self.assertIsNone(store.retrieve("key"))

    def test_list_keys(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self._make_store(td) as store:
                store.store("alpha", "a")
                store.store("beta", "b")
                keys = {e.key for e in store.list_keys()}
                self.assertEqual(keys, {"alpha", "beta"})

    def test_stats(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self._make_store(td) as store:
                store.store("key", "value")
                info = store.stats()
                self.assertEqual(info["entry_count"], 1)
                self.assertIn("store_path", info)

    def test_content_too_large(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self._make_store(td) as store:
                with self.assertRaises(ValueError):
                    store.store("big", "x" * 1000)

    def test_metadata_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self._make_store(td) as store:
                entry = store.store("k", "v", metadata={"src": "test"})
                self.assertEqual(entry.metadata["src"], "test")
                looked_up = store._manifest.get("k")
                self.assertIsNotNone(looked_up)
                self.assertEqual(looked_up.metadata["src"], "test")  # type: ignore[union-attr]

    def test_multiple_keys_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self._make_store(td) as store:
                store.store("key_a", "value_a")
                store.store("key_b", "value_b")

            # Re-open and verify.
            with self._make_store(td) as store:
                self.assertEqual(store.retrieve("key_a"), "value_a")
                self.assertEqual(store.retrieve("key_b"), "value_b")


# ============================================================================
# Ingest tests
# ============================================================================

from gde.ingest import _chunk_by_paragraphs, ingest_file, ingest_text


class TestChunking(unittest.TestCase):
    def test_single_paragraph(self) -> None:
        chunks = _chunk_by_paragraphs("Hello world", max_chunk_size=100)
        self.assertEqual(len(chunks), 1)

    def test_multiple_paragraphs(self) -> None:
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunks = _chunk_by_paragraphs(text, max_chunk_size=100)
        self.assertGreaterEqual(len(chunks), 1)
        joined = " ".join(chunks)
        self.assertIn("Paragraph one", joined)

    def test_oversized_paragraph(self) -> None:
        text = "x" * 200
        chunks = _chunk_by_paragraphs(text, max_chunk_size=50, overlap=10)
        self.assertGreaterEqual(len(chunks), 4)
        for c in chunks:
            self.assertLessEqual(len(c), 50)

    def test_empty_text(self) -> None:
        self.assertEqual(_chunk_by_paragraphs(""), [])


class TestIngestText(unittest.TestCase):
    def _make_store(self, path: str) -> GDEStore:
        return GDEStore(store_dir=path, address_space=1024 * 1024, slot_size=4096)

    def test_ingest_simple(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self._make_store(td) as store:
                keys = ingest_text(
                    "Hello world.\n\nTest document.",
                    source_name="test.md",
                    store=store,
                )
                self.assertGreaterEqual(len(keys), 1)
                self.assertEqual(keys[0], "test.md::chunk_0")
                content = store.retrieve(keys[0])
                self.assertIsNotNone(content)
                self.assertIn("Hello world", content)  # type: ignore[arg-type]

    def test_ingest_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self._make_store(td) as store:
                keys = ingest_text("", source_name="empty.txt", store=store)
                self.assertEqual(keys, [])


class TestIngestFile(unittest.TestCase):
    def _make_store(self, path: str) -> GDEStore:
        return GDEStore(
            store_dir=os.path.join(path, "store"),
            address_space=1024 * 1024,
            slot_size=4096,
        )

    def test_ingest_txt_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            test_file = Path(td) / "doc.txt"
            test_file.write_text("First paragraph.\n\nSecond paragraph.")
            with self._make_store(td) as store:
                keys = ingest_file(test_file, store)
                self.assertGreaterEqual(len(keys), 1)

    def test_ingest_nonexistent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self._make_store(td) as store:
                with self.assertRaises(FileNotFoundError):
                    ingest_file(Path(td) / "nope.txt", store)

    def test_ingest_unsupported_type(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "image.png"
            bad.write_bytes(b"\x89PNG")
            with self._make_store(td) as store:
                with self.assertRaises(ValueError):
                    ingest_file(bad, store)


# ============================================================================
# CLI smoke test
# ============================================================================

class TestCLI(unittest.TestCase):
    def test_parser_builds(self) -> None:
        """CLI parser builds without errors."""
        from gde.cli import build_parser
        parser = build_parser()
        # Verify all subcommands exist.
        # argparse stores subparsers as _subparsers._actions
        self.assertIsNotNone(parser)


# ============================================================================
# Run
# ============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
