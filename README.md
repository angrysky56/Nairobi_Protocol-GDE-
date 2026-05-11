# Nairobi Protocol — Geometric Determinism Engine (GDE)

> **DOI:** https://doi.org/10.5281/zenodo.20036883
> **Author:** Tom Kimingi — RRD Kenya
> **License:** MIT

---

## What It Is

The GDE is a deterministic O(1) intermediary layer between a user, LLM, or agent and a knowledge store.

Given any input key, it computes the exact byte address of the corresponding knowledge chunk and retrieves it directly via mmap. No scanning. No approximation. No training. Constant time regardless of knowledge store size.

This is not a vector database. It does not search for similar vectors. It computes an exact deterministic address and goes directly there.

---

## The Problem It Solves

Standard retrieval systems scan or traverse index structures to find relevant knowledge. Time cost grows as the knowledge base grows. Hardware requirements grow with it.

The GDE eliminates the scan entirely. The address of any knowledge object is a mathematical invariant of its content. Compute it once. Jump directly. Read.

---

## Core Formula

    Offset = Σ(|vi| * wi) + Base Address

    where:
      vi = component i of the 24D geometric hash of the input key
      wi = (i+1) * 2654435761  (Knuth multiplicative constant)
      Slot alignment = (raw_offset // SLOT_SIZE) * SLOT_SIZE

The same key always produces the same offset on any hardware architecture.

---

## Architecture

    User / LLM / Agent
           |
           | input key
           v
    universal_geometric_hash()     24D HashVector     phonological.mojo
           |
           v
    coordinate_to_offset()         byte address       coordinate_bridge.mojo
           |
           v
    mmap seek + read               exact knowledge    knowledge_store.bin
           |
           v
    Knowledge chunk returned in O(1)

---

## Verified Results

All benchmarks run in Mojo on WSL2 Ubuntu, WSL native ext4 filesystem.

### Core Retrieval Pipeline — 1,000,000 queries

| Phase | Per Query | Queries/sec |
|---|---|---|
| Hash + offset + seek | 20.64us | 48,451 |
| Full retrieval (+ read 256 bytes) | 20.99us | 47,620 |
| Read overhead | 0.36us | — |

The read overhead is 0.36 microseconds. The sparse file strategy costs almost nothing at query time.

### Knowledge Store Verification

10 knowledge chunks written and read back at computed offsets across a 100GB sparse file.

    Verified: 10 | Failed: 0

Sample offsets:
| Key | Offset |
|---|---|
| neural network architecture | 89,551,741,440 |
| geometric determinism engine | 102,041,405,184 |
| nairobi kenya technology | 36,097,213,440 |
| mmap memory mapping | 85,601,186,816 |

### Cross-Hardware Determinism

Same key independently hashed on 4GB and 16GB machines:

| Key | 16GB offset | 4GB offset | Match |
|---|---|---|---|
| neural0 | 94,111,959,646 | 94,111,959,646 | Exact |
| quantum1 | 84,601,340,953 | 84,601,340,953 | Exact |

Deterministic to byte level across different hardware architectures.

### mmap Address Space

| Test | 16GB Machine | 4GB Machine |
|---|---|---|
| 100GB boundary jump | 1.805s | — |
| 1,000,000 seeks clean | 1.906s | 9.235s |
| Data integrity | A at byte 0, Z at byte 107,374,182,399 | Identical |

4GB machine is 4.4x slower due to limited page cache. Logic produces identical results.

### Collision Test

| Machine | Words tested | Collisions | Rate |
|---|---|---|---|
| 16GB | 10,000 | 0 | 0.0% |
| 4GB | 10,000 | 0 | 0.0% |

---

## Hardware Requirements

- OS: Linux (WSL2/Ubuntu tested)
- RAM: 4GB minimum
- Storage: ext4 recommended for sparse file support
- CPU: x86_64

---

## Running the System

Install:

    pixi project channel add https://conda.modular.com/max
    pixi install

Write knowledge to the store:

    truncate -s 100G knowledge_store.bin
    pixi run mojo -I src/1_gateway knowledge_store.mojo

Query the store:

    pixi run mojo -I src/1_gateway query_engine.mojo

Run 1M retrieval benchmark:

    pixi run mojo -I src/1_gateway benchmark_retrieval.mojo

mmap stress tests:

    truncate -s 100G stress_test_model.bin
    pixi run mojo stress_test_mmap.mojo
    pixi run mojo stress_test_1m.mojo

Collision verification:

    pixi run mojo -I src/1_gateway benchmark_collision_mojo.mojo

---

## Project Structure

    src/
      0_refinery/          Semantic and ontology processing layer
      1_gateway/           Hash function and coordinate engine
      2_execution/         mmap execution and offset resolution
    knowledge_store.mojo   Writes knowledge chunks to mmap file
    query_engine.mojo      Retrieves knowledge by key in O(1)
    benchmark_retrieval.mojo  1M query benchmark
    benchmark_collision_mojo.mojo  Collision verification
    stress_test_mmap.mojo  100GB boundary jump test
    stress_test_1m.mojo    1M seek stress test
    consistency_check.mojo Cross-hardware determinism check

---

## Status

| Component | Status |
|---|---|
| Hash function (phonological.mojo) | Complete |
| Offset formula (coordinate_bridge.mojo) | Complete |
| Knowledge store write | Complete — verified |
| Knowledge query | Complete — verified |
| 1M retrieval benchmark | Complete — 20.99us |
| Cross-hardware determinism | Complete — proven |
| Collision resistance | Complete — 0 collisions at 10K |
| Document ingestion | Pending |
| LLM integration | Pending |
| API layer | Pending |

---

## Built By

Tom Kimingi — Nairobi, Kenya
RRD Kenya 2026
https://github.com/tkimingi25-spec/Nairobi_Protocol-GDE-
DOI: https://doi.org/10.5281/zenodo.20036883
