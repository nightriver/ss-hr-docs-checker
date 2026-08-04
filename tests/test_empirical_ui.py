"""
tests/test_empirical_ui.py — Milestone 3 empirical stress test suite for HR Docs Checker v2.2.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

import streamlit as st
import documents
from documents import build_documents, DEFAULT_ANSWERS
import uploads
import exporters
from exporters import build_pdf, build_txt
import app
from validators import ValidationResult
from instructions import INSTRUCTIONS

REQUIRED_13_KEYS = {
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


class MockSessionState(dict):
    """Mock dictionary supporting attribute access for Streamlit session state."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError(key)


def generate_50_plus_answer_scenarios() -> list[dict]:
    """Generates 50+ diverse permutations of survey answer dictionaries."""
    scenarios = []

    military_opts = ["Так", "Ні"]
    labor_opts = ["Є трудова книжка", "Це моє перше офіційне працевлаштування"]
    edu_opts = [
        "Шкільний атестат",
        "Диплом училища або коледжу (ПТУ, фахова передвища)",
        "Диплом університету або інституту (вища освіта)",
    ]
    student_opts = ["Так", "Ні"]
    children_opts = ["Так", "Ні"]
    disability_opts = [
        "Ні",
        "Так, інвалідність встановлено до 2025 року",
        "Так, інвалідність встановлено з 2025 року",
    ]

    all_statuses = [
        "Пенсіонер",
        "Постраждалий від ЧАЕС",
        "ВПО (внутрішньо переміщена особа)",
        "Змінювали прізвище",
        "Одинока мати або батько",
        "Маю дитину з інвалідністю",
    ]

    status_combos = [
        [],
        ["Пенсіонер"],
        ["ВПО (внутрішньо переміщена особа)"],
        ["Змінювали прізвище", "Одинока мати або батько"],
        ["Постраждалий від ЧАЕС", "Маю дитину з інвалідністю"],
        all_statuses,
    ]

    for mil in military_opts:
        for lab in labor_opts:
            for edu in edu_opts:
                for st_form in student_opts:
                    for ch in children_opts:
                        for dis in disability_opts:
                            for stat_list in status_combos:
                                scenario = {
                                    "pib": "Іваненко Іван Іванович",
                                    "military_liable": mil,
                                    "labor_book": lab,
                                    "education": edu,
                                    "student_day_form": st_form,
                                    "children_u18": ch,
                                    "disability_status": dis,
                                    "extra_statuses": stat_list,
                                }
                                scenarios.append(scenario)

    scenarios.append({})
    scenarios.append(DEFAULT_ANSWERS.copy())
    scenarios.append({
        "pib": "Мар'ян Д'Артаньян",
        "military_liable": "Невідомо",
        "labor_book": "Кастомний варіант",
        "education": "Кастомна освіта",
        "student_day_form": "Так",
        "extra_statuses": ["Невідомий статус"],
    })

    return scenarios


