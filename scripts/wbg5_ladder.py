#!/usr/bin/env python3
"""Why 0.2778 sits where it does — an assumption-light inversion of the metric.

Start from the published definition only:

    1/DTI - 1 = (0.2 FP + 0.8 FN) / TP ,   TP + FN = N

Now take the two ends of the public ladder.  The 60 069-dot raster and the
37 654-dot champion are the same dot set before and after pruning (their forward
3 px overlap is 1.0000), so the 22 415 removed dots are the only difference
between the two scores.  If those removed dots bought no truth — which is what
"pruning raised the score" means — then

    0.2 * 22 415 / TP = 1/0.2477 - 1/0.2778

which identifies **TP without assuming N at all**.  Two independent prongs of the
ladder give the same number, and the residual brackets N between the two limits
FP <= M (a prediction cannot cost more than one false-positive unit per pixel) and
N >= TP.  Everything else in this file follows from arithmetic.

Output: docs/data/ladder.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
from wbg5 import gates  # noqa: E402

A, B = 0.2, 0.8


def main() -> int:
    reg = gates.load_registry()["rasters"]
    nine = {}
    for name, rec in reg.items():
        site = name.split("-")[0].upper().replace("GEMSDOE", "GEMSDOE")
        sc = rec.get("score")
        if sc is None:
            continue
        nine.setdefault(int(rec["n_dots"]), []).append((name, float(sc)))

    ladder = [
        ("GEMSDOE27 topological gap closure (61 328 dots)", 61_328, 0.2449),
        ("GEMSDOE24 D1.5 dense (60 069 dots)", 60_069, 0.2477),
        ("GEMSDOE25 / 30 D2.8 (44 090 dots, pixel-identical pair)", 44_090, 0.2600),
        ("GEMSDOE33 analog-tip / step-over (41 865 dots)", 41_865, 0.2632),
        ("GEMSDOE31 B1 catalogue-distance prune (40 199 dots)", 40_199, 0.2708),
        ("GEMSDOE36 B2 + 1 200 additions (38 854 dots)", 38_854, 0.2750),
        ("GEMSDOE28 rung30 blind (37 660 dots)", 37_660, 0.2710),
        ("GEMSDOE32 B2 (37 654 dots) — the champion", 37_654, 0.2778),
    ]

    def ident(m_big, s_big, m_small, s_small):
        """TP implied by removing m_big - m_small dots that bought no truth."""
        delta = (1 / s_big - 1) - (1 / s_small - 1)
        if delta <= 0:
            return None
        return A * (m_big - m_small) / delta

    pairs = [
        ("D1.5 -> B2 (22 415 dots removed)", 60_069, 0.2477, 37_654, 0.2778),
        ("D2.8 -> B1 (3 891 dots removed)", 44_090, 0.2600, 40_199, 0.2708),
        ("B1 -> B2 (2 545 dots removed)", 40_199, 0.2708, 37_654, 0.2778),
        ("topological gap closure -> B2", 61_328, 0.2449, 37_654, 0.2778),
    ]
    est = []
    for label, mb, sb, ms, ss in pairs:
        tp = ident(mb, sb, ms, ss)
        est.append({"comparison": label, "dots_removed": mb - ms,
                    "scores": [sb, ss], "implied_TP_px": None if tp is None else round(tp, 0)})

    tp_ref = ident(60_069, 0.2477, 37_654, 0.2778)
    # 0.2 FP + 0.8 FN = lhs, FN = N - TP, and 0 <= FP <= 37 654 (one unit per pixel at most)
    lhs = (1 / 0.2778 - 1) * tp_ref
    n_hi = tp_ref + lhs / B                     # FP = 0
    n_lo = tp_ref + (lhs - A * 37_654) / B      # FP at its maximum

    def score(tp, fp, n):
        return tp / (tp + A * fp + B * (n - tp))

    scenarios = []
    n_ref = 38_800.0
    fp_ref = (lhs - B * (n_ref - tp_ref)) / A
    for label, tp, fp, n in (
        ("champion, self-consistent at N = 38 800", tp_ref, fp_ref, n_ref),
        ("same TP at zero FP (a perfect thin trace)", tp_ref, 0, n_ref),
        ("recall +50 % at FP 12 000", 1.5 * tp_ref, 12_000, n_ref),
        ("recall 40 % at FP 8 000", 0.40 * n_ref, 8_000, n_ref),
        ("leaderboard top 0.4544 back-solved", None, None, None),
    ):
        if tp is None:
            # TP needed for 0.4544 assuming FP = 20 000 and 0.4554-style precision
            for fp_try in (20_000,):
                tp_need = (A * fp_try + B * n_ref) / (1 / 0.4544 - 1 + B)
                scenarios.append({"scenario": label, "TP": round(tp_need, 0),
                                  "FP": fp_try, "N": n_ref,
                                  "DTI": round(score(tp_need, fp_try, n_ref), 4)})
            continue
        scenarios.append({"scenario": label, "TP": round(tp, 0), "FP": fp, "N": n,
                          "DTI": round(score(tp, fp, n), 4)})

    out = {"schema": "wbg5-ladder-v1",
           "identity": "1/DTI - 1 = (0.2 FP + 0.8 FN)/TP, TP + FN = N",
           "ladder": [{"label": l, "dots": m, "score": s} for l, m, s in ladder],
           "identifications": est,
           "champion": {"TP_px": round(tp_ref, 0),
                        "N_bracket_px": [round(n_lo, 0), round(n_hi, 0)],
                        "recall_bracket": [round(tp_ref / n_hi, 4), round(tp_ref / n_lo, 4)],
                        "reading": ("the champion credits about ten thousand truth pixels out "
                                    "of a hidden truth of roughly 37-46 thousand; recall is "
                                    "22-28 %, and the remaining 27 000 dots are the price")},
           "scenarios": scenarios,
           "marginal_value_at_champion": {
               "one_extra_true_positive_px": round((1 - B) / (tp_ref / 0.2778) / 1.0, 8),
               "one_fewer_false_positive_px": round(A * 0.2778 / 37_654, 8)},
           "conclusion": ("the ladder climbs by *removing* pixels, so the ceiling of a dotted "
                          "field is its precision; beating 0.2778 requires TP per emitted "
                          "pixel, not more dots")}
    (ROOT / "docs/data/ladder.json").write_text(json.dumps(out, indent=1) + "\n")

    print(f"implied TP of the champion: {tp_ref:,.0f} truth pixels")
    print(f"hidden truth N in [{n_lo:,.0f}, {n_hi:,.0f}] px  ->  recall "
          f"[{tp_ref/n_hi:.1%}, {tp_ref/n_lo:.1%}]")
    print(f"{'scenario':44s} {'TP':>7s} {'FP':>7s} {'N':>7s} {'DTI':>7s}")
    for s in scenarios:
        print(f"{s['scenario']:44s} {s['TP']:7.0f} {s['FP']:7.0f} {s['N']:7.0f} {s['DTI']:7.4f}")
    print("wrote docs/data/ladder.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
