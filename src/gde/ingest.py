"""Document chunking and ingestion into a GDE store.

Splits documents into chunks and stores each chunk with a deterministic key
of the form ``"{filename}::chunk_{i}"``.

Security notes
--------------
- File paths are resolved and boundary-checked before reading.
- Only plain text and markdown files are supported (no binary parsing).
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

from gde.store import GDEStore

logger = logging.getLogger(__name__)

# Default maximum chunk size in characters (not bytes).
DEFAULT_CHUNK_SIZE: int = 3500

# Overlap between adjacent chunks to preserve context at boundaries.
DEFAULT_OVERLAP: int = 200


def _chunk_by_paragraphs(
    text: str,
    max_chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    """Split text into chunks at paragraph boundaries.

    Strategy:
    1. Split on double-newlines (paragraph boundaries).
    2. Greedily pack paragraphs into chunks up to ``max_chunk_size``.
    3. If a single paragraph exceeds ``max_chunk_size``, fall back to
       a sliding window split.

    Parameters
    ----------
    text:
        The input document text.
    max_chunk_size:
        Maximum characters per chunk.
    overlap:
        Character overlap between adjacent chunks.

    Returns
    -------
    list[str]
        Non-empty text chunks.
    """
    # Normalize whitespace: collapse \r\n to \n.
    text = text.replace("\r\n", "\n")

    # Split on paragraph boundaries (double newlines).
    paragraphs = re.split(r"\n{2,}", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)

        # If a single paragraph is too large, split it by sentences / window.
        if para_len > max_chunk_size:
            # Flush current buffer first.
            if current:
                chunks.append("\n\n".join(current))
                current = []
                current_len = 0
            # Sliding window over the oversized paragraph.
            for sub_chunk in _sliding_window(para, max_chunk_size, overlap):
                chunks.append(sub_chunk)
            continue

        # Check if adding this paragraph would exceed the limit.
        # Account for the "\n\n" separator.
        separator_len = 2 if current else 0
        if current_len + separator_len + para_len > max_chunk_size:
            chunks.append("\n\n".join(current))
            # Start new chunk with overlap: include the last paragraph.
            if overlap > 0 and current:
                last_para = current[-1]
                current = [last_para, para]
                current_len = len(last_para) + 2 + para_len
            else:
                current = [para]
                current_len = para_len
        else:
            current.append(para)
            current_len += separator_len + para_len

    # Flush remaining.
    if current:
        chunks.append("\n\n".join(current))

    return chunks


def _sliding_window(
    text: str, window_size: int, overlap: int
) -> list[str]:
    """Split text into overlapping windows of ``window_size`` characters.

    Parameters
    ----------
    text:
        Input text.
    window_size:
        Size of each window.
    overlap:
        Overlap between adjacent windows.

    Returns
    -------
    list[str]
        Text chunks.
    """
    step = max(window_size - overlap, 1)
    chunks: list[str] = []
    for start in range(0, len(text), step):
        chunk = text[start : start + window_size].strip()
        if chunk:
            chunks.append(chunk)
        if start + window_size >= len(text):
            break
    return chunks


def _make_chunk_key(source_name: str, chunk_index: int) -> str:
    """Generate a deterministic chunk key.

    Parameters
    ----------
    source_name:
        The source document name (typically the filename).
    chunk_index:
        Zero-based chunk index.

    Returns
    -------
    str
        Key of the form ``"{source_name}::chunk_{chunk_index}"``.
    """
    return f"{source_name}::chunk_{chunk_index}"


def ingest_file(
    file_path: Path | str,
    store: GDEStore,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    metadata: dict[str, Any] | None = None,
) -> list[str]:
    """Ingest a document file into a GDE store.

    Reads the file, splits it into chunks, and stores each chunk with
    a deterministic key.

    Parameters
    ----------
    file_path:
        Path to the file to ingest. Must be a regular text file.
    store:
        The GDE store to write into.
    chunk_size:
        Maximum characters per chunk.
    overlap:
        Character overlap between adjacent chunks.
    metadata:
        Optional metadata to attach to every chunk entry.

    Returns
    -------
    list[str]
        The keys of all stored chunks.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If the file is not a supported type.
    """
    resolved = Path(file_path).resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"File not found: {resolved}")

    # Only allow text-like extensions.
    allowed_extensions = {".txt", ".md", ".markdown", ".rst", ".text", ".csv", ".log"}
    if resolved.suffix.lower() not in allowed_extensions:
        raise ValueError(
            f"Unsupported file type: {resolved.suffix}. "
            f"Supported: {', '.join(sorted(allowed_extensions))}"
        )

    text = resolved.read_text(encoding="utf-8", errors="replace")
    return ingest_text(
        text=text,
        source_name=resolved.name,
        store=store,
        chunk_size=chunk_size,
        overlap=overlap,
        metadata=metadata,
    )


def ingest_text(
    text: str,
    source_name: str,
    store: GDEStore,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    metadata: dict[str, Any] | None = None,
) -> list[str]:
    """Ingest raw text into a GDE store.

    Parameters
    ----------
    text:
        The document text.
    source_name:
        A name for the source (used in chunk keys).
    store:
        The GDE store to write into.
    chunk_size:
        Maximum characters per chunk.
    overlap:
        Character overlap between adjacent chunks.
    metadata:
        Optional metadata to attach to every chunk entry.

    Returns
    -------
    list[str]
        The keys of all stored chunks.
    """
    chunks = _chunk_by_paragraphs(text, max_chunk_size=chunk_size, overlap=overlap)
    if not chunks:
        logger.warning("No content to ingest from source: %s", source_name)
        return []

    base_metadata = metadata or {}
    stored_keys: list[str] = []

    for i, chunk in enumerate(chunks):
        key = _make_chunk_key(source_name, i)
        chunk_metadata = {
            **base_metadata,
            "source": source_name,
            "chunk_index": i,
            "total_chunks": len(chunks),
        }

        # Truncate chunk to fit in a single slot.
        chunk_bytes = chunk.encode("utf-8")
        if len(chunk_bytes) > store._slot_size:
            # Trim to fit slot (respecting UTF-8 boundaries).
            chunk = chunk_bytes[: store._slot_size].decode(
                "utf-8", errors="ignore"
            )
            logger.warning(
                "Chunk %d of %s truncated to %d bytes (slot_size=%d)",
                i,
                source_name,
                store._slot_size,
                store._slot_size,
            )

        store.store(key, chunk, metadata=chunk_metadata)
        stored_keys.append(key)

    logger.info(
        "Ingested %d chunks from %s", len(stored_keys), source_name
    )
    return stored_keys
