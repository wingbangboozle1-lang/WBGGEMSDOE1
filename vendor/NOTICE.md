# Shared-template provenance and rights notice

`gems57/*.py` and `template57/prepare_data.py` are reused **byte-for-byte** from the owner project's
shared template at:

- Repository: https://github.com/buffedlizard55-lab/57GEMSDOE
- Commit: `822a0ce5546c7b6749cdd82eb145b6b3e616603d`
- Existing reuse/pin manifest inspected at:
  https://github.com/buffedlizard55-lab/GEMSDOE31/blob/776bf4668a8c10631908c9bba9443a8f11ce5036/registry/shared_template.json
- The 24 source-file SHA-256 pins and their upstream paths are in `registry/shared_template.json`.
- `evidence/template_integrity.json` independently records all local matches.
- The unchanged shared evaluator is `gems57-pooled-hide-v2`. It is **owner code**, not an official
  organizer evaluator or evidence of organizer acceptance.
- The template's cache builder is called unchanged; all nineteen cache hashes are compared to its
  expected list. Raw rasters and caches are ignored by Git.

The user expressly requested reuse of this template. No new upstream license or organizer-origin
authenticity is asserted by this notice. Upstream code/data rights must be verified for any
competition asset package or redistribution; the official rules' external-data/license terms still
apply. A hash is an integrity check, not a license grant. USGS/GDR source links and their stated
licenses are tracked separately in `registry/sources.json`.

The upstream regression test copied into `tests/test_template_evaluator.py` is unchanged from
`tests/test_evaluate_holdout.py` at the template commit (SHA-256
`2e354c977536dcf85dd6230420c1ca2ffec525f7068941e1206736b73061cf68`). Its imports are supplied by the
project's test path configuration; no private evaluator implementation is substituted.
