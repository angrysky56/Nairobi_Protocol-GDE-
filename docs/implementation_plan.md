# GDE MCP Server & CLI — Implementation Plan

Build a Python MCP server and CLI that wraps the GDE core engine, adds the three missing pieces (doc ingestion, LLM integration via MCP, API layer), and fixes critical gaps (collisions, key discovery).

---

## User Review Required

> [!IMPORTANT]
> **Mojo ↔ Python Hash Mismatch**: The Mojo and Python hash implementations produce *different* vectors for the same input. Key differences:
> - **Mojo**: 24D output, raw byte signal, single `scale0` factor for all dimensions
> - **Python**: 8D output, interleaved byte+delta signal, `scale0` for k=0 and `scale` for k>0, L2-normalized output
>
> The Python version is more mathematically correct (proper DCT-II scaling) but incompatible with the Mojo engine. **Which should be canonical?** I recommend making the Python implementation the canonical one (with the Mojo dimensions bumped to match), since the MCP server will be in Python.

> [!WARNING]
> **Data in `knowledge_base.json`**: The 5MB pre-computed vector file uses the Mojo hash (24D, unnormalized). If we switch to the Python hash, this file becomes obsolete. This is fine since nothing reads it anyway.

## Open Questions

1. **Hash dimensions**: Should we keep 24D (Mojo) or 8D (Python reference)? 24D gives better collision resistance. I recommend **24D with proper DCT-II scaling + L2 normalization** — a hybrid that takes the best of both.

2. **Slot size**: Currently 256 bytes. Documents will need larger slots. Should we use variable-length slots with a length header, or a fixed larger slot (e.g., 4KB)?

3. **Ingestion scope**: Should doc ingestion support just plain text files initially, or also PDF/markdown from the start?

---

## Proposed Changes

### Phase 1 — Canonical Python Engine Library

Create a clean Python package at `src/gde/` that is the single source of truth for the hash, offset, and storage logic.

#### [NEW] [src/gde/__init__.py](file:///home/ty/Repositories/ai_workspace/Nairobi_Protocol-GDE-/src/gde/__init__.py)
Package init, exports public API.

#### [NEW] [src/gde/hasher.py](file:///home/ty/Repositories/ai_workspace/Nairobi_Protocol-GDE-/src/gde/hasher.py)
- Port `universal_geometric_hash()` from the Mojo engine to Python
- Use **24D with proper DCT-II scaling and L2 normalization**
- Add `coordinate_to_offset(vector, address_space, slot_size)` 
- Add `distance(left, right)` for semantic proximity checks
- Pure Python + math stdlib — no numpy needed

#### [NEW] [src/gde/store.py](file:///home/ty/Repositories/ai_workspace/Nairobi_Protocol-GDE-/src/gde/store.py)
- `GDEStore` class: manages the sparse binary file + SQLite manifest
- **SQLite manifest** tracks: key, offset, slot_size, content_hash, timestamp, metadata_json
- `store(key, content, metadata=None)` — hash → offset → collision check → write
- `retrieve(key)` → hash → offset → seek → read
- `list_keys(prefix=None, limit=100)` → query manifest
- `search_keys(query)` → FTS5 search over stored keys
- **Collision detection**: before writing, check if offset is occupied by a different key. If collision, use **linear probing** (next slot) with a max probe count
- `delete(key)` → zero the slot, remove from manifest

#### [NEW] [src/gde/manifest.py](file:///home/ty/Repositories/ai_workspace/Nairobi_Protocol-GDE-/src/gde/manifest.py)
- SQLite-backed key registry with FTS5 for key search
- Schema: `entries(key TEXT PRIMARY KEY, offset INTEGER, slot_size INTEGER, content_hash TEXT, created_at TEXT, metadata JSON)`
- FTS5 virtual table for full-text search over keys

---

### Phase 2 — Document Ingestion

