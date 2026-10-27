# Source and claim audit — 2026-10-26

This record separates **official scientific provenance** from **the exact bytes used here**. A link is not a receipt, and a GitHub mirror is not converted into an organizer-authenticated source by hashing it.

| Claim/layer | Official source for manual review | Exact local byte evidence | Verification status | Use in TIP1 |
|---|---|---|---|---|
| USGS 3DEP is the stated origin of the 1 m DEM tiles summarized into the LiDAR feature stack | [USGS 3D Elevation Program](https://www.usgs.gov/3d-elevation-program); [3DEP ScienceBase item `4f70aa9fe4b058caae3f8de5`](https://www.sciencebase.gov/catalog/item/4f70aa9fe4b058caae3f8de5) | `data/external/lidar_scarp_features.json`, SHA-256 `9ef0df6e87598a8b0cd52fe821661e5fdb3a00568c5d9b1c5d61fd6b242dcd41`; cached TIFF SHA-256 `d580bb8bdc941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568` | Provenance is asserted by the pinned metadata and can be manually checked at USGS. Raw 1 m tile bytes were not independently redownloaded in this sandbox. | **Yes** — only the derived `step`, curvature, face, cross, coherence, strike and validity bands |
| GeoDAWN public airborne magnetic/radiometric survey | [USGS data release DOI `10.5066/P93LGLVQ`](https://doi.org/10.5066/P93LGLVQ) | Referenced by the template repository's provenance | Official link recorded; not fetched here | No |
| INGENIOUS/OpenEI Great Basin geothermal data | [OpenEI GDR submission 1391, DOI `10.15121/1881483`](https://gdr.openei.org/submissions/1391) | Referenced by template provenance | Official link recorded; not fetched here | No |
| Competition template/grid and evaluator context | [DrivenData DOE GEMS competition](https://www.drivendata.org/competitions/306/competition-doe-gems/) and [official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) | `data/bridge/sample_submission.tif`, SHA-256 `2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc`; EPSG:32611, shape `3730 × 3292`, transform `[100,0,243350,0,-100,4508550]` | Grid bytes came from the pinned owner template mirror, not an authenticated portal download in this session. Reference-solution repository is official/public. | Yes — geometry and writer template |
| Public fault catalogue proxy used by holdout | Template bridge `labels.tif` / `existing_faults.tif` | SHA-256 `7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093` | Bytes pinned. Catalogue provenance is inherited from the template; no organizer-authenticated receipt was available. | Evaluation/masking only; **never a TIP1 prediction input** |
| Historical focus-site rasters | Immutable public GitHub commits listed in `registry/source_registry.json` | 231 sources restored; 179 unique footprint contents; every Git object, available SHA-256, grid and footprint hash checked; zero rejected | Public owner repositories, not official organizer submissions | Comparison only; never prediction input |
| H33-B2 `0.2778` | No receipt supplied | Exact mask SHA and ancestry reproduced in `evidence/h33_b2_forensics.json` | **OWNER-REPORTED / UNVERIFIED**, not ORGANIZER-CONFIRMED | Historical analysis only |

## Data rights and access limitations

The pinned LiDAR metadata states that USGS 3DEP products are available without use restrictions and requests acknowledgement to the U.S. Geological Survey, National Geospatial Program. That rights statement is preserved verbatim in the metadata; legal interpretation is outside this project.

The sandbox's outbound allowlist did not permit direct retrieval from USGS ScienceBase, USGS S3, OpenEI, DOI or DrivenData hosts. Consequently:

1. official links are supplied for manual review;
2. exact experiment bytes are restored from a pinned public GitHub commit and SHA-checked;
3. no claim is made that the mirror is organizer-authenticated;
4. no private leaderboard, submission page, hidden labels or weekly quota were accessed;
5. `0.2778`, `0.3195`, `0.4413` and every other historical live value without an artifact-linked receipt remain unverified.

## USGS acknowledgement

Map services and data available from U.S. Geological Survey, National Geospatial Program. The project transformed only a precomputed 100 m aggregate stack and did not redistribute raw 1 m DEM tiles.

## 2026-10-27 incremental official-source verification

| Claim | Official source checked this session | Result |
|---|---|---|
| Metric α=0.2, β=0.8, 300 m triangular kernel and one float32 GeoTIFF in `[0,1]` | [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric) | Page retrieved; metric and submission-format text match this repository's shared implementation. |
| Up to three submissions/week; single GeoTIFF selected for both rounds; generative-AI disclosure required | [GEMS Prize Official Rules §3.2](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | PDF retrieved; the three-per-week limit is a rule, **not** proof of this account's current remaining allowance. |
| Public leaderboard observation | [DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) | Rank 1 = **0.4544** (xiaofanhu) observed 2026-10-27. Not a project-file score. Prompt values 0.4413 / 0.3195 are stale. |
| Fault stepovers/terminations localize stress and strain relevant to Great Basin hydrothermal systems | [USGS / Siler (2023)](https://www.usgs.gov/publications/structural-discontinuities-and-their-control-hydrothermal-systems-great-basin-usa) | Official abstract supports the TASC physical motivation, **not** the detector's validity. |
| GeoDAWN magnetic/radiometric source (CC0) | [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) | Page retrieved; confirms 3DEP lidar coordination and CC0 release. |
| INGENIOUS resources (CC BY 4.0) | [GDR 1391](https://gdr.openei.org/submissions/1391) | Page retrieved; confirms geodetic, conductance, geophysical and geothermal resources. |
| 3DEP DEM official collection | [ScienceBase `4f70aa9fe4b058caae3f8de5`](https://www.sciencebase.gov/catalog/item/4f70aa9fe4b058caae3f8de5) | Page retrieved; public-domain 1/3″ and 1 m DEM products. Raw tiles not bulk-downloaded in this sandbox. |
| Great Basin 3-D MT conductance slices | [DOI 10.5066/P9TWT2LU](https://doi.org/10.5066/P9TWT2LU) | Official page retrieved; five depth ranges listed. Bulk host outside sandbox allowlist. |
| Sentinel-2 availability | [USGS EROS notice](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-sentinel-2) | USGS archive decommissioned; Copernicus Data Space is the current source. Replaces a dead `landsat-missions/sentinel-2` link inherited in older docs. |

**Dead-link irregularities.** Two inherited official links returned 404 on 2026-10-27:
`https://www.usgs.gov/landsat-missions/sentinel-2` and
`https://www.sciencebase.gov/catalog/item/5fb70a0ad34eb413d5e14873`. They are replaced in the
2026-10-27 ranked-hypotheses document by the USGS EROS notice and DOI 10.5066/P9TWT2LU above.
No claim is made that every line of every linked page or PDF was verified.
