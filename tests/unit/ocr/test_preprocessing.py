"""Tests for image preprocessing (fast — no OCR engine involved).

We test the TRANSFORMATION, not the engine: output exists, is truly
grayscale, small images get upscaled, and the config knob is live.
The with/without OCR measurement lives in decision #016, not here —
tests pin behavior; the decision log records judgment.
"""

from pathlib import Path

import pytest
from PIL import Image

from mediscan.config import settings
from mediscan.ocr.preprocessing import prepare_image

FIXTURES = Path("tests/fixtures/files")


def test_output_is_a_new_grayscale_file(tmp_path):
    result = prepare_image(FIXTURES / "report_photo.png", tmp_path)

    assert result.exists()
    assert result.name.startswith("prep_")
    assert result.parent == tmp_path
    # Pillow reports an image's mode: "L" means single-channel grayscale
    assert Image.open(result).mode == "L"
    # audit-trail rule: the ORIGINAL is untouched (still RGB)
    assert Image.open(FIXTURES / "report_photo.png").mode == "RGB"


def test_small_images_are_doubled(tmp_path):
    small = tmp_path / "small.png"
    Image.new("L", (200, 100), color=255).save(small)

    result = prepare_image(small, tmp_path)

    width, height = Image.open(result).size
    assert (width, height) == (400, 200)  # 200 < 1000 -> doubled


def test_upscale_threshold_is_read_from_config(tmp_path, monkeypatch):
    # With the knob lowered below the image width, no upscaling happens —
    # proving the threshold is live config, not a decorative number.
    monkeypatch.setattr(settings, "preprocess_min_width", 50)
    small = tmp_path / "small.png"
    Image.new("L", (200, 100), color=255).save(small)

    result = prepare_image(small, tmp_path)

    assert Image.open(result).size == (200, 100)  # untouched


def test_corrupt_image_raises_corrupt_document_error(tmp_path):
    # Hardening (audit): a file with valid PNG magic bytes but a
    # truncated body must fail as OUR error, not a raw Pillow error.
    from mediscan.ocr.exceptions import CorruptDocumentError

    broken = tmp_path / "broken.png"
    broken.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00\x01\x02")  # header only
    with pytest.raises(CorruptDocumentError):
        prepare_image(broken, tmp_path)
