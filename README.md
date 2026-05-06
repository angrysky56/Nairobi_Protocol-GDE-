# Nairobi Protocol — Geometric Determinism Engine (GDE)

A deterministic retrieval engine that replaces probabilistic search with absolute coordinate mapping. Built in Mojo for direct hardware-level memory control. Developed in Nairobi, Kenya by RRD Kenya.

> **DOI:** https://doi.org/10.5281/zenodo.20036883
> **Author:** Tom Kimingi — RRD Kenya
> **License:** MIT

---

## What It Does

The GDE replaces O(n) vector scanning with O(1) geometric addressing. Instead of scanning a knowledge base to find a match, it calculates the exact memory address of a target and jumps directly to it via mmap.

This allows large address spaces (tested up to 100GB) to be navigated on machines with as little as 4GB of RAM, with no data loaded into memory until the exact location is needed.

---

## The Nairobi Protocol — Core Formula

    Offset = sum(|vi| * wi) + Base Address

    where:
      vi = coordinate component in dimension i (from 24D geometric hash)
      wi = (i+1) * 2654435761  (Knuth multiplicative constant)
      Base Address = starting byte of the memory-mapped data file

The same input always produces the same offset. Deterministic, environment-agnostic,
precise to 14 decimal places across different hardware architectures.

---

## Architecture

    Word / Concept
          |
          v
    universal_geometric_hash()   ->   24D HashVector       (phonological.mojo)
          |
          v
    coordinate_to_offset()       ->   Unique byte address  (coordinate_bridge.mojo)
          |
          v
    mmap seek                    ->   Direct hardware jump (stress_test_mmap.mojo)
          |
          v
    Exact data retrieved — no scanning, no guessing

### Layers

| Layer | File | Purpose |
|---|---|---|
| Geometric hashing | src/1_gateway/phonological.mojo | 24D HashVector from text |
| Knowledge persistence | src/1_gateway/persistence.mojo | Save and retrieve vectors via indexed offsets |
| Coordinate bridge | src/2_execution/coordinate_bridge.mojo | Maps coordinates to byte addresses |
| Atlas manager | src/2_execution/atlas_manager.mojo | mmap page tracking |
| Logic kernels | src/2_execution/logic_kernels.mojo | SIMD distance operations |
| Spectral layer | src/1_gateway/spectral.mojo | Laplacian graph signatures |
| Wavelet layer | src/1_gateway/wavelet.mojo | Hierarchical depth encoding |
| Ontology parser | src/0_refinery/ontology_parser.py | SQLite-backed knowledge graph |
| Contrastive LCA | src/0_refinery/contrast_lca.py | Graph-based coordinate scoring |

---

## Benchmark Results

### Scale Comparison: 10K vs 1M Entry Knowledge Base

These results demonstrate how GDE and RAG scale differently as knowledge base size grows.

#### 10,000 Entry Knowledge Base — 16GB Machine

| Metric | RAG (Cosine Scan) | GDE (Deterministic) | Factor |
|---|---|---|---|
| Total time (100 queries) | 13.110s | 0.038s | 345x faster |
| Per query | 131.1ms | 0.379ms | 345x faster |
| Scans per query | 10,000 | 1 | 10,000x fewer |
| Total CPU operations | 1,000,000 | 100 | 99.99% reduction |
| Collisions | N/A | 0 / 10,000 | 100% precise |

#### 1,000,000 Entry Knowledge Base — 16GB Machine

| Metric | RAG (Cosine Scan) | GDE (Deterministic) | Factor |
|---|---|---|---|
| Total time (100 queries) | 691.92s | 0.035s | 19,491x faster |
| Per query | 6,919ms | 0.355ms | 19,491x faster |
| Scans per query | 1,000,000 | 1 | 1,000,000x fewer |
| Total CPU operations | 100,000,000 | 100 | 99.9999% reduction |
| Collisions | N/A | 4 / 1,000,000 | 0.0004% rate |

#### 800,000 Entry Knowledge Base — 4GB Machine (1.9GB RAM, 552MB available)

| Metric | RAG | GDE |
|---|---|---|
| Result | Killed — OOM | Complete success |
| Total time (100 queries) | Cannot complete | 0.019s |
| Per query | Hardware failure | 0.191ms |
| Collisions | N/A | 0 / 800,000 |

RAG was terminated by the OS out-of-memory killer. GDE completed the same workload in 19 milliseconds on the same machine.

---

### Scaling Law — O(1) vs O(n) Proven

| Knowledge Base Size | RAG per query | GDE per query | Ratio |
|---|---|---|---|
| 10,000 entries | 131.1ms | 0.379ms | 345x |
| 1,000,000 entries | 6,919ms | 0.355ms | 19,491x |
| Growth factor | 52.8x slower | Unchanged | Scales linearly |

As the knowledge base grows 100x, RAG gets 52x slower. GDE stays constant. This confirms O(n) vs O(1) complexity in production conditions.

