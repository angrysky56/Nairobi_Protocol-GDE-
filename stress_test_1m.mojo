def main() raises:
    var file_path = "stress_test_model.bin"
    var size = UInt64(100) * 1024 * 1024 * 1024
    var num_jumps = 1_000_000

    print("--- GDE 1,000,000 JUMP STRESS TEST ---")
    print("Address Space: 100GB")
    print("Jumps: 1,000,000")
    print("-----------------------------------")

    with open(file_path, "rw") as f:

        # Write only two anchor points - no loop writes
        _ = f.seek(UInt64(0))
        f.write("A")
        _ = f.seek(UInt64(size - 1))
        f.write("Z")

        # 1,000,000 pure seeks - no writes, no disk allocation
        print("Phase 1: Seeking 1,000,000 deterministic addresses...")
        for i in range(num_jumps):
            var offset = UInt64(i) * UInt64(size) // UInt64(num_jumps)
            _ = f.seek(offset)

        # Verify anchors survived
        print("Phase 2: Verifying anchor points...")
        _ = f.seek(UInt64(0))
        print("Data at 0GB:   ", f.read(1))
        _ = f.seek(UInt64(size - 1))
        print("Data at 100GB: ", f.read(1))

    print("RESULT: 1,000,000 seeks across 100GB complete.")
