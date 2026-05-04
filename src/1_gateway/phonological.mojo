from math import sqrt, cos

alias SIGNAL_LEN = 32
alias HASH_DIM = 24
alias PI = 3.141592653589793

struct HashVector(Copyable, Movable):
    var data: SIMD[DType.float64, 24]

    def __init__(out self):
        self.data = SIMD[DType.float64, 24](0)

    def __copyinit__(out self, existing: Self):
        self.data = existing.data

    def __moveinit__(out self, owned existing: Self):
        self.data = existing.data

    def distance(self, other: HashVector) -> Float64:
        var diff = self.data - other.data
        return sqrt((diff * diff).reduce_add())

def universal_geometric_hash(text: String) -> HashVector:
    var hash_obj = HashVector()
    var lowered = text.lower()
    var signal = SIMD[DType.float64, 32](0)
    var length = lowered.byte_length()
    if length > SIGNAL_LEN:
        length = SIGNAL_LEN
    for i in range(length):
        var char_val = lowered.as_bytes()[i]
        signal[i] = Float64(char_val)
    var scale0 = sqrt(1.0 / Float64(SIGNAL_LEN))
    for k in range(HASH_DIM):
        var sum_val = 0.0
        for n in range(SIGNAL_LEN):
            sum_val += signal[n] * cos(PI * Float64(k) * (Float64(n) + 0.5) / Float64(SIGNAL_LEN))
        hash_obj.data[k] = scale0 * sum_val
    return hash_obj

def compare(left: String, right: String) -> Float64:
    var h1 = universal_geometric_hash(left)
    var h2 = universal_geometric_hash(right)
    return h1.distance(h2)
