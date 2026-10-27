"""WBG-2: metric-first geothermal fault forecasting.

This package implements the competition metric exactly as published by the
organizers, plus the analysis and submission tooling built on top of it.

Provenance of the metric equations:
  https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
  (section "Performance metric" -> "Mathematical representation")

Nothing in this package invents a score. Every number is labelled either
HOLDOUT-DTI (locally measured) or ORGANIZER-REPORTED (a value published by a
third party, not a receipt) or MODEL-ESTIMATE (a projection that is not a score).
"""

__all__ = ["metric", "calibration", "forensics"]
