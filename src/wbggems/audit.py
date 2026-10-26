"""Small orchestration utilities; all scoring/format/novelty arithmetic is shared."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dump_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def single_feature_canary(values, truth, *, name, fold):
    """Audit both orientations; missingness is separately checked, not silently dropped."""
    import numpy as np
    from sklearn.metrics import roc_auc_score

    values = np.asarray(values, float)
    truth = np.asarray(truth, bool)
    if values.shape != truth.shape or not truth.any() or truth.all():
        raise ValueError("canary requires aligned positive and negative samples")
    finite = np.isfinite(values) & (np.abs(values) < 1e30)
    missing_auc = roc_auc_score(truth, ~finite) if not finite.all() and finite.any() else 0.5
    if np.unique(truth[finite]).size == 2:
        auc = float(roc_auc_score(truth[finite], values[finite]))
    else:
        auc = 0.5
    orientation_auc = max(auc, 1 - auc, missing_auc, 1 - missing_auc)
    return {"feature": name, "fold": fold, "evidence_class": "HOLDOUT-FEATURE-AUC",
            "positive_pixels": int(truth.sum()), "negative_pixels": int((~truth).sum()),
            "finite_pixels": int(finite.sum()), "raw_signed_auc": auc,
            "missingness_auc": float(missing_auc), "orientation_invariant_auc": float(orientation_auc),
            "threshold": 0.90, "leakage_suspected": bool(orientation_auc > 0.90),
            "interpretation": "AUC is a leakage canary, not a DTI or leaderboard score."}


def promotion_decision(*, format_ok, novelty_ok, canary_ok, paired_ci95,
                       same_instrument_best_beaten, authorized_lane,
                       organizer_slot_receipt, confirmation_passed):
    """A local candidate can reach a separate selector, never consume a real slot."""
    reasons = []
    for passed, reason in (
        (format_ok, "format validation failed"),
        (novelty_ok, "literal registry uniqueness not cleared"),
        (canary_ok, "single-feature leakage canary failed"),
        (bool(paired_ci95 and len(paired_ci95) == 2 and paired_ci95[0] > 0),
         "paired efficacy lower confidence bound is not positive"),
        (same_instrument_best_beaten, "current best not beaten on the identical instrument"),
        (authorized_lane, "no assigned method lane was supplied"),
        (bool(organizer_slot_receipt), "authenticated current weekly allowance unavailable"),
        (confirmation_passed, "untouched confirmation has not passed"),
    ):
        if not passed:
            reasons.append(reason)
    return {"verdict": "negative" if reasons else "promote",
            "ok_to_download": bool(format_ok), "ok_to_submit": False,
            "eligible_for_separate_selector": not reasons,
            "approved_for_weekly_slot": False, "submission_slots_used": 0,
            "reasons": reasons,
            "note": "Promotion only makes a candidate eligible for a separate selector; no uploader exists in this project."}
