from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import statistics
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
REFINERY_DIR = ROOT / "src" / "0_refinery"


def load_module(name: str, path: Path):
    spec = spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ontology_parser = load_module(
    "geometric_core_ontology_parser", REFINERY_DIR / "ontology_parser.py"
)
contrast_lca = load_module(
    "geometric_core_contrast_lca", REFINERY_DIR / "contrast_lca.py"
)
seed_reference = load_module(
    "geometric_core_seed_reference", ROOT / "tests" / "phonological_seed_reference.py"
)


def benchmark_seed(rounds: int = 5_000) -> tuple[dict[str, float], float]:
    comparisons = [
        ("Apple", "Apples"),
        ("Apple", "Orbit"),
        ("Neural", "Logic"),
    ]
    distances = {
        f"{left}_{right}": seed_reference.distance(left, right)
        for left, right in comparisons
    }
    start = time.perf_counter()
    for _ in range(rounds):
        for left, right in comparisons:
            seed_reference.distance(left, right)
    elapsed = time.perf_counter() - start
    return distances, elapsed


def benchmark_refinery() -> dict[str, float]:
    db_path = ROOT / "data" / "global_ontology.db"
    if db_path.exists():
        db_path.unlink()

    start = time.perf_counter()
    graph = ontology_parser.build_demo_graph(db_path)
    ingest_seconds = time.perf_counter() - start

    sample_pairs = [("apple", "apple_inc"), ("neural", "logic"), ("apple", "orbit")]
    coords = contrast_lca.batch_contrastive_scores(graph, sample_pairs)

    return {
        "ingest_seconds": ingest_seconds,
        "logic_depth": statistics.mean(coord.logic_depth for coord in coords),
        "geometric_resonance": statistics.mean(
            coord.geometric_resonance for coord in coords
        ),
    }


def main() -> None:
    seed_distances, seed_elapsed = benchmark_seed()
    refinery = benchmark_refinery()
    apple_apples = seed_distances["Apple_Apples"]
    apple_orbit = seed_distances["Apple_Orbit"]

    summary = {
        "seed": {
            **seed_distances,
            "success": apple_apples < apple_orbit,
            "resonance_ratio": apple_orbit / apple_apples if apple_apples else None,
            "elapsed_seconds_for_5000_rounds": seed_elapsed,
        },
        "refinery": refinery,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

