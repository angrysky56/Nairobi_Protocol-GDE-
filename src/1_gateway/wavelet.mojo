from math import exp, sqrt


@align(32)
struct Wavelet8:
    var lanes: SIMD[DType.float32, 8]

    fn __init__(inout self):
        self.lanes = SIMD[DType.float32, 8](0.0)

    fn __init__(inout self, lanes: SIMD[DType.float32, 8]):
        self.lanes = lanes


fn hierarchical_wavelet(depths: SIMD[DType.float32, 8]) -> Wavelet8:
    var encoded = SIMD[DType.float32, 8](0.0)
    var energy = Float64(0.0)
    for i in range(8):
        encoded[i] = Float32(exp(-Float64(depths[i])))
        energy += Float64(encoded[i]) * Float64(encoded[i])
    if energy == 0.0:
        return Wavelet8(encoded)
    let scale = sqrt(energy)
    for i in range(8):
        encoded[i] = Float32(Float64(encoded[i]) / scale)
    return Wavelet8(encoded)

