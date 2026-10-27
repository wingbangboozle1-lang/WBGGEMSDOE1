#!/usr/bin/env python3
"""Execute 9-site executive audit, 0.2778 0-XOR mathematical proof, and 118-raster LLI calibration."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wbggems1.forensics import audit_all_9_focus_sites, prove_02778_and_private_inventory  # noqa: E402
from wbggems1.lli_calibrator import fit_lli_calibrator  # noqa: E402


def main() -> None:
    t0 = time.time()
    cal, lli_report = fit_lli_calibrator()
    proof = prove_02778_and_private_inventory()
    focus9 = audit_all_9_focus_sites(cal)

    ev_dir = ROOT / "evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)
    (ev_dir / "lli_calibration_118.json").write_text(json.dumps(lli_report, indent=2) + "\n")
    (ev_dir / "forensic_proof_02778.json").write_text(json.dumps(proof, indent=2) + "\n")
    (ev_dir / "focus9_executive_audit.json").write_text(json.dumps(focus9, indent=2) + "\n")

    print("=== LLI 118-RASTER CALIBRATION ===")
    print(json.dumps(lli_report, indent=2))
    print("\n=== 0.2778 ZERO-XOR PROOF & PRIVATE INVENTORY INVERSION ===")
    print(json.dumps(proof, indent=2))
    print("\n=== 9-SITE EXECUTIVE SUMMARY TABLE ===")
    for row in focus9:
        u = row["uniqueness_vs_all_gemsdoe"]
        print(
            f"{row['site']:9s} | dots={row['positive_dots']:6d} | NaNs={row['nan_cells']:7d} | "
            f"portal={str(row['portal_10_gate_pass']):5s} | holdout={row['latest_holdout_dti_numeric']:.5f} | "
            f"LLI={row['lli_empirical_projection']['projected_value']:.4f} | "
            f"ov3px={u['max_3px_dot_overlap']*100:5.1f}% ({u['closest_overlap_peer'][:28]}) | "
            f"safe={row['safe_to_submit']}"
        )
    print(f"\nCompleted in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
