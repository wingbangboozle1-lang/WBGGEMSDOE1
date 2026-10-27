#!/usr/bin/env python3
"""Build WBG-S2 (`MKSF-1 / EXP-3`) 2026-10-27 9-Site Executive Summary, 0.2778 Forensic Report,
publication figures, and GitHub Pages UI (`docs/wbg-s2-mksf1/`).
"""
from __future__ import annotations

import hashlib
import html
import json
import math
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

import numpy as np
import rasterio
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import binary_dilation, gaussian_filter

from wbggems.audit import dump_json


def _build_nine_site_audit(
    rc: dict[str, Any], uq: dict[str, Any], exp: dict[str, Any], canary: dict[str, Any], b6: dict[str, Any]
) -> dict[str, Any]:
    peer_map = {r["site"]: r for r in uq["post_placement"]["latest_20261027_peers_table"]}

    def _ov(site_key: str) -> dict[str, Any]:
        r = peer_map[site_key]
        return {
            "peer_sha256": r["sha256"],
            "peer_positive_pixels": r["positive_pixels"],
            "wbg_s2_in_peer_3px": round(r["forward_3px_overlap"], 6),
            "peer_in_wbg_s2_3px": round(r["reverse_3px_overlap"], 6),
            "symmetric_3px_overlap": round(r["symmetric_3px_overlap"], 6),
            "worst_directional_3px_overlap": round(r["worst_directional_3px"], 6),
            "spearman_rho": round(r["spearman_rho"], 6),
            "passes_this_peer_diagnostic_only": bool(
                r["worst_directional_3px"] <= 0.70 and abs(r["spearman_rho"]) <= 0.90
            ),
        }

    focus_sites = [
        {
            "site": "WBGGEMSDOE1 (This Repo · WBG-S2 EXP-3)",
            "repo_url": "https://github.com/wingbangboozle1-lang/WBGGEMSDOE1",
            "pinned_head_20261027": "arena/7dce52ff-wbggemsdoe1 (merged with main d5949b5)",
            "file_to_download": rc["artifact"]["tif_path"],
            "zip_to_download": rc["artifact"]["zip_path"],
            "tif_sha256": rc["artifact"]["tif_sha256"],
            "emitted_dots": 37654,
            "holdout_score_labeled": (
                "HOLDOUT-DTI 0.183594 (95% CI [0.170313, 0.196956], gems-segment-pooled-v1, n=60,988) | "
                "HOLDOUT-DTI 0.147773 (95% CI [0.128077, 0.167791], gems57-pooled-hide-v2, n=11,330)"
            ),
            "live_score_labeled": "NONE (0 competition slots spent; never inferred or projected from holdout)",
            "uniqueness_across_sites": (
                "Final forward overlap 99.5538% with r13-lattice-s5 and 100% with WBG-C1; both exceed 70% — STOP. "
                "The sparse subset and sampled Spearman screening are diagnostic only, not full pre-placement clearance."
            ),
            "portal_format_status": "LOCAL FORMAT PASS (not proof of portal acceptance)",
            "go_no_go_status": "RESEARCH DOWNLOAD ONLY · DO NOT SUBMIT · NO SELECTOR ELIGIBILITY",
            "notes": "Parallel-reported holdouts; the selected arm was chosen using these splits and has not been independently replayed here.",
        },
        {
            "site": "GEMSDOE24",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE24",
            "pinned_head_20261027": "2521cb671989fc5b2c20f88926d86e335f63cf45",
            "file_to_download": "docs/downloads/gems24-s3dep1-negative-10m-monoclinal-20261026-464fa34b4091-zeros.tif (latest) / gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif (prior)",
            "tif_sha256": peer_map["GEMSDOE24_S3DEP1"]["sha256"],
            "emitted_dots": 37654,
            "holdout_score_labeled": (
                "HOLDOUT-DTI 0.166060 (95% CI [0.151839, 0.179725], gems-segment-pooled-v1, n=60,988; S3DEP1) | "
                "HOLDOUT-DTI 0.163792 (DPRF1)"
            ),
            "live_score_labeled": (
                "Historical H24-0 mirror: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.2477 (100% H19-5 clone). "
                "Oct 26 gvc1: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.0859."
            ),
            "uniqueness_vs_wbg_s2": _ov("GEMSDOE24_S3DEP1"),
            "uniqueness_across_sites": "S3DEP1 & DPRF1 are distinct (<70% peer overlap), but S3DEP1 self-marked NEGATIVE (Δ +0.0023 CI includes 0 vs DPRF1).",
            "portal_format_status": "PASS ([0, 1], 0 NaN)",
            "go_no_go_status": "NO-GO (Trails WBG-S2 0.183594 by -0.017534 on identical SegmentHoldout)",
        },
        {
            "site": "GEMSDOE25",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE25",
            "pinned_head_20261027": "5a60fb47506a6c94366b7938c149cc4544888d17",
            "file_to_download": "docs/downloads/gems25-h74-rmps-subsurf-catfree-b2-37654-20261026-3751606e1ce5-zeros.tif",
            "tif_sha256": peer_map["GEMSDOE25_H74_SUBSURF"]["sha256"],
            "emitted_dots": 37654,
            "holdout_score_labeled": "HOLDOUT-DTI 0.039060 (95% CI [0.02561, 0.05635], subsurface-only H74) | H73-PM: HOLDOUT-DTI 0.0954",
            "live_score_labeled": (
                "Historical D2.8: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.2600 (100% identical dot set to GEMSDOE30). "
                "Oct 26 h66: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.0742."
            ),
            "uniqueness_vs_wbg_s2": _ov("GEMSDOE25_H74_SUBSURF"),
            "uniqueness_across_sites": "H74 is distinct (39.62% fwd overlap vs WBG-S2), but historical D2.8 is 100.0% pixel-identical to GEMSDOE30.",
            "portal_format_status": "PASS ([0, 1], 0 NaN)",
            "go_no_go_status": "NO-GO (Self-marked NEGATIVE; pure 2-km geophysical resolution cannot localize 100 m fault crests)",
        },
        {
            "site": "GEMSDOE27",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE27",
            "pinned_head_20261027": "69d6f0339b83d46d796f8d3808764be05f688080",
            "file_to_download": "docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif",
            "tif_sha256": peer_map["GEMSDOE27_H31_1_DRCG_WL"]["sha256"],
            "emitted_dots": 37654,
            "holdout_score_labeled": "HOLDOUT-DTI 0.143678 (95% CI [0.130198, 0.157302], 24-block holdout, n=76,120)",
            "live_score_labeled": (
                "Oct 26 H31-1: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.2250 (highest Oct 26 live ML/hybrid submission). "
                "Historical H27-5: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.2449."
            ),
            "uniqueness_vs_wbg_s2": _ov("GEMSDOE27_H31_1_DRCG_WL"),
            "uniqueness_across_sites": "Distinct from WBG-S2 (61.88% fwd / 59.42% sym <= 70%); already submitted in prior cycle.",
            "portal_format_status": "PASS ([0, 1], 0 NaN)",
            "go_no_go_status": "NO-GO FOR RE-UPLOAD (Already submitted; re-uploading duplicates an existing submission)",
        },
        {
            "site": "GEMSDOE28",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE28",
            "pinned_head_20261027": "67dbdf4df6b09cb1064415660394053d296be94a",
            "file_to_download": "NONE generated in S22 (stopped on pre-placement surface Spearman 0.9036); prior S21: gems28-s21-puhgb-20261026-16bbf281ba9b-allfinite.tif",
            "tif_sha256": peer_map["GEMSDOE28_S21_PUHGB"]["sha256"],
            "emitted_dots": 37654,
            "holdout_score_labeled": "S22: HOLDOUT-DTI 0.095452 (surface stopped, no dots) | S21: HOLDOUT-DTI 0.1038",
            "live_score_labeled": (
                "Historical H24-2-q990: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.2710 (95.4% H19-5 family overlap). "
                "Oct 26 S21 PU-HGB: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.0206."
            ),
            "uniqueness_vs_wbg_s2": _ov("GEMSDOE28_S21_PUHGB"),
            "uniqueness_across_sites": "S22 triggered surface Spearman STOP (0.9036 > 0.90); S21 overlapped GEMSDOE31 by 91.59%.",
            "portal_format_status": "S22: NO FILE; S21: PASS format",
            "go_no_go_status": "NO-GO (No S22 artifact; S21 scored 0.0206 user-reported and failed peer uniqueness)",
        },
        {
            "site": "GEMSDOE30",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE30",
            "pinned_head_20261027": "3c3d7255eb078f8457dc3946411c1ca6387ec4af",
            "file_to_download": "docs/downloads/gems30-CSR1-44090-20261026-502fb5948335-zeros.tif",
            "tif_sha256": peer_map["GEMSDOE30_CSR1"]["sha256"],
            "emitted_dots": 44090,
            "holdout_score_labeled": "HOLDOUT-DTI 0.158160 (95% CI [0.14502, 0.17142], gems-segment-pooled-v1, n=60,988)",
            "live_score_labeled": (
                "Historical D2.8: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.2600 (100% clone of GEMSDOE25). "
                "Oct 26 MSDB1: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.1462."
            ),
            "uniqueness_vs_wbg_s2": _ov("GEMSDOE30_CSR1"),
            "uniqueness_across_sites": "CSR1 fixed prior 7.11M exterior-NaN bug (`-zeros.tif`), distinct vs WBG-S2 (50.85% fwd overlap), but places 6,436 excess dots vs 37,654 collar-free optimum.",
            "portal_format_status": "PASS on CSR1 (`-zeros.tif`); prior `-nan.tif` FAILED [0,1] check (7,111,787 NaNs)",
            "go_no_go_status": "NO-GO (Trails WBG-S2 0.183594 by -0.025434 on identical SegmentHoldout)",
        },
        {
            "site": "GEMSDOE31",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE31",
            "pinned_head_20261027": "fbebc0179bb0c188055e12759ebaf3c68b2ef639",
            "file_to_download": "docs/downloads/gemsdoe31-h31x-piedmont-junction-37654-20261026-5a956da9-zeros.tif",
            "tif_sha256": peer_map["GEMSDOE31_H31X_JUNCTION"]["sha256"],
            "emitted_dots": 37654,
            "holdout_score_labeled": "HOLDOUT-DTI 0.166100 (95% CI [0.1465, 0.1859], 8-block spatial CV, n=76,120)",
            "live_score_labeled": (
                "Historical union-b-p060: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.2708 (93.2% H19-5 family overlap). "
                "Oct 26 H31-A: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.0882."
            ),
            "uniqueness_vs_wbg_s2": _ov("GEMSDOE31_H31X_JUNCTION"),
            "uniqueness_across_sites": "Distinct vs WBG-S2 (46.91% fwd / 51.60% rev <= 70%); self-marked HOLD vs historical 0.2708.",
            "portal_format_status": "PASS ([0, 1], 0 NaN)",
            "go_no_go_status": "NO-GO (Self-marked HOLD / lower holdout precision than WBG-S2)",
        },
        {
            "site": "GEMSDOE32",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE32",
            "pinned_head_20261027": "1398109a56e4099b63f74d335c3e1cf76821c074",
            "file_to_download": "docs/downloads/gemsdoe32-h47-ldgi-dualhorizon-corridor-37654-20261026T230609Z-0eb8a25c-zeros.tif (latest) / h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif (historical 0.2778)",
            "tif_sha256": peer_map["GEMSDOE32_H47_LDGI"]["sha256"],
            "emitted_dots": 37654,
            "holdout_score_labeled": "H47-1-LDGI: HOLDOUT-DTI 0.119765 (95% CI [0.100357, 0.140466], gems57-pooled-hide-v2, n=11,330)",
            "live_score_labeled": (
                "Historical H33-2-B2 (`e5eb6e7e`): USER-REPORTED / PEER-REPO-CLAIMED 0.2778 (NOT ORGANIZER-CONFIRMED by this repo; "
                "recorded in peer file `GEMSDOE32/registry/submissions/sub-20261004T234342Z-h33-b2.json`). "
                "Oct 26 H38-G1: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.1456."
            ),
            "uniqueness_vs_wbg_s2": _ov("GEMSDOE32_H47_LDGI"),
            "uniqueness_vs_wbg_s2_historical_b2": _ov("GEMSDOE32_H33_B2_HIST"),
            "uniqueness_across_sites": "H47-1-LDGI is distinct vs WBG-S2 (37.74% fwd) and historical B2 is distinct vs WBG-S2 (49.26% fwd); B2 itself is spent & 100%-subset of H19-5/D2.8.",
            "portal_format_status": "H47-1-LDGI & B2 `-zeros`: PASS ([0, 1], 0 NaN); H38-G1 `-nan.tif`: failed the parallel local all-finite policy (portal cause unverified)",
            "go_no_go_status": "NO-GO (B2 is spent; H47-1-LDGI self-stopped at 0.119765 vs WBG-S2's 0.147773 on identical gems57-pooled-hide-v2)",
        },
        {
            "site": "GEMSDOE33",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE33",
            "pinned_head_20261027": "122e2240ad4e0be1124f275c3ccedfb043bf8a85",
            "file_to_download": "docs/downloads/gemsdoe33-s33-seisdil-strain-seismicity-37654-20261026-3463540a7e02-zeros.tif",
            "tif_sha256": peer_map["GEMSDOE33_S33_SEISDIL"]["sha256"],
            "emitted_dots": 37654,
            "holdout_score_labeled": "S33-SEISDIL: HOLDOUT-DTI 0.044577 (block CV) | G33-COHERENCE: HOLDOUT-DTI 0.025120 (7,949 dots)",
            "live_score_labeled": (
                "Historical H24-1-d2.6: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.2632 (97.5% H19-5 overlap). "
                "Oct 26 s33-seisdil: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.0963."
            ),
            "uniqueness_vs_wbg_s2": _ov("GEMSDOE33_S33_SEISDIL"),
            "uniqueness_across_sites": "Distinct vs WBG-S2 (33.80% fwd overlap), but coarse geodetic strain/seismicity severely under-localizes 100 m fault traces.",
            "portal_format_status": "PASS ([0, 1], 0 NaN)",
            "go_no_go_status": "NO-GO (Self-marked NEGATIVE; 0.0446 holdout / 0.0963 user-reported)",
        },
        {
            "site": "GEMSDOE36",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE36",
            "pinned_head_20261027": "757694238d0dcdf3c5840560a912a988b81a7ec1",
            "file_to_download": "docs/downloads/gemsdoe36-kpl36-exp3-20261026-fc869911e88c-zeros.tif",
            "tif_sha256": peer_map["GEMSDOE36_KPL36_EXP3"]["sha256"],
            "emitted_dots": 37654,
            "holdout_score_labeled": "HOLDOUT-DTI 0.170100 (95% CI [0.15660, 0.18440], gems-segment-pooled-v1, n=60,988)",
            "live_score_labeled": (
                "Historical H36-4: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.2750 (86.7% H33-B2 overlap). "
                "Oct 26 KPL-36 EXP-3: USER-REPORTED / NOT ORGANIZER-CONFIRMED 0.1647."
            ),
            "uniqueness_vs_wbg_s2": _ov("GEMSDOE36_KPL36_EXP3"),
            "uniqueness_across_sites": "Distinct vs WBG-S2 (36.49% fwd / 68.75% rev <= 70%, |rho|=0.0445); strong PU-HGB + CELF peer, already tested live at 0.1647 user-reported.",
            "portal_format_status": "PASS ([0, 1], 0 NaN)",
            "go_no_go_status": "NO-GO FOR RE-UPLOAD (Already submitted; trails WBG-S2 0.183594 by -0.013494 on identical SegmentHoldout)",
        },
        {
            "site": "KANLERGEMSDOE2 (External Peer Benchmark)",
            "repo_url": "https://github.com/kanlerxz87-cyber/KANLERGEMSDOE2",
            "pinned_head_20261027": "4edc3346c394c54638f8635e3265870f010668cc",
            "file_to_download": "docs/downloads/kanlergemsdoe2-kg2-mghv-exp-1-37654-20261026-f5a469e94b14-zeros.tif",
            "tif_sha256": peer_map["KANLERGEMSDOE2_KG2_MGHV"]["sha256"],
            "emitted_dots": 37654,
            "holdout_score_labeled": "HOLDOUT-DTI 0.177056 (95% CI [0.163689, 0.190497], gems-segment-pooled-v1, n=60,988)",
            "live_score_labeled": "NONE reported",
            "uniqueness_vs_wbg_s2": _ov("KANLERGEMSDOE2_KG2_MGHV"),
            "uniqueness_across_sites": "Distinct vs WBG-S2 (57.08% fwd / 50.29% rev <= 70%, |rho|=0.0338); previous fleet holdout leader before WBG-S2 (0.183594).",
            "portal_format_status": "PASS ([0, 1], 0 NaN)",
            "go_no_go_status": "SUPERSEDED ON HOLDOUT BY WBG-S2 (+0.006538 on identical SegmentHoldout)",
        },
    ]

    irregularities = [
        {
            "id": "IR-S2-001",
            "severity": "HIGH",
            "title": "Band 6 (`tc`) in `training_features.tif` is GeoDAWN Radiometric Total Count, NOT Terrain-Corrected Gravity",
            "evidence": (
                f"Direct pixel correlation across {b6['valid_overlap_pixels']:,} valid footprint cells yields "
                f"Spearman rho = {b6['spearman_rho']:.5f} between `training_features.tif` Band 6 (`tc`) and "
                "`geodawn_rad_u8.tif` Band 4 (`TC`). Prior repositories treating Band 6 as Bouguer terrain-corrected "
                "gravity mixed gamma-ray radiometrics into subsurface density operators."
            ),
            "resolution": "WBG-S2 treats Band 6 strictly as radiometric TC and builds all gravity operators from Band 13 (`iso_grav_anom`), Band 11 (`iso_grav_anom_vg`), and Band 18 (`iso_grav_anom_hg`).",
        },
        {
            "id": "IR-S2-002",
            "severity": "CRITICAL",
            "title": "DrivenData `[0, 1]` Portal Rejection of Outside-Footprint `NaN` Submissions",
            "evidence": (
                "`sample_submission.tif` contains 7,111,787 outside-footprint `NaN` cells (`12,279,160 - 5,167,373`), "
                "yet DrivenData's portal validator checks `0 <= x <= 1` across the entire 3730x3292 array and rejects "
                "`-nan.tif` uploads with `'Predicted values must be in range [0, 1]'` (observed on GEMSDOE30 & GEMSDOE32 H38-G1)."
            ),
            "resolution": "WBG-S2 writes `0.0` outside footprint (`nodata=None`), verified across all 12,279,160 pixels (`n_nan=0`, `n_inf=0`, `min=0.0`, `max=1.0`).",
        },
        {
            "id": "IR-S2-003",
            "severity": "HIGH",
            "title": "24.63% USGS 3DEP 1 m LiDAR Coverage Gap & Tree Feature-Starvation Trap",
            "evidence": (
                "`lidar_scarp_features_u8.tif` covers 3,894,769 / 5,167,373 footprint pixels (75.37%), leaving 1,272,604 "
                "basin/range pixels (`24.63%`, heavily concentrated in NE fold) without 1 m LiDAR. Single-tree models "
                "trained on 1 m + 10 m features simultaneously allocate top splits to 1 m scarps and starve seamless 10 m features."
            ),
            "resolution": "WBG-S2 trains a dedicated unstarved `Seamless-68ch` specialist (100% 10 m 3DEP + geophysics) alongside `Full-81ch` and aligns gap quantiles on held-in OOB data, surging `NE_LidarGapHeavy` holdout DTI to `0.25915` (vs `0.17974` in WBG-H1).",
        },
        {
            "id": "IR-S2-004",
            "severity": "CRITICAL",
            "title": "99.95% Target Leakage in `derived_gdr_qfaults_v2_100m_u8.tif` & GDR `dist_known_fault_px`",
            "evidence": "`derived_gdr_qfaults_v2_100m_u8.tif` overlaps `labels.tif` at 99.95%, and GDR CSV `dist_known_fault_px` columns encode full-catalogue distances.",
            "resolution": "Hard-banned in `src/wbggems2/features.py`; verified by 332/332 single-feature orientation-invariant & missingness leakage canaries (`max AUC = 0.79251 <= 0.90`).",
        },
        {
            "id": "IR-S2-005",
            "severity": "HIGH",
            "title": "Near-Flank Negative Purge Trap (`WBG-H1` 900 m Purge Caused 300–800 m Apron Halo)",
            "evidence": (
                "Purging `0 < d_vis < 9 px` during training removes all near-fault alluvial-fan pixels from negatives, "
                "causing tree ensembles to emit 700 m halos whose precision collapses under the official `beta=0.8` 300 m kernel."
            ),
            "resolution": "WBG-S2 purges only `0 < d_vis < 3.2 px` for binary crest classification AND adds a second `HistGradientBoostingRegressor` trained directly on continuous `max(0, 1 - d_vis/3)` expected DTI credit.",
        },
        {
            "id": "IR-S2-006",
            "severity": "MEDIUM",
            "title": "Synthetic `13GEMSDOE` Spacing-5 Calibration Lattice Covers 99.8713% of Footprint Within 300 m",
            "evidence": "`r13-lattice-s5` places 206,895 grid dots covering 5,160,722 / 5,167,373 footprint pixels within 3 px, forcing >=82.34% literal forward overlap for any 37,654-dot submission.",
            "resolution": "Reported transparently in dual scope: competing sparse detectors pass (`max 66.20% <= 70%`), while literal unseparated `gems57.uniqueness` overlap (`99.55%`) is preserved unwaived per `AGENTS.md`.",
        },
        {
            "id": "IR-S2-007",
            "severity": "HIGH",
            "title": "Historical Focus-9 `0.2449–0.2778` Family Clone Saturation",
            "evidence": "All 9 historical high-scoring Focus-9 files (`GEMSDOE24..36`) derive from `19GEMSDOE H19-5` (`86.7%–100.0%` 3-px dot overlap; `GEMSDOE25 == GEMSDOE30` 0-XOR identical).",
            "resolution": "WBG-S2 is trained from scratch with zero `H19-5`/`B2` inheritance (`49.26%` forward overlap vs `GEMSDOE32 B2`, `Spearman = 0.0308`).",
        },
        {
            "id": "IR-S2-008",
            "severity": "MEDIUM",
            "title": "Evaluator Incomparability Across Repositories (`SegmentHoldout` vs `gems57-v2` vs `8/24-block CV`)",
            "evidence": "`gems-segment-pooled-v1` withholds 60,988 positives (100% quadrant), whereas `gems57-pooled-hide-v2` withholds 11,330 positives (20% components).",
            "resolution": "WBG-S2 evaluates every arm (`B0`, `EXP-1`, `EXP-2`, `EXP-3`) on BOTH `gems-segment-pooled-v1` (`0.183594`) and `gems57-pooled-hide-v2` (`0.147773`), achieving #1 across the fleet on both.",
        },
    ]

    # Scope and safety corrections supersede the producer's historical claims;
    # the original builder and report are preserved in research/history.
    irregularities[0]["title"] = "Band 6 provenance requires independent confirmation"
    irregularities[0]["evidence"] = (
        f"The parallel receipt reports Spearman {b6['spearman_rho']:.5f} against an owner-mirrored "
        "GeoDAWN TC raster. Correlation is useful but does not independently authenticate organizer-provided bytes."
    )
    irregularities[0]["resolution"] = "Use the feature interpretation provisionally; verify provenance with organizer sources before relying on it."
    irregularities[1]["title"] = "Range-rejection cause and exterior convention remain unresolved"
    irregularities[1]["evidence"] = (
        "A previous upload reported a [0,1] range error. Local all-finite checks pass for this file; "
        "there is no file-specific portal receipt proving what caused that rejection or that this TIFF would be accepted. "
        "The organizer's public data guidance says outside-boundary values should be null/NaN."
    )
    irregularities[1]["resolution"] = "Do not submit a negative TIFF; reconcile the public exterior guidance with the authenticated portal before any future cleared submission."
    irregularities[2]["resolution"] = "Parallel-reported ablations only; the selected arm was chosen on these splits and was not independently replayed in this review."
    irregularities[4]["title"] = "Near-fault purge and halo are a hypothesis, not a proven causal mechanism"
    irregularities[4]["evidence"] = "Different negative-purge configurations were evaluated by the parallel run; the halo explanation remains unverified."
    irregularities[4]["resolution"] = "Retain the ablation as a reported diagnostic, not proof of generalization."
    irregularities[6]["resolution"] = "Regardless of selected peers, final overlap is 100% with WBG-C1 and 99.5538% with r13; both independently trigger STOP."
    irregularities[7]["resolution"] = "Do not rank across inconsistent evaluations. The parallel values below are selection-limited and not independently replayed."
    for row in focus_sites:
        row["holdout_score_labeled"] = "PARALLEL-REPORTED (some peer metadata may be incomplete); " + row["holdout_score_labeled"]
        row["scope_warning"] = "A peer-specific comparison cannot establish complete uniqueness or approve a submission."
        if row is not focus_sites[0]:
            row["go_no_go_status"] = "RESEARCH COMPARISON ONLY; no full registry or submission clearance established"
            row["portal_format_status"] = "PRODUCER-REPORTED LOCAL FORMAT: " + row["portal_format_status"]
    observation = json.loads((ROOT / "docs/data/feed.json").read_text())["leaderboard"]
    return {
        "schema_version": "wbggems-s2-executive-audit-20261027-v1",
        "scope_warning": "Research only; final literal STOP against two pinned witnesses. Pre-placement full literal clearance not established. Parallel holdouts and peer diagnostics are not independent confirmation.",
        "generated_utc": rc["generated_utc"],
        "audit_date": "2026-10-27",
        "official_public_leaderboard_observation": {
            "score": observation["public_dw_tversky"],
            "observed_date": observation.get("observed_utc") or observation.get("observed_date_utc") or "date unavailable",
            "url": "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
            "note": "Dated public leaderboard observation, not a file-specific organizer receipt. See the automated feed for status.",
        },
        "research_artifact_not_selector_eligible": {
            "lane_id": "WBG-S2",
            "selected_arm": rc["selected_arm"],
            "holdout_limitation": "Parallel-reported; selected on these same splits; no independent replay or untouched confirmation here.",
            "eligible_for_separate_selector": False,
            "ok_to_submit": False,
            "tif_path": rc["artifact"]["tif_path"],
            "zip_path": rc["artifact"]["zip_path"],
            "tif_sha256": rc["artifact"]["tif_sha256"],
            "zip_sha256": rc["artifact"]["zip_sha256"],
            "decoded_pixels_sha256": rc["artifact"]["decoded_pixels_sha256"],
            "submission_name": rc["submission_name"],
            "submission_note": rc["submission_note"],
            "holdout_segment_v1_evaluator": "gems-segment-pooled-v1",
            "holdout_segment_v1_withheld_positives": 60988,
            "holdout_segment_v1_dti": rc["holdout_dti"]["primary_segment_holdout"]["dti"],
            "holdout_segment_v1_ci95": rc["holdout_dti"]["primary_segment_holdout"]["ci95"],
            "holdout_gems57_v2_evaluator": "gems57-pooled-hide-v2",
            "holdout_gems57_v2_withheld_positives": 11330,
            "holdout_gems57_v2_dti": rc["holdout_dti"]["secondary_gems57_buffered_components"]["dti"],
            "holdout_gems57_v2_ci95": rc["holdout_dti"]["secondary_gems57_buffered_components"]["ci95"],
            "partial_sparse_screen_pass": rc["competing_detector_gate"]["competing_sparse_3px_and_spearman_pass"],
            "literal_registry_gate_pass": False,
            "strict_governance_verdict": rc["verdict"],
            "live_slots_used_in_this_session": 0,
        },
        "official_external_data_sources": [
            {
                "name": "DrivenData DOE GEMS Competition #306",
                "url": "https://www.drivendata.org/competitions/306/competition-doe-gems/",
                "license": "Competition Rules (CC-BY / Public Federal Source Data)",
            },
            {
                "name": "USGS 3D Elevation Program (3DEP) 1 m LiDAR & Seamless 1/3 arc-second (~10 m) DEM",
                "url": "https://www.usgs.gov/3d-elevation-program",
                "api_url": "https://tnmaccess.nationalmap.gov/api/v1/products",
                "license": "US Public Domain (17 USC 105)",
            },
            {
                "name": "USGS GeoDAWN Airborne Magnetic & Gamma-Ray Radiometric Survey (Data Release)",
                "url": "https://www.sciencebase.gov/catalog/item/61955dcad34eb622f6908d6c",
                "license": "US Public Domain",
            },
            {
                "name": "DOE Geothermal Data Repository (GDR) Submission #1391 — Great Basin INGENIOUS Play Fairway",
                "url": "https://gdr.openei.org/submissions/1391",
                "license": "CC-BY-4.0 / US DOE Open Data",
            },
            {
                "name": "USGS State Geologic Map Compilation (SGMC) — Held-In Auxiliary Label Ablation Only",
                "url": "https://pubs.usgs.gov/ds/1052/",
                "license": "US Public Domain",
            },
            {
                "name": "US Census Bureau TIGER/Line 2024 Roads & Rails (`tl_2024_32/06/41/16`)",
                "url": "https://www2.census.gov/geo/tiger/TIGER2024/PRISECROADS/",
                "license": "US Public Domain",
            },
            {
                "name": "NREL / DOE GEMS Benchmark Technical Report (FY26 OSTI #96647)",
                "url": "https://docs.nlr.gov/docs/fy26osti/96647.pdf",
                "license": "US DOE Technical Report",
            },
        ],
        "sites_table": focus_sites,
        "irregularities": irregularities,
    }


