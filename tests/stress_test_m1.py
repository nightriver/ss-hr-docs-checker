"""
tests/stress_test_m1.py — Empirical stress test and adversarial harness for Milestone 1
Tests text_utils, file_naming, and image_tools with edge cases, corrupt data, and benchmark images.
"""

import io
import time
import unittest
from PIL import Image, ImageDraw, ImageOps

from text_utils import CYRILLIC_TRANSLIT, transliterate, sanitize_filename
from file_naming import format_candidate_name, generate_attachment_filename
from image_tools import compress_image


class StressTestTransliterationAndNaming(unittest.TestCase):
    def test_ukrainian_alphabet_coverage(self):
        ukr_alphabet_upper = "АБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ"
        ukr_alphabet_lower = "абвгґдеєжзиіїйклмнопрстуфхцчшщьюя"
        
        for char in ukr_alphabet_upper + ukr_alphabet_lower:
            self.assertIn(char, CYRILLIC_TRANSLIT, f"Missing Ukrainian letter: {char}")
            trans = transliterate(char)
            self.assertTrue(trans.isascii(), f"Transliteration of {char} ({trans}) is not ASCII")

    def test_apostrophe_variations(self):
        apostrophes = ["'", "’", "ʼ", "`", "‘"]
        base_names = [
            ("Мар{}ян", "Maryan"),
            ("Лук{}ян", "Lukyan"),
            ("В{}ячеслав", "Vyacheslav"),
            ("Дем{}ян", "Demyan"),
            ("О{}Браєн", "OBrayen"),
        ]
        for ap in apostrophes:
            for template, expected in base_names:
                name = template.format(ap)
                res = transliterate(name)
                self.assertEqual(res, expected, f"Failed for apostrophe '{ap}' in {name}: got {res}, expected {expected}")

    def test_unusual_and_adversarial_names(self):
        test_cases = [
            ("Ґудзь Їжакевич-Євгеній", "Gudz_Yizhakevych_yevheniy"),
            ("Мар'ян-Лук'ян О'Коннор", "Maryan_lukyan_Okonnor"),
            ("   Петро   Олексійович   ", "Petro_Oleksiyovych"),
            ("—Петро— —Іваненко—", "Petro_Ivanenko"),
            ("Алёна Фёдорова", "Alna_Fdorova"), # Russian Ё test
            ("John Smith-Jr.", "John_Smith_jr"),
            ("12345 67890", "12345_67890"),
            ("!!! ???", "Doc_Doc"),
            ("", "Kandydat"),
            ("   ", "Kandydat"),
            (None, "Kandydat"),
            ("ь ь", "Doc_Doc"),
            ("О'Браєн Джон-Пол", "Obrayen_Dzhon_pol"),
            ("Щукар Черепаха", "Shchukar_Cherepakha"),
            ("Юрія Ясенева", "Yuriya_Yaseneva"),
        ]
        
        for pib, expected in test_cases:
            res = format_candidate_name(pib)
            print(f"PIB: '{pib}' -> Formatted: '{res}' (Expected: '{expected}')")

    def test_extreme_file_labels_and_path_traversal(self):
        labels = [
            ("../../Pasport/../secret.txt", "Pasportsecrettxt"),
            ("Витяг з Резерв+", "Vytyah_z_Rezerv"),
            ("Паспорт (стор. 1-2 & 3) #1!", "Pasport_stor_1_2_3_1"),
            ("   ", "Doc"),
            ("<script>alert(1)</script>", "scriptalert1script"),
            ("A" * 300, "A" * 300),
        ]
        for label, expected in labels:
            res = sanitize_filename(label)
            self.assertEqual(res, expected, f"Failed for label '{label}': got '{res}'")

    def test_filename_collisions_and_page_suffixes(self):
        # multiple=False, but total_files > 1 -> should we expect suffix or no suffix?
        fn1 = generate_attachment_filename("Іваненко Петро", "IPN", doc_index=0, total_files_for_doc=2, multiple=False, original_filename="doc1.pdf")
        fn2 = generate_attachment_filename("Іваненко Петро", "IPN", doc_index=1, total_files_for_doc=2, multiple=False, original_filename="doc2.pdf")
        print(f"multiple=False multi-file generation: fn1='{fn1}', fn2='{fn2}'")
        if fn1 == fn2:
            print("WARNING: Filename collision detected when multiple=False and total_files_for_doc > 1!")


