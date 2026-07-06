"""Image cleanup before OCR.

WHY THIS FILE EXISTS
    OCR accuracy depends heavily on input quality. Real phone photos of
    reports are dim, low-contrast and small — a "dusty window". This
    module wipes the window: grayscale, contrast stretch, and upscaling
    of small images, each one Pillow call.

MEASURED, NOT ASSUMED
    PaddleOCR does some internal cleanup already, so this step must
    justify itself with numbers. See docs/04-decision-log.md #016 for
    the with/without measurement that decided its fate.
"""

from pathlib import Path

from PIL import Image, ImageOps

from mediscan.config import settings


def prepare_image(source: Path, workdir: Path) -> Path:
    """Clean an image for OCR and save the result as a NEW file.

    The original is never modified (audit-trail habit: inputs are
    evidence). The cleaned copy is written into `workdir`, which the
    caller controls — in the real pipeline that is a SecureUploadDir,
    so cleanup of the copy stays guaranteed.

    Returns the path of the cleaned image.
    """
    image = Image.open(source)

    # 1. Grayscale: "L" is Pillow's name for single-channel gray
    #    (one brightness number per pixel instead of three color numbers).
    image = image.convert("L")

    # 2. Contrast stretch: darkest pixel becomes black, lightest becomes
    #    white, everything between spreads out — text separates from paper.
    image = ImageOps.autocontrast(image)

    # 3. Upscale small images: double the size until letters have enough
    #    pixels to keep their shapes. Threshold from config (a judgment).
    if image.width < settings.preprocess_min_width:
        image = image.resize((image.width * 2, image.height * 2))

    destination = workdir / f"prep_{source.name}"
    image.save(destination)
    return destination
