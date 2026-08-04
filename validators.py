"""
validators.py — Stream-level validation and text extraction routines for HR Docs Checker v2.2.

Provides:
- ValidationResult dataclass
- validate_mime_type: Magic byte and filename extension verification
- extract_text_from_pdf: Defensive pypdf plain text extraction
- validate_reserve_plus_pdf: Reserve+ / Oberig PDF extract marker verification
"""

from dataclasses import dataclass
import io
import logging
import re
from typing import Optional

import pypdf

logger = logging.getLogger(__name__)

RESERVE_PLUS_MARKERS: list[str] = [
    "Єдиного державного реєстру призовників",
    "військовозобов'язаних та резервістів",
    "РНОКПП",
    "Сформовано:",
    "ТЦК та СП",
]


@dataclass
class ValidationResult:
    """
    Represents outcome of document stream validation.

    Attributes:
        ok: True if file meets validation requirements.
        blocking: True if upload must be rejected and blocked.
        reason: Ukrainian message for error display or non-blocking warning note.
    """
    ok: bool
    blocking: bool = False
    reason: Optional[str] = None


def validate_mime_type(
    file_bytes: bytes,
    filename: str,
    allowed_exts: list[str],
) -> ValidationResult:
    """
    Validates binary file bytes against magic byte signatures and allowed extensions.

    :param file_bytes: Raw binary bytes of uploaded file
    :param filename: Filename including extension
    :param allowed_exts: Allowed extension strings (e.g. ['pdf', 'jpg', 'png'])
    :return: ValidationResult instance
    """
    if not file_bytes or len(file_bytes) == 0:
        return ValidationResult(ok=False, blocking=True, reason="Файл порожній.")

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    norm_allowed = [e.lower() for e in allowed_exts]
    if "jpeg" in norm_allowed and "jpg" not in norm_allowed:
        norm_allowed.append("jpg")
    if "jpg" in norm_allowed and "jpeg" not in norm_allowed:
        norm_allowed.append("jpeg")

    if ext and ext not in norm_allowed:
        display_allowed = ", ".join(sorted(list(set(allowed_exts))))
        return ValidationResult(
            ok=False,
            blocking=True,
            reason=f"Формат .{ext} не підтримується. Дозволені формати: {display_allowed}.",
        )

    # Magic byte inspection
    detected_type: Optional[str] = None
    if file_bytes.startswith(b"\xff\xd8\xff"):
        detected_type = "jpg"
    elif file_bytes.startswith(b"\x89PNG"):
        detected_type = "png"
    elif file_bytes.lstrip().startswith(b"%PDF-"):
        detected_type = "pdf"

    if detected_type is None:
        return ValidationResult(
            ok=False,
            blocking=True,
            reason="Нерозпізнаний або пошкоджений вміст файлу.",
        )

    is_allowed = False
    if detected_type == "jpg" and ("jpg" in norm_allowed or "jpeg" in norm_allowed):
        is_allowed = True
    elif detected_type in norm_allowed:
        is_allowed = True

    if not is_allowed:
        return ValidationResult(
            ok=False,
            blocking=True,
            reason=f"Вміст файлу ({detected_type.upper()}) не відповідає дозволеному типу.",
        )

    return ValidationResult(ok=True, blocking=False, reason=None)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Defensively extracts plain text content from a PDF byte stream using pypdf.

    :param file_bytes: PDF file byte array
    :return: Extracted text joined with newlines, or empty string on error / empty text
    """
    if not file_bytes:
        return ""

    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as err:
                logger.warning("PDF decryption failed: %s", type(err).__name__)
                return ""

        text_parts: list[str] = []
        for page in reader.pages:
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            except Exception as page_err:
                logger.warning("Failed to extract text from PDF page: %s", type(page_err).__name__)

        return "\n".join(text_parts).strip()
    except Exception as err:
        logger.warning("Failed to parse PDF stream: %s", type(err).__name__)
        return ""


def validate_reserve_plus_pdf(file_bytes: bytes) -> ValidationResult:
    """
    Validates Reserve+ / Oberig extract PDF document stream.

    - Non-PDF / corrupt -> blocking error
    - Empty text layer -> blocking error (scanned image or photo inside PDF)
    - Valid text layer & >= 2 markers -> ok=True, blocking=False, reason=None
    - Valid text layer & < 2 markers -> ok=True, blocking=False, non-blocking warning reason
    """
    mime_res = validate_mime_type(file_bytes, "reserve_plus.pdf", ["pdf"])
    if not mime_res.ok:
        return mime_res

    text = extract_text_from_pdf(file_bytes)
    if not text or not text.strip():
        return ValidationResult(
            ok=False,
            blocking=True,
            reason=(
                "Файл не містить текстового шару — схоже на скан або фото екрана. "
                "Будь ласка, завантажте PDF, вивантажений напряму з застосунку."
            ),
        )

    text_norm = re.sub(r"[’ʼ`‘]", "'", text)
    hits = sum(1 for marker in RESERVE_PLUS_MARKERS if marker in text_norm)

    if hits >= 2:
        return ValidationResult(ok=True, blocking=False, reason=None)

    return ValidationResult(
        ok=True,
        blocking=False,
        reason="⚠️ Потребує ручної перевірки (мало збігів з очікуваним форматом)",
    )
