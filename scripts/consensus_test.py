#!/usr/bin/env python3
"""Does agreement with the historical submission consensus predict a better score?

For each of the 118 owner-reported submissions we measure the mean historical
support (number of *other* submissions placing a dot at that cell) under its own
dots, and correlate that with its reported score.  A positive correlation means
the crowd's shared geological guess is better than any individual guess
(consensus is informative); a negative one means the consensus is a rut.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    fetch = json.loads((ROOT / "evidence/scored_raster_fetch.json").read_text())
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as src:
        foot = np.isfinite(src.read(1))
    dots = []
    for rec in fetch["entries"]:
        with rasterio.open(ROOT / rec["local"]) as src:
            a = src.read(1)
        dots.append(np.isfinite(a) & (a > 0) & foot)
    support = np.zeros(foot.shape, np.uint16)
    for d in dots:
        support += d.astype(np.uint16)
    # 3-px dilated support: how much *nearby* consensus a dot has
    near_support = ndi.uniform_filter(support.astype(np.float32), size=7)

    scores = np.array([r["score"] for r in fetch["entries"]], float)
    own = np.array([support[d].mean() for d in dots])
    excl = np.array([((support[d] - 1).clip(0).mean()) for d in dots])
    nb = np.array([near_support[d].mean() for d in dots])
    for label, v in (("mean support (incl. self)", own), ("mean support (excl. self)", excl),
                     ("mean 7x7-dilated support", nb)):
        rho = spearmanr(v, scores)
        r = pearsonr(v, scores)
        print(f"{label:30s} Spearman {rho.statistic:+.3f} (p={rho.pvalue:.2g})  "
              f"Pearson {r.statistic:+.3f} (p={r.pvalue:.2g})")
    out = {"schema": "wbg-consensus-test-v1", "n": int(len(scores)),
           "score_label": "OWNER-REPORTED",
           "spearman_support_excl_self": float(spearmanr(excl, scores).statistic),
           "p_support_excl_self": float(spearmanr(excl, scores).pvalue),
           "spearman_dilated_support": float(spearmanr(nb, scores).statistic),
           "p_dilated_support": float(spearmanr(nb, scores).pvalue)}
    (ROOT / "evidence/consensus_test.json").write_text(json.dumps(out, indent=1))
    np.save(ROOT / ".cache/support_dilated.npy", near_support)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
