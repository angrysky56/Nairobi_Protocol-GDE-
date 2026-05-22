"""GDE MCP Tool Server.

Exposes the GDE store as MCP tools that LLMs can call:

- ``gde_store``    — Store a key-value pair
- ``gde_retrieve`` — Retrieve content by exact key
- ``gde_search``   — Full-text search over stored keys
- ``gde_ingest``   — Ingest a document file into the store
- ``gde_list``     — List stored keys with optional prefix filter
- ``gde_delete``   — Delete a key
- ``gde_stats``    — Store statistics

Security notes
--------------
- The server binds to ``127.0.0.1`` only (localhost), never ``0.0.0.0``.
- File paths from ``gde_ingest`` are resolved and validated against an
  allowlist of extensions before reading.
- All SQLite operations use parameterized queries.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from gde.ingest import ingest_file
from gde.store import CollisionError, GDEStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default store location
# ---------------------------------------------------------------------------

_DEFAULT_STORE_DIR = os.environ.get(
    "GDE_STORE_DIR",
    str(Path.home() / ".gde" / "default_store"),
)


def _get_store() -> GDEStore:
    """Get or create the singleton GDE store instance."""
    # TODO(performance): Consider caching this across calls.
    return GDEStore(store_dir=_DEFAULT_STORE_DIR)


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "gde",
    instructions=(
        "Geometric Determinism Engine (GDE) — a deterministic O(1) "
        "content-addressed knowledge store. Use gde_search to find keys "
        "matching a query, then gde_retrieve to fetch the content. "
        "Use gde_ingest to add documents, or gde_store for individual entries."
    ),
)


@mcp.tool()
def gde_store(key: str, content: str, metadata: str = "{}") -> str:
    """Store a key-value pair in the GDE knowledge store.

    Args:
        key: The storage key (any string, e.g. "neural network architecture").
        content: The content to store (must fit in a single slot, default 4KB).
        metadata: Optional JSON string of metadata to attach to the entry.

    Returns:
        JSON with the stored entry details (key, offset, content_hash).
    """
    try:
        meta = json.loads(metadata) if metadata else {}
    except json.JSONDecodeError:
        meta = {}

    with _get_store() as store:
        try:
            entry = store.store(key, content, metadata=meta)
        except CollisionError as exc:
            return json.dumps({"error": str(exc)})
        except ValueError as exc:
            return json.dumps({"error": str(exc)})

    return json.dumps({
        "status": "stored",
        "key": entry.key,
        "offset": entry.offset,
        "content_hash": entry.content_hash,
    })


@mcp.tool()
def gde_retrieve(key: str) -> str:
    """Retrieve content by exact key from the GDE knowledge store.

    Args:
        key: The exact key to look up.

    Returns:
        The stored content as a string, or an error message if not found.
    """
    with _get_store() as store:
        content = store.retrieve(key)

    if content is None:
        return json.dumps({"error": f"Key not found: {key!r}"})

    return json.dumps({"key": key, "content": content})


@mcp.tool()
def gde_search(query: str, limit: int = 20) -> str:
    """Search stored keys by natural language query.

    Use this to find relevant keys before calling gde_retrieve.
    Supports full-text search over all stored key names.

    Args:
        query: Natural language search query (e.g. "neural network").
        limit: Maximum number of results (default: 20).

    Returns:
        JSON array of matching entries with key, offset, and metadata.
    """
    with _get_store() as store:
        entries = store.search(query, limit=limit)

    results = [
        {
            "key": e.key,
            "offset": e.offset,
            "created_at": e.created_at,
            "metadata": e.metadata,
        }
        for e in entries
    ]
    return json.dumps({"matches": results, "count": len(results)})


@mcp.tool()
def gde_ingest(file_path: str) -> str:
    """Ingest a document file into the GDE knowledge store.

    Splits the document into chunks and stores each with a deterministic key.
    Supported file types: .txt, .md, .markdown, .rst, .text, .csv, .log

    Args:
        file_path: Absolute path to the file to ingest.

    Returns:
        JSON with the list of stored chunk keys.
    """
    resolved = Path(file_path).resolve()

    with _get_store() as store:
        try:
            keys = ingest_file(resolved, store)
        except FileNotFoundError as exc:
            return json.dumps({"error": str(exc)})
        except ValueError as exc:
            return json.dumps({"error": str(exc)})

    return json.dumps({
        "status": "ingested",
        "file": str(resolved),
        "chunks_stored": len(keys),
        "keys": keys,
    })


@mcp.tool()
def gde_list(prefix: str = "", limit: int = 100) -> str:
    """List stored keys with optional prefix filter.

    Args:
        prefix: Only return keys starting with this prefix. Empty for all.
        limit: Maximum number of results (default: 100).

    Returns:
        JSON array of entries with key, offset, and metadata.
    """
    with _get_store() as store:
        entries = store.list_keys(
            prefix=prefix if prefix else None, limit=limit
        )

    results = [
        {
            "key": e.key,
            "offset": e.offset,
            "created_at": e.created_at,
            "metadata": e.metadata,
        }
        for e in entries
    ]
    return json.dumps({"keys": results, "count": len(results)})


@mcp.tool()
def gde_delete(key: str) -> str:
    """Delete a key from the GDE knowledge store.

    Args:
        key: The exact key to delete.

    Returns:
        JSON indicating success or failure.
    """
    with _get_store() as store:
        deleted = store.delete(key)

    if deleted:
        return json.dumps({"status": "deleted", "key": key})
    return json.dumps({"error": f"Key not found: {key!r}"})


@mcp.tool()
def gde_stats() -> str:
    """Get GDE knowledge store statistics.

    Returns:
        JSON with entry count, disk usage, virtual size, and slot size.
    """
    with _get_store() as store:
        info = store.stats()

    return json.dumps(info)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the MCP server."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting GDE MCP server (store_dir=%s)", _DEFAULT_STORE_DIR)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
