from phonological import compare
from std.python import Python

def main() raises:
    # Use Python math to bypass the linker error
    var math = Python.import_module("math")
    var word_a = String("Quantum")
    var word_b = String("Symmetry")
    
    # Warm-up
    for i in range(100):
        _ = compare(word_a, word_b)
    
    # Measured Workload
    for i in range(10000):
        _ = compare(word_a, word_b)