class StressTestImageTools(unittest.TestCase):
    def create_test_image(self, width, height, mode="RGB", color=(255, 0, 0), exif_orientation=None):
        img = Image.new(mode, (width, height), color)
        # Add some patterns so compression work is realistic
        draw = ImageDraw.Draw(img)
        draw.line((0, 0, width, height), fill=(0, 255, 0) if mode=="RGB" else 128, width=5)
        draw.rectangle((width//4, height//4, 3*width//4, 3*height//4), fill=(0, 0, 255) if mode=="RGB" else 200)
        
        buf = io.BytesIO()
        exif = None
        if exif_orientation is not None:
            exif = img.getexif()
            exif[0x0112] = exif_orientation
            img.save(buf, format="JPEG", quality=90, exif=exif)
        else:
            fmt = "PNG" if mode in ("RGBA", "LA", "P") else "JPEG"
            img.save(buf, format=fmt, quality=90 if fmt=="JPEG" else None)
        return buf.getvalue()

    def test_exif_orientation_preservation_and_bug_check(self):
        print("\n--- Testing EXIF Auto-Rotation Across Orientations 1-8 ---")
        # Orientation 6: 400x200 image -> when transposed should become 200x400
        for orientation in range(1, 9):
            img_bytes = self.create_test_image(400, 200, mode="RGB", exif_orientation=orientation)
            out_bytes, ext = compress_image(img_bytes, f"exif_{orientation}.jpg", max_dim=2000, target_bytes=2097152)
            
            res_img = Image.open(io.BytesIO(out_bytes))
            print(f"Orientation {orientation}: Orig size {len(img_bytes)} bytes, Out size {len(out_bytes)} bytes, Out dims {res_img.size}")
            
            # For orientation 5, 6, 7, 8, the dimensions (400, 200) should be swapped to (200, 400)
            if orientation in (5, 6, 7, 8):
                if res_img.size != (200, 400):
                    print(f"CRITICAL BUG: EXIF Orientation {orientation} failed to transpose dimensions! Expected (200, 400), got {res_img.size}")

    def test_rgba_and_transparency_flattening(self):
        print("\n--- Testing RGBA / LA / Palette Transparency Flattening ---")
        modes = [
            ("RGBA", (255, 0, 0, 128)),
            ("LA", (128, 64)),
            ("P", 1),
            ("L", 128),
            ("CMYK", (0, 255, 255, 0)),
        ]
        for mode, color in modes:
            img_bytes = self.create_test_image(200, 200, mode=mode, color=color)
            out_bytes, ext = compress_image(img_bytes, f"test_{mode}.png", target_bytes=100) # force re-encode
            res_img = Image.open(io.BytesIO(out_bytes))
            print(f"Mode {mode} -> Output format: {res_img.format}, mode: {res_img.mode}, ext: {ext}")
            self.assertEqual(res_img.mode, "RGB", f"Mode {mode} was not converted to RGB")
            self.assertEqual(ext, "jpg")

    def test_pdf_passthrough(self):
        pdf_header = b"%PDF-1.7 header content..." + b"A" * 1000
        out_bytes, ext = compress_image(pdf_header, "doc.pdf")
        self.assertEqual(out_bytes, pdf_header)
        self.assertEqual(ext, "pdf")

    def test_image_compression_performance_and_metrics(self):
        print("\n--- Performance & Compression Benchmark ---")
        test_sizes = [
            ("Large 5000x4000 RGB", 5000, 4000, "RGB"),
            ("Medium 3000x2000 RGBA", 3000, 2000, "RGBA"),
            ("High-Res Square 4000x4000 RGB", 4000, 4000, "RGB"),
        ]
        
        for name, w, h, mode in test_sizes:
            raw_bytes = self.create_test_image(w, h, mode=mode)
            start_time = time.perf_counter()
            out_bytes, ext = compress_image(raw_bytes, f"{name}.jpg", max_dim=2000, target_bytes=2097152)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            res_img = Image.open(io.BytesIO(out_bytes))
            ratio = (1 - len(out_bytes) / len(raw_bytes)) * 100
            print(f"[{name}] Original: {len(raw_bytes)/1024:.1f} KB ({w}x{h}) -> Compressed: {len(out_bytes)/1024:.1f} KB ({res_img.width}x{res_img.height}) in {elapsed_ms:.1f} ms | Reduction: {ratio:.1f}%")


if __name__ == "__main__":
    unittest.main()
