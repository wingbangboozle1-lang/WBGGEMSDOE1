"""The exact marginal-inclusion rule, derived from the metric.

Why this module exists rather than a patch to ``gems.metric``
-------------------------------------------------------------
``src/gems/metric.py`` is a *frozen inherited shared source*: its sha256 is
recorded in ``evidence/parallel_main_integration.json`` and re-asserted by
``tests/test_evidence.py``. Editing it in place would rewrite a past audit
receipt, so the correction is published alongside it instead. The frozen
function is left byte-identical and its divergence is documented and pinned by
``tests/test_marginal_threshold.py``.

The rule
--------
With the organiser's ``DTI = TP_w / (TP_w + a*FP_w + b*FN_w)`` and ``a = 0.2``,
``b = 0.8``, one added dot of value 1 with realised kernel credit ``k`` on a
previously uncovered truth pixel changes

    TP_w -> TP_w + k
    FN_w -> FN_w - k
    FP_w -> FP_w + (1 - k)

so the denominator moves by

    dD = k + a*(1 - k) - b*k = a + k*(1 - a - b) = a

because ``1 - a - b = 0``. The shift is therefore exactly ``a`` for *every* ``k``,
and

    dDTI > 0  <=>  k*D - DTI*a*D > 0  <=>  k > a*DTI.

The frozen fork used ``(a*DTI)/(1 - a*DTI)``, a rational factor that does not
follow from the formula. At DTI 0.2778 the two differ by 0.0033 in ``k`` (about
0.010 px), which is why no recorded result moves -- but the derivation is what
must be trusted, not the coincidence.

The same identity gives the practical placement rule used by this lane: a dot is
worth adding iff it lands within ``R*(1 - a*DTI)`` pixels of a truth pixel, i.e.
``3 * (1 - 0.2*0.28) = 2.83 px`` at DTI 0.28. Coverage of *distinct* truth
pixels is what the metric pays for; ranking alone is not.
"""

from __future__ import annotations

from .metric import ALPHA, BETA

__all__ = [
    "ALPHA",
    "BETA",
    "break_even_kernel_credit",
    "break_even_radius_px",
    "denominator_shift",
    "dot_is_worth_adding",
]


def break_even_kernel_credit(current_dti: float, alpha: float = ALPHA) -> float:
    """Smallest realised kernel credit ``k`` for which one extra dot raises DTI."""
    dti = float(current_dti)
    if not 0.0 <= dti <= 1.0:
        raise ValueError("DTI must be inside [0, 1]")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be inside (0, 1)")
    return alpha * dti


def break_even_radius_px(current_dti: float, alpha: float = ALPHA, radius_px: float = 3.0) -> float:
    """Distance form of :func:`break_even_kernel_credit` for a triangular kernel."""
    k = break_even_kernel_credit(current_dti, alpha)
    return float(radius_px * (1.0 - k))


def denominator_shift(k: float, alpha: float = ALPHA, beta: float = BETA) -> float:
    """Exact change in the metric denominator from one dot with credit ``k``."""
    return float(k + alpha * (1.0 - k) - beta * k)


def dot_is_worth_adding(k: float, current_dti: float, alpha: float = ALPHA) -> bool:
    """Whether one non-redundant dot with realised credit ``k`` improves DTI."""
    return bool(k > break_even_kernel_credit(current_dti, alpha))
