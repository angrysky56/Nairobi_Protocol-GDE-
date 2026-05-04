from phonological import compare

def main() raises:
    var word_a = String("Quantum")
    var word_b = String("Symmetry")

    var dist = compare(word_a, word_b)

    print("--- GDE Cross-Hardware Consistency Check ---")
    print("Comparing: Quantum vs Symmetry")
    print("Distance Result: ", dist)

    # Tolerance-based check instead of exact float match
    var desktop_baseline = Float64(64.19382644539132)
    var tolerance = Float64(0.0001)
    var diff = dist - desktop_baseline
    if diff < 0:
        diff = -diff

    if diff < tolerance:
        print("STATUS: VERIFIED — within tolerance")
    else:
        print("STATUS: VARIANCE DETECTED")
        print("Difference: ", diff)
        print("Tolerance:  ", tolerance)