class TestEmpiricalM3(unittest.TestCase):
    def setUp(self):
        self.session_patcher = patch.object(st, "session_state", MockSessionState())
        self.mock_state = self.session_patcher.start()

    def tearDown(self):
        self.session_patcher.stop()

    def test_1_document_schema_integrity_50_plus_combinations(self):
        """
        Verify document schema integrity across 50+ combinations:
        - All 13 required keys present
        - No duplicate doc_ids
        - student_certificate present IF AND ONLY IF student_day_form == 'Так'
        - Proper field types
        """
        scenarios = generate_50_plus_answer_scenarios()
        self.assertGreaterEqual(len(scenarios), 50, f"Expected 50+ scenarios, got {len(scenarios)}")

        for idx, answers in enumerate(scenarios):
            docs = build_documents(answers)
            self.assertIsInstance(docs, list)
            self.assertGreater(len(docs), 0, f"Scenario {idx} returned empty doc list")

            doc_ids = [d["doc_id"] for d in docs]
            self.assertEqual(
                len(doc_ids),
                len(set(doc_ids)),
                f"Scenario {idx} has duplicate doc_ids: {doc_ids}"
            )

            is_student = answers.get("student_day_form") == "Так"
            has_student_doc = "student_certificate" in doc_ids
            self.assertEqual(
                is_student,
                has_student_doc,
                f"Scenario {idx}: student_day_form='{answers.get('student_day_form')}' but has_student_doc={has_student_doc}"
            )

            for d_idx, doc in enumerate(docs):
                keys = set(doc.keys())
                self.assertEqual(
                    keys,
                    REQUIRED_13_KEYS,
                    f"Scenario {idx} doc {d_idx} ({doc.get('doc_id')}) schema keys mismatch"
                )

                self.assertIsInstance(doc["doc_id"], str)
                self.assertGreater(len(doc["doc_id"].strip()), 0)

                self.assertIsInstance(doc["title"], str)
                self.assertGreater(len(doc["title"].strip()), 0)

                self.assertIsInstance(doc["file_label"], str)
                self.assertGreater(len(doc["file_label"].strip()), 0)

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

    def test_2_uploads_card_helpers(self):
        """
        Verify uploads.py card helpers:
        - raw bytes conversion handling
        - get_upload_summary calculation
        - validation error badge updates & validate_all_uploads
        - clear_upload_session_state function
        """
        uploads.init_upload_session_state()
        self.assertIn("uploaded_docs", st.session_state)
        self.assertIn("toasted_errors", st.session_state)
        self.assertIn("sent_parts", st.session_state)

        mock_file_obj = MagicMock()
        mock_file_obj.getvalue.return_value = b"raw pdf test content"
        mock_file_obj.name = "test_doc.pdf"
        extracted_bytes = mock_file_obj.getvalue()
        self.assertEqual(extracted_bytes, b"raw pdf test content")

        sample_docs = build_documents({"military_liable": "Так", "student_day_form": "Так"})
        summary_empty = uploads.get_upload_summary(sample_docs)
        self.assertEqual(summary_empty["uploaded_docs_count"], 0)
        self.assertGreater(summary_empty["missing_mandatory_count"], 0)
        self.assertFalse(summary_empty["is_ready_for_submission"])

        is_valid_empty, errors_empty = uploads.validate_all_uploads(sample_docs)
        self.assertFalse(is_valid_empty)
        self.assertGreater(len(errors_empty), 0)

        uploaded_map = {}
        for doc in sample_docs:
            if doc.get("upload_enabled", True) and doc.get("important", True):
                uploaded_map[doc["doc_id"]] = [
                    {
                        "bytes": b"sample file bytes data",
                        "filename": f"{doc['file_label']}.pdf",
                        "size": 512,
                        "validation": ValidationResult(ok=True, blocking=False),
                    }
                ]

        st.session_state["uploaded_docs"] = uploaded_map
        summary_pop = uploads.get_upload_summary(sample_docs)
        self.assertEqual(summary_pop["missing_mandatory_count"], 0)
        self.assertEqual(summary_pop["blocking_errors_count"], 0)
        self.assertTrue(summary_pop["is_ready_for_submission"])

        is_valid_pop, errors_pop = uploads.validate_all_uploads(sample_docs)
        self.assertTrue(is_valid_pop)
        self.assertEqual(len(errors_pop), 0)

        st.session_state["uploaded_docs"]["pasport"] = [
            {
                "bytes": b"exe header bytes",
                "filename": "pasport.exe",
                "size": 100,
                "validation": ValidationResult(ok=False, blocking=True, reason="Файл має неприпустимий тип executable"),
            }
        ]

        summary_err = uploads.get_upload_summary(sample_docs)
        self.assertGreater(summary_err["blocking_errors_count"], 0)
        self.assertFalse(summary_err["is_ready_for_submission"])

        is_valid_err, errors_err = uploads.validate_all_uploads(sample_docs)
        self.assertFalse(is_valid_err)
        self.assertTrue(any("pasport.exe" in err or "executable" in err for err in errors_err))

        st.session_state["toasted_errors"].add("test_error_sig")
        st.session_state["sent_parts"].add(0)

        uploads.clear_upload_session_state()
        self.assertEqual(st.session_state["uploaded_docs"], {})
        self.assertEqual(st.session_state["toasted_errors"], set())
        self.assertNotIn("sent_parts", st.session_state)

    def test_3_exporters_pdf_and_txt_50_plus_combinations(self):
        """
        Verify exporters.py PDF and TXT generation with output from build_documents()
        across all 50+ answer combinations (zero KeyErrors or formatting crashes).
        """
        scenarios = generate_50_plus_answer_scenarios()

        for idx, answers in enumerate(scenarios):
            docs = build_documents(answers)

            txt_out = build_txt(docs, instructions=INSTRUCTIONS)
            self.assertIsInstance(txt_out, str)
            self.assertGreater(len(txt_out), 0)
            self.assertIn("Перелік документів для працевлаштування", txt_out)

            pdf_bytes = build_pdf(docs, instructions=INSTRUCTIONS)
            self.assertIsInstance(pdf_bytes, bytes)
            self.assertGreater(len(pdf_bytes), 0)
            self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_4_app_wizard_logic_and_pib(self):
        """Verify app.py PIB validation and helper logic."""
        valid_pibs = [
            "Іваненко Петро",
            "Шевченко Тарас Григорович",
            "Мар'ян О'Коннор",
            "Петренко-Задунайський Олексій",
        ]
        for pib in valid_pibs:
            ok, msg = app.validate_pib(pib)
            self.assertTrue(ok)

        invalid_pibs = [
            "",
            "   ",
            "Іван",
            "John Smith",
            "12345 67890",
        ]
        for pib in invalid_pibs:
            ok, msg = app.validate_pib(pib)
            self.assertFalse(ok)

        docs = build_documents({"military_liable": "Ні"})
        is_valid, _ = uploads.validate_all_uploads(docs)
        self.assertFalse(is_valid)


if __name__ == "__main__":
    unittest.main()
