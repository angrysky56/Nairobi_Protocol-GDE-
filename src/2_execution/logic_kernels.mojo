from math import sqrt

def masked_select(
    mask: SIMD[DType.bool, 8],
    on_true: SIMD[DType.float32, 8],
    on_false: SIMD[DType.float32, 8],
) -> SIMD[DType.float32, 8]:
    var merged = SIMD[DType.float32, 8](0.0)
    for i in range(8):
        merged[i] = on_true[i] if mask[i] else on_false[i]
    return merged

def branchless_distance(
    left: SIMD[DType.float32, 8], right: SIMD[DType.float32, 8]
) -> Float64:
    var acc = Float64(0.0)
    for i in range(8):
        var delta = Float64(left[i]) - Float64(right[i])
        acc += delta * delta
    return sqrt(acc)
