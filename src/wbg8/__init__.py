"""WBG-8 lane: concealed-cover inter-field concordance habitat + registry-calibrated
DTI estimator.

This package contains only the pieces that are new relative to the inherited lanes:

* :mod:`wbg8.habitat`  - the geological susceptibility field (a ranking, never a score);
* :mod:`wbg8.estimator` - the exact one-parameter registry-inversion estimator of a
  submission's DTI, using the linearity of ``TP_w`` in the truth indicator;
* :mod:`wbg8.emit`     - thin wrappers that call the *shared* ``gems57`` allocator so no
  private emission fork exists.
"""

from __future__ import annotations
