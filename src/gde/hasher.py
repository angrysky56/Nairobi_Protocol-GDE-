"""DCT-II geometric hash and coordinate-to-offset mapping.

This module implements the core Nairobi Protocol formula:

1. Convert text → 32-element signal (byte values of lowered UTF-8)
2. Apply a Type-II Discrete Cosine Transform to produce a 24D vector
3. L2-normalize the vector for consistent magnitude
4. Map the vector to a byte offset via weighted accumulation + modular reduction

The hash is fully deterministic: same input → same vector → same offset,
regardless of hardware, OS, or runtime.

References
----------
- DCT-II: https://en.wikipedia.org/wiki/Discrete_cosine_transform#DCT-II
- Knuth multiplicative hash constant: 2654435761 (2^32 × φ⁻¹, rounded)
"""

from __future__ import annotations

import math
from typing import Sequence

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SIGNAL_LEN: int = 32
"""Number of signal samples extracted from the input text."""

HASH_DIM: int = 24
"""Dimensionality of the output hash vector."""

_PI: float = math.pi
_SQRT_INV_N: float = math.sqrt(1.0 / SIGNAL_LEN)
_SQRT_2_INV_N: float = math.sqrt(2.0 / SIGNAL_LEN)

KNUTH_CONSTANT: int = 2_654_435_761
"""Knuth multiplicative hash constant (2^32 × φ⁻¹, rounded)."""

DEFAULT_ADDRESS_SPACE: int = 100 * 1024 * 1024 * 1024  # 100 GB
"""Default address space size in bytes."""

DEFAULT_SLOT_SIZE: int = 4096
"""Default slot alignment size in bytes (4 KB for document chunks)."""


# ---------------------------------------------------------------------------
# Hash function
# ---------------------------------------------------------------------------


def _build_signal(text: str) -> list[float]:
    """Convert text to a fixed-length signal of byte values.

    Parameters
    ----------
    text:
        The input text to convert.

    Returns
    -------
    list[float]
        A list of ``SIGNAL_LEN`` float values derived from the UTF-8
        encoding of the lowered input.
    """
    lowered = text.lower().encode("utf-8")[:SIGNAL_LEN]
    signal = [0.0] * SIGNAL_LEN
    for i, byte_val in enumerate(lowered):
        signal[i] = float(byte_val)
    return signal


def _dct_ii(signal: Sequence[float]) -> list[float]:
    """Apply a Type-II DCT to produce a ``HASH_DIM``-dimensional vector.

    Uses proper DCT-II scaling:
    - k=0: scale = sqrt(1/N)
    - k>0: scale = sqrt(2/N)

    Parameters
    ----------
    signal:
        Input signal of length ``SIGNAL_LEN``.

    Returns
    -------
    list[float]
        DCT coefficients of length ``HASH_DIM``.
    """
    out: list[float] = []
    for k in range(HASH_DIM):
        acc = 0.0
        for n in range(SIGNAL_LEN):
            angle = _PI * k * (n + 0.5) / SIGNAL_LEN
            acc += signal[n] * math.cos(angle)
        scale = _SQRT_INV_N if k == 0 else _SQRT_2_INV_N
        out.append(acc * scale)
    return out


def _l2_normalize(vector: list[float]) -> list[float]:
    """L2-normalize a vector. Returns zero vector if norm is zero.

    Parameters
    ----------
    vector:
        Input vector.

    Returns
    -------
    list[float]
        Unit-length vector, or zero vector if input has zero norm.
    """
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0.0:
        return vector
    return [v / norm for v in vector]


def universal_geometric_hash(text: str) -> list[float]:
    """Compute a 24D deterministic geometric hash of the input text.

    Pipeline: text → lowercase → UTF-8 bytes → signal → DCT-II → L2 normalize

    Parameters
    ----------
    text:
        The input key (any string).

    Returns
    -------
    list[float]
        A 24-dimensional unit vector (L2-normalized DCT-II coefficients).

    Examples
    --------
    >>> v = universal_geometric_hash("Neural")
    >>> len(v)
    24
    >>> abs(sum(x*x for x in v) - 1.0) < 1e-10  # unit vector
    True
    """
    signal = _build_signal(text)
    raw = _dct_ii(signal)
    return _l2_normalize(raw)


def distance(left: str, right: str) -> float:
    """Euclidean distance between the hash vectors of two strings.

    Parameters
    ----------
    left:
        First input key.
    right:
        Second input key.

    Returns
    -------
    float
        Euclidean distance in 24D space. Ranges from 0.0 (identical)
        to 2.0 (maximally different, since vectors are unit-length).

    Examples
    --------
    >>> distance("Apple", "Apples") < distance("Apple", "Orbit")
    True
    """
    lv = universal_geometric_hash(left)
    rv = universal_geometric_hash(right)
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(lv, rv, strict=True)))


# ---------------------------------------------------------------------------
# Coordinate-to-offset mapping
# ---------------------------------------------------------------------------


def coordinate_to_offset(
    vector: Sequence[float],
    address_space: int = DEFAULT_ADDRESS_SPACE,
    slot_size: int = DEFAULT_SLOT_SIZE,
) -> int:
    """Map a hash vector to a deterministic byte offset.

    Implements the Nairobi Protocol formula:

        raw = Σ(|v_i| × w_i)   where w_i = (i+1) × 2654435761
        offset = (raw mod address_space) aligned to slot_size

    Parameters
    ----------
    vector:
        A hash vector (typically 24D, from :func:`universal_geometric_hash`).
    address_space:
        Total size of the address space in bytes (default: 100 GB).
    slot_size:
        Slot alignment size in bytes (default: 4096).

    Returns
    -------
    int
        A deterministic, slot-aligned byte offset within ``[0, address_space)``.

    Examples
    --------
    >>> v = universal_geometric_hash("neural network architecture")
    >>> offset = coordinate_to_offset(v)
    >>> offset % 4096 == 0  # slot-aligned
    True
    """
    if address_space <= 0:
        raise ValueError(f"address_space must be positive, got {address_space}")
    if slot_size <= 0:
        raise ValueError(f"slot_size must be positive, got {slot_size}")

    weighted_sum = 0.0
    for i, v in enumerate(vector):
        weight = (i + 1) * KNUTH_CONSTANT
        weighted_sum += abs(v) * weight
    raw = int(weighted_sum % address_space)
    return (raw // slot_size) * slot_size


def key_to_offset(
    key: str,
    address_space: int = DEFAULT_ADDRESS_SPACE,
    slot_size: int = DEFAULT_SLOT_SIZE,
) -> int:
    """Convenience: hash a key and return its byte offset in one step.

    Parameters
    ----------
    key:
        The input key (any string).
    address_space:
        Total size of the address space in bytes.
    slot_size:
        Slot alignment size in bytes.

    Returns
    -------
    int
        A deterministic, slot-aligned byte offset.
    """
    return coordinate_to_offset(
        universal_geometric_hash(key),
        address_space=address_space,
        slot_size=slot_size,
    )