---

### mmap Address Space Tests — Concurrent Cross-Hardware

Both machines ran the same test simultaneously. Same code. Same address space. Bit-identical results.

| Test | 16GB Machine | 4GB Machine |
|---|---|---|
| 100GB boundary jump | 1.805s | — |
| 1,000,000 seeks (under load) | 5.738s | 9.606s |
| 1,000,000 seeks (clean) | 1.906s | 9.235s |
| Result at byte 0 | A | A |
| Result at byte 107,374,182,399 | Z | Z |
| Logic verified | Pass | Pass |

The 4GB machine is 4.4x slower due to limited page cache. The logic produces identical results on both architectures — hardware-stable determinism confirmed.

---

### Offset Distribution Validation — 1M Entries

Sample offsets across the 100GB address space:

| Word | Offset (bytes) |
|---|---|
| orbit432748 | 94,733,045,963 |
| osmosis916601 | 80,900,678,474 |
| antibody200493 | 47,265,435,865 |
| derivative69520 | 97,851,950,232 |
| abstraction806452 | 86,294,524,786 |
| protein925794 | 95,605,065,213 |

Collision rate at 1M entries: 4 / 1,000,000 (0.0004%)

---

## Thermal Efficiency

CPU operations are a direct proxy for processor load, heat generation, and power consumption.

At 1M entries, GDE reduces CPU operations by 99.9999% per query compared to RAG.

Projected at 1 billion queries per day:

| | RAG (1M KB) | GDE (1M KB) |
|---|---|---|
| Daily CPU active time | ~6,919,000,000s | ~355,000s |
| Operations executed | 100 quadrillion | 100 billion |
| Operations eliminated | — | 99.9999% |

RAG cannot run at all on 4GB hardware at this scale. GDE runs in 19ms.
This is not a performance improvement. It is the difference between possible and impossible.

---

## Why This Matters

Current AI infrastructure scales by adding hardware. The Nairobi Protocol scales by improving geometry. The result is the same intelligence at a fraction of the operational cost — accessible on modest, offline hardware without cloud dependency.

This decouples intelligence from wealth. A 4GB machine in Nairobi can perform retrieval that kills a standard RAG system. The hardware constraint that was supposed to be a limitation became the proof of concept.

---

## Hardware Requirements

- OS: Linux (tested on WSL2/Ubuntu)
- RAM: 4GB minimum (RAG requires significantly more at scale)
- Storage: Any filesystem supporting sparse files (ext4 recommended)
- CPU: x86_64 with SSE4.2 and AVX
- External storage: Supported for large model files via mmap

---

## Running the Tests

Install environment:

    pixi project channel add https://conda.modular.com/max
    pixi install

Build the knowledge base (generates data/ locally):

    python3 build_knowledge_base.py

Run RAG benchmark:

    python3 benchmark_rag.py

Run GDE benchmark:

    python3 benchmark_gde.py

Run mmap boundary jump test:

    truncate -s 100G stress_test_model.bin
    time pixi run mojo stress_test_mmap.mojo

Run 1,000,000 seek stress test:

    time pixi run mojo stress_test_1m.mojo

Run geometric engine tests:

    pixi run seed-mojo
    pixi run bench-mojo

Run coordinate bridge:

    pixi run mojo -I src/1_gateway -I src/2_execution src/2_execution/coordinate_bridge.mojo

Note: data/ is not committed. Run build_knowledge_base.py to generate locally.

---

## Project Structure

    src/
      0_refinery/     Phonological and semantic processing
      1_gateway/      Geometric hash and coordinate engine
      2_execution/    mmap execution and offset resolution
    tests/            Reference validators and benchmarks
    build_knowledge_base.py   Generates knowledge base locally
    benchmark_rag.py          RAG cosine similarity benchmark
    benchmark_gde.py          GDE deterministic retrieval benchmark
    stress_test_mmap.mojo     100GB boundary jump test
    stress_test_1m.mojo       1,000,000 seek stress test
    consistency_check.mojo    Cross-hardware determinism check

---

## Status

| Component | Status |
|---|---|
| mmap address space navigation | Complete and verified |
| Geometric coordinate engine | Implemented, cross-hardware consistency confirmed |
| Coordinate bridge | Complete — connects hash layer to mmap layer |
| Knowledge persistence | Saving and retrieving vectors via indexed offsets |
| RAG vs GDE benchmark (10K) | Complete — 345x improvement verified |
| RAG vs GDE benchmark (1M) | Complete — 19,491x improvement verified |
| Cross-hardware concurrent test | Complete — 4GB and 16GB verified simultaneously |
| 4GB RAG failure documented | Complete — OOM at 800K entries confirmed |
| 10M entry test | Pending |

---

## Built By

Tom Kimingi — Nairobi, Kenya
RRD Kenya 2026
https://github.com/tkimingi25-spec/Nairobi_Protocol-GDE-
DOI: https://doi.org/10.5281/zenodo.20036883
