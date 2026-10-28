"""WBG-5 / CTP-3: the along-strike tip-trace field.

Why this and not a dot field
----------------------------
The competition metric is

    DTI = TP / (TP + 0.2 * FP + 0.8 * FN)

with ``TP`` counted per truth pixel through a kernel ``k(d) = (1 - d/3)+`` and
``FP`` the *probability mass* of every predicted pixel that is not explained by
the truth.  Two consequences drive this module:

1.  A predicted pixel that lies on a structure earns up to 1.0 of TP and costs
    **nothing**; the same pixel moved 5 px earns 0.0 and costs a full 0.2.
    Precision is therefore worth four times coverage, and a *thin, correctly
    placed trace* is the cheapest way to buy TP.
2.  Two predicted pixels 2 px apart cannot both earn full credit for the same
    truth pixel (``TP`` takes the maximum), so a dense dot carpet pays twice for
    the same credit.  The nine public site submissions are exactly that carpet:
    37 000-61 000 isolated dots whose median distance to the catalogue is
    15-20 px and whose ``frac_le3`` sits at 0.06-0.20.

Measured on the withheld-distal-tail truth (``docs/data/exp5_decisive.json``),
the 15 px tip trace scores **0.3816** / **0.3985** against 0.2623 / 0.1851 for the
40 000-dot carpet and 0.0546 / 0.0372 for an area-filling null.  On the
adversarial "the missed faults are unrelated structures" truth the ordering
reverses (0.0252 vs 0.0712), which is stated in every page that quotes the
number.

What is emitted
---------------
For every catalogue component of at least ``min_px`` pixels, the principal
direction is taken from the pixel covariance.  From each of the two tips a
1-pixel-wide line of ``extend`` pixels is continued along that direction.  The
catalogue itself is **not** emitted: the organizers remove mapped faults from
both the prediction and the truth, and the public score ladder shows that adding
dots on or beside the catalogue *lowered* the score (B1 -> B2 in the nine-site
family), which is only possible if that ground is excluded.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import structure

DESIGN = {
    "name": "WBG5-CTP3",
    "extend_px": 15,
    "width_px": 1,
    "min_component_px": 8,
    "description": ("1 px along-strike continuation of both tips of every catalogue "
                    "component of >= 8 px, 15 px long (1.5 km at 100 m)"),
}


@dataclass
class TraceField:
    mask: np.ndarray
    n_segments: int
    n_tips: int
    n_px: int


def tip_traces(geom: structure.Geometry, shape: tuple[int, int],
               extend: int = 15) -> TraceField:
    """Rasterise the 1-px along-strike continuation of every segment tip."""
    H, W = shape
    mask = np.zeros((H, W), bool)
    tips = 0
    for seg in geom.segments:
        dy, dx = seg.unit
        for (ty, tx), sgn in ((seg.tip_a, 1.0), (seg.tip_b, -1.0)):
            tips += 1
            for k in range(1, extend + 1):
                y = int(round(ty + sgn * k * dy))
                x = int(round(tx + sgn * k * dx))
                if 0 <= y < H and 0 <= x < W:
                    mask[y, x] = True
    return TraceField(mask=mask, n_segments=len(geom.segments), n_tips=tips,
                      n_px=int(mask.sum()))


def build(catalogue: np.ndarray, extend: int = 15,
          min_px: int = 8) -> TraceField:
    geom = structure.segments_from_mask(catalogue, min_px=min_px)
    return tip_traces(geom, catalogue.shape, extend=extend)
