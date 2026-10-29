"""Consistency checks for the 2026-10-29 per-fold leakage receipt and nine-site summary."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECHECK = ROOT / "evidence/per_fold_recheck_blind_adjacency.json"
SUMMARY = ROOT / "docs/data/focus9_summary_20261029.json"


def test_archived_value_reproduces_run_card():
    card = json.loads(RECHECK.read_text())
    arch = card["archived_full_catalogue"]
    assert abs(arch["pooled_dti"] - arch["original_run_card_value"]) < 1e-9
    assert arch["n_withheld_positives"] == 60161


def test_sum_of_fold_counts_reproduces_shared_pooling():
    card = json.loads(RECHECK.read_text())
    assert abs(card["sum_check_pooled_from_fold_counts_on_archived"]
               - card["archived_full_catalogue"]["pooled_dti"]) < 1e-9


def test_per_fold_pooling_and_verdict():
    card = json.loads(RECHECK.read_text())
    folds = card["per_fold_visible_only"]["folds"]
    assert sum(f["n_withheld_positives"] for f in folds) == card["per_fold_visible_only"]["n_withheld_positives"]
    tp = sum(f["tp"] for f in folds)
    fp = sum(f["fp"] for f in folds)
    fn = sum(f["fn"] for f in folds)
    pooled = tp / (tp + 0.2 * fp + 0.8 * fn + 1e-12)
    assert abs(pooled - card["per_fold_visible_only"]["pooled_dti"]) < 1e-6
    assert card["verdict"].startswith("NEGATIVE")
    assert card["submission_slots_used"] == 0


def test_leakage_canary_below_threshold():
    canary = json.loads(RECHECK.read_text())["leakage_canary"]
    assert canary["threshold"] == 0.90
    assert canary["status"] == "PASS"


def test_summary_says_no_file_cleared():
    summary = json.loads(SUMMARY.read_text())
    assert summary["headline"]["ok_to_submit_any_file"] == "NO"
    focus = [r for r in summary["rows"] if r["site"].startswith("GEMSDOE")]
    assert len(focus) == 9
    assert all(r["decision"] == "DO NOT SUBMIT" for r in focus)
    assert all(r["unique_vs_other_focus_sites"] is False for r in focus)
