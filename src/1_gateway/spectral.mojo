from math import sqrt

struct Spectral8:
    var lanes: SIMD[DType.float32, 8]

    def __init__(out self):
        self.lanes = SIMD[DType.float32, 8](0.0)

    def __init__(out self, lanes: SIMD[DType.float32, 8]):
        self.lanes = lanes

def laplacian_signature(degrees: SIMD[DType.float32, 8]) -> Spectral8:
    var normalized = SIMD[DType.float32, 8](0.0)
    var energy = Float64(0.0)
    for i in range(8):
        var value = max(Float64(degrees[i]), 0.0)
        normalized[i] = Float32(sqrt(value + 1.0))
        energy += Float64(normalized[i]) * Float64(normalized[i])
    if energy == 0.0:
        return Spectral8()
    var scale = sqrt(energy)
    for i in range(8):
        normalized[i] = Float32(Float64(normalized[i]) / scale)
    return Spectral8(normalized)