def _generate_figures(rc: dict[str, Any], exp: dict[str, Any], uq: dict[str, Any], out_assets: Path) -> None:
    out_assets.mkdir(parents=True, exist_ok=True)
    tif_path = ROOT / rc["artifact"]["tif_path"]
    with rasterio.open(tif_path) as ds:
        dots = ds.read(1) > 0
    with rasterio.open(ROOT / "data" / "sample_submission.tif") as ds:
        fp = np.isfinite(ds.read(1))
    with rasterio.open(ROOT / "data" / "existing_faults.tif") as ds:
        cat = (ds.read(1) > 0) & fp
    with rasterio.open(ROOT / "data" / "external" / "lidar_scarp_features_u8.tif") as ds:
        lid_valid = (ds.read(12) > 0) & fp

    # Figure 1: Side-by-side crisp PNG map (Left: Emitted Dots + Catalogue + LiDAR Gap; Right: Density)
    step = 4
    fp_s = fp[::step, ::step]
    lid_s = lid_valid[::step, ::step]
    cat_s = binary_dilation(cat, iterations=2)[::step, ::step]
    dots_s = binary_dilation(dots, iterations=2)[::step, ::step]

    h_s, w_s = fp_s.shape  # 933 x 823
    rgb_left = np.full((h_s, w_s, 3), (245, 248, 247), dtype=np.uint8)
    rgb_left[fp_s & lid_s] = (229, 236, 235)
    rgb_left[fp_s & (~lid_s)] = (254, 243, 199)  # warm pale amber = 24.63% 1m LiDAR gap!
    rgb_left[cat_s & fp_s] = (148, 163, 184)      # slate = mapped catalogue
    rgb_left[dots_s & fp_s] = (15, 118, 110)      # deep teal = WBG-S2 37,654 binary dots

    dens = gaussian_filter(dots.astype(np.float32), sigma=12.0)[::step, ::step] * 100.0
    t_norm = np.clip(dens / 2.2, 0.0, 1.0)
    rgb_right = np.full((h_s, w_s, 3), (245, 248, 247), dtype=np.uint8)
    r_ch = (240 - 225 * t_norm).astype(np.uint8)
    g_ch = (249 - 131 * t_norm).astype(np.uint8)
    b_ch = (232 - 122 * t_norm).astype(np.uint8)
    rgb_right[fp_s] = np.stack([r_ch[fp_s], g_ch[fp_s], b_ch[fp_s]], axis=-1)

    pad = 24
    head_h = 68
    foot_h = 42
    canvas_w = w_s * 2 + pad * 3
    canvas_h = h_s + head_h + foot_h
    map_img = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    map_img.paste(Image.fromarray(rgb_left), (pad, head_h))
    map_img.paste(Image.fromarray(rgb_right), (pad * 2 + w_s, head_h))

    draw = ImageDraw.Draw(map_img)
    font = ImageFont.load_default()
    draw.text(
        (pad, 16),
        "WBG-S2 (EXP-3) Spatial Predictions: 37,654 Zero-Collar Binary Dots (Teal) vs Mapped Catalogue (Slate)",
        fill=(16, 36, 40),
        font=font,
    )
    draw.text(
        (pad, 36),
        "Amber tint = 24.63% 1 m LiDAR gap (1,272,604 px) seamlessly bridged by unstarved 10 m USGS 3DEP specialist",
        fill=(75, 99, 104),
        font=font,
    )
    draw.text(
        (pad * 2 + w_s, 16),
        "Smoothed 300 m Submodular CELF Allocation Density (dots / km^2)",
        fill=(16, 36, 40),
        font=font,
    )
    draw.text(
        (pad * 2 + w_s, 36),
        "Regime A: 28,617 Scarp/Flexure Dots (76%)  |  Regime B: 9,037 Concealed Conduit Dots (24%)",
        fill=(75, 99, 104),
        font=font,
    )
    draw.text(
        (pad, head_h + h_s + 12),
        f"EPSG:32611 · 3730x3292 (100 m) · min=0.0, max=1.0, n_nan=0 · SHA-256: {rc['artifact']['tif_sha256'][:24]}...",
        fill=(75, 99, 104),
        font=font,
    )
    map_img.save(out_assets / "wbg_s2_map_overview.png", optimize=True)

    # Figure 2: Clean Horizontal Bar Chart PNG for Both Evaluators
    cw, ch = 1320, 620
    chart = Image.new("RGB", (cw, ch), (255, 255, 255))
    cd = ImageDraw.Draw(chart)

    def _draw_panel(
        x0: int,
        title1: str,
        title2: str,
        items: list[tuple[str, float, tuple[int, int, int]]],
        max_v: float,
    ) -> None:
        cd.text((x0, 18), title1, fill=(16, 36, 40), font=font)
        cd.text((x0, 38), title2, fill=(75, 99, 104), font=font)
        bar_x = x0 + 210
        bar_w_max = 365
        y_start = 74
        row_h = 44
        for idx_i, (lbl, val, col) in enumerate(items):
            yy = y_start + idx_i * row_h
            cd.text((x0, yy + 7), lbl, fill=(16, 36, 40), font=font)
            bw = max(2, int(round((val / max_v) * bar_w_max)))
            cd.rectangle([bar_x, yy + 3, bar_x + bw, yy + 27], fill=col, outline=(30, 41, 59))
            cd.text((bar_x + bw + 8, yy + 8), f"{val:.6f}", fill=(16, 36, 40), font=font)

    seg_items = [
        ("WBG-H1 B0 (31ch)", 0.103855, (148, 163, 184)),
        ("WBG-S2 B0 (19ch+CELF)", exp["segment_holdout_v1"]["B0_19ch_CELF28"]["dti"], (100, 116, 139)),
        ("WBGGEMSDOE1 WBG-H1", 0.123310, (148, 163, 184)),
        ("GEMSDOE30 CSR-1", 0.158160, (186, 230, 253)),
        ("GEMSDOE24 DPRF1", 0.163792, (147, 197, 253)),
        ("GEMSDOE24 S3DEP1", 0.166060, (147, 197, 253)),
        ("GEMSDOE36 KPL-36", 0.170100, (96, 165, 250)),
        ("KANLERGEMSDOE2 KG2", 0.177056, (59, 130, 246)),
        ("WBG-S2 EXP-2 (+SGMC)", exp["segment_holdout_v1"]["EXP2_MKSF_SGMCDualPop"]["dti"], (45, 212, 191)),
        ("WBG-S2 EXP-1 (MKSF-1)", exp["segment_holdout_v1"]["EXP1_MKSF_Core"]["dti"], (20, 184, 166)),
        ("WBG-S2 EXP-3 (selected)", exp["segment_holdout_v1"]["EXP3_MKSF_VierbeinCoulomb"]["dti"], (15, 118, 110)),
    ]
    g57_items = [
        ("WBG-C1 Surface (Prior)", 0.014045, (252, 165, 165)),
        ("WBG-S2 B0 (19ch+CELF)", exp["gems57_buffered_component_v2"]["B0_19ch_CELF28"]["dti"], (100, 116, 139)),
        ("GEMSDOE32 H47-1-LDGI", 0.119765, (147, 197, 253)),
        ("WBG-S2 EXP-2 (+SGMC)", exp["gems57_buffered_component_v2"]["EXP2_MKSF_SGMCDualPop"]["dti"], (45, 212, 191)),
        ("WBG-S2 EXP-1 (MKSF-1)", exp["gems57_buffered_component_v2"]["EXP1_MKSF_Core"]["dti"], (20, 184, 166)),
        ("GEMSDOE57 H57 Ref", 0.136150, (96, 165, 250)),
        ("WBG-S2 EXP-3 (selected)", exp["gems57_buffered_component_v2"]["EXP3_MKSF_VierbeinCoulomb"]["dti"], (15, 118, 110)),
    ]
    _draw_panel(
        24,
        "Evaluator 1: gems-segment-pooled-v1 (n = 60,988 Withheld Fault Pixels)",
        "Parallel-reported values; selected on these splits; not a fleet ranking",
        seg_items,
        0.20,
    )
    _draw_panel(
        680,
        "Evaluator 2: gems57-pooled-hide-v2 (n = 11,330 Buffered Component Holdout)",
        "Parallel-reported values; selection-limited; not independently replayed",
        g57_items,
        0.165,
    )
    chart.save(out_assets / "wbg_s2_holdout_and_fleet_comparison.png", optimize=True)


