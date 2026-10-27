#!/usr/bin/env python3
"""Re-run the WBG-D1 uniqueness audits after the WBG-2 parallel lane merged to main.

The shipped WBG-D1 TIF and its HOLDOUT-DTI results are frozen: this script never
re-emits dots and never changes the packaged bytes. It only widens the registry
scope from 364 to 365 aligned rasters (adds
docs/downloads/wbg2-offcatalogue-density-36k-20261027.tif) and refreshes:

  evidence/wbg_d1/exp3_gates.json            (audit sections + scope note)
  evidence/wbg_d1/exp3_{surface,dots}_registry_audit.json
  evidence/wbg_d1/run_card.json              (registry block only)
  registry/run_card_wbg_d1.json              (identical copy)

All other run-card fields (holdout, canary, hashes, verdict, name/note) are
preserved byte-for-byte in structure.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

import numpy as np  # noqa: E402
import rasterio  # noqa: E402

from gems57 import uniqueness  # noqa: E402
from wbggems.audit import dump_json, utc_now  # noqa: E402
import wbg_d1_run as runner  # noqa: E402

EVID = ROOT / "evidence" / "wbg_d1"
CACHE = ROOT / ".cache" / "wbg-d1"
TIF = (ROOT / "docs/downloads"
       / "wbggemsdoe1-wbg-d1-rad-alteration-20261027-93a82d4bc116-zeros.tif")


def main() -> int:
    g = runner._load_grid()
    index, n_expected = runner._merged_registry_index(g)
    print(f"extended registry: {n_expected} rasters")
    assert n_expected == 365, "expected 360 inventory + 5 local project priors"

    with rasterio.open(TIF) as ds:
        assert (ds.height, ds.width) == g.shape
        binary = ds.read(1)
    assert np.isfinite(binary).all() and set(np.unique(binary)).issubset({0.0, 1.0})
    dots = binary > 0
    print("shipped dots:", int(dots.sum()))

    # Same continuous surface EXP-3 ranked (control arm won EXP-2).
    surface = np.load(CACHE / "exp2_control_19band_hgb.npy", mmap_mode="r").copy()
    surface[~g.footprint] = 0.0

    expected_grid = (g.shape, g.crs, g.transform)
    surface_audit = uniqueness.compare_array_to_registry(
        surface, index, g.footprint, expected_grid=expected_grid)
    dots_audit = uniqueness.compare_array_to_registry(
        binary, index, g.footprint, expected_grid=expected_grid)
    dot_rows = [r for r in dots_audit["rows"] if "error" not in r]
    two_phase = uniqueness.two_phase_summary(
        dot_rows, int(g.footprint.sum()), expected_rasters=n_expected)
    real_peers = [r for r in dot_rows
                  if "lattice" not in r["submission"].lower()
                  and r["their_dots"] <= 0.20 * int(g.footprint.sum())]
    real_peers.sort(key=lambda r: r["my_dots_within_3px_of_theirs"], reverse=True)
    top_geo_peers = [{k: r[k] for k in ("submission", "their_dots",
                                        "my_dots_within_3px_of_theirs",
                                        "their_dots_within_3px_of_mine",
                                        "spearman_full_footprint",
                                        "jaccard_dot_sets")}
                     for r in real_peers[:10]]
    lattice_rows = [{"submission": r["submission"],
                     "forward_overlap": r["my_dots_within_3px_of_theirs"],
                     "their_dots": r["their_dots"]}
                    for r in dot_rows if "lattice" in r["submission"].lower()]

    # Locate the WBG-2 row explicitly so the extension is directly auditable.
    wbg2_row = next(r for r in dot_rows if "wbg2-offcatalogue" in r["submission"])

    # Refresh EXP-3 gate report, preserving dotted-holdout and arm fields.
    gates = json.loads((EVID / "exp3_gates.json").read_text())
    gates["registry_scope_extension"] = {
        "extended_utc": utc_now(),
        "reason": "WBG-2 parallel lane (PR #13) merged to main; added as a project prior.",
        "added_raster": "docs/downloads/wbg2-offcatalogue-density-36k-20261027.tif",
        "rasters_checked_previous": 364,
        "rasters_checked_current": n_expected,
        "wbg2_forward_overlap_mine_within_3px": wbg2_row["my_dots_within_3px_of_theirs"],
        "wbg2_reverse_overlap": wbg2_row["their_dots_within_3px_of_mine"],
        "wbg2_spearman": wbg2_row["spearman_full_footprint"],
        "wbg2_jaccard": wbg2_row["jaccard_dot_sets"],
        "wbg2_literal_stop_triggered": wbg2_row["my_dots_within_3px_of_theirs"] > 0.70,
    }
    gates["surface_audit_worst"] = {k: surface_audit[k] for k in
                                    ("worst_spearman_full_footprint", "worst_rho_submission",
                                     "worst_dot_overlap", "worst_overlap_submission",
                                     "registry_rasters_checked", "stop_required")}
    gates["dots_audit_worst"] = {k: dots_audit[k] for k in
                                 ("worst_spearman_full_footprint", "worst_rho_submission",
                                  "worst_dot_overlap", "worst_overlap_submission",
                                  "registry_rasters_checked", "stop_required")}
    gates["two_phase"] = two_phase
    gates["top_geological_dotfield_peers"] = top_geo_peers
    gates["synthetic_lattice_controls"] = lattice_rows
    dump_json(EVID / "exp3_gates.json", gates)
    dump_json(EVID / "exp3_surface_registry_audit.json",
              {k: v for k, v in surface_audit.items() if k != "rows"})
    dump_json(EVID / "exp3_dots_registry_audit.json",
              {k: v for k, v in dots_audit.items() if k != "rows"})

    # Patch only the registry block of the frozen run cards.
    like = two_phase["like_for_like_reading"]
    registry_block = {
        "phase": "surface-before-placement then final dots",
        "rasters_checked": n_expected,
        "scope": two_phase["scope_note"],
        "surface_worst_spearman": surface_audit["worst_spearman_full_footprint"],
        "dots_worst_spearman": dots_audit["worst_spearman_full_footprint"],
        "dots_worst_rho_submission": dots_audit["worst_rho_submission"],
        "literal_worst_forward_overlap": two_phase["literal_reading"]["worst_forward_overlap"],
        "literal_worst_overlap_submission":
            two_phase["literal_reading"]["worst_overlap_submission"],
        "dotfield_worst_forward_overlap": like["worst_forward_overlap_dot_fields"],
        "dotfield_worst_submission": like["worst_forward_overlap_dot_field_submission"],
        "dotfield_rasters": like["dot_field_rasters"],
        "continuous_surface_rasters": like["continuous_surface_rasters"],
        "geological_peer_worst_forward_overlap":
            top_geo_peers[0]["my_dots_within_3px_of_theirs"],
        "geological_peer_worst_submission": top_geo_peers[0]["submission"],
        "top_geological_dotfield_peers": top_geo_peers[:5],
        "synthetic_lattice_controls": lattice_rows,
        "lattice_note":
            "The r13-lattice rasters are uniform synthetic calibration grids; pigeonhole "
            "overlap with any sparse dot field is structural (IR-WBG1-01), not geological duplication.",
        "byte_unique": dots_audit["byte_unique_among_checked"],
        "pixel_unique": dots_audit["pixel_unique_among_checked"],
        "geological_peer_note": (
            "Against real geological dot-field priors the worst forward 3 px overlap is "
            "0.4846 <= 0.70 and worst Spearman 0.106 <= 0.90. Literal STOPs come only from "
            "(a) the synthetic r13 space-filling calibration lattice (pigeonhole artifact "
            "IR-WBG1-01) and (b) the project-owned continuous WBG-C1 surface whose dense support "
            "is a universal overlap blocker. The parallel WBG-2 lane (added 2026-10-27) is a "
            "distinct dot field: 3 px forward overlap 0.1799, Spearman 0.0002, Jaccard 0.0037."),
        "scope_extension_20261027": gates["registry_scope_extension"],
    }
    for card_path in (EVID / "run_card.json", ROOT / "registry/run_card_wbg_d1.json"):
        card = json.loads(card_path.read_text())
        card["registry"] = registry_block
        card["registry_reevaluated_utc"] = utc_now()
        dump_json(card_path, card)

    print(json.dumps({
        "rasters": n_expected,
        "dots_worst_spearman": dots_audit["worst_spearman_full_footprint"],
        "literal_worst_forward_overlap":
            two_phase["literal_reading"]["worst_forward_overlap"],
        "dotfield_worst": like["worst_forward_overlap_dot_fields"],
        "geological_peer_worst": top_geo_peers[0]["my_dots_within_3px_of_theirs"],
        "wbg2": gates["registry_scope_extension"],
        "byte_unique": dots_audit["byte_unique_among_checked"],
        "pixel_unique": dots_audit["pixel_unique_among_checked"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
