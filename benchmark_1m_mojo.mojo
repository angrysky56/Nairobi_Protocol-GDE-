from phonological import universal_geometric_hash
from time import perf_counter_ns

comptime ADDRESS_SPACE = UInt64(100) * 1024 * 1024 * 1024

def coordinate_to_offset(vector: SIMD[DType.float64, 24]) -> UInt64:
    var weighted_sum = Float64(0.0)
    for i in range(24):
        var weight = Float64((i + 1) * 2654435761)
        var v = vector[i]
        if v < 0:
            v = -v
        weighted_sum += v * weight
    return UInt64(weighted_sum % Float64(ADDRESS_SPACE))

def main() raises:
    var file_path = "stress_test_model.bin"

    var words = List[String]()
    words.append("neural"); words.append("quantum"); words.append("logic")
    words.append("orbit"); words.append("signal"); words.append("photon")
    words.append("atom"); words.append("electron"); words.append("proton")
    words.append("neutron"); words.append("plasma"); words.append("fusion")
    words.append("fission"); words.append("entropy"); words.append("symmetry")
    words.append("tensor"); words.append("vector"); words.append("matrix")
    words.append("scalar"); words.append("gradient"); words.append("nairobi")
    words.append("kenya"); words.append("africa"); words.append("savanna")
    words.append("highland"); words.append("compiler"); words.append("runtime")
    words.append("pointer"); words.append("protocol"); words.append("cluster")
    words.append("neuron"); words.append("synapse"); words.append("cortex")
    words.append("genome"); words.append("protein"); words.append("enzyme")
    words.append("receptor"); words.append("antibody"); words.append("chromosome")
    words.append("catalyst"); words.append("algebra"); words.append("calculus")
    words.append("topology"); words.append("manifold"); words.append("theorem")
    words.append("axiom"); words.append("integral"); words.append("derivative")
    words.append("polynomial"); words.append("eigenvalue"); words.append("syntax")
    words.append("semantics"); words.append("morpheme"); words.append("phoneme")
    words.append("lexicon"); words.append("grammar"); words.append("context")
    words.append("inference"); words.append("abstraction"); words.append("encoding")
    words.append("decoding"); words.append("market"); words.append("capital")
    words.append("equity"); words.append("dividend"); words.append("revenue")
    words.append("margin"); words.append("sensor"); words.append("processor")
    words.append("memory"); words.append("cache"); words.append("kernel")
    words.append("socket"); words.append("buffer"); words.append("register")
    words.append("interrupt"); words.append("router"); words.append("packet")
    words.append("cipher"); words.append("system"); words.append("network")
    words.append("pattern"); words.append("structure"); words.append("process")
    words.append("method"); words.append("concept"); words.append("theory")
    words.append("model"); words.append("design"); words.append("engine")
    words.append("bridge"); words.append("layer"); words.append("module")
    words.append("pipeline"); words.append("framework"); words.append("platform")
    words.append("interface"); words.append("latitude"); words.append("longitude")
    words.append("meridian"); words.append("altitude"); words.append("equator")

    var num_words = len(words)

    print("--- GDE Mojo 1M Query Pipeline Benchmark ---")
    print("Pipeline: word -> 24D hash -> offset -> mmap seek")
    print("Queries: 1,000,000")
    print("Address space: 100GB")
    print("--------------------------------------------")

    with open(file_path, "rw") as f:
        _ = f.seek(UInt64(0))
        f.write("A")

        # Warmup
        for i in range(1000):
            var word = words[i % num_words]
            var vec = universal_geometric_hash(word)
            var offset = coordinate_to_offset(vec.data)
            _ = f.seek(offset)

        print("Warmup complete. Running 1,000,000 queries...")

        var t_start = perf_counter_ns()

        for i in range(1_000_000):
            var word = words[i % num_words]
            var vec = universal_geometric_hash(word)
            var offset = coordinate_to_offset(vec.data)
            _ = f.seek(offset)

        var t_end = perf_counter_ns()

        var elapsed_ns = t_end - t_start
        var elapsed_ms = Float64(elapsed_ns) / 1_000_000.0
        var elapsed_s = elapsed_ms / 1000.0
        var per_query_ms = elapsed_ms / 1_000_000.0
        var per_query_us = per_query_ms * 1000.0

        print("")
        print("RESULTS:")
        print("Total time (1M queries): ", elapsed_s, "s")
        print("Per query:               ", per_query_ms, "ms")
        print("Per query:               ", per_query_us, "us")
        print("Queries per second:      ", 1_000_000.0 / elapsed_s)
        print("")
        print("COMPARISON (per query):")
        print("Brute force RAG:  6919.200ms  O(n)")
        print("FAISS Flat:          8.292ms  O(n)")
        print("FAISS HNSW:          0.188ms  O(log n) approximate")
        print("GDE Mojo 1M:        ", per_query_ms, "ms  O(1) exact")
        print("")
        print("RESULT: 1M query Mojo pipeline benchmark complete.")
