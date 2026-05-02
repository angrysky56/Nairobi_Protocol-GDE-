from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
from typing import Iterable

import networkx as nx


def depth_map(graph: nx.DiGraph) -> dict[str, int]:
    roots = [node for node, degree in graph.in_degree() if degree == 0]
    depths: dict[str, int] = {}
    queue = deque((root, 0) for root in roots)
    while queue:
        node, depth = queue.popleft()
        current = depths.get(node)
        if current is not None and current <= depth:
            continue
        depths[node] = depth
        for child in graph.successors(node):
            queue.append((child, depth + 1))
    return depths


@dataclass(slots=True)
class ContrastiveCoordinates:
    left_depth: float
    right_depth: float
    lca_depth: float
    contrast_penalty: float

    @property
    def logic_depth(self) -> float:
        return self.lca_depth

    @property
    def geometric_resonance(self) -> float:
        baseline = self.left_depth + self.right_depth + 1.0
        return 1.0 - (self.contrast_penalty / baseline)


def contrastive_lca_coordinates(
    graph: nx.DiGraph, left: str, right: str
) -> ContrastiveCoordinates:
    if not nx.is_directed_acyclic_graph(graph):
        raise ValueError("Contrastive LCA requires a DAG.")

    depths = depth_map(graph)
    lca = nx.lowest_common_ancestor(graph, left, right)
    lca_depth = float(depths.get(lca, 0))
    left_depth = float(depths[left])
    right_depth = float(depths[right])
    penalty = abs(left_depth - lca_depth) + abs(right_depth - lca_depth)
    penalty += 0.5 * abs(left_depth - right_depth)
    return ContrastiveCoordinates(
        left_depth=left_depth,
        right_depth=right_depth,
        lca_depth=lca_depth,
        contrast_penalty=penalty,
    )


def batch_contrastive_scores(
    graph: nx.DiGraph, pairs: Iterable[tuple[str, str]]
) -> list[ContrastiveCoordinates]:
    return [contrastive_lca_coordinates(graph, left, right) for left, right in pairs]


def euclidean(values: Iterable[float]) -> float:
    return math.sqrt(sum(value * value for value in values))

