import math
import time
import random

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

def coordinate_to_offset(vector, address_space=100*1024*1024*1024):
    """
    Nairobi Protocol: Offset = sum(vi * wi) + Base Address
    Dimensional weights spread components across full address space.
    """
    dims = len(vector)
    weighted_sum = 0.0
    for i, v in enumerate(vector):
        # Each dimension gets a unique prime-based weight
        weight = (i + 1) * 2654435761  # Knuth multiplicative hash constant
        weighted_sum += abs(v) * weight
    return int(weighted_sum % address_space)

if __name__ == "__main__":
    print("Loading word list...")
    with open("data/word_list.txt") as f:
        words = [w.strip() for w in f.readlines()]

    print("Building GDE index with distributed offsets...")
    t_idx_start = time.perf_counter()
    index = {}
    collisions = 0
    for word in words:
        vec = char_vector(word)
        offset = coordinate_to_offset(vec)
        if offset in index:
            collisions += 1
        index[offset] = (word, offset)
    t_idx_end = time.perf_counter()

    queries = random.sample(words, 100)

    t_start = time.perf_counter()
    results = []
    for query in queries:
        vec = char_vector(query)
        offset = coordinate_to_offset(vec)
        match = index.get(offset, ("not_found", -1))
        results.append((query, offset))
    t_end = time.perf_counter()

    elapsed = t_end - t_start
    per_query = elapsed / len(queries)

    print(f"Index built in:  {t_idx_end - t_idx_start:.4f}s")
    print(f"Collisions:      {collisions} / {len(words)}")
    print(f"Total time:      {elapsed:.6f}s")
    print(f"Per query:       {per_query*1000:.6f}ms")

    print("\nSample offsets (should span billions):")
    for query, offset in results[:8]:
        print(f"  {query:25s} -> {offset:,}")
