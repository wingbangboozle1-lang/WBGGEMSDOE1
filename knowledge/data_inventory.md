# Data inventory (auditable; verify every row)

Grid for all competition rasters: 3730 x 3292, EPSG:32611, 100 m cells,
origin (243350 E, 4508550 N). Hashes = restored bytes in THIS repo
(`registry/data_manifest.json`), cross-checked against sibling pins.

## Competition files (login-walled official; github-mirror hash-verified here)

| File | sha256 (restored bytes) | bytes | Official source |
|---|---|---|---|
| training_features.tif (19 x float32, nodata -3.4e38) | 4371c82e3b8339b8… | 418,912,844 | https://www.drivendata.org/competitions/306/competition-doe-gems/data/ |
| labels.tif (int8, nodata -1; 60,988 positives) | 7ba308ccdc4418b3… | 425,830 | same data tab |
| existing_faults.tif (byte-identical to labels.tif) | 7ba308ccdc4418b3… | 425,830 | Dropbox mirror in task statement |
| sample_submission.tif (float32, NaN nodata; footprint 5,167,373 px) | 2176d08e485aa2cd… | 1,599,597 | same data tab |

Mirror provenance (integrity-pinned, NOT organizer-authenticated):
- 19-band stack: https://github.com/buffedlizard55-lab/GEMSDOE `data/bridge/` (5 parts)
- labels/sample/externals: https://github.com/buffedlizard55-lab/GEMSDOE24 `data/bridge/`, `data/external/`

## 19 bands (from GeoTIFF tags, verified in-repo)

mag_anom, rtp, tmi_hg, geod_2ndinv, iso_grav_anom_slope, tc, geod_shearrate,
geod_dilaterate, tmi_vg, deq_n100a15, iso_grav_anom_vg, det_elev, iso_grav_anom,
tmi, depth_to_base_surf, ieq_n100a15, cond_surf, iso_grav_anom_hg, det_elev_slope.

## External layers (free, official provenance)

| File | content | Official root |
|---|---|---|
| lidar_scarp_features_u8.tif (12 bands, 36 MB) | 1 m-derived scarp/relief/coherence/strike | USGS 3DEP (706 of 716 tiles per owner receipt) |
| geodawn_rad_u8.tif (K/Th/U/TC) | airborne radiometrics | USGS GeoDAWN DOI 10.5066/P93LGLVQ |
| geodawn_extensions_u8.tif (ThK/UK/UTh/TMI_up150) | ratios + upcont TMI | same DOI |
| derived_sgmc_faults_100m_u8.tif (83,593 px; 62,122 off-catalogue) | SGMC fault raster | USGS SGMC via owner derivation |
| gdr_wellspring_in_footprint.csv (27,092 rows) | INGENIOUS springs + temps | GDR https://gdr.openei.org/submissions/1391 |
| gdr_volcanic_vents_in_footprint.csv (21 rows) | vents | same GDR submission |
| gdr_qfaults_traces.csv | Quaternary fault traces | USGS QFaults via GDR |
| 2m_temperature_probe_INGENIOUS_regional_data.zip | shallow-T survey | INGENIOUS via GDR |
| paleo_geothermal_regional.zip | paleo-geothermal sites | INGENIOUS via GDR |

## Reference solution / docs

- Reference U-Net: https://github.com/drivendataorg/gems-prize-reference-solution
- Leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- Problem: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- About/resources: https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/
- Competition PDF: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- CRS: https://epsg.io/32611 ; Tversky: https://en.wikipedia.org/wiki/Tversky_index
- GeoDAWN release: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- INGENIOUS: https://gbcge.org/current-projects/ingenious/

## Irregularities / verification limits (flagged, not hidden)

1. drivendata.org is unreachable from this sandbox (egress allowlist); the
   leaderboard top (prompt says 0.4413/0.3195 in different places; a sibling
   read 0.4437 on 2026-10-26; our last pinned snapshot top is 0.3262 from
   2026-10-04) is UNVERIFIED here. All submission scores are OWNER-REPORTED.
2. No organizer receipt ties any score to exact raster bytes anywhere in the
   fleet; byte-identity (e.g. G30 == G25) is proven, score attribution is not.
3. Dropbox links in the task statement are unreachable from this sandbox;
   competition bytes arrive via the hash-pinned github mirrors above.
