"""Tests for the nine-site audit: pure-function logic, the shipped audit artifact, and the no-approval guard.

The shipped JSON was produced from pinned GitHub snapshots (see scripts/nine_site_audit.py). These
tests check internal consistency and the exact identities the executive summary relies on. They do
not re-download anything and they never assert a score.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import nine_site_audit as nsa  # noqa: E402

AUDIT = ROOT / "docs" / "data" / "nine_site_audit_20261029.json"


def _toy_catalogue():
    cat = np.zeros((9, 9), dtype=bool)
    cat[4, :] = True  # one horizontal catalogue fault
    return cat, ndimage.distance_transform_edt(~cat)


def test_stats_counts_distance_bins_and_range():
    cat, dist = _toy_catalogue()
    arr = np.zeros((9, 9))
    arr[0, 0] = 1.0   # 4 px from the catalogue row
    arr[3, 0] = 0.5   # 1 px away
    arr[4, 4] = 1.0   # on the catalogue
    arr[8, 8] = 0.0   # zero is not a positive
    sample_finite = np.ones((9, 9), dtype=bool)
    meta = dict(transform=list(nsa.EXPECTED_TRANSFORM))
    st = nsa.stats_for(arr, meta, b"raw", cat, dist, sample_finite)
    assert st["n_positive"] == 3
    assert st["n_positive_on_catalogue"] == 1
    assert st["n_positive_within_1px"] == 2   # the catalogue cell (d=0) and the 1 px cell
    assert st["n_positive_within_3px"] == 2
    assert st["n_outside_0_1"] == 0
    assert st["transform_matches_official"] is True
    assert st["nan_mask_matches_official_sample"] is True


def test_stats_flags_out_of_range_and_footprint_mismatch():
    cat, dist = _toy_catalogue()
    arr = np.zeros((9, 9))
    arr[0, 0] = 1.5
    arr[1, 1] = np.nan
    sample_finite = np.ones((9, 9), dtype=bool)
    st = nsa.stats_for(arr, dict(transform=[0] * 6), b"x", cat, dist, sample_finite)
    assert st["n_outside_0_1"] == 1
    assert st["n_nan"] == 1
    assert st["nan_mask_matches_official_sample"] is False


def test_pairwise_detects_identical_and_subset_sets():
    a = np.zeros((9, 9), dtype=bool)
    a[1, 1] = a[7, 7] = True
    b = a.copy()
    c = a.copy()
    c[0, 8] = True  # superset of a
    rows = {r["a"] + "|" + r["b"]: r for r in nsa.pairwise({"a": a, "b": b, "c": c})}
    assert rows["a|b"]["identical_positive_sets"] is True
    assert rows["a|c"]["identical_positive_sets"] is False
    # a is a subset of c: every dot of a sits at distance 0 from c's positives
    assert rows["a|c"]["frac_a_within_3px_of_b"] == pytest.approx(1.0)
    assert rows["a|c"]["frac_b_within_3px_of_a"] < 1.0  # c has an extra dot at (0, 8)


def test_shipped_audit_has_all_named_files_and_pins():
    data = json.loads(AUDIT.read_text())
    assert data["n_files"] == 11 and len(data["files"]) == 11
    keys = {f["key"] for f in data["files"]}
    assert "GEMSDOE32:h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros" in keys
    for f in data["files"]:
        assert len(f["sha256"]) == 64
        assert f["commit"] and len(f["commit"]) == 40
        assert f["user_reported_label"].startswith("USER-REPORTED")
        assert f["n_outside_0_1"] == 0, f["key"]


def test_shipped_audit_matches_documented_identities():
    data = json.loads(AUDIT.read_text())
    byname = {f["key"]: f for f in data["files"]}
    b2 = byname["GEMSDOE32:h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros"]
    assert b2["sha256"] == "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
    assert b2["n_positive"] == 37654
    assert b2["n_positive_within_2px"] == 0          # B2 removes everything within 200 m
    assert b2["n_positive_on_catalogue"] == 0
    d28 = byname["GEMSDOE25:dotted-h19-5-d2-8-20261002-e56ea318af89-nan"]
    b1 = byname["GEMSDOE31:h27-4-solo-d28-20261004-8acb75e1-nan"]
    assert d28["n_positive"] - b1["n_positive"] == d28["n_positive_within_1px"] == 3891
    assert b1["n_positive"] - b2["n_positive"] == b1["n_positive_within_2px"] == 2545
    pairs = {(p["a"], p["b"]): p for p in data["pairwise"]}
    same = [p for p in data["pairwise"] if p["identical_positive_sets"]]
    assert {frozenset((p["a"].split(":")[0], p["b"].split(":")[0])) for p in same} == {
        frozenset(("GEMSDOE25", "GEMSDOE30")), frozenset(("GEMSDOE28", "GEMSDOE31"))}
    assert len(pairs) == 55


def test_official_sample_footprint_counts():
    """The mirrored sample's finite footprint is the reference for the NaN convention."""
    import rasterio
    with rasterio.open(ROOT / "data" / "bridge" / "sample_submission.tif") as ds:
        a = ds.read(1)
    assert int(np.isfinite(a).sum()) == 5167373
    assert int(np.isnan(a).sum()) == 7111787
    assert int((a == 1).sum()) == 60988  # equals the catalogue's positives: see irregularity 3


