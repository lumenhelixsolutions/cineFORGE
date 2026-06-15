#!/usr/bin/env python3
"""CineForge render pipeline LangGraph CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from runner import invoke_graph


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CineForge render pipeline graph")
    parser.add_argument("--profile", default="preview-chain")
    parser.add_argument("--project", required=True, help="CineForge project UUID")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--auto-approve", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = invoke_graph(
        args.profile,
        project_id=args.project,
        dry_run_mode=args.dry_run,
        auto_approve=args.auto_approve
        or os.environ.get("RENDER_GRAPH_AUTO_APPROVE", "").lower() in ("1", "true", "yes"),
    )
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    elif result.get("error"):
        print(f"Graph failed: {result['error']}")
    elif result.get("stitched"):
        print(f"Stitch complete for project {args.project}")
    elif args.dry_run:
        print(f"Dry-run OK for project {args.project}")
    else:
        print("Graph completed")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())