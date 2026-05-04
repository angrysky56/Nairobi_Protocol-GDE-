from python import Python
from phonological import compare
from time import perf_counter_ns

def main() raises:
    var word_a = String("Quantum")
    var word_b = String("Symmetry")

    # Warm-up
    print("Warming up...")
    for i in range(100):
        _ = compare(word_a, word_b)

    # Timed workload
    print("Running 10,000 comparisons...")
    var t_start = perf_counter_ns()
    for i in range(10000):
        _ = compare(word_a, word_b)
    var t_end = perf_counter_ns()

    var elapsed_ms = (t_end - t_start) / 1_000_000
    var per_op_us = (t_end - t_start) / 10_000 / 1_000

    print("--- GDE Phonological Performance ---")
    print("Operations:       10,000")
    print("Total time (ms):  ", elapsed_ms)
    print("Per op (us):      ", per_op_us)
    print("RESULT: Phonological engine benchmark complete.")
