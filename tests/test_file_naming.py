"""
tests/test_file_naming.py — Unit tests for short company name and email subject generation
"""

import unittest

from file_naming import COMPANY_SUBJECT_MAX_LEN, build_email_subject, short_company_name

PIB = "Затишний Євгеній Михайлович"


class TestShortCompanyName(unittest.TestCase):
    def test_strips_legal_form_and_quotes(self):
        cases = [
            ("Товариство з обмеженою відповідальністю «Флагман Трейдинг»", "Флагман Трейдинг"),
            ('ТОВ "Флагман Трейдинг"', "Флагман Трейдинг"),
            ("ТОВ «Флагман Трейдинг»", "Флагман Трейдинг"),
            ("товариство з обмеженою відповідальністю “Флагман Трейдинг”", "Флагман Трейдинг"),
            ("Флагман Трейдинг, ТОВ", "Флагман Трейдинг"),
            ("Флагман Трейдинг", "Флагман Трейдинг"),
            ("ТОВ 'Флагман Трейдинг'", "Флагман Трейдинг"),
            ("Приватне акціонерне товариство «Оболонь»", "Оболонь"),
            ("ПрАТ «Оболонь»", "Оболонь"),
            ("Акціонерне товариство «Укрпошта»", "Укрпошта"),
            ("ФОП Іваненко Іван", "Іваненко Іван"),
            ("Фізична особа - підприємець Іваненко Іван", "Іваненко Іван"),
            ("ДП «Антонов»", "Антонов"),
            ("Smart Solutions LLC", "Smart Solutions"),
        ]
        for raw, expected in cases:
            self.assertEqual(short_company_name(raw), expected, f"input: {raw!r}")

    def test_legal_form_only_inside_words_is_kept(self):
        self.assertEqual(short_company_name("ППК Груп"), "ППК Груп")
        self.assertEqual(short_company_name("Атлант"), "Атлант")
        self.assertEqual(short_company_name("Товариш"), "Товариш")

    def test_apostrophe_inside_word_is_kept(self):
        self.assertEqual(short_company_name("ТОВ «Слов'янська зірка»"), "Слов'янська зірка")

    def test_forbidden_filename_chars_removed(self):
        result = short_company_name("ТОВ «Флагман/Трейдинг: Груп»")
        self.assertEqual(result, "Флагман Трейдинг Груп")
        for ch in '\\/:*?"<>|«»':
            self.assertNotIn(ch, result)

    def test_empty_or_legal_form_only(self):
        for raw in ["", "   ", "ТОВ", "  тов  ", "«»", "Товариство з обмеженою відповідальністю"]:
            self.assertEqual(short_company_name(raw), "", f"input: {raw!r}")

    def test_long_name_cut_at_word_boundary(self):
        raw = "ТОВ «Науково виробниче об'єднання передових енергетичних технологій та інновацій»"
        result = short_company_name(raw)
        self.assertLessEqual(len(result), COMPANY_SUBJECT_MAX_LEN)
        self.assertTrue(result.startswith("Науково виробниче"))
        self.assertTrue(raw.replace("ТОВ «", "").startswith(result + " "), "cut must fall on a word boundary")


class TestBuildEmailSubject(unittest.TestCase):
    def test_company_and_pib(self):
        subject = build_email_subject(PIB, "Товариство з обмеженою відповідальністю «Флагман Трейдинг»")
        self.assertEqual(subject, "[Флагман Трейдинг] - Затишний Євгеній Михайлович")

    def test_without_company(self):
        self.assertEqual(build_email_subject(PIB, ""), PIB)
        self.assertEqual(build_email_subject(PIB, "ТОВ"), PIB)
        self.assertEqual(build_email_subject(PIB), PIB)

    def test_empty_pib_fallback(self):
        self.assertEqual(build_email_subject("", "ТОВ «Флагман Трейдинг»"), "[Флагман Трейдинг] - Кандидат")
        self.assertEqual(build_email_subject("   ", ""), "Кандидат")

    def test_pib_whitespace_normalized(self):
        self.assertEqual(build_email_subject("  Затишний   Євгеній Михайлович ", ""), PIB)

    def test_multipart_suffix(self):
        subject = build_email_subject(PIB, "ТОВ «Флагман Трейдинг»", part_number=1, total_parts=2)
        self.assertEqual(subject, "[Флагман Трейдинг] - Затишний Євгеній Михайлович (частина 1 з 2)")
        self.assertNotIn("/", subject)

    def test_multipart_without_company(self):
        subject = build_email_subject(PIB, "", part_number=2, total_parts=2)
        self.assertEqual(subject, "Затишний Євгеній Михайлович (частина 2 з 2)")

    def test_single_part_has_no_suffix(self):
        subject = build_email_subject(PIB, "ТОВ «Флагман Трейдинг»", part_number=1, total_parts=1)
        self.assertNotIn("частина", subject)

    def test_no_legacy_prefix(self):
        subject = build_email_subject(PIB, "ТОВ «Флагман Трейдинг»", part_number=2, total_parts=3)
        self.assertNotIn("Документи для працевлаштування", subject)
        self.assertNotIn("Частина", subject)
        self.assertNotIn("—", subject)

    def test_no_brackets_without_company(self):
        subject = build_email_subject(PIB, "ТОВ")
        self.assertNotIn("[", subject)
        self.assertNotIn(" - ", subject)


if __name__ == "__main__":
    unittest.main()