def _write_markdown_report(audit: dict[str, Any], rc: dict[str, Any], exp: dict[str, Any]) -> None:
    """Emit a truthful executive record; preserve prior claims only as historical material."""
    md = """# WBG-S2 research audit — DO NOT SUBMIT

The parallel run produced three experiments and this research TIFF. This integration did not
retrain, place dots, select a weekly slot or submit. **WBG-S2 is negative and is not eligible
for a selector**. Its final forward overlap is **99.5538%** with pinned r13 and **100%** with
WBG-C1; both exceed 70%. The pre-placement Spearman sample is not the full literal overlap gate.
See [the independent forensic audit](../evidence/wbg_s2/safety_review_20261027.json) and
[run card](../evidence/wbg_s2/run_card.json). Local all-finite, range and grid checks pass;
that is not proof of portal acceptance and does not resolve the prior range error.

The parallel run reports **HOLDOUT-DTI 0.183594** (95% CI [0.170313, 0.196956],
`gems-segment-pooled-v1`, 60,988 positives) and **0.147773** (95% CI [0.128077, 0.167791],
`gems57-pooled-hide-v2`, 11,330 positives). These results were not independently replayed
here; arm selection used these holdouts and untouched confirmation has not been established.
They are not organizer scores or leaderboard forecasts. Input hashes are owner-mirrored, not
authenticated organizer downloads. The original report, source and card are retained in
`research/history/wbg_s2_20261027/` as historical, non-authoritative records.

## Peer-specific diagnostics (not overall uniqueness clearance)

| Site | File reported by the parallel run | Holdout reported | Historical live claim | Decision / scope |
|---|---|---|---|---|
"""
    for row in audit["sites_table"]:
        md += (f"| {row['site']} | `{row['file_to_download']}` | {row['holdout_score_labeled'].replace('|', '<br>')} | "
               f"{row['live_score_labeled']} | {row['go_no_go_status']} |\n")
    md += """

## Why the GEMSDOE32 0.2778 is not proof of a new score

`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` and 0.2778 are owner-reported;
we have no organizer receipt binding the score to these bytes. D2.8, B1 and B2 progressively
reduce 44,090, 40,199 and 37,654 predicted dots. Sparse kernel coverage and avoiding
low-credit predictions are plausible explanations, not established causal facts: hidden
labels and exact per-dot contributions are unavailable. A genuinely unique model might
outperform it, but there is no verified forecast, no proven submission, and no copy or
retuning of a stopped lane is allowed. See
[the corrected analysis](../docs/research/wbg2-why-02778.md) and
[future hypotheses](../docs/research/future-hypotheses-20261027.md).
"""
    (ROOT / "knowledge" / "03_executive_summary_and_02778_forensics_2026-10-27.md").write_text(md)


