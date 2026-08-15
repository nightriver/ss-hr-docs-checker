"""
tests/test_app_logic.py — Unit tests for app wizard logic, PIB validation, and submission flow.
"""

import unittest
from app import validate_pib, validate_phone, validate_email
from documents import DEFAULT_ANSWERS
import emailer
from validators import validate_reserve_plus_pdf


class TestAppLogic(unittest.TestCase):
    def test_validate_pib_valid(self):
        """Test valid candidate Cyrillic PIB inputs."""
        valid_inputs = [
            "Іваненко Петро Олексійович",
            "Петренко-Ганна Марія",
            "О'Коннор Джон",
            "Кравчук Іван",
            "Гуменюк-Шевченко Ольга Вікторівна",
        ]
        for name in valid_inputs:
            is_valid, msg = validate_pib(name)
            self.assertTrue(is_valid, f"Failed for valid name: {name} ({msg})")
            self.assertEqual(msg, "")

    def test_validate_pib_invalid(self):
        """Test invalid candidate PIB inputs (empty, single word, Latin, numbers, punctuation only)."""
        invalid_inputs = [
            "",
            "   ",
            "Іваненко",  # single word
            "Ivanenko Petro",  # Latin
            "Іваненко123",  # digits
            "--- ---",  # punctuation only
        ]
        for name in invalid_inputs:
            is_valid, msg = validate_pib(name)
            self.assertFalse(is_valid, f"Expected invalid for: '{name}'")
            self.assertGreater(len(msg), 0)

    def test_validate_phone_valid(self):
        """Test valid phone formats and verify correct normalization."""
        cases = [
            ("+380501234567", "+380501234567"),
            ("0501234567", "+380501234567"),
            ("+38 (050) 123-45-67", "+380501234567"),
            ("380501234567", "+380501234567"),
            ("+14155552671", "+14155552671"),
            ("+44 20 7183-8750", "+442071838750"),
        ]
        for input_val, expected_norm in cases:
            ok, err, norm = validate_phone(input_val)
            self.assertTrue(ok, f"Failed for valid phone: {input_val} ({err})")
            self.assertEqual(err, "")
            self.assertEqual(norm, expected_norm)

    def test_validate_phone_invalid(self):
        """Test invalid phone inputs (empty, letters, short, bad prefixes, excessive digits, non-ASCII Unicode digits)."""
        invalid_inputs = [
            "",
            "   ",
            "123",
            "abc",
            "+380",
            "05012345678",  # 11 digits starting with 0
            "1234567890",   # 10 digits not starting with 0 or +
            "+38050123456a",  # contains letter
            "+123",  # international with < 10 digits
            "+1234567890123456",  # international with > 15 digits
            "+38050123456²",  # Unicode superscript digit
            "+٠١٢٣٤٥٦٧٨٩١٢",  # Arabic-Indic digits
        ]
        for input_val in invalid_inputs:
            ok, err, norm = validate_phone(input_val)
            self.assertFalse(ok, f"Expected invalid for phone: '{input_val}'")
            self.assertGreater(len(err), 0)
            self.assertEqual(norm, "")

    def test_validate_email_valid(self):
        """Test valid email addresses, empty/optional email, and normalization to lowercase."""
        cases = [
            ("", ""),
            ("   ", ""),
            ("user@example.com", "user@example.com"),
            ("  Name.Surname@Smart-Solutions.UA  ", "name.surname@smart-solutions.ua"),
            ("test+label@domain.co", "test+label@domain.co"),
            ("hr_support@sub.domain.org", "hr_support@sub.domain.org"),
        ]
        for input_val, expected_norm in cases:
            ok, err, norm = validate_email(input_val)
            self.assertTrue(ok, f"Failed for valid email: {input_val} ({err})")
            self.assertEqual(err, "")
            self.assertEqual(norm, expected_norm)

    def test_validate_email_invalid(self):
        """Test invalid email inputs (spaces inside, missing @, missing domain/TLD, short TLD, leading/trailing hyphen in domain, Cyrillic)."""
        invalid_inputs = [
            "user name@mail.com",
            "test@",
            "@domain.com",
            "user@domain.c",  # TLD < 2 chars
            "plainaddress",
            "user@.com",
            "user@-domain.com",  # Domain starting with hyphen
            "user@domain-.com",  # Domain ending with hyphen
            "user@domain.-com",  # Subdomain starting with hyphen
            "ivan@пошта.укр",    # Non-ASCII Cyrillic domain
        ]
        for input_val in invalid_inputs:
            ok, err, norm = validate_email(input_val)
            self.assertFalse(ok, f"Expected invalid for email: '{input_val}'")
            self.assertGreater(len(err), 0)
            self.assertEqual(norm, "")

    def test_default_answers(self):
        """Test default answers dictionary values."""
        self.assertEqual(DEFAULT_ANSWERS["pib"], "")
        self.assertEqual(DEFAULT_ANSWERS["phone"], "")
        self.assertEqual(DEFAULT_ANSWERS["email"], "")
        self.assertEqual(DEFAULT_ANSWERS["student_day_form"], "Ні")
        self.assertEqual(DEFAULT_ANSWERS["military_liable"], "Так")
        self.assertEqual(DEFAULT_ANSWERS["labor_book"], "Є трудова книжка")
        self.assertEqual(DEFAULT_ANSWERS["extra_statuses"], [])

    def test_submission_retry_loop_logic(self):
        """Test DocsMailer send_parts retry logic with sent_parts tracking set."""
        provider = emailer.MockMailProvider(should_succeed=True)
        mailer = emailer.DocsMailer(provider=provider, from_addr="hr-bot@test.com")

        msg1 = emailer.build_email_message("hr-bot@test.com", "hr@test.com", "Part 1", "Body 1")
        msg2 = emailer.build_email_message("hr-bot@test.com", "hr@test.com", "Part 2", "Body 2")
        parts = [msg1, msg2]

        sent_parts = set()
        results = mailer.send_parts("hr@test.com", parts, sent_parts=sent_parts)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r.ok for r in results))
        self.assertEqual(sent_parts, {0, 1})
        self.assertEqual(len(provider.sent_messages), 2)

        # Second attempt: sent_parts already contains {0, 1} -> parts skipped and results return ok=True, no re-send
        results_retry = mailer.send_parts("hr@test.com", parts, sent_parts=sent_parts)
        self.assertEqual(len(results_retry), 2)
        self.assertTrue(all(r.ok for r in results_retry))
        self.assertEqual(len(provider.sent_messages), 2)

    def test_reserve_plus_validation_blocking_scanned_pdf(self):
        """Verify scanned PDF (no text layer) blocks Reserve+ upload."""
        minimal_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"
        res = validate_reserve_plus_pdf(minimal_pdf)
        self.assertFalse(res.ok)
        self.assertTrue(res.blocking)
        self.assertIn("Файл не містить текстового шару", res.reason)


if __name__ == "__main__":
    unittest.main()
