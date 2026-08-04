"""
tests/test_app_logic.py — Unit tests for app wizard logic, PIB validation, and submission flow.
"""

import unittest
from app import validate_pib, check_mandatory_uploads
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

    def test_check_mandatory_uploads(self):
        """Test check_mandatory_uploads helper function."""
        docs = [
            {"doc_id": "pasport", "important": True, "min_files": 1, "upload_enabled": True},
            {"doc_id": "ipn", "important": True, "min_files": 1, "upload_enabled": True},
            {"doc_id": "photo", "important": True, "min_files": 0, "upload_enabled": False},
            {"doc_id": "vpo", "important": False, "min_files": 1, "upload_enabled": True},
        ]

        # Scenario 1: missing all mandatory
        self.assertFalse(check_mandatory_uploads(docs, {}))

        # Scenario 2: missing IPN
        uploaded_partial = {
            "pasport": [{"bytes": b"pass"}]
        }
        self.assertFalse(check_mandatory_uploads(docs, uploaded_partial))

        # Scenario 3: all mandatory present
        uploaded_full = {
            "pasport": [{"bytes": b"pass"}],
            "ipn": [{"bytes": b"ipn"}],
        }
        self.assertTrue(check_mandatory_uploads(docs, uploaded_full))

    def test_default_answers(self):
        """Test default answers dictionary values."""
        self.assertEqual(DEFAULT_ANSWERS["pib"], "")
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
