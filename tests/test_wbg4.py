"""Tests for WBG-4 (CSJF-1) operators, receipts, GeoTIFF/ZIP integrity, and subsite."""

from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import unquote, urlsplit
import zipfile

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []
        self.ids: set[str] = set()
        self.text: list[str] = []
        self.alts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        d = dict(attrs)
        if d.get("id"):
            self.ids.add(str(d["id"]))
        for k in ("href", "src"):
            if d.get(k):
                self.urls.append(str(d[k]))
        if tag == "img":
            self.alts.append(str(d.get("alt") or ""))

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def test_wbg4_preregistration_and_run_card_governance():
    prereg_path = ROOT / "registry/wbg4_preregistration.json"
    rc_path = ROOT / "evidence/wbg4/run_card.json"
    assert prereg_path.is_file() and rc_path.is_file()

    prereg_sha = hashlib.sha256(prereg_path.read_bytes()).hexdigest()
    rc = json.loads(rc_path.read_text(encoding="utf-8"))
    assert rc["preregistration_sha256"] == prereg_sha
    assert rc["lane_id"] == "WBG-4"
    assert rc["method_code"] == "CSJF-1"
    assert rc["experiments_executed"] == 3
    assert rc["experiments_executed"] <= rc["experiment_budget_max"] == 3
    assert rc["wall_clock_seconds"] <= rc["wall_clock_budget_max_seconds"] == 7200
    assert rc["submission_slots_used"] == 0
    assert rc["leaderboard_estimate"] is None
    assert rc["organizer_confirmed_score"] is None
    assert rc["verdict"] == "negative"
    assert len(rc["submission_metadata"]["portal_note_140char"]) <= 140
    assert len(rc["submission_metadata"]["unique_submission_name"]) <= 140


def test_wbg4_leakage_canary_and_monotone_three_evaluator_results():
    canary = json.loads((ROOT / "evidence/wbg4/leakage_canary.json").read_text(encoding="utf-8"))
    ablation = json.loads((ROOT / "evidence/wbg4/ablation_results.json").read_text(encoding="utf-8"))
    uniq = json.loads((ROOT / "evidence/wbg4/uniqueness_audit.json").read_text(encoding="utf-8"))

    assert canary["n_features_tested"] == 78
    assert canary["all_passed"] is True
    assert canary["max_effective_auc"] <= 0.90
    forbidden = ("dist_known_fault", "existing_fault", "catalogue", "label")
    for row in canary["features"]:
        name_low = row["feature"].lower()
        assert not any(tok in name_low for tok in forbidden), row["feature"]
        assert row["effective_max_auc"] <= 0.90

    p = ablation["primary_segment_holdout"]["arms"]
    assert (
        p["arm1_ctrl_19band_edti35600"]["dti"]
        < p["arm2_dalbp_csjt_78ch_edti35600"]["dti"]
        < p["arm3_csjf_mscp_stack_tworegime35600"]["dti"]
    )
    s20 = ablation["secondary_intrabasin_holdout"]["scores"]
    assert (
        s20["arm1_ctrl_19band_edti35600"]["dti"]
        < s20["arm2_dalbp_csjt_78ch_edti35600"]["dti"]
        < s20["arm3_csjf_mscp_stack_tworegime35600"]["dti"]
    )
    c77 = ablation["untouched_confirmation_holdout"]["scores"]
    assert c77["arm3_csjf_mscp_stack_tworegime35600"]["dti"] > c77["arm1_ctrl_19band_edti35600"]["dti"]

    assert uniq["full_footprint_exact_spearman_no_subsampling"] is True
    assert uniq["pre_placement_surface_gate"]["pass"] is True
    assert uniq["pre_placement_surface_gate"]["max_abs_spearman_full_footprint"] <= 0.90
    assert uniq["final_dots_competing_sparse_diagnostic"]["competing_sparse_pass"] is True
    assert uniq["final_dots_competing_sparse_diagnostic"]["max_forward_3px_overlap"] <= 0.70
    assert uniq["literal_all_entry_gate"]["literal_pass"] is False


