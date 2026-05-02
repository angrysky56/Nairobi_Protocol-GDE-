from math import sqrt


@align(32)
struct Spectral8:
    var lanes: SIMD[DType.float32, 8]

    fn __init__(inout self):
        self.lanes = SIMD[DType.float32, 8](0.0)


fn laplacian_signature(degrees: SIMD[DType.float32, 8]) -> Spectral8:
    var normalized = SIMD[DType.float32, 8](0.0)
    var energy = Float64(0.0)
    for i in range(8):
        let value = max(Float64(degrees[i]), 0.0)
        normalized[i] = Float32(sqrt(value + 1.0))
        energy += Float64(normalized[i]) * Float64(normalized[i])
    if energy == 0.0:
        return Spectral8()
    let scale = sqrt(energy)
    for i in range(8):
        normalized[i] = Float32(Float64(normalized[i]) / scale)
    return Spectral8(normalized)

