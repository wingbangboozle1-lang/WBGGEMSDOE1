# Source and claim audit — 2026-10-26

**Update 2026-10-27:** The official [GeoDAWN USGS release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [competition problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [GDR INGENIOUS listing](https://gdr.openei.org/submissions/1391), [NLR official rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) and [public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) were directly retrieved through the web page reader. See `evidence/official_leaderboard_observation_20261027.json` (public top 0.4544; no file receipt). The raw 19-band organizer download and the original K/Th/U/1 m DEM bytes were **not** independently retrieved; all restored training bytes remain owner mirrors. Statements below saying "not fetched here" describe the **frozen 2026-10-26 TIP1 session**, not the 27 October page-level review.


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