def _write_site_html(audit: dict[str, Any], rc: dict[str, Any], exp: dict[str, Any], uq: dict[str, Any], site_dir: Path) -> None:
    (site_dir / "assets").mkdir(parents=True, exist_ok=True)
    (site_dir / "data").mkdir(parents=True, exist_ok=True)

    # Copy exact run_card.json and audit JSON into `docs/wbg-s2-mksf1/data/`
    shutil.copyfile(ROOT / "evidence" / "wbg_s2" / "run_card.json", site_dir / "data" / "run_card.json")
    shutil.copyfile(ROOT / "evidence" / "wbg_s2" / "safety_review_20261027.json", site_dir / "data" / "safety_review_20261027.json")
    shutil.copyfile(ROOT / "evidence" / "wbg_s2" / "safety_review_passes_20261027.json", site_dir / "data" / "safety_review_passes_20261027.json")
    shutil.copyfile(
        ROOT / "evidence" / "wbg_s2" / "nine_site_executive_summary_20261027.json",
        site_dir / "data" / "nine_site_executive_summary_20261027.json",
    )

    css = """
:root {
  --bg: #f7f9f8;
  --surface: #ffffff;
  --ink: #102428;
  --muted: #4b6368;
  --line: #d7e2e0;
  --teal: #0f766e;
  --teal-dark: #115e59;
  --teal-soft: #e6f4f1;
  --amber: #b45309;
  --amber-soft: #fef3c7;
  --red: #b91c1c;
  --red-soft: #fee2e2;
  --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  --sans: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font-family: var(--sans); line-height: 1.55; }
a { color: var(--teal-dark); text-decoration: underline; text-underline-offset: 2px; overflow-wrap: anywhere; }
a:hover { color: #042f2e; }
code { overflow-wrap: anywhere; }
.wrap { max-width: 1200px; margin: 0 auto; padding: 0 22px; }
header.top { background: #0f292e; color: #f0fdfa; border-bottom: 3px solid var(--teal); }
.nav { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; padding: 14px 0; gap: 14px; }
.brand { color: #f0fdfa; text-decoration: none; font-weight: 800; letter-spacing: -0.01em; font-size: 1.05rem; }
.brand small { display: block; font-weight: 500; font-size: 0.72rem; color: #99f6e4; letter-spacing: 0.06em; text-transform: uppercase; }
.navlinks { display: flex; flex-wrap: wrap; gap: 14px; font-size: 0.9rem; }
.navlinks a { color: #ccfbf1; text-decoration: none; padding: 5px 10px; border-radius: 6px; }
.navlinks a.active, .navlinks a:hover { background: rgba(255,255,255,0.14); color: #ffffff; }
.hero-dl { background: var(--surface); border: 2px solid var(--teal); border-radius: 12px; padding: 22px 24px; margin: 22px 0 18px; box-shadow: 0 4px 16px rgba(15,41,46,0.06); }
.badge-row { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; }
.badge { display: inline-flex; align-items: center; gap: 6px; font-size: 0.78rem; font-weight: 700; padding: 4px 10px; border-radius: 999px; letter-spacing: 0.02em; }
.badge.pass { background: var(--teal-soft); color: var(--teal-dark); border: 1px solid #99f6e4; }
.badge.gov { background: var(--amber-soft); color: var(--amber); border: 1px solid #fcd34d; }
.dl-grid { display: grid; grid-template-columns: 1.45fr 1fr; gap: 20px; align-items: center; }
@media (max-width: 860px) { .dl-grid { grid-template-columns: 1fr; } }
.btn-row { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }
.btn { display: inline-flex; align-items: center; gap: 8px; background: var(--teal); color: #ffffff !important; text-decoration: none; font-weight: 700; padding: 11px 18px; border-radius: 8px; font-size: 0.94rem; }
.btn:hover { background: var(--teal-dark); }
.btn.sec { background: #1e293b; }
.btn.outline { background: transparent; color: var(--teal-dark) !important; border: 1.5px solid var(--teal); }
.codebox { background: #f1f5f9; border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; font-family: var(--mono); font-size: 0.78rem; overflow-x: auto; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(225px, 1fr)); gap: 14px; margin: 18px 0 26px; }
.kpi { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 16px; }
.kpi label { display: block; font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); font-weight: 700; }
.kpi .val { font-size: 1.62rem; font-weight: 800; color: var(--ink); margin: 4px 0; font-family: var(--mono); }
.kpi .sub { font-size: 0.8rem; color: var(--muted); margin: 0; }
section { margin: 28px 0; }
h1 { font-size: 1.75rem; margin: 6px 0 10px; line-height: 1.22; }
h2 { font-size: 1.32rem; margin: 0 0 10px; border-bottom: 2px solid var(--line); padding-bottom: 6px; }
h3 { font-size: 1.05rem; margin: 14px 0 6px; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 18px 20px; margin-bottom: 16px; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
@media (max-width: 860px) { .two-col { grid-template-columns: 1fr; } }
table { width: 100%; border-collapse: collapse; font-size: 0.84rem; background: var(--surface); }
th, td { border: 1px solid var(--line); padding: 9px 10px; text-align: left; vertical-align: top; }
th { background: #eef4f3; font-weight: 700; color: #0f292e; }
tr:nth-child(even) td { background: #fafcfc; }
.table-wrap { overflow-x: auto; border-radius: 8px; border: 1px solid var(--line); }
img.fig { width: 100%; height: auto; border-radius: 8px; border: 1px solid var(--line); background: #fff; }
footer { margin-top: 40px; padding: 20px 0 32px; border-top: 1px solid var(--line); font-size: 0.82rem; color: var(--muted); }
code { font-family: var(--mono); font-size: 0.84em; background: #edf2f4; padding: 1px 5px; border-radius: 4px; }
"""
    (site_dir / "assets" / "style.css").write_text(css.strip() + "\n")

    tif_rel = f"../downloads/{Path(rc['artifact']['tif_path']).name}"
    zip_rel = f"../downloads/{Path(rc['artifact']['zip_path']).name}"

    def _layout(title: str, active: str, body: str) -> str:
        nav_items = [
            ("index.html", "Overview & Download"),
            ("executive-summary.html", "9-Site Executive Audit"),
            ("forensics-02778.html", "0.2778 Analysis"),
            ("hypotheses-and-validation.html", "Hypotheses & Ablations"),
            ("how-to-submit.html", "No-submit guidance"),
        ]
        nav_html = "".join(
            f'<a class="{"active" if href == active else ""}" href="{href}">{html.escape(lbl)}</a>'
            for href, lbl in nav_items
        )
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} · WBGGEMSDOE1 WBG-S2 (MKSF-1)</title>
  <link rel="stylesheet" href="assets/style.css">
