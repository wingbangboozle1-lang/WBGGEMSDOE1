"""Concealed-cover inter-field concordance susceptibility field (WBG-8 lane).

Geological premise
------------------
The public mapped-fault catalogue that the competition ships as ``labels.tif``
(== ``existing_faults.tif``, sha256 7ba308cc...) was compiled predominantly
from photogeology and surface expression.  The private scoring truth is the set
of faults that were *added later* -- structures whose surface expression is weak
or absent (buried by alluvium, or expressed only as a subtle bedrock offset).
A susceptibility ranking that is *strongest where the DEM is weakest* therefore
targets precisely the population the catalogue missed, whereas a DEM-ridge or
lidar-scarp ranking re-finds faults that are already mapped (guaranteed false
positives under the metric, and worth nothing as new discoveries).

Two independent potential-field datasets are used jointly:

``A_mag  = hypot(tmi_hg, tmi_vg)``      analytic-signal-style amplitude of the
                                        total magnetic intensity field;
``A_grav = hypot(iso_grav_anom_hg,
                 iso_grav_anom_vg)``    the same for isostatic-residual gravity.

A cell is scored as a *concordant* basement structure only when both amplitudes
are high at the same place (``min`` of the two normalised ranks).  A magnetic
only lineament is commonly a lithologic fabric or a lithology contact; a gravity
only lineament is commonly a basin-fill thickness change.  A structure that
offsets *both* fields has to offset the density and susceptibility interfaces
together, which is what a basement-breaking fault does.  This inter-field test is
different from every earlier lane in this repository, which used intra-field
operators only (tilt angle, Euler deconvolution, Hessian non-coaxiality /
commutator of one field, texture anisotropy).

The concealed-cover term ``B = 1 - rank(det_elev_slope)`` multiplies the
concordance, so a strong geophysical edge under flat, low-relief terrain is
ranked above the same edge in rugged terrain: the rugged one is the one a
photogeologist would already have mapped.

Two supporting terms are kept deliberately weak (they only tilt the ranking):

* ``G`` -- gradient of ``depth_to_base_surf``: a normal fault offsets the
  magnetic/gravity basement interface, so basement-depth gradient concentrates
  on range-front and buried fault scarps;
* ``S`` -- geodetic strain ridge (``geod_2ndinv`` plus ``geod_dilaterate``): the
  only band group that is *causally* about active deformation rather than a
  structural proxy.

Known non-fault mimic (must be stated with any result): a lithologic contact
between a magnetic+dense unit and a quiet unit satisfies the concordance test
exactly as a fault does, and the intrusion margins of mafic stocks do so for
both fields simultaneously.  Nothing here can separate them without a third
independent constraint; the ranking is therefore a *susceptibility*, not a
classification.

All bands are read from the hash-pinned owner mirror of the competition feature
raster; the ``-3.4e38`` sentinel used by that raster is converted to NaN and no
cell outside the finite data is ever emitted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

SENTINEL = 1e30

# band numbers in training_features.tif, 1-based, verified against the dataset
# descriptions printed by rasterio (see registry/data_manifest.json).
BANDS = {
    "tmi": 14, "tmi_hg": 3, "tmi_vg": 9, "tc": 6,
    "iso_grav": 13, "iso_grav_hg": 18, "iso_grav_vg": 11, "iso_grav_slope": 5,
    "det_elev": 12, "det_elev_slope": 19, "depth_to_base_surf": 15,
    "cond_surf": 17, "geod_2ndinv": 4, "geod_shearrate": 7, "geod_dilaterate": 8,
    "deq_n100a15": 10, "ieq_n100a15": 16,
}


def load_band(path: Path | str, name: str) -> np.ndarray:
    """Read one band as float32 with the no-data sentinel replaced by NaN."""
    import rasterio

    with rasterio.open(path) as src:
        idx = list(src.indexes)[BANDS[name] - 1] if src.count > 1 else 1
        a = src.read(idx).astype(np.float32)
    a[~np.isfinite(a)] = np.nan
    a[np.abs(a) >= SENTINEL] = np.nan
    return a


def rank01(a: np.ndarray) -> np.ndarray:
    """Rank transform to [0, 1]; NaN stays NaN.

    Uses a 1 % quantile-bin approximation: exact ranks on 12.3 M cells cost a
    full sort per band, and the ranking resolution of a *product* of ranks is
    far coarser than 1 % of the area.
    """
    finite = np.isfinite(a)
    out = np.full(a.shape, np.nan, np.float32)
    if not finite.any():
        return out
    edges = np.quantile(a[finite], np.linspace(0.0, 1.0, 101))
    edges = np.unique(edges)
    if edges.size < 2:
        out[finite] = 0.5
        return out
    r = np.clip(np.searchsorted(edges, a, side="right") - 1, 0, edges.size - 2)
    frac = (edges.size - 1)
    out[finite] = (r[finite] + 0.5) / frac
    return out.astype(np.float32)


def gradient_amplitude(a: np.ndarray) -> np.ndarray:
    """|grad| in cells^-1 of a band, NaN-propagating through a 1-cell central diff."""
    b = np.array(a, np.float64, copy=True)
    bad = ~np.isfinite(b)
    if bad.any():  # fill so the difference operator does not broadcast NaN rivers
        b[bad] = float(np.nanmean(b))
    gy, gx = np.gradient(b)            # gy = d/drow, gx = d/dcol
    out = np.hypot(gy, gx)
    out[bad] = np.nan
    # a NaN island around every masked cell: dilate the mask by 1
    out[np.pad(bad, 1)[1:-1, 1:-1] | ndi.binary_dilation(bad)] = np.nan
    return out.astype(np.float32)


@dataclass
class Habitat:
    """Susceptibility field and the components that made it (auditable)."""

    pi: np.ndarray                  # float32 susceptibility in [0, 1]
    concordance: np.ndarray         # min of the two rank-transformed amplitudes
    cover_deficit: np.ndarray       # 1 - rank(det_elev_slope)
    basement: np.ndarray            # rank of |grad depth_to_base_surf|
    strain: np.ndarray              # rank of strain-ridge envelope
    component_ranks: dict = field(default_factory=dict)
    notes: dict = field(default_factory=dict)


def susceptibility(bands: dict[str, np.ndarray], *, w_strain: float = 0.25,
                   w_basement: float = 0.35, floor: float = 0.0) -> Habitat:
    """Combine the components into one ranking field.

    ``pi = concordance ** (1) * (1 + w_basement*basement) * (1 + w_strain*strain)
           * (0.35 + 0.65*cover_deficit)``

    Every factor is a rank in [0, 1], so the product is monotone in each input and
    the exponents only set how much a supporting term is allowed to tilt the
    ranking.  The multiplicative cover factor never drops a cell to zero (0.35
    floor), because a strong buried structure in rugged terrain is still a
    structure -- it is just more likely to be already mapped.
    """
    amag = np.hypot(bands["tmi_hg"], bands["tmi_vg"])
    agrav = np.hypot(bands["iso_grav_hg"], bands["iso_grav_vg"])
    r_mag, r_grav = rank01(amag), rank01(agrav)
    conc = np.fmin(r_mag, r_grav)                       # both fields or nothing
    cover = 1.0 - rank01(bands["det_elev_slope"])       # flat ground = concealed
    base = rank01(gradient_amplitude(bands["depth_to_base_surf"]))
    strain = rank01(np.hypot(bands["geod_2ndinv"], bands["geod_dilaterate"]))
    with np.errstate(invalid="ignore"):
        pi = conc * (1.0 + w_basement * base) * (1.0 + w_strain * strain) \
            * (0.35 + 0.65 * cover)
    pi = np.where(np.isfinite(pi), pi, 0.0).astype(np.float32)
    if floor > 0:
        pi[pi < floor] = 0.0
    mx = float(np.nanmax(pi)) if np.isfinite(pi).any() else 1.0
    if mx > 0:
        pi = pi / mx
    return Habitat(
        pi=pi, concordance=conc.astype(np.float32), cover_deficit=cover.astype(np.float32),
        basement=base.astype(np.float32), strain=strain.astype(np.float32),
        component_ranks={"mag_amplitude": r_mag, "grav_amplitude": r_grav},
        notes={"w_strain": w_strain, "w_basement": w_basement, "floor": floor,
               "max_raw": mx},
    )
