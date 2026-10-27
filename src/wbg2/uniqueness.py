"""Retired unsafe WBG-2 novelty implementation.

The old code applied a private chance-enrichment exemption and Manhattan
rather than Euclidean 3-pixel distance. Both could falsely approve duplicates.
New and retrospective audits must call the pinned ``gems57.uniqueness``
shared implementation directly, including its literal fail-closed gate.
"""


def _retired(*args, **kwargs):
    raise RuntimeError('Retired unsafe WBG-2 gate; use the pinned gems57.uniqueness shared gate')


compare = _retired
scan_registry = _retired
load_aligned = _retired
