"""
tests/test_documents.py — Unit tests for documents.py schema & build_documents generator.
"""

import unittest
from documents import build_documents, DEFAULT_ANSWERS
from exporters import build_txt, build_pdf

REQUIRED_KEYS = {
    "doc_id",
    "title",
    "file_label",
    "details",
    "format",
    "instruction_key",
    "important",
    "hr_note",
    "accept",
    "multiple",
    "min_files",
    "upload_enabled",
    "special_validation",
}


class TestDocumentsSchema(unittest.TestCase):
    def test_default_answers_structure(self):
        """Verify DEFAULT_ANSWERS dictionary contains required default keys."""
        self.assertIn("pib", DEFAULT_ANSWERS)
        self.assertEqual(DEFAULT_ANSWERS["pib"], "")
        self.assertIn("student_day_form", DEFAULT_ANSWERS)
        self.assertEqual(DEFAULT_ANSWERS["student_day_form"], "Ні")
        self.assertIn("military_liable", DEFAULT_ANSWERS)
        self.assertIn("labor_book", DEFAULT_ANSWERS)
        self.assertIn("education", DEFAULT_ANSWERS)
        self.assertIn("children_u18", DEFAULT_ANSWERS)
        self.assertIn("disability_status", DEFAULT_ANSWERS)
        self.assertIn("extra_statuses", DEFAULT_ANSWERS)

    def test_schema_keys_and_types_all_scenarios(self):
        """Test that ALL documents returned across diverse answer combinations contain all 13 keys with correct types."""
        scenarios = [
            {},
            DEFAULT_ANSWERS,
            {
                "pib": "Тестовий Тест",
                "military_liable": "Так",
                "labor_book": "Є трудова книжка",
                "education": "Диплом університету або інституту (вища освіта)",
                "student_day_form": "Так",
                "children_u18": "Так",
                "disability_status": "Так, інвалідність встановлено до 2025 року",
                "extra_statuses": ["Пенсіонер", "ВПО (внутрішньо переміщена особа)"],
            },
            {
                "pib": "Коваль Ганна",
                "military_liable": "Ні",
                "labor_book": "Це моє перше офіційне працевлаштування",
                "education": "Шкільний атестат",
                "student_day_form": "Ні",
                "children_u18": "Ні",
                "disability_status": "Так, інвалідність встановлено з 2025 року",
                "extra_statuses": [
                    "Постраждалий від ЧАЕС",
                    "Змінювали прізвище",
                    "Одинока мати або батько",
                    "Маю дитину з інвалідністю",
                ],
            },
        ]

        for answers in scenarios:
            docs = build_documents(answers)
            self.assertGreater(len(docs), 0)
            doc_ids = [d["doc_id"] for d in docs]
            self.assertEqual(len(doc_ids), len(set(doc_ids)), f"Duplicate doc_ids found: {doc_ids}")

            for doc in docs:
                self.assertEqual(
                    set(doc.keys()),
                    REQUIRED_KEYS,
                    f"Keys mismatch for doc_id {doc.get('doc_id')}",
                )
                self.assertIsInstance(doc["doc_id"], str)
                self.assertGreater(len(doc["doc_id"]), 0)
                self.assertIsInstance(doc["title"], str)
                self.assertGreater(len(doc["title"]), 0)
                self.assertIsInstance(doc["file_label"], str)
                self.assertGreater(len(doc["file_label"]), 0)
                self.assertIsInstance(doc["details"], str)
                self.assertIsInstance(doc["format"], str)
                if doc["instruction_key"] is not None:
                    self.assertIsInstance(doc["instruction_key"], str)
                self.assertIsInstance(doc["important"], bool)
                if doc["hr_note"] is not None:
                    self.assertIsInstance(doc["hr_note"], str)
                self.assertIsInstance(doc["accept"], list)
                self.assertTrue(all(isinstance(x, str) for x in doc["accept"]))
                self.assertIsInstance(doc["multiple"], bool)
                self.assertIsInstance(doc["min_files"], int)
                self.assertGreaterEqual(doc["min_files"], 0)
                self.assertIsInstance(doc["upload_enabled"], bool)
                if doc["special_validation"] is not None:
                    self.assertIsInstance(doc["special_validation"], str)

    def test_photo_3x4_non_uploadable_rule(self):
        """Verify Photo 3x4 schema constraints (upload_enabled=False, min_files=0)."""
        docs = build_documents(DEFAULT_ANSWERS)
        photo_docs = [d for d in docs if d["doc_id"] == "photo"]
        self.assertEqual(len(photo_docs), 1)
        photo = photo_docs[0]
        self.assertFalse(photo["upload_enabled"])
        self.assertEqual(photo["min_files"], 0)
        self.assertEqual(photo["file_label"], "Photo")

    def test_student_day_form_rule(self):
        """Verify Student certificate inclusion when student_day_form == 'Так'."""
        docs_yes = build_documents({"student_day_form": "Так"})
        student_docs = [d for d in docs_yes if d["doc_id"] == "student_certificate"]
        self.assertEqual(len(student_docs), 1)
        st_doc = student_docs[0]
        self.assertTrue(st_doc["upload_enabled"])
        self.assertEqual(st_doc["min_files"], 1)
        self.assertEqual(st_doc["file_label"], "Dovidka_VNZ")

        docs_no = build_documents({"student_day_form": "Ні"})
        self.assertFalse(any(d["doc_id"] == "student_certificate" for d in docs_no))

    def test_reserve_plus_pdf_rule(self):
        """Verify Military Reserve+ document schema constraints when military_liable == 'Так'."""
        docs = build_documents({"military_liable": "Так"})
        res_docs = [d for d in docs if d["doc_id"] == "reserve_plus"]
        self.assertEqual(len(res_docs), 1)
        res = res_docs[0]
        self.assertEqual(res["accept"], ["pdf"])
        self.assertEqual(res["special_validation"], "reserve_plus_pdf")
        self.assertTrue(res["upload_enabled"])
        self.assertEqual(res["min_files"], 1)

    def test_disability_rules(self):
        """Verify pre-2025 vs post-2025 disability status rules."""
        pre_docs = build_documents({"disability_status": "Так, інвалідність встановлено до 2025 року"})
        pre_ids = [d["doc_id"] for d in pre_docs]
        self.assertIn("msek", pre_ids)
        self.assertIn("ipr", pre_ids)

        post_docs = build_documents({"disability_status": "Так, інвалідність встановлено з 2025 року"})
        post_ids = [d["doc_id"] for d in post_docs]
        self.assertIn("expert_decision", post_ids)
        self.assertIn("disability_recommendations", post_ids)

    def test_exporters_compatibility(self):
        """Verify build_txt and build_pdf execute seamlessly with updated document dictionaries."""
        answers = {
            "military_liable": "Так",
            "labor_book": "Є трудова книжка",
            "student_day_form": "Так",
            "extra_statuses": ["ВПО (внутрішньо переміщена особа)"],
        }
        docs = build_documents(answers)

        txt_output = build_txt(docs)
        self.assertIn("Перелік документів для працевлаштування", txt_output)
        self.assertIn("Витяг з Резерв+", txt_output)

        pdf_bytes = build_pdf(docs)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 0)


if __name__ == "__main__":
    unittest.main()