</head>
<body>
<a href="#main" style="position:absolute;left:-9999px;top:auto;width:1px;height:1px;overflow:hidden">Skip to main content</a>
<header class="top">
  <div class="wrap nav">
    <a class="brand" href="index.html">WBGGEMSDOE1 · Lane WBG-S2 (MKSF-1 / EXP-3)<small>2026-10-27 · Seamless 10m/1m + Cross-Gradient + Vierbein-Coulomb · 37,654 Binary Dots</small></a>
    <nav class="navlinks" aria-label="WBG-S2 navigation">
      {nav_html}
      <a href="../index.html">← Root Desk</a>
    </nav>
  </div>
</header>
<main id="main" class="wrap">
{body}
</main>
<footer>
  <div class="wrap">
    <strong>WBGGEMSDOE1 · WBG-S2 (MKSF-1)</strong> · Research download only. <strong>DO NOT SUBMIT; NO SELECTOR ELIGIBILITY.</strong> Parallel holdouts are not independently confirmed. No slot spent by this integration.<br>
    Artifacts: <a href="data/run_card.json">Run Card JSON</a> · <a href="data/nine_site_executive_summary_20261027.json">9-Site Audit JSON</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData Competition #306 ↗</a> · <a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE1">GitHub Repository ↗</a>
  </div>
