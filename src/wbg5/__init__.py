"""WBG-5 — annular structural-emission lane.

Modules
-------
sources      official provenance pins for the independent evidence rasters
structure    catalogue geometry: components, tips, strike, tip/step-over corridors
evidence     independent terrain & potential-field evidence fields (coverage aware)
emission     minimal-mass, isolated-dot emitter with min-separation selection
holdout      hide-and-recover evaluator (component folds, official DTI)
fsm          fleet-wide score model fitted to 60 labelled public rasters
gates        uniqueness gates (exact / forward-3px / surface) + lattice degeneracy
"""

__all__ = ["structure", "evidence", "emission", "holdout", "fsm", "gates", "sources"]
