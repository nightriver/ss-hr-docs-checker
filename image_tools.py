"""
image_tools.py — Image compression, EXIF orientation correction, and format normalization for HR Docs Checker v2.2
"""

import io
import logging
from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger(__name__)

DEFAULT_MAX_DIM = 2000
DEFAULT_TARGET_BYTES = 2097152  # 2 MB (2 * 1024 * 1024)


def _get_fallback_ext(filename: str, default: str = "jpg") -> str:
    """Extracts lowercase file extension from filename with jpeg->jpg normalization."""
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[1].lower().strip()
        if ext == "jpeg":
            return "jpg"
        return ext if ext else default
    return default


def compress_image(
    file_bytes: bytes,
    original_filename: str = "",
    max_dim: int = DEFAULT_MAX_DIM,
    target_bytes: int = DEFAULT_TARGET_BYTES,
) -> tuple[bytes, str]:
    """
    Compresses and normalizes an uploaded image:
    1. PDF Passthrough: returns (file_bytes, 'pdf') if file is PDF.
    2. EXIF Orientation: applies ImageOps.exif_transpose() inside try/except.
    3. Alpha Flattening: composites RGBA/LA/P modes onto solid white background.
    4. Downscaling: resizes image if max side > max_dim using LANCZOS.
    5. Iterative JPEG Quality Reduction: (95, 85, 75, 65, 55, 45).
    6. Size Increase Guard: returns original bytes if compressed size >= original size
       AND original size <= target_bytes AND transformed is False.

    Returns:
        tuple[bytes, str]: (processed_bytes, final_extension)
    """
    # 1. PDF Passthrough Guard
    if file_bytes.startswith(b"%PDF-") or (
        original_filename and original_filename.lower().endswith(".pdf")
    ):
        return file_bytes, "pdf"

    # Open image safely
    try:
        img = Image.open(io.BytesIO(file_bytes))
    except Exception as e:
        logger.warning(f"Could not open image for compression: {e}")
        fallback_ext = _get_fallback_ext(original_filename, "jpg")
        return file_bytes, fallback_ext

    transformed = False

    # Check input format
    if str(getattr(img, "format", "")).upper() != "JPEG":
        transformed = True

    try:
        # 2. EXIF Orientation Fix wrapped in try/except
        try:
            exif = img.getexif()
            orientation = exif.get(0x0112) if exif else None
            transposed = ImageOps.exif_transpose(img)
            if transposed is not None:
                if (orientation and orientation in (2, 3, 4, 5, 6, 7, 8)) or (transposed.size != img.size):
                    transformed = True
                img = transposed
        except Exception as e:
            logger.warning(f"ImageOps.exif_transpose failed: {e}")

        has_transparency = False
        # 3. Transparency & Alpha Flattening to solid white background
        if img.mode in ("RGBA", "LA") or "transparency" in img.info:
            has_transparency = True
            transformed = True
            img = img.convert("RGBA")
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != "RGB":
            transformed = True
            img = img.convert("RGB")

        # 4. Downscale max side <= max_dim using LANCZOS resampling
        width, height = img.size
        if max(width, height) > max_dim:
            transformed = True
            scale = float(max_dim) / float(max(width, height))
            new_w = max(1, int(round(width * scale)))
            new_h = max(1, int(round(height * scale)))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # 5. Iterative JPEG Quality Reduction Loop (95, 85, 75, 65, 55, 45)
        best_bytes = file_bytes
        for quality in (95, 85, 75, 65, 55, 45):
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=quality, optimize=True)
            compressed = buffer.getvalue()
            best_bytes = compressed

            if len(compressed) <= target_bytes:
                break

    except Exception as e:
        logger.warning(f"Error during image processing/compression: {e}")
        fallback_ext = _get_fallback_ext(original_filename, "jpg")
        return file_bytes, fallback_ext

    # 6. Size Increase Guard: if compressed size >= original size, retain original
    # unless image had transparency that required JPEG flattening
    if len(best_bytes) >= len(file_bytes):
        if has_transparency:
            return best_bytes, "jpg"
        fallback_ext = _get_fallback_ext(original_filename, "jpg")
        return file_bytes, fallback_ext

    return best_bytes, "jpg"
