"""
tests/test_validators.py — Unit tests for validators.py in HR Docs Checker v2.2
"""

import unittest
from fpdf import FPDF

from validators import (
    RESERVE_PLUS_MARKERS,
    ValidationResult,
    extract_text_from_pdf,
    validate_mime_type,
    validate_reserve_plus_pdf,
)


def create_pdf_bytes(text: str = "") -> bytes:
    """
    Helper to generate valid PDF byte stream in memory using fpdf2.
    """
    pdf = FPDF()
    pdf.add_page()
    if text:
        import os
        font_path = "C:/Windows/Fonts/arial.ttf"
        if os.path.exists(font_path):
            pdf.add_font("Arial", "", font_path)
            pdf.set_font("Arial", size=12)
        else:
            pdf.set_font("Helvetica", size=12)
        pdf.cell(200, 10, text=text, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


class TestValidationResult(unittest.TestCase):
    def test_default_instantiation(self):
        res = ValidationResult(ok=True)
        self.assertTrue(res.ok)
        self.assertFalse(res.blocking)
        self.assertIsNone(res.reason)

    def test_blocking_error_instantiation(self):
        res = ValidationResult(ok=False, blocking=True, reason="Error message")
        self.assertFalse(res.ok)
        self.assertTrue(res.blocking)
        self.assertEqual(res.reason, "Error message")


class TestValidateMimeType(unittest.TestCase):
    def test_valid_pdf_bytes(self):
        pdf_bytes = create_pdf_bytes("Test PDF")
        res = validate_mime_type(pdf_bytes, "doc.pdf", ["pdf"])
        self.assertTrue(res.ok)
        self.assertFalse(res.blocking)
        self.assertIsNone(res.reason)

    def test_valid_jpeg_bytes(self):
        jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 100
        res = validate_mime_type(jpeg_bytes, "photo.jpg", ["jpg", "jpeg"])
        self.assertTrue(res.ok)
        self.assertFalse(res.blocking)
        self.assertIsNone(res.reason)

    def test_valid_png_bytes(self):
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        res = validate_mime_type(png_bytes, "scan.png", ["png"])
        self.assertTrue(res.ok)
        self.assertFalse(res.blocking)
        self.assertIsNone(res.reason)

    def test_extension_not_allowed(self):
        pdf_bytes = create_pdf_bytes("Test PDF")
        res = validate_mime_type(pdf_bytes, "doc.exe", ["pdf"])
        self.assertFalse(res.ok)
        self.assertTrue(res.blocking)
        self.assertIn("Формат .exe не підтримується", res.reason)

    def test_magic_byte_extension_mismatch(self):
        # PNG magic bytes renamed to .pdf when allowed is ['pdf']
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        res = validate_mime_type(png_bytes, "spoofed.pdf", ["pdf"])
        self.assertFalse(res.ok)
        self.assertTrue(res.blocking)
        self.assertIn("не відповідає дозволеному типу", res.reason)

    def test_undetected_magic_bytes(self):
        garbage_bytes = b"RANDOM_TEXT_FILE_BYTES_NOT_IMAGE_OR_PDF"
        res = validate_mime_type(garbage_bytes, "file.pdf", ["pdf"])
        self.assertFalse(res.ok)
        self.assertTrue(res.blocking)
        self.assertIn("Нерозпізнаний або пошкоджений вміст", res.reason)

    def test_empty_bytes(self):
        res = validate_mime_type(b"", "file.pdf", ["pdf"])
        self.assertFalse(res.ok)
        self.assertTrue(res.blocking)
        self.assertEqual(res.reason, "Файл порожній.")


class TestExtractTextFromPdf(unittest.TestCase):
    def test_extract_text_valid(self):
        pdf_bytes = create_pdf_bytes("Hello World Sample Text")
        text = extract_text_from_pdf(pdf_bytes)
        self.assertIn("Hello World Sample Text", text)

    def test_extract_text_empty_pdf(self):
        pdf_bytes = create_pdf_bytes("")
        text = extract_text_from_pdf(pdf_bytes)
        self.assertEqual(text, "")

    def test_extract_text_corrupt_bytes(self):
        text = extract_text_from_pdf(b"INVALID PDF BYTES")
        self.assertEqual(text, "")

    def test_extract_text_empty_input(self):
        text = extract_text_from_pdf(b"")
        self.assertEqual(text, "")


class TestValidateReservePlusPdf(unittest.TestCase):
    def test_reserve_plus_full_matches(self):
        sample_text = (
            "Extract from " + RESERVE_PLUS_MARKERS[0] + ". " +
            RESERVE_PLUS_MARKERS[1] + ". " +
            RESERVE_PLUS_MARKERS[2] + ": 1234567890"
        )
        pdf_bytes = create_pdf_bytes(sample_text)
        res = validate_reserve_plus_pdf(pdf_bytes)
        self.assertTrue(res.ok)
        self.assertFalse(res.blocking)
        self.assertIsNone(res.reason)

    def test_reserve_plus_low_hits_warning(self):
        sample_text = "Some document header. " + RESERVE_PLUS_MARKERS[3] + " 2026-01-01"
        pdf_bytes = create_pdf_bytes(sample_text)
        res = validate_reserve_plus_pdf(pdf_bytes)
        self.assertTrue(res.ok)
        self.assertFalse(res.blocking)
        self.assertEqual(res.reason, "⚠️ Потребує ручної перевірки (мало збігів з очікуваним форматом)")

    def test_reserve_plus_empty_text_blocking(self):
        pdf_bytes = create_pdf_bytes("")
        res = validate_reserve_plus_pdf(pdf_bytes)
        self.assertFalse(res.ok)
        self.assertTrue(res.blocking)
        self.assertIn("не містить текстового шару", res.reason)

    def test_reserve_plus_corrupt_file_blocking(self):
        res = validate_reserve_plus_pdf(b"GARBAGE BYTES")
        self.assertFalse(res.ok)
        self.assertTrue(res.blocking)


if __name__ == "__main__":
    unittest.main()
