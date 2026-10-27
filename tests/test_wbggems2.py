"""End-to-end verification tests for Session-2 Lane WBG-S2 (`MKSF-1 / EXP-3`).

Designed to run cleanly both with full local `data/` and on fresh CI checkouts
where git-ignored `data/` is absent (decoding the footprint directly from
`docs/data/footprint.bin`).
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

import numpy as np
import rasterio

from wbggems2 import LANE_ID, MODEL_FAMILY
from wbggems2.features import FEATURE_NAMES, IDX
from wbggems2.mksf_model import SEAMLESS_68_COLS, compute_visible_coulomb_lobes, crest_sharpen_and_dehalo

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
    out = np.zeros(shape[0] * shape[1], dtype=bool)
    pos = 0
    state = False
    for r in runs:
        if state:
            out[pos : pos + r] = True
        pos += r
        state = not state
    assert pos == out.size
    return out.reshape(shape)


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        d = dict(attrs)
        for k in ("href", "src"):
            if d.get(k):
                self.refs.append(str(d[k]))


def test_wbggems2_feature_catalog_invariants() -> None:
    assert LANE_ID == "WBG-S2"
    assert MODEL_FAMILY == "MKSF-1"
    assert len(FEATURE_NAMES) == 81
    assert len(set(FEATURE_NAMES)) == 81
    # Seamless 68-ch specialist must strictly exclude all 13 `lid_*` channels
    assert len(SEAMLESS_68_COLS) == 68
    for col in SEAMLESS_68_COLS:
        assert not FEATURE_NAMES[col].startswith("lid_")
    # No banned `qfaults` or `sgmc` feature names in the 81-channel inference stack
    joined = " ".join(FEATURE_NAMES).lower()
    assert "qfault" not in joined
    assert "sgmc" not in joined
    assert "dist_known_fault" not in joined
    assert "pjmf_bajada_break_10m" in IDX
    assert "cgmd_crossgrad_grav_mag" in IDX


def test_wbggems2_operators_on_synthetic_fault_trace() -> None:
    fp = np.ones((48, 48), dtype=bool)
    vis = np.zeros((48, 48), dtype=bool)
    # Two en-echelon fault strands separated by a 6-px step-over relay ramp
    vis[10:22, 18] = True
    vis[26:38, 22] = True
    tip_f, relay_f = compute_visible_coulomb_lobes(vis, fp)
    assert tip_f.shape == (48, 48)
    assert relay_f.shape == (48, 48)
    assert np.isfinite(tip_f).all() and np.isfinite(relay_f).all()
    assert float(tip_f.min()) >= 0.0 and float(tip_f.max()) <= 1.0
    assert float(relay_f.min()) >= 0.0 and float(relay_f.max()) <= 1.0
    # Crack-tip cone ahead of strand 1 tip `(21, 18)` (`r=25, c=18`, d=4 px) must fire > far background
    assert float(tip_f[25, 18]) > float(tip_f[5, 5]) + 0.30
    # En-echelon relay ramp midpoint `(23, 20)` must fire > far background
    assert float(relay_f[23, 20]) > float(relay_f[5, 42]) + 0.25

    # Crest sharpener preserves [0, 1] and suppresses broad flank halo relative to razor crest
    raw = np.zeros((48, 48), dtype=np.float32)
    raw[8:40, 24] = 0.80
    raw[8:40, 23] = 0.35
    raw[8:40, 25] = 0.35
    sharp = crest_sharpen_and_dehalo(raw, fp)
    assert sharp.dtype == np.float32
    assert float(sharp.min()) >= 0.0 and float(sharp.max()) <= 1.0
    assert float(sharp[24, 24]) > 2.2 * float(sharp[24, 21] + 1e-4)


def test_wbg_s2_canary_and_band6_provenance_receipts() -> None:
    b6 = json.loads((ROOT / "evidence/wbg_s2/band6_provenance_receipt.json").read_text())
    assert b6["band_index_1based"] == 6
    assert b6["spearman_rho"] > 0.9999

    canary = json.loads((ROOT / "evidence/wbg_s2/leakage_canary_81ch.json").read_text())
    assert canary["passed"] is True
    assert canary["leakage_suspected"] is False
    assert canary["total_canary_tests"] == 332
    assert canary["maximum_orientation_invariant_auc"] <= 0.90


def test_wbg_s2_run_card_experiments_and_validated_geotiff() -> None:
    rc = json.loads((ROOT / "evidence/wbg_s2/run_card.json").read_text())
    rc_docs = json.loads((ROOT / "docs/wbg-s2-mksf1/data/run_card.json").read_text())
    assert rc == rc_docs

    exp = json.loads((ROOT / "evidence/wbg_s2/experiments.json").read_text())
    uq = json.loads((ROOT / "evidence/wbg_s2/uniqueness_audit.json").read_text())
    audit = json.loads((ROOT / "evidence/wbg_s2/nine_site_executive_summary_20261027.json").read_text())

    # Protocol & budget checks
    assert rc["lane_id"] == "WBG-S2"
    assert rc["experiments_used"] == 3
    assert rc["submission_slots_used"] == 0
    assert rc["organizer_confirmed_score"] is None
    assert rc["leaderboard_projection"] is None
    assert len(rc["submission_note"]) == rc["submission_note_length"] <= 140
    assert rc["verdict"] in {"promote", "negative"}

    # Dual-evaluator holdout superiority checks
    seg = rc["holdout_dti"]["primary_segment_holdout"]
    g57 = rc["holdout_dti"]["secondary_gems57_buffered_components"]
    assert seg["label"] == "HOLDOUT-DTI"
    assert seg["evaluator_version"] == "gems-segment-pooled-v1"
    assert seg["withheld_positive_pixels"] == 60988
    assert seg["dti"] > 0.180  # beats KANLERGEMSDOE2 (0.1771), GEMSDOE36 (0.1701), GEMSDOE24 (0.1661), WBG-H1 (0.1233)
    assert seg["paired_delta_vs_b0"] > 0.065
    assert seg["paired_delta_vs_b0_ci95"][0] > 0.055

    assert g57["label"] == "HOLDOUT-DTI"
    assert g57["evaluator_version"] == "gems57-pooled-hide-v2"
    assert g57["withheld_positive_pixels"] == 11330
    assert g57["dti"] > 0.145  # beats GEMSDOE57 (0.1362), GEMSDOE32 H47 (0.1198), WBG-C1 (0.0140)
    assert g57["paired_delta_vs_b0_ci95"][0] > 0.040
    assert exp["gems57_buffered_component_v2"]["EXP3_MKSF_VierbeinCoulomb"]["dti"] > (
        exp["gems57_buffered_component_v2"]["EXP1_MKSF_Core"]["dti"] + 0.012
    )

    # Pre-placement and post-placement competing-sparse uniqueness checks
    assert uq["pre_placement"]["passed"] is True
    assert uq["pre_placement"]["max_abs_spearman_rho"] <= 0.90
    assert uq["post_placement"]["competing_sparse_gate"]["passed"] is True
    assert uq["post_placement"]["competing_sparse_gate"]["max_forward_3px_overlap"] <= 0.70
    assert uq["post_placement"]["competing_sparse_gate"]["max_worst_directional_3px_overlap"] <= 0.70
    assert uq["post_placement"]["competing_sparse_gate"]["max_abs_spearman_rho"] <= 0.90
    assert uq["post_placement"]["non_lattice_symmetric_gate"]["passed"] is True
    assert uq["post_placement"]["non_lattice_symmetric_gate"]["max_symmetric_3px_overlap"] <= 0.70

    # Direct on-disk verification of the GeoTIFF and One-TIFF ZIP
    tif_path = ROOT / rc["artifact"]["tif_path"]
    zip_path = ROOT / rc["artifact"]["zip_path"]
    assert tif_path.is_file()
    assert zip_path.is_file()
    assert hashlib.sha256(tif_path.read_bytes()).hexdigest() == rc["artifact"]["tif_sha256"]
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == rc["artifact"]["zip_sha256"]

    fp_mask = _decode_uleb128_runs((ROOT / "docs/data/footprint.bin").read_bytes(), (3730, 3292))
    with rasterio.open(tif_path) as ds:
        assert ds.count == 1
        assert ds.dtypes[0] == "float32"
        assert ds.shape == (3730, 3292)
        assert str(ds.crs) == "EPSG:32611"
        assert ds.nodata is None
        arr = ds.read(1)

    assert np.isfinite(arr).all()
    assert float(arr.min()) == 0.0
    assert float(arr.max()) == 1.0
    assert int(np.count_nonzero(arr[~fp_mask])) == 0
    assert np.isin(arr, [0.0, 1.0]).all()
    assert int(np.count_nonzero(arr > 0.0)) == 37654
    assert hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest() == rc["artifact"]["decoded_pixels_sha256"]

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert len(names) == 1
        assert zf.read(names[0]) == tif_path.read_bytes()

    # Executive summary covers all 9 requested GEMSDOE sites + KANLERGEMSDOE2 + WBGGEMSDOE1
    site_names = " ".join(s["site"] for s in audit["sites_table"])
    for req_site in (
        "GEMSDOE24",
        "GEMSDOE25",
        "GEMSDOE27",
        "GEMSDOE28",
        "GEMSDOE30",
        "GEMSDOE31",
        "GEMSDOE32",
        "GEMSDOE33",
        "GEMSDOE36",
        "KANLERGEMSDOE2",
        "WBGGEMSDOE1",
    ):
        assert req_site in site_names


def test_wbg_s2_docs_pages_and_internal_links() -> None:
    site_dir = ROOT / "docs" / "wbg-s2-mksf1"
    pages = [
        site_dir / "index.html",
        site_dir / "executive-summary.html",
        site_dir / "forensics-02778.html",
        site_dir / "hypotheses-and-validation.html",
        site_dir / "how-to-submit.html",
    ]
    rc = json.loads((ROOT / "evidence/wbg_s2/run_card.json").read_text())

    for page in pages:
        assert page.is_file(), f"Missing {page}"
        txt = page.read_text()
        assert rc["submission_name"] in txt
        parser = _LinkParser()
        parser.feed(txt)
        for ref in parser.refs:
            parsed = urlparse(ref)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            assert target.is_relative_to((ROOT / "docs").resolve()), f"Escaped docs/: {ref}"
            assert target.is_file(), f"Broken link {ref} in {page.name}"

    assert "wbg-s2-mksf1/index.html" in (ROOT / "docs/index.html").read_text()
    assert rc["artifact"]["tif_sha256"] in (ROOT / "README.md").read_text()
