"""
Tests for scripts/generate_sample_docs.py.
Runs the script into a temp dir so it doesn't pollute sample_docs/ during CI.
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

PROJECT = Path(__file__).resolve().parent.parent
SCRIPT = PROJECT / "scripts" / "generate_sample_docs.py"

EXPECTED_FILES = [
    "prescription_clean.png",
    "bill_clean.png",
    "bill_apollo.png",
    "pharmacy_bill_blurry.png",
    "prescription_wrong_patient.png",
    "dental_bill_mixed.png",
]


@pytest.fixture(scope="module")
def out_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("sample_docs")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(d)],
        capture_output=True, text=True, cwd=str(PROJECT),
    )
    assert result.returncode == 0, result.stderr
    return d


def test_generates_all_six_files(out_dir):
    missing = [f for f in EXPECTED_FILES if not (out_dir / f).exists()]
    assert not missing, f"missing files: {missing}"


def test_all_images_are_800_wide(out_dir):
    for name in EXPECTED_FILES:
        with Image.open(out_dir / name) as img:
            assert img.width == 800, f"{name}: width={img.width}"


def test_all_images_are_rgb(out_dir):
    for name in EXPECTED_FILES:
        with Image.open(out_dir / name) as img:
            assert img.mode == "RGB", f"{name}: mode={img.mode}"


def test_blurry_has_lower_sharpness_than_clean(out_dir):
    """Blurred image should have lower pixel-level variance (less edge detail)."""
    def variance(path):
        arr = np.array(Image.open(path).convert("L"), dtype=float)
        return float(np.var(np.diff(arr, axis=1)))

    blurry = variance(out_dir / "pharmacy_bill_blurry.png")
    clean = variance(out_dir / "bill_clean.png")
    assert blurry < clean, f"blurry variance {blurry:.1f} should be < clean {clean:.1f}"


def test_wrong_patient_doc_is_not_same_as_clean_prescription(out_dir):
    """prescription_wrong_patient must differ from prescription_clean (different name)."""
    a = np.array(Image.open(out_dir / "prescription_clean.png"))
    b = np.array(Image.open(out_dir / "prescription_wrong_patient.png"))
    assert not np.array_equal(a, b), "wrong-patient doc is identical to clean prescription"


def test_script_prints_count(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(tmp_path)],
        capture_output=True, text=True, cwd=str(PROJECT),
    )
    # The reported count must match the number of PNGs actually written (robust to
    # adding more sample docs over time).
    written = len(list(tmp_path.glob("*.png")))
    assert written >= 6, f"expected at least the 6 originals, wrote {written}"
    assert str(written) in result.stdout, f"expected '{written}' in stdout: {result.stdout!r}"