def test_no_file_is_marked_approved_for_submission():
    """Never claim organizer approval; the current decision must cite the receipt."""
    text = (ROOT / "AGENTS.md").read_text()
    assert "APPROVED FOR SUBMISSION" not in text
    assert "NOT APPROVED" in text  # historical artifacts remain not approved
    readme = (ROOT / "README.md").read_text()
    assert "SUBMIT NO" in readme  # superseded artifacts keep their no-go notices
    # 31 Oct state: one candidate cleared for the owner's selector, receipt-linked
    card = json.loads((ROOT / "evidence/wbg8/run_card.json").read_text())
    if card["decision"]["ok_to_submit"]:
        assert "WBG-8" in readme and "CLEARED" in readme.upper()
        assert card["decision"]["ok_to_submit"] is True
    else:
        assert "NO FILE IS CLEARED" in readme.upper()


def test_executive_summary_and_homepage_show_the_decision():
    page = (ROOT / "docs" / "executive-summary-20261029.html").read_text()
    assert "SUBMIT: NO" in page and "UNAVAILABLE" in page and "0.2778" in page
    assert "0.4544" in page and "0.3167" in page
    home = (ROOT / "docs" / "index.html").read_text()
    # The homepage headline must match the WBG-8 run-card receipt, both ways.
    card = json.loads((ROOT / "evidence/wbg8/run_card.json").read_text())
    if card["decision"]["ok_to_submit"]:
        assert "SUBMIT: CLEARED" in home
        assert card["submission_name"] in home or "WBG-8" in home
        assert "executive-summary-wbg8-20261031.html" in home
        assert "how-to-submit-wbg8-20261031.html" in home
    else:
        assert "SUBMIT: NO. No file is cleared." in home
    assert "executive-summary-20261029.html" in home
    # 31 Oct pages must exist and carry the required table columns
    exec31 = (ROOT / "docs" / "executive-summary-wbg8-20261031.html").read_text()
    for needle in ("What to download", "estimated score", "0.2778",
                   card["submission_name"], "MODEL-ESTIMATE"):
        assert needle.lower() in exec31.lower(), needle
    how31 = (ROOT / "docs" / "how-to-submit-wbg8-20261031.html").read_text()
    assert "[0, 1]" in how31 or "[0,1]" in how31
    assert card["note"][:40] in how31


def test_bridge_pins_match_local_files_when_present():
    """Pinned hashes in data/bridge/manifest.json must match the local files (skip if absent)."""
    bridge = ROOT / "data" / "bridge"
    pins = {"sample_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
            "labels.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
            "existing_faults.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093"}
    checked = 0
    for name, want in pins.items():
        f = bridge / name
        if f.exists():
            assert hashlib.sha256(f.read_bytes()).hexdigest() == want, name
            checked += 1
    if checked == 0:
        pytest.skip("bridge files not present in this checkout")
    # the two label files are byte-identical in the mirror; the summary tells readers to treat them as one
    if (bridge / "labels.tif").exists() and (bridge / "existing_faults.tif").exists():
        assert (bridge / "labels.tif").read_bytes() == (bridge / "existing_faults.tif").read_bytes()
