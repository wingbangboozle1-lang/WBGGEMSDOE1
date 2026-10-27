"""Fail-closed selector gate for experimental prediction rasters.

Format validity and uniqueness are necessary but not sufficient. A raster is not
cleared for a live slot unless a comparable, paired holdout efficacy result beats
the same-instrument control and a separate selector authorization is recorded.
"""
from __future__ import annotations

from collections.abc import Mapping


def submission_eligibility(gates: Mapping[str, object]) -> bool:
    """Return True only when every scientific and governance gate is explicit.

    Required truthy fields:
      * format_valid
      * focus_site_uniqueness_pass
      * comparable_holdout_dti_available
      * beats_current_holdout_best
      * authorized_slot_selector_record
    Missing or false fields fail closed.
    """
    required = (
        "format_valid",
        "focus_site_uniqueness_pass",
        "comparable_holdout_dti_available",
        "beats_current_holdout_best",
        "authorized_slot_selector_record",
    )
    return all(gates.get(key) is True for key in required)
