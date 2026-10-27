"""Quarantined legacy WBG-2 validator.

The former private validator did not verify the complete affine transform and
could treat NaN outside an inferred footprint as valid. Use the shared
``scripts/validate_submission.py`` exact-file validator instead. A format pass
alone never authorizes an upload. Historical code is retained as non-executable
audit text under ``research/history/wbg2_20261027/``.
"""


def _disabled(*args, **kwargs):
    raise RuntimeError("Legacy WBG-2 validator is disabled; use scripts/validate_submission.py.")


validate_tif = _disabled
validate_zip = _disabled