</footer>
</body>
</html>
"""

    top_dl_banner = f"""
<div class="hero-dl" role="region" aria-label="Research artifact and strict no-submit verdict">
  <div class="badge-row">
    <span class="badge gov">DOWNLOAD: YES (RESEARCH ONLY) · SUBMIT: NO · DO NOT SUBMIT · NO SELECTOR ELIGIBILITY</span>
    <span class="badge gov">R13 OVERLAP 99.5538% · WBG-C1 OVERLAP 100% · STOP</span>
  </div>
  <div class="dl-grid">
    <div>
      <h1>WBG-S2 · parallel research result</h1>
      <p>Research download only. Both independently reproduced final-dot overlaps exceed 70%.
      The sampled pre-placement Spearman screen did not establish full literal clearance; a selector cannot waive STOP.
      No competition slot was used by this integration.</p>
      <div class="btn-row">
        <a class="btn" href="{tif_rel}" download>↓ Research-only TIFF</a>
        <a class="btn sec" href="{zip_rel}" download>↓ Research-only ZIP</a>
        <a class="btn outline" href="data/safety_review_20261027.json">Independent safety audit</a>
        <a class="btn outline" href="data/run_card.json">Run card</a>
        <a class="btn outline" href="data/safety_review_passes_20261027.json">Three review passes</a>
      </div>
      <p>Local all-finite [0,1] raster checks pass; this does <strong>not</strong> establish portal acceptance or the cause of the prior range rejection.</p>
    </div>
    <div class="codebox">
      <div><strong>File:</strong> <code>{Path(rc['artifact']['tif_path']).name}</code></div>
      <div><strong>TIFF SHA-256:</strong> <code>{rc['artifact']['tif_sha256']}</code></div>
      <div><strong>Grid:</strong> <code>EPSG:32611 · 3730×3292 · float32 [0,1]</code></div>
      <div><strong>Dots:</strong> <code>37,654</code></div>
      <div><strong>Holdouts:</strong> parallel-reported, selected on these splits; not independently replayed or confirmed on untouched data.</div>
    </div>
  </div>
</div>
"""

    # 1. index.html
    seg = rc["holdout_dti"]["primary_segment_holdout"]
    g57 = rc["holdout_dti"]["secondary_gems57_buffered_components"]
    index_body = top_dl_banner + f"""
<section class="two-col">
  <div class="card">
    <h2>Parallel-reported holdouts, not organizer scores</h2>
    <p><strong>HOLDOUT-DTI {seg['dti']:.6f}</strong>, 95% CI [{seg['ci95'][0]:.6f}, {seg['ci95'][1]:.6f}],
    <code>gems-segment-pooled-v1</code>, 60,988 withheld positives.</p>
    <p><strong>HOLDOUT-DTI {g57['dti']:.6f}</strong>, 95% CI [{g57['ci95'][0]:.6f}, {g57['ci95'][1]:.6f}],
    <code>gems57-pooled-hide-v2</code>, 11,330 withheld positives.</p>
    <p>The parallel run selected arms on these same splits. We did not replay training or confirm the result on untouched data.
    Evaluators and representations differ; do not convert these into a leaderboard forecast.</p>
  </div>
  <div class="card">
    <h2>What the safety check established</h2>
    <p>The existing TIFF and ZIP are byte-identical after extraction; local single-band, grid and finite [0,1] checks passed.
    Final predictions fail the literal registry gate against two witnesses. Sparse peer-only results do not cancel either failure.
    Organizer provenance and a file-specific score receipt are not established.</p>
    <p>Read the <a href="executive-summary.html">peer evidence table</a>,
    <a href="forensics-02778.html">0.2778 analysis</a> and
    <a href="../research/future-hypotheses-20261027.md">future hypothesis limitations</a>.</p>
  </div>
</section>
<section>
  <h2>Parallel-generated figures (descriptive only)</h2>
  <div class="two-col">
    <div class="card"><img class="fig" src="assets/wbg_s2_map_overview.png" alt="Parallel research raster map"></div>
    <div class="card"><p>The parallel comparison figure is retained as a historical asset, not as a reliable fleet ranking. The selected arm and peer values have not been independently replayed for comparability.</p></div>
  </div>
</section>
"""
    (site_dir / "index.html").write_text(_layout("Overview & Validated GeoTIFF", "index.html", index_body))

    # 2. executive-summary.html
    rows_html = ""
    for row in audit["sites_table"]:
        if "uniqueness_vs_wbg_s2" in row:
            u = row["uniqueness_vs_wbg_s2"]
            u_cell = (
                f"Fwd 3px: <strong>{u['wbg_s2_in_peer_3px']*100:.2f}%</strong><br>"
                f"Rev 3px: <strong>{u['peer_in_wbg_s2_3px']*100:.2f}%</strong><br>"
                f"Sym 3px: {u['symmetric_3px_overlap']*100:.2f}% · ρ={u['spearman_rho']:.4f}<br>"
                f"<span class='badge pass'>THIS PEER ONLY</span>"
            )
        else:
            u_cell = (
                "Self · Sparse-only diagnostic (not full gate):<br>"
                "Max fwd <strong>66.20%</strong> · Max sym <strong>59.42%</strong> · Max |ρ| <strong>0.0473</strong><br>"
                "<span class='badge gov'>LITERAL STOP</span>"
            )
        rows_html += f"""
        <tr>
          <td><strong><a href="{html.escape(row['repo_url'])}">{html.escape(row['site'])}</a></strong><br><code>{html.escape(row['pinned_head_20261027'][:16])}</code></td>
          <td><code>{html.escape(row['file_to_download'])}</code><br><small>Dots: {row['emitted_dots']:,} · SHA: <code>{row['tif_sha256'][:12]}…</code></small></td>
          <td>{html.escape(row['holdout_score_labeled'])}</td>
          <td>{html.escape(row['live_score_labeled'])}</td>
          <td>{u_cell}</td>
          <td><strong>{html.escape(row['go_no_go_status'])}</strong><br><small>{html.escape(row['portal_format_status'])}</small></td>
        </tr>"""

    irr_html = "".join(
        f"<tr><td><code>{html.escape(ir['id'])}</code><br><strong>{html.escape(ir['severity'])}</strong></td>"
        f"<td><strong>{html.escape(ir['title'])}</strong></td>"
        f"<td>{html.escape(ir['evidence'])}</td>"
        f"<td>{html.escape(ir['resolution'])}</td></tr>"
        for ir in audit["irregularities"]
    )
    src_html = "".join(
        f"<li><strong>{html.escape(s['name'])}:</strong> <a href='{html.escape(s['url'])}'>{html.escape(s['url'])}</a> ({html.escape(s['license'])})</li>"
        for s in audit["official_external_data_sources"]
    )

    exec_body = (
        top_dl_banner
        + f"""
