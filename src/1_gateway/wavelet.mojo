from math import exp, sqrt

struct Wavelet8:
    var lanes: SIMD[DType.float32, 8]

    def __init__(out self):
        self.lanes = SIMD[DType.float32, 8](0.0)

    def __init__(out self, lanes: SIMD[DType.float32, 8]):
        self.lanes = lanes

def hierarchical_wavelet(depths: SIMD[DType.float32, 8]) -> Wavelet8:
    var encoded = SIMD[DType.float32, 8](0.0)
    var energy = Float64(0.0)
    for i in range(8):
        encoded[i] = Float32(exp(-Float64(depths[i])))
        energy += Float64(encoded[i]) * Float64(encoded[i])
    if energy == 0.0:
        return Wavelet8(encoded)
    var scale = sqrt(energy)
    for i in range(8):
        encoded[i] = Float32(Float64(encoded[i]) / scale)
    return Wavelet8(encoded)
