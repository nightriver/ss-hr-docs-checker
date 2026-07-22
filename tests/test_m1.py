"""
tests/test_m1.py — Comprehensive unit tests for Milestone 1 modules
(text_utils, file_naming, image_tools)
"""

import io
import unittest
from PIL import Image

from text_utils import CYRILLIC_TRANSLIT, transliterate, sanitize_filename
from file_naming import format_candidate_name, generate_attachment_filename
from image_tools import compress_image


class TestTextUtils(unittest.TestCase):
    def test_cyrillic_translit_dict(self):
        self.assertEqual(CYRILLIC_TRANSLIT['И'], 'Y')
        self.assertEqual(CYRILLIC_TRANSLIT['І'], 'I')
        self.assertEqual(CYRILLIC_TRANSLIT['Ї'], 'Yi')
        self.assertEqual(CYRILLIC_TRANSLIT['Є'], 'Ye')
        self.assertEqual(CYRILLIC_TRANSLIT['Ґ'], 'G')
        self.assertEqual(CYRILLIC_TRANSLIT['Г'], 'H')
        self.assertEqual(CYRILLIC_TRANSLIT["'"], '')
        self.assertEqual(CYRILLIC_TRANSLIT["’"], '')
        self.assertEqual(CYRILLIC_TRANSLIT['Ё'], 'Yo')
        self.assertEqual(CYRILLIC_TRANSLIT['ё'], 'yo')

    def test_transliterate_ukrainian_names(self):
        self.assertEqual(transliterate("Іваненко Петро"), "Ivanenko Petro")
        self.assertEqual(transliterate("Їжакевич Євген"), "Yizhakevych Yevhen")
        self.assertEqual(transliterate("Ґудзь Ганна"), "Gudz Hanna")
        self.assertEqual(transliterate("Мар'ян Лук’ян"), "Maryan Lukyan")
        self.assertEqual(transliterate("Пилип"), "Pylyp")
        self.assertEqual(transliterate("Алёна Фёдорова"), "Alyona Fyodorova")

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename("Pasport (копія #1)"), "Pasport_kopiya_1")
        self.assertEqual(sanitize_filename("  Іваненко   Петро  "), "Ivanenko_Petro")
        self.assertEqual(sanitize_filename("!!!"), "Doc")
        self.assertEqual(sanitize_filename(""), "Doc")
        self.assertEqual(sanitize_filename(None), "Doc")


