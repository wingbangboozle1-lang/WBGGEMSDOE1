#!/usr/bin/env python3
"""Repository-level holdout entry point for frozen TIP1 and inherited MVGZ evidence.

TIP1 uses the shared ``gems.holdout.SegmentHoldout`` protocol recorded in its
immutable run card. A positional candidate preserves the already-merged MVGZ
compatibility evaluator; those numbers have a different evaluator version and
must never be compared as if they were the TIP1 protocol.

The exact upstream GEMSDOE24 CLI is retained as
``scripts/template_evaluate_holdout.py`` with its source hash.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def verify_tip1() -> dict:
    spec = importlib.util.spec_from_file_location("run_tip1_lane", ROOT / "scripts/run_tip1_lane.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load frozen TIP1 verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.verify_recorded()


def evaluate_mvgz_compat(candidate: Path, b_visible_px: float, name: str | None) -> dict:
    from gems1 import grid, holdout

    _, footprint, _ = grid.read_template()
    labels = grid.read_labels()
    context = holdout.build_context(footprint, labels)
    with rasterio.open(candidate) as dataset:
        array = dataset.read(1)
    mask = np.isfinite(array) & (array > 0) & footprint
    return holdout.evaluate_mask(
        mask,
        context,
        b_visible_px=b_visible_px,
        name=name or candidate.stem,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", nargs="?", type=Path)
    parser.add_argument("--verify-tip1", action="store_true")
    parser.add_argument("--b-visible-px", type=float, default=2.0)
    parser.add_argument("--name", default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    if args.verify_tip1:
        if args.candidate is not None:
            parser.error("candidate and --verify-tip1 are mutually exclusive")
        result = {"verified": True, "experiment_rerun": False, "run_card": verify_tip1()}
    elif args.candidate is not None:
        result = evaluate_mvgz_compat(args.candidate, args.b_visible_px, args.name)
    else:
        parser.error("supply --verify-tip1 or an inherited MVGZ-compatible candidate")
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    print(text, end="")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
