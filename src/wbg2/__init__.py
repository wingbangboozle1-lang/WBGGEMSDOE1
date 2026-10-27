"""Archived WBG-2 research modules; not an authorized submission pipeline.

The WBG-2 artifact is retained as a research-only download and the lane is
stopped. These legacy helpers are not the authoritative evaluator, writer, or
novelty gate for any new work. Use the pinned shared ``gems57`` tools in
``vendor/gems57`` for any separately authorized lane. The WBG-2 builder is
retired and cannot regenerate pixels or approve a file.

The official competition description and metric source are retained for
manual review at:
https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
"""

__all__ = ["metric", "prior", "uniqueness", "validate", "verification"]
