"""End-to-end physics, holdout-receipt, uniqueness, and GeoTIFF contract tests for WBG-3."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio

from wbg3.physics import (
    STATIC_FEATURE_NAMES,
    WCS_FEATURE_NAMES,
    compute_monogenic_pc,
    compute_spi_and_ppdr,
    compute_visible_wcs_channels,
)

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_wbg3_channel_counts_match_preregistration():
    prereg = json.loads((ROOT / "registry/wbg3_preregistration.json").read_text())
    assert len(STATIC_FEATURE_NAMES) == 36
    assert len(WCS_FEATURE_NAMES) == 4
    assert prereg["gates"]["canary_max_orientation_invariant_auc"] == 0.90


def test_spi_and_ppdr_operators_are_finite_and_localize_contacts_and_demagnetization():
    h, w = 96, 96
    fp = np.ones((h, w), dtype=bool)
    # Synthetic vertical contact at col 48 in gravity & basement; magnetite destroyed along col 48 in RTP
    grav = np.zeros((h, w), dtype=np.float32)
    grav[:, 48:] = 15.0
    gy, gx = np.gradient(grav)
    grav_hg = np.hypot(gy, gx).astype(np.float32)
    grav_vg = np.gradient(gx, axis=1).astype(np.float32)

    rtp = np.zeros((h, w), dtype=np.float32)
    rtp[48:, :] = 80.0  # orthogonal magnetic step at row 48, absent at col 48
    ry, rx = np.gradient(rtp)
    tmi_hg = np.hypot(ry, rx).astype(np.float32)
    tmi_vg = np.gradient(ry, axis=0).astype(np.float32)

    kept = {
        "tmi_hg": tmi_hg,
        "tmi_vg": tmi_vg,
        "iso_grav_anom_hg": grav_hg,
        "iso_grav_anom_vg": grav_vg,
        "depth_to_base_surf": grav * 20.0,
        "rtp": rtp,
        "cond_surf": np.ones((h, w), dtype=np.float32) * 2.0,
    }
    rad_k = np.ones((h, w), dtype=np.float32) * 3.0
    rad_th = np.ones((h, w), dtype=np.float32) * 1.0
    rad_u = np.ones((h, w), dtype=np.float32) * 1.0

    out = compute_spi_and_ppdr(kept, rtp.copy(), rad_k, rad_th, rad_u, fp)
    assert len(out) == 9
    for arr in out.values():
        assert arr.shape == (h, w)
        assert np.isfinite(arr).all()
    # Gravity SPI peaks near col 48; PPDR magnetite destruction is strongly positive along col 48
    assert out["ppdr_mag_destruction"][24:72, 47:50].mean() > out["ppdr_mag_destruction"][24:72, 10:20].mean() + 1.0


def test_riesz_monogenic_phase_congruency_is_contrast_invariant_on_steps():
    fp = np.ones((128, 128), dtype=bool)
    low_step = np.zeros((128, 128), dtype=np.float32)
    low_step[:, 64:] = 0.05
    high_step = low_step * 100.0
    pc_low, _, _, _ = compute_monogenic_pc(low_step, fp, (4.0, 8.0, 16.0))
    pc_high, _, _, _ = compute_monogenic_pc(high_step, fp, (4.0, 8.0, 16.0))
    assert np.isfinite(pc_low).all() and np.isfinite(pc_high).all()
    assert ((pc_low >= 0.0) & (pc_low <= 1.0)).all()
    # Amplitude invariance across a 100x contrast ratio at the interior step edge
    assert pc_low[64, 64] == pytest.approx(pc_high[64, 64], abs=0.02)
    assert pc_low[64, 64] > pc_low[64, 20] + 0.15


def test_visible_wcs_channels_never_leak_withheld_segments():
    fp = np.ones((72, 72), dtype=bool)
    vis_only = np.zeros((72, 72), dtype=bool)
    vis_only[12:28, 20] = True
    full_with_secret = vis_only.copy()
    full_with_secret[46:62, 52] = True  # withheld fault in held-out quadrant

    rng = np.random.default_rng(42)
    strain = rng.uniform(0.0, 1.0, (72, 72)).astype(np.float32)
    hydro = rng.uniform(0.0, 1.0, (72, 72)).astype(np.float32)

    ch_a = compute_visible_wcs_channels(vis_only, fp, strain, hydro)
    ch_b = compute_visible_wcs_channels(vis_only.copy(), fp, strain, hydro)
    assert set(ch_a.keys()) == set(WCS_FEATURE_NAMES)
    for k in WCS_FEATURE_NAMES:
        assert np.isfinite(ch_a[k]).all()
        assert np.array_equal(ch_a[k], ch_b[k])

    ch_leaked = compute_visible_wcs_channels(full_with_secret, fp, strain, hydro)
    assert not np.allclose(
        ch_a["wcs_echelon_halo"][42:66, 44:62],
        ch_leaked["wcs_echelon_halo"][42:66, 44:62],
    )


def test_wbg3_run_card_protocol_and_holdout_contracts():
    card = json.loads((ROOT / "evidence/wbg3_spipmr/run_card.json").read_text())
    assert _sha256(ROOT / card["preregistration_path"]) == card["preregistration_sha256"]
    assert card["experiments_executed"] == 3 <= card["experiment_budget_limit"]
    assert card["elapsed_seconds"] <= card["wall_budget_seconds"] == 7200
    assert card["submission_slots_used"] == 0
    assert card["leakage_canary"]["passed"] is True
    assert card["leakage_canary"]["features_checked"] == 40
    assert card["leakage_canary"]["worst_orientation_invariant_auc"] <= 0.90

    seg = card["holdout_dti"]["primary_segment_holdout"]
    intra = card["holdout_dti"]["secondary_intrabasin_holdout"]
    for h in (seg, intra):
        assert h["evidence_class"] == "HOLDOUT-DTI"
        assert len(h["ci95"]) == 2 and h["ci95"][0] < h["dti"] < h["ci95"][1]
        assert h["withheld_positive_pixels"] > 0

    vs_ctrl = seg["paired_comparisons"]["arm3_vs_arm1_ctrl19b"]
    assert vs_ctrl["fold_wins"] == 4
    assert vs_ctrl["ci95_strictly_positive"] is True
    assert seg["dti"] > 300.0 * seg["all_arms"]["wbg2_pr13_random_kde_36000"]["dti"]
    assert intra["paired_differences"]["wbg2_pr13_random_kde_36000"]["ci95"][0] > 0.0

    comp = card["correlation_overlap_vs_registry"]["final_dots_competing_sparse"]
    lit = card["correlation_overlap_vs_registry"]["final_dots_literal_all_entries"]
    assert card["correlation_overlap_vs_registry"]["total_unique_rasters_checked"] >= 207
    assert card["correlation_overlap_vs_registry"]["pre_placement_surface"]["passed_threshold_0_90"] is True
    assert comp["passed_competing_uniqueness"] is True
    assert comp["max_forward_3px_overlap"] <= 0.70
    assert lit["passed_literal_uniqueness"] is False
    assert card["leaderboard_estimate"] is None
    assert card["organizer_confirmed_score"] is None
    assert card["verdict"] == "negative"
    assert card["decision"]["ok_to_submit"] is False
    assert len(card["submission_note"]) <= 140


def test_wbg3_shipped_geotiff_and_zip_roundtrip():
    card = json.loads((ROOT / "evidence/wbg3_spipmr/run_card.json").read_text())
    tif_path = ROOT / card["artifact"]
    zip_path = ROOT / card["zip_artifact"]
    assert tif_path.exists() and zip_path.exists()
    assert _sha256(tif_path) == card["raster_sha256"]
    assert _sha256(zip_path) == card["zip_sha256"]

    with rasterio.open(tif_path) as ds:
        assert ds.count == 1
        assert ds.dtypes == ("float32",)
        assert str(ds.crs) == "EPSG:32611"
        assert ds.shape == (3730, 3292)
        assert tuple(ds.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        assert ds.nodata is None
        arr = ds.read(1)

    assert np.isfinite(arr).all()
    assert ((arr == 0.0) | (arr == 1.0)).all()
    assert int(np.count_nonzero(arr > 0)) == 36800

    sample_p = ROOT / "data/sample_submission.tif"
    labels_p = ROOT / "data/labels.tif"
    if sample_p.exists() and labels_p.exists():
        with rasterio.open(sample_p) as sds, rasterio.open(labels_p) as lds:
            fp = np.isfinite(sds.read(1))
            cat = (lds.read(1) > 0) & fp
        assert int(np.count_nonzero(arr[~fp])) == 0
        assert int(np.count_nonzero(arr[cat])) == 0

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert names == [tif_path.name]
        assert zf.read(tif_path.name) == tif_path.read_bytes()


def test_wbg3_static_pages_and_no_raw_latex():
    card = json.loads((ROOT / "evidence/wbg3_spipmr/run_card.json").read_text())
    comp = card["correlation_overlap_vs_registry"]["final_dots_competing_sparse"]
    assert card["correlation_overlap_vs_registry"]["total_unique_rasters_checked"] == 209
    assert card["correlation_overlap_vs_registry"]["competing_sparse_rasters_checked"] == 207
    assert comp["vs_wbg_s2"]["forward_3px_overlap"] <= 0.70
    assert comp["vs_wbg3_exp3det"]["forward_3px_overlap"] <= 0.70

    for rel in (
        "docs/wbg3/index.html",
        "docs/wbg3/how-to-submit.html",
        "docs/wbg3/forensics-and-hypotheses.html",
    ):
        html = (ROOT / rel).read_text(encoding="utf-8")
        assert "$" not in html, f"Raw LaTeX dollar sign found in {rel}"
        assert "0.2824" not in html
        assert "DO NOT SUBMIT" in html
        assert "NO SELECTOR ELIGIBILITY" in html
        assert "99.9946%" in html
        assert "100%" in html
        assert "OK to submit</span>" not in html

