#!/usr/bin/env python3
"""Align the WBG-8 run card with the shared validator's governance fields.

Idempotent: recomputes decision flags from the recorded gates + uniqueness
receipts. No raster is rebuilt; no slot is spent; nothing is uploaded.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    p = ROOT / "evidence/wbg8/run_card.json"
    card = json.loads(p.read_text())
    u = json.loads((ROOT / "evidence/wbg8/uniqueness.json").read_text())
    gates = card["decision"]["gates"]
    unique_ok = (u["passes_spearman_gate"] and u["passes_literal_nonlattice_gate"]
                 and u["passes_same_budget_gate"])
    ok = bool(gates["format_hard"] and gates["leakage_canary"] and unique_ok)
    card["decision"].update({
        "verdict": "promote" if ok else "negative",
        "approved_for_weekly_slot": ok,
        "user_decision_required": (
            "Score for this file is a MODEL-ESTIMATE, never organizer-confirmed. "
            "Spending a weekly DrivenData slot is the owner's call; the file is "
            "pre-cleared for format, range, canary and uniqueness so a submit "
            "attempt cannot fail on the '[0,1]' portal error. "
            "approved_for_weekly_slot marks readiness for the selector step "
            "within the weekly cap shown on the submission page; this "
            "repository never uploads anything itself."),
    })
    card["registry"] = {
        "passes_literal_uniqueness": bool(unique_ok),
        "evaluation": ("non-degenerate rasters (n<100k) literal direction + "
                       "same-budget class (n<=45k) both directions + "
                       "|Spearman|<=0.90; dense-field forced overlap reported "
                       "separately per AGENTS.md defect ii"),
        "max_literal_mine_on_theirs_nonlattice": u["max_literal_mine_on_theirs"],
        "max_literal_same_budget": u["max_literal_same_budget"],
        "max_reverse_same_budget": u["max_reverse_same_budget"],
        "max_abs_spearman": u["max_abs_spearman"],
    }
    card["verdict"] = "promote" if ok else "negative"
    card["note"] = card["note"][:140]
    card["session_budget"] = {
        "session_date": "2026-10-31",
        "experiments_used": 2,
        "experiments_max": 3,
        "detail": ("E1 blind multi-layer placement (coverage 0.721, estimate 0.0696) "
                   "archived as archive_E1_*; E2 coverage-stratified re-placement "
                   "(this card) with corrected protocol-faithful registry gates; "
                   "one deterministic re-derivation of E2 receipts (identical dots). "
                   "Wall time < 2 h. submission_slots_used = 0."),
        "wall_hours_max": 2,
    }
    p.write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    print("patched run card; verdict =", card["verdict"], "unique_ok =", unique_ok)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
