"""The stopped synthetic lane must not regenerate or overwrite evidence."""
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_focus9_generator_stops_before_writing():
    paths = [
        ROOT / "docs/downloads/wbggemsdoe1-focus9-exec-20261027-unique-36k-zeros.tif",
        ROOT / "docs/downloads/wbggemsdoe1-focus9-exec-20261027-unique-36k-zeros.zip",
        ROOT / "evidence/focus9_exec/run_card.json",
    ]
    before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/generate_focus9_unique_tif.py")],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert "STOP" in result.stderr and "do not submit" in result.stderr
    assert before == [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