<section>
  <h2>2026-10-27 Executive Audit Across GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36 &amp; Peers</h2>
  <p>These are parallel-run peer reports, not independently replayed results. Missing evaluator details or confidence intervals limit comparability. A per-peer diagnostic is not overall uniqueness clearance and does not override the two literal STOP witnesses. Historical live values are owner-reported unless backed by a file-specific organizer receipt.</p>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Site &amp; Pinned Commit</th>
          <th>File to Download</th>
          <th>Measured Holdout Score (Strictly Labeled)</th>
          <th>Historical / Recent Live Score</th>
          <th>Uniqueness vs WBG-S2</th>
          <th>Automated GO / NO-GO Status</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>
</section>

<section>
  <h2>Flagged Irregularities &amp; Line-by-Line Forensics (<code>IR-S2-001</code> .. <code>IR-S2-008</code>)</h2>
  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>ID / Severity</th><th>Irregularity</th><th>Verified Empirical Evidence</th><th>WBG-S2 Resolution</th></tr>
      </thead>
      <tbody>{irr_html}</tbody>
    </table>
  </div>
</section>

<section class="card">
  <h2>Parallel-reported source links (coverage and bytes require separate verification)</h2>
  <ul>{src_html}</ul>
</section>
"""
    )
    (site_dir / "executive-summary.html").write_text(
        _layout("9-Site Executive Summary (2026-10-27)", "executive-summary.html", exec_body)
    )

    # 3. forensics-02778.html
    forensics_body = top_dl_banner + """
<section class="card">
  <h2>GEMSDOE32 B2 and the reported 0.2778</h2>
  <p><code>h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros</code> has a
  <strong>USER/OWNER-REPORTED 0.2778</strong>; no file-specific organizer receipt is available here.
  D2.8, B1 and B2 reduce the predictions from 44,090 to 40,199 to 37,654 dots.
  Sparse max-cover and avoiding low-credit predictions are plausible explanations, not established causes:
  hidden labels and individual false-positive contributions are unknown.</p>
  <p>A genuinely unique file might beat that number, but no such validated winner was demonstrated.
  Different holdouts do not establish a live score. The public leaderboard is a separate observation, not a receipt for this artifact.
  <a href="../research/wbg2-why-02778.md">Read the corrected analysis and limitations.</a></p>
</section>
"""
    (site_dir / "forensics-02778.html").write_text(
        _layout("PhD Forensics of 0.2778 & Path Higher", "forensics-02778.html", forensics_body)
    )

    # 4. hypotheses-and-validation.html
    hyp_specs = [
        {
            "rank": 1,
            "id": "WBG-S2-H1 (MKSF-1)",
            "status": "EXECUTED · EXP-1 (+0.0720 SegDTI)",
            "title": "Seamless 10m/1m Transgressive Piedmont-Flexure, Gallardo-Meju Cross-Gradient & Expected 300m Kernel-Credit Submodular Field",
            "layers": "12 seamless USGS 3DEP 10 m bands (`dem10_*`), 13 1 m LiDAR scarp bands, 19 competition bands (Band 6 fixed as radiometric TC), 8 GeoDAWN rad/mag bands, DOE GDR #1391 F2mDAB/springs/wells/vents, Census TIGER 2024 roads.",
            "transform": "Transgressive piedmont-bajada slope break (`pjmf_bajada_break_10m`, AUC=0.7385) + Lake Lahontan contour-obliquity + Gallardo-Meju gravity×magnetic cross-gradient + magnetite-destruction conduit + Dual-Specialist (`Full-81ch` + unstarved `Seamless-68ch`) × Dual-Target (`Crest` + `max(0, 1-d/3)` Kernel Regressor) + Two-Regime CELF (`d>=2.8`, `37,654` dots).",
            "why": "Could detect scarps across reported LiDAR gaps and concealed structures; whether it does so remains unconfirmed.",
            "gain_cost": "Expected +0.045 to +0.070 vs B0 (Observed: +0.07204 SegDTI, +0.04313 g57DTI) · ~18 min CPU",
        },
        {
            "rank": 2,
            "id": "WBG-S2-H2 (Vierbein-Coulomb)",
            "status": "EXECUTED · EXP-3 SELECTED (+0.0146 g57 lift)",
            "title": "Fold-Visible Elastic Crack-Tip & En-Echelon Relay-Ramp Stress-Transfer Corroboration",
            "layers": "Strictly fold-visible fault graph (`fold['visible']` during CV; `existing_faults.tif` at test time) + MKSF-1 physical backbone.",
            "transform": "PCA tangent tip orientation (`AUC=0.7925`) + 6-hash inter-component en-echelon relay bridge (`AUC=0.6613`) multiplying MKSF-1 odds ONLY where physical scarp/geophysical evidence (`p >= q_60`) co-occurs.",
            "why": "Concealed splays and relay ramps may extend mapped faults; the gate is intended to limit featureless tip spray, not proven to prevent it.",
            "gain_cost": "Expected +0.006 to +0.018 on component holdout (Observed: +0.01457 over EXP-1 on gems57-v2 across 4/4 folds) · ~2 min CPU",
        },
        {
            "rank": 3,
            "id": "WBG-S2-H3 (SGMC-DualPop)",
            "status": "EXECUTED · EXP-2 (-0.0009 Honest Negative)",
            "title": "Held-In Pre-2022 Bedrock Fault Reactivation Dual-Population Transfer",
            "layers": "USGS SGMC (`derived_sgmc_faults_100m_u8.tif`) strictly inside held-in `train` fold + `geod_shearrate` + hydrothermal conduit.",
            "transform": "Auxiliary Seamless-68ch HGB head trained with `w=0.32` on high-strain/hydrothermal held-in SGMC bedrock contacts; zero SGMC input at inference.",
            "why": "Tests whether pre-Quaternary bedrock faults reactivated under modern Basin-and-Range transtension improve blind fault recall.",
            "gain_cost": "Expected +0.002 to +0.008 (Observed: -0.00090 SegDTI / -0.00180 g57DTI vs EXP-1; rejected cleanly) · ~4 min CPU",
        },
        {
            "rank": 4,
            "id": "WBG-S2-H4 (Chi-Knick)",
            "status": "DEFERRED (3-Experiment Cap)",
            "title": "D8 Fluvial Hack-Chi Steepness & Cross-Divide Disequilibrium",
            "layers": "100 m `det_elev` + seamless 10 m `dem10_hand_mean` / `dem10_tpi15_max`.",
            "transform": "Upstream integral chi-steepness step across range-bounding footwall-to-hangingwall transitions.",
            "why": "Captures transient fluvial knickzones migrating upstream from unmapped active normal faults.",
            "gain_cost": "Expected +0.004 to +0.010 · Medium cost (~20 min D8 routing)",
        },
        {
            "rank": 5,
            "id": "WBG-S2-H5 (Biharmonic-Flexure)",
            "status": "DEFERRED (3-Experiment Cap)",
            "title": "Thin-Plate Elastic Basement Flexure Curvature Coupling",
            "layers": "`depth_to_base_surf`, `iso_grav_anom`, `geod_2ndinv`.",
            "transform": "Biharmonic flexural stress concentration `D·∇⁴w_base` gated by geodetic second invariant.",
            "why": "Targets deep blind accommodation zones beneath >1.5 km Cenozoic basin fill.",
            "gain_cost": "Expected +0.002 to +0.006 · Low-Medium cost (2 km gravity grid limits 100 m localization)",
        },
    ]
    hyp_rows = "".join(
        f"<tr><td><strong>#{h['rank']} · {html.escape(h['id'])}</strong><br><code>{html.escape(h['status'])}</code></td>"
        f"<td><strong>{html.escape(h['title'])}</strong></td>"
        f"<td>{html.escape(h['layers'])}</td>"
        f"<td>{html.escape(h['transform'])}</td>"
        f"<td>{html.escape(h['why'])}</td>"
        f"<td>{html.escape(h['gain_cost'].split(' · ')[-1])} (parallel estimate)</td></tr>"
        for h in hyp_specs
    )
    seg_e = exp["segment_holdout_v1"]
    g57_e = exp["gems57_buffered_component_v2"]
    hyp_body = (
        top_dl_banner
        + f"""
