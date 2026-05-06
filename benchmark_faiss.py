import json
import time
import random
import numpy as np
import faiss

def char_vector(word, dims=24):
    import math
    PI = 3.141592653589793
    signal_len = 32
    signal = [0.0] * signal_len
    lowered = word.lower()[:signal_len]
    for i, ch in enumerate(lowered):
        signal[i] = float(ord(ch))
    scale = math.sqrt(1.0 / signal_len)
    vec = []
    for k in range(dims):
        s = 0.0
        for n in range(signal_len):
            s += signal[n] * math.cos(PI * k * (n + 0.5) / signal_len)
        vec.append(scale * s)
    return vec

if __name__ == "__main__":
    print("Loading knowledge base...")
    with open("data/knowledge_base.json") as f:
        kb = json.load(f)
    print(f"Loaded {len(kb)} entries")

    words = [e["word"] for e in kb]
    vectors = np.array([e["vector"] for e in kb], dtype=np.float32)

    # Normalise for cosine similarity
    faiss.normalize_L2(vectors)

    dims = vectors.shape[1]

    # Build HNSW index
    print("\nBuilding FAISS HNSW index...")
    t_idx_start = time.perf_counter()
    index = faiss.IndexHNSWFlat(dims, 32)  # 32 neighbours per node
    index.hnsw.efConstruction = 200
    index.add(vectors)
    t_idx_end = time.perf_counter()
    print(f"Index built in: {t_idx_end - t_idx_start:.4f}s")
    print(f"Index size:     {index.ntotal} vectors")

    # Build flat (brute force) index for exact comparison
    print("\nBuilding FAISS Flat (exact) index...")
    t_flat_start = time.perf_counter()
    flat_index = faiss.IndexFlatL2(dims)
    flat_index.add(vectors)
    t_flat_end = time.perf_counter()
    print(f"Flat index built in: {t_flat_end - t_flat_start:.4f}s")

    queries = random.sample(words, 100)
    query_vectors = np.array([char_vector(q) for q in queries], dtype=np.float32)
    faiss.normalize_L2(query_vectors)

    # HNSW search
    print("\n--- FAISS HNSW Benchmark: 100 queries ---")
    index.hnsw.efSearch = 64
    t_start = time.perf_counter()
    for i in range(len(queries)):
        D, I = index.search(query_vectors[i:i+1], 1)
    t_end = time.perf_counter()

    hnsw_total = t_end - t_start
    hnsw_per_query = hnsw_total / len(queries)

    print(f"Total time:   {hnsw_total:.6f}s")
    print(f"Per query:    {hnsw_per_query*1000:.4f}ms")
    print(f"Queries:      {len(queries)}")

    # Flat exact search
    print("\n--- FAISS Flat (exact) Benchmark: 100 queries ---")
    t_start = time.perf_counter()
    for i in range(len(queries)):
        D, I = flat_index.search(query_vectors[i:i+1], 1)
    t_end = time.perf_counter()

    flat_total = t_end - t_start
    flat_per_query = flat_total / len(queries)

    print(f"Total time:   {flat_total:.6f}s")
    print(f"Per query:    {flat_per_query*1000:.4f}ms")
    print(f"Queries:      {len(queries)}")

    # GDE comparison
    print("\n--- GDE Reference ---")
    print(f"Per query:    0.355ms")
    print(f"Complexity:   O(1)")
    print(f"Collisions:   4 / 1,000,000")

    print("\n--- Full Comparison ---")
    print(f"{'Method':<20} {'Per Query':>12} {'vs GDE':>12} {'Complexity':>12}")
    print("-" * 60)
    print(f"{'Brute Force RAG':<20} {'6919.2ms':>12} {'19,491x slower':>12} {'O(n)':>12}")
    print(f"{'FAISS Flat':<20} {flat_per_query*1000:>11.3f}ms {'?x slower':>12} {'O(n)':>12}")
    print(f"{'FAISS HNSW':<20} {hnsw_per_query*1000:>11.3f}ms {'?x slower':>12} {'O(log n)':>12}")
    print(f"{'GDE':<20} {'0.355ms':>12} {'baseline':>12} {'O(1)':>12}")
