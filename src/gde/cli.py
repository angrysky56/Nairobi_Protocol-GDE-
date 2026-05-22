"""GDE command-line interface.

Usage
-----
::

    # Store a value
    gde store "neural network architecture" "Neural networks are..."

    # Retrieve a value
    gde retrieve "neural network architecture"

    # Ingest a document
    gde ingest docs/paper.md

    # Search keys
    gde search "neural"

    # List all keys
    gde list

    # Delete a key
    gde delete "neural network architecture"

    # Show statistics
    gde stats

    # Start MCP server
    gde serve

Security notes
--------------
- File paths are resolved before use.
- No user input is passed to shell commands or SQL without parameterization.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from gde.ingest import ingest_file
from gde.store import CollisionError, GDEStore

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULT_STORE_DIR = os.environ.get(
    "GDE_STORE_DIR",
    str(Path.home() / ".gde" / "default_store"),
)


def _get_store(args: argparse.Namespace) -> GDEStore:
    """Create a GDEStore from CLI arguments."""
    store_dir = getattr(args, "store_dir", _DEFAULT_STORE_DIR) or _DEFAULT_STORE_DIR
    return GDEStore(store_dir=store_dir)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def _cmd_store(args: argparse.Namespace) -> None:
    """Store a key-value pair."""
    meta = {}
    if args.metadata:
        try:
            meta = json.loads(args.metadata)
        except json.JSONDecodeError:
            print("Warning: invalid metadata JSON, ignoring.", file=sys.stderr)

    with _get_store(args) as store:
        try:
            entry = store.store(args.key, args.content, metadata=meta)
        except CollisionError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

    print(f"Stored: {entry.key}")
    print(f"  Offset:       {entry.offset}")
    print(f"  Content hash: {entry.content_hash}")


def _cmd_retrieve(args: argparse.Namespace) -> None:
    """Retrieve content by key."""
    with _get_store(args) as store:
        content = store.retrieve(args.key)

    if content is None:
        print(f"Key not found: {args.key!r}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps({"key": args.key, "content": content}, indent=2))
    else:
        print(content)


def _cmd_ingest(args: argparse.Namespace) -> None:
    """Ingest a document file."""
    resolved = Path(args.file_path).resolve()

    with _get_store(args) as store:
        try:
            keys = ingest_file(resolved, store)
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

    print(f"Ingested: {resolved.name}")
    print(f"  Chunks: {len(keys)}")
    for key in keys:
        print(f"  - {key}")


def _cmd_search(args: argparse.Namespace) -> None:
    """Search stored keys."""
    with _get_store(args) as store:
        entries = store.search(args.query, limit=args.limit)

    if not entries:
        print("No matching keys found.")
        return

    print(f"Found {len(entries)} match(es):")
    for entry in entries:
        print(f"  {entry.key}")
        if args.verbose:
            print(f"    Offset:     {entry.offset}")
            print(f"    Created:    {entry.created_at}")
            if entry.metadata:
                print(f"    Metadata:   {json.dumps(entry.metadata)}")


def _cmd_list(args: argparse.Namespace) -> None:
    """List stored keys."""
    with _get_store(args) as store:
        entries = store.list_keys(
            prefix=args.prefix if args.prefix else None,
            limit=args.limit,
        )

    if not entries:
        print("No keys found.")
        return

    print(f"Keys ({len(entries)}):")
    for entry in entries:
        print(f"  {entry.key}")
        if args.verbose:
            print(f"    Offset:     {entry.offset}")
            print(f"    Created:    {entry.created_at}")


def _cmd_delete(args: argparse.Namespace) -> None:
    """Delete a key."""
    with _get_store(args) as store:
        deleted = store.delete(args.key)

    if deleted:
        print(f"Deleted: {args.key}")
    else:
        print(f"Key not found: {args.key!r}", file=sys.stderr)
        sys.exit(1)


def _cmd_stats(args: argparse.Namespace) -> None:
    """Show store statistics."""
    with _get_store(args) as store:
        info = store.stats()

    print("GDE Store Statistics")
    print(f"  Entries:       {info['entry_count']}")
    print(f"  Slot size:     {info['slot_size']} bytes")
    print(f"  Virtual size:  {info['virtual_size_bytes'] / (1024**3):.1f} GB")
    print(f"  Disk usage:    {info['actual_disk_bytes'] / 1024:.1f} KB")
    print(f"  Store path:    {info['store_path']}")
    print(f"  Manifest DB:   {info['manifest']['db_path']}")


def _cmd_serve(args: argparse.Namespace) -> None:
    """Start the MCP server."""
    # Set the store dir env var so the MCP server picks it up.
    store_dir = getattr(args, "store_dir", _DEFAULT_STORE_DIR) or _DEFAULT_STORE_DIR
    os.environ["GDE_STORE_DIR"] = store_dir

    from gde.mcp_server import main as mcp_main

    mcp_main()


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="gde",
        description="Geometric Determinism Engine — deterministic O(1) knowledge store",
    )
    parser.add_argument(
        "--store-dir",
        default=_DEFAULT_STORE_DIR,
        help=f"Path to the GDE store directory (default: {_DEFAULT_STORE_DIR})",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- store ---
    p_store = subparsers.add_parser("store", help="Store a key-value pair")
    p_store.add_argument("key", help="The storage key")
    p_store.add_argument("content", help="The content to store")
    p_store.add_argument("--metadata", help="JSON metadata string")
    p_store.set_defaults(func=_cmd_store)

    # --- retrieve ---
    p_retrieve = subparsers.add_parser("retrieve", help="Retrieve content by key")
    p_retrieve.add_argument("key", help="The key to look up")
    p_retrieve.add_argument("--json", action="store_true", help="Output as JSON")
    p_retrieve.set_defaults(func=_cmd_retrieve)

    # --- ingest ---
    p_ingest = subparsers.add_parser("ingest", help="Ingest a document file")
    p_ingest.add_argument("file_path", help="Path to the file to ingest")
    p_ingest.set_defaults(func=_cmd_ingest)

    # --- search ---
    p_search = subparsers.add_parser("search", help="Search stored keys")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")
    p_search.set_defaults(func=_cmd_search)

    # --- list ---
    p_list = subparsers.add_parser("list", help="List stored keys")
    p_list.add_argument("--prefix", default="", help="Filter by key prefix")
    p_list.add_argument("--limit", type=int, default=100, help="Max results (default: 100)")
    p_list.set_defaults(func=_cmd_list)

    # --- delete ---
    p_delete = subparsers.add_parser("delete", help="Delete a key")
    p_delete.add_argument("key", help="The key to delete")
    p_delete.set_defaults(func=_cmd_delete)

    # --- stats ---
    p_stats = subparsers.add_parser("stats", help="Show store statistics")
    p_stats.set_defaults(func=_cmd_stats)

    # --- serve ---
    p_serve = subparsers.add_parser("serve", help="Start the MCP server")
    p_serve.set_defaults(func=_cmd_serve)

    return parser


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    args.func(args)


if __name__ == "__main__":
    main()
