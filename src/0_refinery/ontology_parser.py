from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3
from typing import Iterable

import networkx as nx


NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


def normalize_label(label: str) -> str:
    collapsed = NORMALIZE_RE.sub("_", label.strip().lower()).strip("_")
    return collapsed or "empty"


@dataclass(slots=True)
class OntologyNode:
    label: str
    node_id: int


class OntologyParser:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def ensure_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ontology_nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ontology_edges (
                    parent_id INTEGER NOT NULL,
                    child_id INTEGER NOT NULL,
                    UNIQUE(parent_id, child_id)
                )
                """
            )
            conn.commit()

    def _get_or_create_node(self, conn: sqlite3.Connection, label: str) -> OntologyNode:
        normalized = normalize_label(label)
        conn.execute(
            "INSERT OR IGNORE INTO ontology_nodes(label) VALUES (?)",
            (normalized,),
        )
        row = conn.execute(
            "SELECT id, label FROM ontology_nodes WHERE label = ?",
            (normalized,),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"Failed to materialize ontology node for {label!r}")
        return OntologyNode(label=row[1], node_id=row[0])

    def get_or_create_node(self, label: str) -> OntologyNode:
        self.ensure_schema()
        with sqlite3.connect(self.db_path) as conn:
            node = self._get_or_create_node(conn, label)
            conn.commit()
        return node

    def ingest_edges(self, edges: Iterable[tuple[str, str]]) -> nx.DiGraph:
        self.ensure_schema()
        graph = nx.DiGraph()
        with sqlite3.connect(self.db_path) as conn:
            for parent, child in edges:
                parent_node = self._get_or_create_node(conn, parent)
                child_node = self._get_or_create_node(conn, child)
                graph.add_edge(parent_node.label, child_node.label)
                conn.execute(
                    """
                    INSERT OR IGNORE INTO ontology_edges(parent_id, child_id)
                    VALUES (?, ?)
                    """,
                    (parent_node.node_id, child_node.node_id),
                )
            conn.commit()
        return graph


def build_demo_graph(db_path: Path) -> nx.DiGraph:
    parser = OntologyParser(db_path)
    return parser.ingest_edges(
        [
            ("root", "science"),
            ("root", "commerce"),
            ("science", "neural"),
            ("science", "logic"),
            ("commerce", "apple_inc"),
            ("commerce", "orchard"),
            ("orchard", "apple"),
            ("science", "orbit"),
        ]
    )
