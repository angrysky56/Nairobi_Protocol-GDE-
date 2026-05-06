from phonological import universal_geometric_hash, compare
from time import perf_counter_ns

comptime NUM_PAIRS = 100000

def main() raises:
    print("--- GDE Mojo Semantic Distance at Scale ---")
    print("Computing", NUM_PAIRS, "pairwise distances")
    print("-------------------------------------------")

    var word_a = List[String]()
    var word_b = List[String]()

    var set_a = List[String]()
    set_a.append("neural"); set_a.append("quantum"); set_a.append("logic")
    set_a.append("orbit"); set_a.append("signal"); set_a.append("genome")
    set_a.append("algebra"); set_a.append("syntax"); set_a.append("market")
    set_a.append("nairobi")

    var set_b = List[String]()
    set_b.append("synapse"); set_b.append("photon"); set_b.append("reason")
    set_b.append("planet"); set_b.append("sensor"); set_b.append("protein")
    set_b.append("calculus"); set_b.append("grammar"); set_b.append("capital")
    set_b.append("kenya")

    var na = len(set_a)
    var nb = len(set_b)

    # Warmup
    for i in range(100):
        _ = compare(set_a[i % na], set_b[i % nb])

    print("Warmup complete. Running", NUM_PAIRS, "comparisons...")

    var t_start = perf_counter_ns()

    var total_distance = Float64(0.0)
    for i in range(NUM_PAIRS):
        var dist = compare(set_a[i % na], set_b[i % nb])
        total_distance += dist

    var t_end = perf_counter_ns()

    var elapsed_ns = t_end - t_start
    var elapsed_ms = Float64(elapsed_ns) / 1_000_000.0
    var per_op_us = elapsed_ms * 1000.0 / Float64(NUM_PAIRS)
    var ops_per_sec = Float64(NUM_PAIRS) / (elapsed_ms / 1000.0)

    print("")
    print("RESULTS:")
    print("Total comparisons:    ", NUM_PAIRS)
    print("Total time:           ", elapsed_ms, "ms")
    print("Per comparison:       ", per_op_us, "us")
    print("Comparisons per sec:  ", ops_per_sec)
    print("Avg distance:         ", total_distance / Float64(NUM_PAIRS))
    print("")
    print("Sample distances:")
    for i in range(5):
        var d = compare(set_a[i], set_b[i])
        print(" ", set_a[i], "vs", set_b[i], "->", d)
    print("")
    print("RESULT: Semantic distance scale test complete.")
