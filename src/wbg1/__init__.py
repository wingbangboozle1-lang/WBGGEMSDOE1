"""WBGGEMSDOE1: DOE GEMS Prize (DrivenData #306) fault-discovery research.

Package layout
-------------
metric    pooled distance-tolerant Tversky (DTI) + block-bootstrap CI + projections
holdout   hide-and-recover context (strip folds) + SGMC off-catalogue instrument + canary
features  label-free transforms + geothermal anchors + H1 surface builder
emission  priority Poisson-disk emission + budget helpers
submission writer for zeros/nan pairs + audit JSON + zip
validate  format validator + uniqueness-vs-registry audit
paths     directory resolution (env-overridable)
"""