class TestFileNaming(unittest.TestCase):
    def test_format_candidate_name(self):
        self.assertEqual(format_candidate_name("Іваненко Петро Олексійович"), "Ivanenko_Petro")
        self.assertEqual(format_candidate_name("петренко ганна"), "Petrenko_Hanna")
        self.assertEqual(format_candidate_name("Шевченко"), "Shevchenko")
        self.assertEqual(format_candidate_name("Мар'ян Лук'яненко"), "Maryan_Lukyanenko")
        self.assertEqual(format_candidate_name(""), "Kandydat")
        self.assertEqual(format_candidate_name(None), "Kandydat")

    def test_format_candidate_name_compound(self):
        self.assertEqual(format_candidate_name("Гулак-Артемовський Петро"), "Hulak_Artemovskyy_Petro")
        self.assertEqual(format_candidate_name("Hulak-Artemovskyi"), "Hulak_Artemovskyi")
        self.assertEqual(format_candidate_name("петров-водкін михайло"), "Petrov_Vodkin_Mykhaylo")

    def test_generate_attachment_filename_single(self):
        # Single file, multiple=False
        res = generate_attachment_filename(
            pib="Іваненко Петро",
            file_label="IPN",
            doc_index=0,
            total_files_for_doc=1,
            multiple=False,
            original_filename="scan.pdf",
        )
        self.assertEqual(res, "Ivanenko_Petro_IPN.pdf")

    def test_generate_attachment_filename_multiple_single_upload(self):
        # Single file uploaded for a doc marked multiple=True -> NO page suffix
        res = generate_attachment_filename(
            pib="Іваненко Петро",
            file_label="Pasport",
            doc_index=0,
            total_files_for_doc=1,
            multiple=True,
            original_filename="scan.jpg",
        )
        self.assertEqual(res, "Ivanenko_Petro_Pasport.jpg")

    def test_generate_attachment_filename_multiple_multi_upload(self):
        # 2 files uploaded for a doc marked multiple=True -> page suffix _p1, _p2
        res1 = generate_attachment_filename(
            pib="Іваненко Петро",
            file_label="Pasport",
            doc_index=0,
            total_files_for_doc=2,
            multiple=True,
            original_filename="scan1.jpg",
        )
        self.assertEqual(res1, "Ivanenko_Petro_Pasport_p1.jpg")

        res2 = generate_attachment_filename(
            pib="Іваненко Петро",
            file_label="Pasport",
            doc_index=1,
            total_files_for_doc=2,
            multiple=True,
            original_filename="scan2.JPEG",
        )
        self.assertEqual(res2, "Ivanenko_Petro_Pasport_p2.jpg")

    def test_generate_attachment_filename_non_multiple_multi_file(self):
        # total_files_for_doc > 1 with multiple=False -> page suffix still applied
        res1 = generate_attachment_filename(
            pib="Іваненко Петро",
            file_label="IPN",
            doc_index=0,
            total_files_for_doc=2,
            multiple=False,
            original_filename="scan1.pdf",
        )
        self.assertEqual(res1, "Ivanenko_Petro_IPN_p1.pdf")

        res2 = generate_attachment_filename(
            pib="Іваненко Петро",
            file_label="IPN",
            doc_index=1,
            total_files_for_doc=2,
            multiple=False,
            original_filename="scan2.pdf",
        )
        self.assertEqual(res2, "Ivanenko_Petro_IPN_p2.pdf")

    def test_extension_normalization(self):
        res = generate_attachment_filename(
            pib="Сидоренко Олексій",
            file_label="Dovidka",
            doc_index=0,
            total_files_for_doc=1,
            multiple=False,
            original_filename="file.JPEG",
        )
        self.assertEqual(res, "Sydorenko_Oleksiy_Dovidka.jpg")

        res_conv = generate_attachment_filename(
            pib="Сидоренко Олексій",
            file_label="Dovidka",
            doc_index=0,
            total_files_for_doc=1,
            multiple=False,
            original_filename="file.png",
            converted_ext="jpeg",
        )
        self.assertEqual(res_conv, "Sydorenko_Oleksiy_Dovidka.jpg")


class TestImageTools(unittest.TestCase):
    def test_pdf_passthrough(self):
        pdf_bytes = b"%PDF-1.4 fake pdf content..."
        out_bytes, ext = compress_image(pdf_bytes, "test_doc.pdf")
        self.assertEqual(out_bytes, pdf_bytes)
        self.assertEqual(ext, "pdf")

    def test_rgba_image_compression(self):
        # Create RGBA image with transparent background
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        out_bytes, ext = compress_image(png_bytes, "sample.png")
        self.assertEqual(ext, "jpg")
        # Verify result is valid JPEG image
        out_img = Image.open(io.BytesIO(out_bytes))
        self.assertEqual(out_img.format, "JPEG")
        self.assertEqual(out_img.mode, "RGB")

    def test_large_image_resizing(self):
        # Create 3000x2000 RGB image
        img = Image.new("RGB", (3000, 2000), (0, 128, 255))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        raw_bytes = buf.getvalue()

        out_bytes, ext = compress_image(raw_bytes, "large.jpg", max_dim=2000)
        self.assertEqual(ext, "jpg")
        out_img = Image.open(io.BytesIO(out_bytes))
        width, height = out_img.size
        self.assertLessEqual(max(width, height), 2000)
        self.assertEqual(width, 2000)
        self.assertEqual(height, 1333)

    def test_exif_transpose_size_increase_guard(self):
        img = Image.new("RGB", (100, 40))
        buf = io.BytesIO()
        exif = img.getexif()
        exif[0x0112] = 6  # Rotate 90 CW -> should become (40, 100)
        img.save(buf, format="JPEG", quality=30, exif=exif)
        jpeg_bytes = buf.getvalue()

        out_bytes, ext = compress_image(jpeg_bytes, "photo.jpg")
        self.assertEqual(ext, "jpg")
        res_img = Image.open(io.BytesIO(out_bytes))
        self.assertEqual(res_img.size, (40, 100))

    def test_unreadable_bytes_fallback(self):
        garbage = b"not an image"
        out_bytes, ext = compress_image(garbage, "invalid.png")
        self.assertEqual(out_bytes, garbage)
        self.assertEqual(ext, "png")


if __name__ == "__main__":
    unittest.main()
