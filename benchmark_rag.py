import json
import math
import time
import random

def cosine_similarity(vec_a, vec_b):
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)

def char_vector(word, dims=24):
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

def rag_search(query_vec, knowledge_base):
    """Scan entire knowledge base — O(n) probabilistic search."""
    best_score = -1.0
    best_word = ""
    for entry in knowledge_base:
        score = cosine_similarity(query_vec, entry["vector"])
        if score > best_score:
            best_score = score
            best_word = entry["word"]
    return best_word, best_score

if __name__ == "__main__":
    print("Loading knowledge base...")
    with open("data/knowledge_base.json") as f:
        kb = json.load(f)
    print(f"Loaded {len(kb)} entries")

    # Pick 100 random queries
    queries = random.sample([e["word"] for e in kb], 100)

    print("\n--- RAG Benchmark: 100 queries x O(n) scan ---")
    print(f"Knowledge base size: {len(kb)} entries")
    print("Running...")

    t_start = time.perf_counter()
    results = []
    for query in queries:
        q_vec = char_vector(query)
        match, score = rag_search(q_vec, kb)
        results.append((query, match, score))
    t_end = time.perf_counter()

    elapsed = t_end - t_start
    per_query = elapsed / len(queries)

    print(f"\nTotal time:      {elapsed:.4f}s")
    print(f"Queries run:     {len(queries)}")
    print(f"Per query:       {per_query*1000:.4f}ms")
    print(f"Scans per query: {len(kb)}")
    print(f"Total scans:     {len(kb) * len(queries):,}")

    print("\nSample results:")
    for query, match, score in results[:5]:
        print(f"  Query: {query:20s} -> Match: {match:20s} (score: {score:.4f})")
