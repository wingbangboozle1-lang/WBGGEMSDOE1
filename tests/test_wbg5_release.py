"""The release verifier is the machine inspector: if it fails, nothing is submittable.

These tests prove the gate is real rather than decorative by re-running the
verifier on the shipped bytes and by tampering with a copy of the receipts to
confirm the verifier refuses.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts" / "verify_wbg5_release.py"


def run(script, cwd=ROOT):
    return subprocess.run(
        [sys.executable, str(script), "--quiet"],
        cwd=cwd, capture_output=True, text=True, timeout=900,
    )


@pytest.mark.skipif(not (ROOT / "docs" / "downloads" / "wbg5-manifest.json").exists(),
                    reason="WBG-5 release not present")
def test_shipped_release_passes_all_gates():
    proc = run(VERIFIER)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "SUBMITTABLE" in proc.stdout


@pytest.mark.skipif(not (ROOT / "docs" / "downloads" / "wbg5-manifest.json").exists(),
                    reason="WBG-5 release not present")
def test_verifier_refuses_a_tampered_decision(tmp_path):
    """Flip one recorded gate to false and the verifier must stop the release."""
    for rel in ("scripts", "src", "vendor", "evidence", "docs", "data"):
        target = tmp_path / rel
        if target.exists():
            continue
        src = ROOT / rel
        if src.is_dir():
            shutil.copytree(src, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    dec = tmp_path / "evidence" / "wbg5" / "decision.json"
    payload = json.loads(dec.read_text())
    payload["gates"]["competitor_uniqueness"] = False
    dec.write_text(json.dumps(payload))

    proc = subprocess.run(
        [sys.executable, str(tmp_path / "scripts" / "verify_wbg5_release.py"), "--quiet"],
        cwd=tmp_path, capture_output=True, text=True, timeout=900,
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "NOT SUBMITTABLE" in proc.stdout


@pytest.mark.skipif(not (ROOT / "docs" / "downloads" / "wbg5-manifest.json").exists(),
                    reason="WBG-5 release not present")
def test_note_and_name_are_submission_ready():
    man = json.loads((ROOT / "docs" / "downloads" / "wbg5-manifest.json").read_text())
    assert man["submission_name"] == "wbg5-satcov-morph-20261028"
    assert 0 < len(man["note"]) <= 140
    assert man["ok_to_submit"] is True
    assert man["ok_to_download"] is True
