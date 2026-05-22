"""Tests for gde.ingest — document chunking and ingestion."""

from __future__ import annotations

from pathlib import Path

from gde.ingest import _chunk_by_paragraphs, ingest_file, ingest_text
from gde.store import GDEStore


class TestChunking:
    """Tests for the paragraph-based chunking algorithm."""

    def test_single_paragraph(self) -> None:
        """A single short paragraph stays as one chunk."""
        chunks = _chunk_by_paragraphs("Hello world", max_chunk_size=100)
        assert len(chunks) == 1
        assert chunks[0] == "Hello world"

    def test_multiple_paragraphs(self) -> None:
        """Paragraphs are packed into chunks."""
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunks = _chunk_by_paragraphs(text, max_chunk_size=100)
        assert len(chunks) >= 1
        # All content is preserved.
        joined = " ".join(chunks)
        assert "Paragraph one" in joined
        assert "Paragraph three" in joined

    def test_paragraph_splitting(self) -> None:
        """Paragraphs that exceed max_chunk_size trigger splitting."""
        # Two paragraphs, each 60 chars. With max_chunk_size=50, they
        # can't fit together.
        p1 = "a" * 50
        p2 = "b" * 50
        text = f"{p1}\n\n{p2}"
        chunks = _chunk_by_paragraphs(text, max_chunk_size=55, overlap=0)
        assert len(chunks) >= 2

    def test_oversized_paragraph_window(self) -> None:
        """An oversized single paragraph is split by sliding window."""
        text = "x" * 200
        chunks = _chunk_by_paragraphs(text, max_chunk_size=50, overlap=10)
        assert len(chunks) >= 4
        # All chunks fit within the limit.
        for chunk in chunks:
            assert len(chunk) <= 50

    def test_empty_text(self) -> None:
        """Empty text produces no chunks."""
        assert _chunk_by_paragraphs("") == []
        assert _chunk_by_paragraphs("   \n\n  ") == []


class TestIngestText:
    """Tests for text ingestion into a store."""

    def _make_store(self, tmp_path: Path) -> GDEStore:
        return GDEStore(
            store_dir=tmp_path,
            address_space=1024 * 1024,
            slot_size=4096,
        )

    def test_ingest_simple(self, tmp_path: Path) -> None:
        """Ingest a simple document and verify chunks are stored."""
        with self._make_store(tmp_path) as store:
            keys = ingest_text(
                "Hello world.\n\nThis is a test document.",
                source_name="test.md",
                store=store,
            )
            assert len(keys) >= 1
            assert keys[0] == "test.md::chunk_0"

            # Retrieve the first chunk.
            content = store.retrieve(keys[0])
            assert content is not None
            assert "Hello world" in content

    def test_ingest_empty(self, tmp_path: Path) -> None:
        """Ingesting empty text returns no keys."""
        with self._make_store(tmp_path) as store:
            keys = ingest_text("", source_name="empty.txt", store=store)
            assert keys == []

    def test_ingest_metadata(self, tmp_path: Path) -> None:
        """Metadata is attached to each chunk."""
        with self._make_store(tmp_path) as store:
            keys = ingest_text(
                "Some content here.",
                source_name="meta.md",
                store=store,
                metadata={"author": "test"},
            )
            entry = store._manifest.get(keys[0])
            assert entry is not None
            assert entry.metadata["author"] == "test"
            assert entry.metadata["source"] == "meta.md"


class TestIngestFile:
    """Tests for file-based ingestion."""

    def _make_store(self, tmp_path: Path) -> GDEStore:
        return GDEStore(
            store_dir=tmp_path / "store",
            address_space=1024 * 1024,
            slot_size=4096,
        )

    def test_ingest_txt_file(self, tmp_path: Path) -> None:
        """Ingest a .txt file."""
        test_file = tmp_path / "doc.txt"
        test_file.write_text("First paragraph.\n\nSecond paragraph.")

        with self._make_store(tmp_path) as store:
            keys = ingest_file(test_file, store)
            assert len(keys) >= 1

    def test_ingest_md_file(self, tmp_path: Path) -> None:
        """Ingest a .md file."""
        test_file = tmp_path / "readme.md"
        test_file.write_text("# Title\n\nSome content.\n\nMore content.")

        with self._make_store(tmp_path) as store:
            keys = ingest_file(test_file, store)
            assert len(keys) >= 1

    def test_ingest_nonexistent_file(self, tmp_path: Path) -> None:
        """Ingesting a nonexistent file raises FileNotFoundError."""
        with self._make_store(tmp_path) as store:
            try:
                ingest_file(tmp_path / "nonexistent.txt", store)
                assert False, "Should have raised FileNotFoundError"
            except FileNotFoundError:
                pass

    def test_ingest_unsupported_type(self, tmp_path: Path) -> None:
        """Ingesting an unsupported file type raises ValueError."""
        test_file = tmp_path / "image.png"
        test_file.write_bytes(b"\x89PNG")

        with self._make_store(tmp_path) as store:
            try:
                ingest_file(test_file, store)
                assert False, "Should have raised ValueError"
            except ValueError:
                pass
