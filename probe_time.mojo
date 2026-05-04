from time import perf_counter_ns, now

def main() raises:
    print("--- Library Probe ---")

    var t1 = perf_counter_ns()
    print("Success: perf_counter_ns() -> ", t1)

    var t2 = now()
    print("Success: now() -> ", t2)

    print("RESULT: Time library probe complete.")