#### [NEW] [src/gde/ingest.py](file:///home/ty/Repositories/ai_workspace/Nairobi_Protocol-GDE-/src/gde/ingest.py)
- `ingest_file(path, store, chunk_size=2048)` — read file, split into chunks, store each
- **Chunking strategy**: split by paragraph boundaries, fall back to sliding window with overlap
- **Key generation**: `"{filename}::chunk_{i}"` — deterministic, reconstructable
- Support plain text and markdown initially
- Returns list of stored keys for the ingested document

#### [MODIFY] [src/gde/store.py](file:///home/ty/Repositories/ai_workspace/Nairobi_Protocol-GDE-/src/gde/store.py)
- Increase default slot size to **4096 bytes** for document chunks
- Add `store_document(key, content)` for content longer than one slot — chains across multiple slots with a linked-list header

---

### Phase 3 — MCP Server

#### [NEW] [src/gde/mcp_server.py](file:///home/ty/Repositories/ai_workspace/Nairobi_Protocol-GDE-/src/gde/mcp_server.py)
MCP tool server using the `mcp` Python SDK. Exposes these tools:

| Tool | Description |
|---|---|
| `gde_store` | Store a key-value pair: `(key, content, metadata?)` → offset |
| `gde_retrieve` | Retrieve content by exact key: `(key)` → content |
| `gde_search` | Search stored keys by natural language query: `(query, limit?)` → matching keys |
| `gde_ingest` | Ingest a file into the store: `(file_path)` → list of chunk keys |
| `gde_list` | List all stored keys: `(prefix?, limit?)` → keys with metadata |
| `gde_delete` | Delete a key: `(key)` → success/failure |
| `gde_stats` | Store statistics: entry count, file size, collision count |

The `gde_search` tool is what bridges the "LLM generates fuzzy queries" → "GDE requires exact keys" gap. It searches the SQLite FTS5 index over stored keys, then the LLM can call `gde_retrieve` with the matched key.

#### [NEW] [pyproject.toml](file:///home/ty/Repositories/ai_workspace/Nairobi_Protocol-GDE-/pyproject.toml)
- Python project configuration
- Dependencies: `mcp` (MCP SDK)
- Entry point: `gde-server` CLI command
- Scripts: `gde` CLI command

---

### Phase 4 — CLI

#### [NEW] [src/gde/cli.py](file:///home/ty/Repositories/ai_workspace/Nairobi_Protocol-GDE-/src/gde/cli.py)
argparse-based CLI wrapping the store:

```bash
# Store a value
gde store "neural network architecture" "Neural networks are..."

# Retrieve a value  
gde retrieve "neural network architecture"

# Ingest a file
gde ingest docs/paper.md

# Search keys
gde search "neural"

# List all keys
gde list

# Stats
gde stats

# Start MCP server
gde serve
```

---

## File Tree (New Files)

```
src/
  gde/
    __init__.py          # Package init
    hasher.py            # DCT hash + offset computation
    store.py             # GDEStore: sparse file + SQLite manifest
    manifest.py          # SQLite manifest with FTS5
    ingest.py            # Document chunking + ingestion
    mcp_server.py        # MCP tool server
    cli.py               # CLI entry point
pyproject.toml           # Python project config
```

---

## Verification Plan

### Automated Tests

```bash
# Unit tests for hash determinism
python -m pytest tests/test_hasher.py -v

# Unit tests for store operations (store, retrieve, delete, collision)
python -m pytest tests/test_store.py -v

# Unit tests for ingestion
python -m pytest tests/test_ingest.py -v

# Integration test: hash parity check (Python output matches expected values)
python -m pytest tests/test_parity.py -v

# MCP server smoke test (start server, call each tool)
python -m pytest tests/test_mcp_server.py -v
```

### Manual Verification

1. Run `gde store` / `gde retrieve` round-trip from CLI
2. Ingest a real markdown file and retrieve chunks
3. Test `gde search` with fuzzy queries against stored keys
4. Connect the MCP server to an AI assistant and verify tool-calling works
5. Verify collision detection by storing keys that map to the same offset

### Regression Against Mojo Engine

- Verify the Python hash produces consistent, deterministic outputs
- Benchmark Python hash throughput vs Mojo (expected: Python ~100x slower, which is fine for an MCP server)
