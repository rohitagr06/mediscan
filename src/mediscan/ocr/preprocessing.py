"""Image cleanup before OCR.

WHY THIS FILE EXISTS
    OCR accuracy depends heavily on input quality. Real phone photos of
    reports are dim, low-contrast and small — a "dusty window". This
    module wipes the window: grayscale, contrast stretch, and upscaling
    of small images, each one Pillow call.

MEASURED, NOT ASSUMED
    PaddleOCR does some internal cleanup already, so this step must
    justify itself with numbers. Decision #016: on a degraded photo,
    confidence rose from 0.829 to 0.911 with this cleanup applied.
"""

from pathlib import Path

from PIL import Image, ImageOps

from mediscan.config import settings
from mediscan.ocr.exceptions import CorruptDocumentError

# A tiny file can decode into a gigapixel "pixel bomb" and exhaust
# memory. Cap decoded size well above any real report scan (40M px).
Image.MAX_IMAGE_PIXELS = 40_000_000


def prepare_image(source: Path, workdir: Path) -> Path:
    """Clean an image for OCR and save the result as a NEW file.

    The original is never modified (audit-trail habit: inputs are
    evidence). The cleaned copy is written into `workdir`, which the
    caller controls — in the real pipeline that is a SecureUploadDir,
    so cleanup of the copy stays guaranteed.

    PHI note: the cleaned file is named prep_<source.name>, so `source`
    is expected to be an already-de-identified stored upload (a
    SecureUploadDir gives it a UUID name). Never pass a raw patient
    filename here — that would write PHI into the temp filename.

    Returns the path of the cleaned image.
    """
    try:
        image = Image.open(source)
        image.load()  # force full decode NOW so bombs/corruption fail here
    except Exception as err:
        raise CorruptDocumentError(
            f"could not open image for preprocessing ({type(err).__name__})"
        ) from err

    # 1. Grayscale: "L" = single-channel gray, one brightness per pixel.
    image = image.convert("L")

    # 2. Contrast stretch: text separates from paper.
    image = ImageOps.autocontrast(image)

    # 3. Upscale small images so letters keep their shapes (config knob).
    if image.width < settings.preprocess_min_width:
        image = image.resize((image.width * 2, image.height * 2))

    destination = workdir / f"prep_{source.name}"
    image.save(destination)
    return destination
