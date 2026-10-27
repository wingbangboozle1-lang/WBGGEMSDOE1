"""Fail-closed checks for the WBG-D1 radiometric alteration lane artifacts."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio

from gems57.grid import SHAPE, TRANSFORM

ROOT = Path(__file__).resolve().parents[1]
CARD_PATH = ROOT / "registry/run_card_wbg_d1.json"
TEMPLATE = ROOT / "data/bridge/sample_submission.tif"


@pytest.fixture(scope="module")
def card():
    return json.loads(CARD_PATH.read_text())


def test_run_card_governance(card):
    assert card["verdict"] == "negative"
    assert card["ok_to_download"] is True
    assert card["ok_to_submit"] is False
    assert card["submission_slots_used"] == 0
    assert card["experiments_completed"] == 3
    assert card["canary"]["leakage_suspected"] is False
    assert card["canary"]["maximum_orientation_invariant_auc"] <= 0.90
    # efficacy gate honestly recorded as not established
    ci = card["holdout"]["paired_ci95"]
    assert ci[0] <= 0.0 <= ci[1]
    assert card["holdout"]["withheld_positive_pixels"] == 11330
    assert card["holdout"]["evaluator_version"] == "gems57-pooled-hide-v2"
    assert len(card["submission_note"]) <= 140 and len(card["submission_name"]) <= 140


def test_shipped_tif_matches_portal_contract(card):
    tif = ROOT / card["artifact"]
    assert tif.exists()
    with rasterio.open(tif) as ds:
        assert ds.count == 1
        assert ds.dtypes == ("float32",)
        assert (ds.height, ds.width) == SHAPE
        assert ds.crs.to_epsg() == 32611
        assert tuple(ds.transform)[:6] == tuple(TRANSFORM)[:6]
        assert ds.nodata is None
        a = ds.read(1)
    assert np.isfinite(a).all()
    assert a.min() >= 0.0 and a.max() <= 1.0
    assert int((a > 0).sum()) == 37654
    # zero outside the footprint and on the mapped catalogue
    with rasterio.open(TEMPLATE) as ds:
        fp = np.isfinite(ds.read(1))
    with rasterio.open(ROOT / "data/bridge/labels.tif") as ds:
        cat = ds.read(1) > 0
    assert not (a[~fp] > 0).any()
    assert not (a[cat & fp] > 0).any()


def test_zip_contains_exactly_the_same_tif(card):
    tif = ROOT / card["artifact"]
    zip_path = ROOT / card["zip_artifact"]
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as z:
        assert z.namelist() == [tif.name]
        assert z.read(tif.name) == tif.read_bytes()


def test_geological_peer_uniqueness_but_literal_stop(card):
    reg = card["registry"]
    # real geological dot-field priors clear the binding 0.70 / 0.90 gates
    assert reg["geological_peer_worst_forward_overlap"] <= 0.70
    assert (reg["dots_worst_spearman"] or 0.0) <= 0.90
    assert reg["byte_unique"] and reg["pixel_unique"]
    # the literal gate still fires via the synthetic lattice / dense surface
    assert reg["dotfield_worst_forward_overlap"] > 0.70
    assert any("lattice" in c["submission"].lower() for c in card["synthetic_lattice_controls"])
