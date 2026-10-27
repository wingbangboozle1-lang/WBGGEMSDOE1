# Provenance pointer — read the dated records, not a bare file label

This small index is not an official-source manifest. For original agency links, direct-access status, licenses, frozen owner-mirror commits and uncertainty, see [registry/sources.json](../registry/sources.json), [registry/data_manifest.json](../registry/data_manifest.json), [knowledge/source_audit.md](source_audit.md), and [the 2026-10-27 official-page observation](../evidence/official_leaderboard_observation_20261027.json).

- Official task and GeoTIFF/DTI requirements: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Official rules §3.2, §3.4–3.5: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- USGS GeoDAWN release: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- Public leaderboard snapshot 2026-10-27: rank one **0.4544**; *not a score for any file in this project*. https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- Owner-mirror sample template SHA-256 `2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc`; fault catalogue SHA-256 `7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093`; 19-band feature TIFF SHA-256 `4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`. Their GitHub digests prove **mirror integrity**, not organizer-origin authenticity.
- Historical H33-B2 zeros TIFF SHA-256 `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`, OWNER-REPORTED 0.2778 / **not organizer-confirmed**. Its 6,436-dot parent pruning was proven from pixels, not hidden-truth causality.
- Current main research-only WBG-C1 TIFF SHA-256 `8e6f25053116fca1220a9fd9a7a16c081478d79e6ba93ac142ee8c80a111e875`. Byte-distinct but literal overlap STOP, negative HOLDOUT-DTI, **DO NOT SUBMIT**.
- Inherited MVGZ research TIFF SHA-256 `0c2516fa5e5727eab1150750b72c189a454968aba4f9afbc5e2aac84dcc8faba`. Separate negative run with a different evaluator; **DO NOT SUBMIT**. Do not pool its metric with WBG-C1.

Never use a peer prediction as a feature or treat fault map confidence as proof of a geothermal vent.
