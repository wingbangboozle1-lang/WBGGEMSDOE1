"""Comprehensive automated test & verification suite for WBGGEMSDOE1."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

from gems.metric import dti_components_exact
from wbggems1.dpgf_model import IDX, REGIONAL_SCALAR_COLS, RegionalResidualizer
from wbggems1.submodular import emit_celf_submodular

ROOT = Path(__file__).resolve().parents[1]


def _decode_uleb128_runs(buf: bytes, shape: tuple[int, int]) -> np.ndarray:
    runs: list[int] = []
    val = 0
    shift = 0
    for b in buf:
        val |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            runs.append(val)
            val = 0
            shift = 0
        else:
            shift += 7
    out = np.empty(shape[0] * shape[1], dtype=bool)
    pos = 0
    state = False  # first run = outside footprint
    for r in runs:
        out[pos : pos + r] = state
        pos += r
        state = not state
    assert pos == shape[0] * shape[1]
    return out.reshape(shape)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_footprint_bin_rle_regression_guard() -> None:
    """Guard against IR-WBG1-02 (UTF-8 mangled footprint.bin)."""
    fp_meta = json.loads((ROOT / "docs/data/footprint.json").read_text())
    fp_bytes = (ROOT / "docs/data/footprint.bin").read_bytes()
    assert len(fp_bytes) == 15_681
    mask = _decode_uleb128_runs(fp_bytes, (fp_meta["height"], fp_meta["width"]))
    assert mask.shape == (3730, 3292)
    assert int(mask.sum()) == 5_167_373


def test_canonical_submission_tif_and_zip_strict_portal_compliance() -> None:
    """Verify the generated GeoTIFF and ZIP satisfy 100% of DrivenData [0,1] portal gates."""
    rc = json.loads((ROOT / "evidence/wbg_h1/run_card.json").read_text())
    rc_docs = json.loads((ROOT / "docs/wbg-h1-dpgf1/data/run_card.json").read_text())
    assert rc == rc_docs

    tif_path = ROOT / rc["raster_sha256"]["tif_file"]
    zip_path = ROOT / rc["raster_sha256"]["zip_file"]
    assert tif_path.exists()
    assert zip_path.exists()

    assert _sha256(tif_path) == rc["raster_sha256"]["tif_sha256"]
    assert _sha256(zip_path) == rc["raster_sha256"]["zip_sha256"]

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        assert names == [tif_path.name]
        assert hashlib.sha256(zf.read(tif_path.name)).hexdigest() == rc["raster_sha256"]["tif_sha256"]

    fp_mask = _decode_uleb128_runs((ROOT / "docs/data/footprint.bin").read_bytes(), (3730, 3292))

    with rasterio.open(tif_path) as ds:
        assert ds.count == 1
        assert ds.dtypes[0] == "float32"
        assert (ds.height, ds.width) == (3730, 3292)
        assert ds.crs.to_epsg() == 32611
        assert tuple(ds.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        assert ds.nodata is None
        arr = ds.read(1)

    # Strict whole-array [0, 1] check (no NaN, no Inf anywhere across all 12,279,160 cells)
    assert arr.size == 12_279_160
    assert int(np.isnan(arr).sum()) == 0
    assert int(np.isinf(arr).sum()) == 0
    assert bool(((arr >= 0.0) & (arr <= 1.0)).all())
    assert float(arr[~fp_mask].max()) == 0.0
    assert float(arr[~fp_mask].min()) == 0.0
    assert int((arr[fp_mask] > 0.0).sum()) == 37_654
    assert set(np.unique(arr).tolist()).issubset({0.0, 1.0})


def test_official_dti_metric_invariants() -> None:
    """Verify official DTI (alpha=0.2, beta=0.8, 300 m kernel) properties."""
    gt = np.zeros((25, 25), dtype=bool)
    gt[12, 12] = True

    # Exact center hit: TP_w = 1.0, FP_w = 0.0, FN_w = 0.0 -> DTI = 1.0
    pred_exact = np.zeros((25, 25), dtype=np.float32)
    pred_exact[12, 12] = 1.0
    c_exact = dti_components_exact(pred_exact, gt)
    assert np.isclose(c_exact["dti"], 1.0)

    # 2-pixel offset (200 m): k(200m) = 1 - 2/3 = 1/3 -> TP_w = 1/3, FP_w = 2/3, FN_w = 2/3
    pred_2px = np.zeros((25, 25), dtype=np.float32)
    pred_2px[12, 14] = 1.0
    c_2px = dti_components_exact(pred_2px, gt)
    expected_2px = (1.0 / 3.0) / ((1.0 / 3.0) + 0.2 * (2.0 / 3.0) + 0.8 * (2.0 / 3.0))
    assert np.isclose(c_2px["dti"], expected_2px, atol=1e-5)

    # 4-pixel offset (400 m > 300 m): k = 0 -> DTI = 0.0
    pred_4px = np.zeros((25, 25), dtype=np.float32)
    pred_4px[12, 16] = 1.0
    c_4px = dti_components_exact(pred_4px, gt)
    assert np.isclose(c_4px["dti"], 0.0)


def test_submodular_300m_celf_emitter() -> None:
    """Verify submodular 300 m CELF obeys budget, collar mask, and spacing separation."""
    prob = np.full((60, 60), 0.01, dtype=np.float32)
    prob[20, 20] = 0.98
    prob[20, 21] = 0.70  # adjacent duplicate ridge pixel that CELF should suppress
    prob[40, 40] = 0.92

    eligible = np.ones((60, 60), dtype=bool)
    eligible[:5, :] = False  # collar / exterior exclusion
    prob[2, 2] = 0.99  # high score inside excluded collar must never be placed

    out, cov = emit_celf_submodular(prob, eligible, budget_dots=15, min_separation_px=2.25)
    assert out.shape == (60, 60)
    assert cov.shape == (60, 60)
    assert out.dtype == np.float32
    assert float(out[:5, :].sum()) == 0.0
    assert out[20, 20] == 1.0
    assert out[40, 40] == 1.0
    assert out[20, 21] == 0.0  # suppressed by min_separation_px + 300 m coverage discount
    assert int((out > 0).sum()) == 15


def test_regional_residualizer_fold_safety() -> None:
    """Ensure RegionalResidualizer fits strictly on training rows and transforms cleanly."""
    rng = np.random.default_rng(7)
    n = 600
    mm = rng.normal(0.0, 1.0, size=(n, 66)).astype(np.float32)
    r_norm = rng.uniform(-1.0, 1.0, size=n).astype(np.float32)
    c_norm = rng.uniform(-1.0, 1.0, size=n).astype(np.float32)
    mm[:, IDX["org_det_elev"]] = 100.0 * r_norm
    c0 = REGIONAL_SCALAR_COLS[0]
    raw_trend = 15.0 * r_norm - 10.0 * c_norm
    mm[:, c0] = raw_trend + rng.normal(0.0, 0.05, size=n).astype(np.float32)

    train_bg = np.arange(0, 400, dtype=np.int64)
    rr = RegionalResidualizer.fit(mm, train_bg, r_norm, c_norm, seed=7)
    x_copy = mm.copy()
    rr.transform_inplace(x_copy, {c: c for c in REGIONAL_SCALAR_COLS}, r_norm, c_norm, mm[:, IDX["org_det_elev"]])
    # On held-out rows 400..600, raw std is ~10+, while standardized residual std is ~1.0
    assert float(np.std(mm[400:, c0])) > 6.0
    assert 0.5 < float(np.std(x_copy[400:, c0])) < 1.8


def test_evidence_run_card_and_pages_consistency() -> None:
    """Verify Run Card protocol rules, canary ceiling, forensics, and built HTML pages."""
    rc = json.loads((ROOT / "evidence/wbg_h1/run_card.json").read_text())
    canary = json.loads((ROOT / "evidence/wbg_h1/leakage_canary_66ch.json").read_text())
    exp = json.loads((ROOT / "evidence/wbg_h1/wbg_h1_experiments.json").read_text())
    proof = json.loads((ROOT / "evidence/wbg_h1/forensic_proof_02778.json").read_text())
    f9 = json.loads((ROOT / "evidence/wbg_h1/focus9_executive_audit.json").read_text())

    # Rule 4: Leakage canary <= 0.90 across all 66 channels
    assert canary["n_features_tested"] == 66
    assert canary["passed"] is True
    assert canary["max_symmetric_auc"] <= 0.90

    # Rule 1 & 5: Uniqueness & Run Card schema
    cov = rc["registry_correlation_and_overlap"]
    assert cov["pre_placement_surface_max_abs_spearman"] <= 0.90
    assert cov["sparse_dot_submissions_le_100k_max_3px_overlap"] <= 0.70
    assert cov["focus9_sites_max_3px_dot_overlap"] <= 0.70
    assert cov["all_206_competing_symmetric_3px_max_overlap"] <= 0.70
    assert len(rc["submission_note"]) == rc["submission_note_length"] <= 140
    assert rc["verdict"] in {"promote", "negative"}
    assert rc["verdict"] == "negative"  # honest gate vs 0.163792 analytical reference

    # Experiment lift over matched B0
    b0 = exp["arms"]["B0_Raw31_HGB_NMS28"]["holdout"]["dti"]
    e3 = exp["arms"]["EXP3_DPGF_TwoRegime_Submod"]["holdout"]["dti"]
    assert e3 > b0 + 0.015
    assert rc["holdout_dti"]["paired_delta_vs_b0_ci95"][0] > 0.0

    # Forensic 0-XOR proof & verified 0.0904 r13-lattice-s5 inversion
    assert proof["zero_xor_proof"]["xor_differing_pixels_across_5167373_footprint"] == 0
    assert "0.0904" in proof["private_test_set_inversion"]["calibration_artifact_s5"]
    assert len(f9) == 9

    # Built GitHub Pages & README checks
    idx_html = (ROOT / "docs/wbg-h1-dpgf1/index.html").read_text()
    sub_html = (ROOT / "docs/wbg-h1-dpgf1/executive-summary.html").read_text()
    main_idx = (ROOT / "docs/index.html").read_text()
    readme = (ROOT / "README.md").read_text()
    for doc in (idx_html, sub_html, readme):
        assert rc["raster_sha256"]["tif_sha256"] in doc
        assert rc["submission_name"] in doc
        assert "0.2778" in doc
    assert "wbg-h1-dpgf1/index.html" in main_idx
    assert "Maximize P(Win)" in readme
    assert "Own the Outcome" in readme
    assert (ROOT / "docs/wbg-h1-dpgf1/assets/wbggems1_map_overview.png").exists()
    assert (ROOT / "docs/wbg-h1-dpgf1/assets/holdout_ablation_and_forensics.png").exists()