def test_wbg4_emitted_geotiff_and_zip_strict_range_and_grid():
    rc = json.loads((ROOT / "evidence/wbg4/run_card.json").read_text(encoding="utf-8"))
    tif_path = ROOT / rc["artifact"]["tif_relpath"]
    zip_path = ROOT / rc["artifact"]["zip_relpath"]
    assert tif_path.is_file() and zip_path.is_file()
    assert hashlib.sha256(tif_path.read_bytes()).hexdigest() == rc["artifact"]["tif_sha256"]
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == rc["artifact"]["zip_sha256"]

    with rasterio.open(tif_path) as ds:
        assert ds.count == 1
        assert ds.dtypes == ("float32",)
        assert str(ds.crs) == "EPSG:32611"
        assert (ds.height, ds.width) == (3730, 3292)
        assert tuple(ds.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        arr = ds.read(1)

    assert np.isfinite(arr).all()
    assert int(np.isnan(arr).sum()) == 0
    assert int(np.isinf(arr).sum()) == 0
    assert float(arr.min()) == 0.0 and float(arr.max()) == 1.0
    assert set(np.unique(arr).tolist()).issubset({0.0, 1.0})
    assert int(np.count_nonzero(arr > 0.0)) == rc["artifact"]["emitted_dots"] == 35135

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert names == [tif_path.name]
        assert hashlib.sha256(zf.read(names[0])).hexdigest() == rc["artifact"]["tif_sha256"]


def test_wbg4_verify_recorded_cli():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_wbg4_lane.py"), "--verify-recorded"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "PASS:" in proc.stdout


def test_wbg4_conjugate_junction_and_two_regime_emitter_unit():
    from wbg4.features import _strike_termination_asymmetry, _structure_tensor_eigs
    from wbg4.model import emit_edti_two_regime

    # Orthogonal crossing lines produce strictly stronger minor eigenvalue sqrt(lam2) than a 1D line
    h, w = 64, 64
    fp = np.ones((h, w), dtype=bool)
    line_only = np.zeros((h, w), dtype=np.float32)
    line_only[32, :] = 1.0
    cross = line_only.copy()
    cross[:, 32] += 1.0

    lam2_line, _, _ = _structure_tensor_eigs(line_only, fp, grad_sigma=1.2, window_sigma=2.4)
    lam2_cross, _, _ = _structure_tensor_eigs(cross, fp, grad_sigma=1.2, window_sigma=2.4)
    assert float(lam2_cross[32, 32]) > 5.0 * float(lam2_line[32, 32] + 1e-6)

    # Strike-termination asymmetry fires at a terminating half-line tip vs interior
    half_line = np.zeros((h, w), dtype=np.float32)
    half_line[32, 8:33] = 1.0
    term = _strike_termination_asymmetry(half_line, fp, half_px=6)
    assert term.shape == (h, w) and np.isfinite(term).all()
    assert float(term[32, 32]) > 2.0 * float(term[32, 20] + 1e-6)

    # Two-regime emitter honors eligibility mask, min separation, and strict {0, 1} values
    rng = np.random.default_rng(42)
    p = rng.uniform(0.05, 0.8, size=(48, 48)).astype(np.float32)
    q = rng.uniform(0.0, 0.3, size=(48, 48)).astype(np.float32)
    b_prior = rng.uniform(0.0, 1.0, size=(48, 48)).astype(np.float32)
    elig = np.ones((48, 48), dtype=bool)
    elig[:6, :] = False
    dots, stats = emit_edti_two_regime(p, q, b_prior, elig, 20, min_separation_px=2.8)
    assert dots.dtype == np.float32
    assert set(np.unique(dots).tolist()).issubset({0.0, 1.0})
    assert int(np.count_nonzero((dots > 0) & (~elig))) == 0
    assert 1 <= stats["emitted_total"] <= 20


@pytest.mark.parametrize(
    "rel",
    ["wbg4/index.html", "wbg4/how-to-submit.html", "wbg4/forensics-and-hypotheses.html"],
)
def test_wbg4_pages_links_copy_and_accessibility(rel: str):
    f = DOCS / rel
    assert f.is_file()
    html = f.read_text(encoding="utf-8")
    p = _PageParser()
    p.feed(html)
    visible = " ".join(p.text)
    low = visible.lower()

    assert "download: yes" in low and "submit: no" in low
    assert "do not submit" in low
    assert "no selector eligibility" in low
    assert "no competition slot" in low
    assert "$" not in visible
    assert "0.2824" not in visible
    assert '<html lang="en">' in html
    assert 'name="viewport"' in html
    assert 'href="#main"' in html
    assert all(len(a) > 20 for a in p.alts)

    for u in p.urls:
        parts = urlsplit(u)
        if parts.scheme or parts.netloc:
            assert "localhost" not in u and "127.0.0.1" not in u
            continue
        target = (f.parent / unquote(parts.path)).resolve() if parts.path else f
        assert target.is_relative_to(ROOT)
        assert target.exists(), (rel, u)
        if parts.fragment and target.suffix == ".html":
            tp = _PageParser()
            tp.feed(target.read_text(encoding="utf-8"))
            assert parts.fragment in tp.ids, (rel, u)
