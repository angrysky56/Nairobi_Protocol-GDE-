from phonological import compare

def main():
    var word_a = String("Quantum")
    var word_b = String("Symmetry")
    
    # Calculate distance
    var dist = compare(word_a, word_b)
    
    print("--- Geometric Engine Verification ---")
    print("Comparing: 'Quantum' vs 'Symmetry'")
    print("Distance Result:", dist)
    
    # The "Gold Standard" from your Desktop
    var desktop_baseline = 64.19382644539132
    
    if dist == desktop_baseline:
        print("STATUS: VERIFIED (Exact Match)")
    else:
        print("STATUS: VARIANCE DETECTED")
        print("Difference:", dist - desktop_baseline)
