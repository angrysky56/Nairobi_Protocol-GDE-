"""Tests for gde.hasher — DCT-II hash and offset computation."""

from __future__ import annotations

import math

from gde.hasher import (
    DEFAULT_ADDRESS_SPACE,
    DEFAULT_SLOT_SIZE,
    HASH_DIM,
    coordinate_to_offset,
    distance,
    key_to_offset,
    universal_geometric_hash,
)


class TestUniversalGeometricHash:
    """Tests for the hash function."""

    def test_output_length(self) -> None:
        """Hash always produces a 24D vector."""
        v = universal_geometric_hash("Neural")
        assert len(v) == HASH_DIM

    def test_unit_vector(self) -> None:
        """Hash output is L2-normalized (unit vector)."""
        v = universal_geometric_hash("Neural")
        norm = math.sqrt(sum(x * x for x in v))
        assert abs(norm - 1.0) < 1e-10

    def test_deterministic(self) -> None:
        """Same input always produces the same vector."""
        v1 = universal_geometric_hash("Quantum computing")
        v2 = universal_geometric_hash("Quantum computing")
        assert v1 == v2

    def test_case_insensitive(self) -> None:
        """Hash is case-insensitive (lowered internally)."""
        v1 = universal_geometric_hash("Neural")
        v2 = universal_geometric_hash("neural")
        assert v1 == v2

    def test_different_inputs_differ(self) -> None:
        """Different inputs produce different vectors."""
        v1 = universal_geometric_hash("Apple")
        v2 = universal_geometric_hash("Orbit")
        assert v1 != v2

    def test_empty_string(self) -> None:
        """Empty string produces a valid vector (all zeros → zero norm edge case)."""
        v = universal_geometric_hash("")
        assert len(v) == HASH_DIM

    def test_long_string_truncated(self) -> None:
        """Strings longer than 32 bytes are truncated to 32."""
        short = "a" * 32
        long_ = "a" * 100
        v1 = universal_geometric_hash(short)
        v2 = universal_geometric_hash(long_)
        assert v1 == v2


class TestDistance:
    """Tests for the distance function."""

    def test_identical_strings_zero_distance(self) -> None:
        """Identical strings have zero distance."""
        assert distance("Apple", "Apple") == 0.0

    def test_similar_strings_closer(self) -> None:
        """Similar strings are closer than dissimilar ones."""
        assert distance("Apple", "Apples") < distance("Apple", "Orbit")

    def test_symmetry(self) -> None:
        """Distance is symmetric."""
        d1 = distance("Neural", "Logic")
        d2 = distance("Logic", "Neural")
        assert abs(d1 - d2) < 1e-15

    def test_max_distance_bounded(self) -> None:
        """Distance between unit vectors is at most 2.0."""
        d = distance("aaa", "zzz")
        assert d <= 2.0 + 1e-10


class TestCoordinateToOffset:
    """Tests for the offset computation."""

    def test_deterministic(self) -> None:
        """Same vector always maps to the same offset."""
        v = universal_geometric_hash("neural network architecture")
        o1 = coordinate_to_offset(v)
        o2 = coordinate_to_offset(v)
        assert o1 == o2

    def test_slot_aligned(self) -> None:
        """Offset is always aligned to slot_size."""
        v = universal_geometric_hash("Quantum")
        offset = coordinate_to_offset(v)
        assert offset % DEFAULT_SLOT_SIZE == 0

    def test_within_address_space(self) -> None:
        """Offset is always within [0, address_space)."""
        for word in ["Neural", "Logic", "Quantum", "Apple", "Orbit"]:
            v = universal_geometric_hash(word)
            offset = coordinate_to_offset(v)
            assert 0 <= offset < DEFAULT_ADDRESS_SPACE

    def test_custom_slot_size(self) -> None:
        """Custom slot size is respected."""
        v = universal_geometric_hash("test")
        offset = coordinate_to_offset(v, slot_size=256)
        assert offset % 256 == 0

    def test_invalid_address_space(self) -> None:
        """Negative address space raises ValueError."""
        v = universal_geometric_hash("test")
        try:
            coordinate_to_offset(v, address_space=-1)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


class TestKeyToOffset:
    """Tests for the convenience key_to_offset function."""

    def test_matches_two_step(self) -> None:
        """key_to_offset matches hash → offset two-step."""
        key = "neural network architecture"
        v = universal_geometric_hash(key)
        expected = coordinate_to_offset(v)
        assert key_to_offset(key) == expected
