"""Quarantined legacy uniqueness API.

The old private scan silently skipped files, ignored transforms and overrode the
literal overlap gate with a chance-enrichment exemption. It must not be used to
make decisions. The frozen implementation is retained only as audit text in
``research/history/wbg2_20261027/``. Use the pinned shared
``gems57.uniqueness`` implementation with a hash-verified complete registry.
"""


def _disabled(*args, **kwargs):
    raise RuntimeError("Legacy WBG-2 uniqueness is disabled; use the pinned shared gems57.uniqueness gate.")


load_aligned = _disabled
compare = _disabled
scan_registry = _disabled
