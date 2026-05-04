from phonological import HashVector, universal_geometric_hash, compare

comptime DIMENSIONS = 24

struct CoordinateBridge:
    var base_address: UInt64
    var address_space: UInt64
    var weights: SIMD[DType.float64, 24]

    def __init__(out self, base_address: UInt64, address_space: UInt64):
        self.base_address = base_address
        self.address_space = address_space
        # Default dimensional weights - uniform distribution
        self.weights = SIMD[DType.float64, 24](1.0)

    def set_weights(mut self, weights: SIMD[DType.float64, 24]):
        self.weights = weights

    def coordinate_to_offset(self, vector: HashVector) -> UInt64:
        # Core Nairobi Protocol formula:
        # Offset = Σ(vi * wi) + Base Address
        var weighted_sum = Float64(0.0)
        for i in range(DIMENSIONS):
            weighted_sum += vector.data[i] * self.weights[i]

        # Normalize to address space using absolute value
        if weighted_sum < 0:
            weighted_sum = -weighted_sum

        # Map into valid address range
        var normalized = weighted_sum % Float64(self.address_space)
        return self.base_address + UInt64(normalized)

    def word_to_offset(self, word: String) -> UInt64:
        var vector = universal_geometric_hash(word)
        return self.coordinate_to_offset(vector)

    def words_are_close(self, word_a: String, word_b: String, threshold: Float64) -> Bool:
        var dist = compare(word_a, word_b)
        return dist < threshold


def main() raises:
    var address_space = UInt64(100) * 1024 * 1024 * 1024
    var bridge = CoordinateBridge(
        base_address=UInt64(0),
        address_space=address_space
    )

    print("--- GDE Coordinate Bridge ---")
    print("Address Space: 100GB")
    print("")

    # Test 1: Word to offset mapping
    var words = List[String]()
    words.append("Neural")
    words.append("Logic")
    words.append("Quantum")
    words.append("Apple")
    words.append("Orbit")

    print("Word -> Deterministic Offset:")
    for i in range(len(words)):
        var word = words[i]
        var offset = bridge.word_to_offset(word)
        print(" ", word, "->", offset, "bytes")

    print("")

    # Test 2: Same word always maps to same offset
    print("Determinism Check (same word, 3 calls):")
    for i in range(3):
        var offset = bridge.word_to_offset("Quantum")
        print("  Quantum ->", offset)

    print("")

    # Test 3: Semantic proximity check
    print("Semantic Proximity Check:")
    var pairs = List[Tuple[String, String]]()
    pairs.append(("Neural", "Logic"))
    pairs.append(("Apple", "Orbit"))
    pairs.append(("Sensor", "Sensors"))

    for i in range(len(pairs)):
        var a = pairs[i][0]
        var b = pairs[i][1]
        var close = bridge.words_are_close(a, b, Float64(60.0))
        print(" ", a, "~", b, "->", close)

    print("")
    print("RESULT: Coordinate Bridge operational.")