<section>
  <h2>Five parallel hypotheses (three arms run; two deferred)</h2>
  <p>Results were reported by the parallel run and selected on the same splits; they have not been independently replayed here. Pre-registration SHA-256: <code>{exp['preregistration_sha256']}</code> (<a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE1/blob/main/knowledge/02_preregistration_wbg_s2_hypotheses_2026-10-27.md">view full markdown specification</a>).</p>
  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Rank &amp; ID</th><th>Hypothesis</th><th>Specific Layers</th><th>Physical Transform</th><th>Why Missing From Catalogue</th><th>Approximate cost (parallel estimate)</th></tr>
      </thead>
      <tbody>{hyp_rows}</tbody>
    </table>
  </div>
</section>

<section>
  <h2>Parallel-reported holdout results (selection-limited)</h2>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Experiment Arm</th>
          <th><code>gems-segment-pooled-v1</code> (n=60,988, 100% Quadrant Holdout)</th>
          <th><code>gems57-pooled-hide-v2</code> (n=11,330, 20% Buffered Component Holdout)</th>
          <th>Empirical Takeaway</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>B0_19ch_CELF28</strong> (Control)</td>
          <td><code>HOLDOUT-DTI {seg_e['B0_19ch_CELF28']['dti']:.6f}</code><br>95% CI [{seg_e['B0_19ch_CELF28']['ci95']['interval'][0]:.6f}, {seg_e['B0_19ch_CELF28']['ci95']['interval'][1]:.6f}]</td>
          <td><code>HOLDOUT-DTI {g57_e['B0_19ch_CELF28']['dti']:.6f}</code><br>95% CI [{g57_e['B0_19ch_CELF28']['ci95'][0]:.6f}, {g57_e['B0_19ch_CELF28']['ci95'][1]:.6f}]</td>
          <td>19 competition bands + purged 3.2 px collar + 37,654-dot CELF d≥2.8 control.</td>
        </tr>
        <tr>
          <td><strong>EXP1_MKSF_Core</strong> (H1: MKSF-1)</td>
          <td><code>HOLDOUT-DTI {seg_e['EXP1_MKSF_Core']['dti']:.6f}</code><br>95% CI [{seg_e['EXP1_MKSF_Core']['ci95']['interval'][0]:.6f}, {seg_e['EXP1_MKSF_Core']['ci95']['interval'][1]:.6f}]</td>
          <td><code>HOLDOUT-DTI {g57_e['EXP1_MKSF_Core']['dti']:.6f}</code><br>95% CI [{g57_e['EXP1_MKSF_Core']['ci95'][0]:.6f}, {g57_e['EXP1_MKSF_Core']['ci95'][1]:.6f}]</td>
          <td>Parallel-reported differences vs B0; causal attribution and generalization are not established.</td>
        </tr>
        <tr>
          <td><strong>EXP2_MKSF_SGMCDualPop</strong> (H1 + H3)</td>
          <td><code>HOLDOUT-DTI {seg_e['EXP2_MKSF_SGMCDualPop']['dti']:.6f}</code><br>95% CI [{seg_e['EXP2_MKSF_SGMCDualPop']['ci95']['interval'][0]:.6f}, {seg_e['EXP2_MKSF_SGMCDualPop']['ci95']['interval'][1]:.6f}]</td>
          <td><code>HOLDOUT-DTI {g57_e['EXP2_MKSF_SGMCDualPop']['dti']:.6f}</code><br>95% CI [{g57_e['EXP2_MKSF_SGMCDualPop']['ci95'][0]:.6f}, {g57_e['EXP2_MKSF_SGMCDualPop']['ci95'][1]:.6f}]</td>
          <td>Parallel-reported negative ablation vs EXP-1; its causal mechanism is unconfirmed.</td>
        </tr>
        <tr>
          <td><strong>EXP3_MKSF_VierbeinCoulomb</strong> (H1 + H2 · <strong>SELECTED ARM</strong>)</td>
          <td><strong><code>HOLDOUT-DTI {seg_e['EXP3_MKSF_VierbeinCoulomb']['dti']:.6f}</code></strong><br>95% CI [{seg_e['EXP3_MKSF_VierbeinCoulomb']['ci95']['interval'][0]:.6f}, {seg_e['EXP3_MKSF_VierbeinCoulomb']['ci95']['interval'][1]:.6f}]</td>
          <td><strong><code>HOLDOUT-DTI {g57_e['EXP3_MKSF_VierbeinCoulomb']['dti']:.6f}</code></strong><br>95% CI [{g57_e['EXP3_MKSF_VierbeinCoulomb']['ci95'][0]:.6f}, {g57_e['EXP3_MKSF_VierbeinCoulomb']['ci95'][1]:.6f}]</td>
          <td>Selected on these reported splits; no independent replay or untouched confirmation is established.</td>
        </tr>
      </tbody>
    </table>
  </div>
</section>
"""
    )
    (site_dir / "hypotheses-and-validation.html").write_text(
        _layout("Hypotheses, Canaries & Holdout Ablations", "hypotheses-and-validation.html", hyp_body)
    )

    # 5. how-to-submit.html
    submit_body = top_dl_banner + """
<section class="card">
  <h2>No submission workflow for this stopped artifact</h2>
  <p><strong>Do not upload WBG-S2.</strong> The literal duplicate STOP is binding; it is not eligible for a selector.
  Local format checks are not a portal acceptance receipt. A future distinct candidate would need the
  unchanged complete gate before and after placement, a comparable holdout win, a valid filename/note,
  and a separate selector decision before any competition slot is used.</p>
  <p>See the <a href="../how-to-submit.html">general submission guide</a> and the
  <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official task guidance</a>.
  Account-specific availability and acceptance are not visible without authenticated access.</p>
</section>
"""
    (site_dir / "how-to-submit.html").write_text(
        _layout("How to Submit to DrivenData", "how-to-submit.html", submit_body)
    )


def assert_safe_to_publish(rc: dict[str, Any], safety: dict[str, Any]) -> None:
    """Reject inconsistent decision records or changed negative artifact bytes."""
    from audit_wbg_s2_safety import C1_SHA, EXPECTED, WITNESS_SHA

    artifact = rc["artifact"]
    tif = ROOT / artifact["tif_path"]
    zip_path = ROOT / artifact["zip_path"]
    witnesses = safety["witnesses"]
    decision = rc["strict_governance_decision"]
    if (artifact["tif_sha256"] != EXPECTED or hashlib.sha256(tif.read_bytes()).hexdigest() != EXPECTED
            or safety["existing_tiff_sha256"] != EXPECTED or rc["verdict"] != "negative"
            or decision["ok_to_submit"] is not False or decision["eligible_for_separate_selector"] is not False
            or safety["ok_to_submit"] is not False or safety["eligible_for_separate_selector"] is not False
            or len(witnesses) != 2 or [row["sha256"] for row in witnesses] != [WITNESS_SHA, C1_SHA]
            or any(not math.isfinite(row["my_dots_within_3px_of_theirs"])
                   or not .70 < row["my_dots_within_3px_of_theirs"] <= 1
                   or row["duplicate_by_overlap"] is not True for row in witnesses)):
        raise ValueError("WBG-S2 artifact or binding negative STOP is inconsistent")
    with zipfile.ZipFile(zip_path) as archive:
        if archive.namelist() != [tif.name] or hashlib.sha256(archive.read(tif.name)).hexdigest() != EXPECTED:
            raise ValueError("WBG-S2 ZIP does not contain the exact stopped TIFF")


def main() -> None:
    rc = json.loads((ROOT / "evidence" / "wbg_s2" / "run_card.json").read_text())
    safety = json.loads((ROOT / "evidence" / "wbg_s2" / "safety_review_20261027.json").read_text())
    assert_safe_to_publish(rc, safety)
    uq = json.loads((ROOT / "evidence" / "wbg_s2" / "uniqueness_audit.json").read_text())
    exp = json.loads((ROOT / "evidence" / "wbg_s2" / "experiments.json").read_text())
    canary = json.loads((ROOT / "evidence" / "wbg_s2" / "leakage_canary_81ch.json").read_text())
    b6 = json.loads((ROOT / "evidence" / "wbg_s2" / "band6_provenance_receipt.json").read_text())

    audit = _build_nine_site_audit(rc, uq, exp, canary, b6)
    dump_json(ROOT / "evidence" / "wbg_s2" / "nine_site_executive_summary_20261027.json", audit)
    _write_markdown_report(audit, rc, exp)

    site_dir = ROOT / "docs" / "wbg-s2-mksf1"
    fig1 = site_dir / "assets" / "wbg_s2_map_overview.png"
    fig2 = site_dir / "assets" / "wbg_s2_holdout_and_fleet_comparison.png"
    if "--regenerate-figures" in sys.argv or not (fig1.exists() and fig2.exists()):
        _generate_figures(rc, exp, uq, site_dir / "assets")
    _write_site_html(audit, rc, exp, uq, site_dir)
    print("Built evidence/wbg_s2/nine_site_executive_summary_20261027.json, knowledge report, figures, and docs/wbg-s2-mksf1/!")


if __name__ == "__main__":
    main()
