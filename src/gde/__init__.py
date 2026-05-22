"""Nairobi Protocol — Geometric Determinism Engine (GDE).

A deterministic O(1) content-addressed storage engine that maps text keys
to exact byte offsets in a sparse file via a DCT-II geometric hash.

Public API
----------
- :func:`universal_geometric_hash` — 24D DCT-II hash of a text key
- :func:`coordinate_to_offset` — Map a hash vector to a byte offset
- :func:`distance` — Euclidean distance between two hash vectors
- :class:`GDEStore` — Sparse-file-backed key-value store with SQLite manifest
- :func:`ingest_file` — Chunk and ingest a document into a GDEStore
"""

from __future__ import annotations

from gde.hasher import coordinate_to_offset, distance, universal_geometric_hash

__all__ = [
    "universal_geometric_hash",
    "coordinate_to_offset",
    "distance",
]
