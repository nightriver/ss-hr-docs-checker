"""
test_challenger_m3_2_pipeline.py — Empirical challenge test suite for Milestone 3 UI/App Pipeline.
Empirically tests:
1. Step 1 ПІБ Cyrillic validator (validate_pib) on valid, edge-case, and invalid names.
2. Full end-to-end simulation of Step 8 submit pipeline:
   - Mock session state & uploaded document bytes
   - Validation & Reserve+ checks
   - Compression & file naming
   - Bin-packing & chunking into email parts
   - DocsMailer send & retry tracking (sent_parts) across success and partial failure scenarios.
"""

import io
import sys
import unittest
from email.message import EmailMessage
import pypdf
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
from app import validate_pib
from documents import build_documents, DEFAULT_ANSWERS
import uploads
import validators
import image_tools
import file_naming
import chunking
import emailer


def create_sample_pdf(text: str) -> bytes:
    """Helper to generate a minimal in-memory PDF with specified text layer."""
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length " + str(len(text) + 50).encode("ascii") + b" >>\nstream\n"
        b"BT /F1 12 Tf 100 700 Td (" + text.encode("utf-8") + b") Tj ET\nendstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n10\n%%EOF\n"
    )
    return pdf_content


def create_sample_png() -> bytes:
    """Helper to generate a minimal valid 1x1 PNG image."""
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
    )


class CustomFlakyMailProvider:
    """MailProvider that fails on a specified part index during sending."""
    def __init__(self, fail_on_part_index: int):
        self.fail_on_part_index = fail_on_part_index
        self.sent_messages: list[EmailMessage] = []

    def send(self, msg: EmailMessage) -> bool:
        part_idx = len(self.sent_messages)
        if part_idx == self.fail_on_part_index:
            raise RuntimeError(f"Simulated network drop on part index {part_idx}")
        self.sent_messages.append(msg)
        return True


class EmpiricalAppPipelineChallenge(unittest.TestCase):

    def setUp(self):
        st.session_state.clear()
        uploads.init_upload_session_state()

    def test_01_step1_pib_cyrillic_validator(self):
        """
        Challenge Step 1 ПІБ validator with valid Ukrainian names and invalid/edge-case inputs.
        """
        valid_cases = [
            "Іваненко Петро Олексійович",
            "Петренко-Ганна Марія",
            "О'Браєн Тарас",
            "Ґудзь Василь",
            "Гуменюк-Шевченко Ольга Вікторівна",
            "Кравчук Іван",
            "Мар'ян Ігор",
            "Лук'яненко Сергій",
            "Ярослав-Олександр Ґедзь",
        ]

        for name in valid_cases:
            is_valid, msg = validate_pib(name)
            self.assertTrue(is_valid, f"Expected valid for '{name}', got error: {msg}")
            self.assertEqual(msg, "")

        # Test single-word Cyrillic names explicitly mentioned in prompt: "О'Браєн", "Ґудзь"
        single_word_cases = ["О'Браєн", "Ґудзь", "Іваненко"]
        for name in single_word_cases:
            is_valid, msg = validate_pib(name)
            self.assertFalse(is_valid, f"Single word '{name}' passed validation unexpectedly!")
            self.assertIn("принаймні прізвище та ім'я", msg)

        # Invalid cases expected to fail
        invalid_cases = [
            ("", "empty string"),
            ("   ", "whitespace only"),
            ("Petro", "Latin single word"),
            ("Ivanenko Petro", "Latin full name"),
            ("Ivanenko123", "Latin with numbers"),
            ("Іваненко123", "Cyrillic with numbers"),
            ("--- ---", "punctuation only"),
            ("Петро@Олексійович", "symbol @"),
            ("Іваненко!", "symbol !"),
        ]

        for name, desc in invalid_cases:
            is_valid, msg = validate_pib(name)
            self.assertFalse(is_valid, f"Expected invalid for '{name}' ({desc})")
            self.assertGreater(len(msg), 0)

    def test_02_step8_submit_pipeline_success(self):
        """
        Challenge full end-to-end Step 8 submit pipeline in success scenario.
        Mock session state, uploaded docs, compression, naming, bin-packing, and DocsMailer.
        """
        st.session_state.step = 8
        st.session_state.answers = {
            "pib": "Іваненко Петро Олексійович",
            "military_liable": "Так",
            "labor_book": "Є трудова книжка",
            "education": "Вища",
            "student_day_form": "Ні",
            "children_u18": "Ні",
            "disability_status": "Ні",
            "extra_statuses": [],
        }

        docs = build_documents(st.session_state.answers)
        mandatory_doc_ids = [d["doc_id"] for d in docs if d.get("important", True) and d.get("min_files", 1) >= 1]

        png_bytes = create_sample_png()
        reserve_pdf_text = "Єдиного державного реєстру призовників, військовозобов'язаних та резервістів. РНОКПП 1234567890. Сформовано: 2026-01-01. ТЦК та СП."
        reserve_pdf_bytes = create_sample_pdf(reserve_pdf_text)
        general_pdf_bytes = create_sample_pdf("Загальний документ PDF")

        uploaded_docs = {}

        for doc in docs:
            doc_id = doc["doc_id"]
            if not doc.get("upload_enabled", True):
                continue

            if doc_id == "reserve_plus":
                file_bytes = reserve_pdf_bytes
                filename = "reserve_plus.pdf"
                val_res = validators.validate_reserve_plus_pdf(file_bytes)
            elif doc_id == "trudova":
                file_bytes = general_pdf_bytes
                filename = "trudova.pdf"
                val_res = validators.validate_mime_type(file_bytes, filename, doc.get("accept", ["pdf"]))
            else:
                file_bytes = png_bytes
                filename = f"{doc_id}.png"
                val_res = validators.validate_mime_type(file_bytes, filename, doc.get("accept", ["png"]))

            uploaded_docs[doc_id] = [{
                "bytes": file_bytes,
                "filename": filename,
                "size": len(file_bytes),
                "validation": val_res,
            }]

        st.session_state.uploaded_docs = uploaded_docs

        # Step A: File Validation Check
        val_ok, val_errs = uploads.validate_all_uploads(docs)
        self.assertTrue(val_ok, f"Validation failed unexpectedly: {val_errs}")

        # Step B & C: Image Compression & Attachment Naming
        processed_files: list[chunking.ProcessedFile] = []
        pib_str = st.session_state.answers.get("pib", "")

        for doc in docs:
            doc_id = doc["doc_id"]
            raw_files = st.session_state.uploaded_docs.get(doc_id, [])
            total_count = len(raw_files)

            for idx, fdict in enumerate(raw_files):
                comp_bytes, comp_ext = image_tools.compress_image(
                    fdict["bytes"],
                    original_filename=fdict["filename"],
                )

                gen_filename = file_naming.generate_attachment_filename(
                    pib=pib_str,
                    file_label=doc.get("file_label", doc_id),
                    doc_index=idx,
                    total_files_for_doc=total_count,
                    multiple=doc.get("multiple", False),
                    original_filename=fdict["filename"],
                    converted_ext=comp_ext,
                )

                pf = chunking.ProcessedFile(
                    doc_id=doc_id,
                    file_label=doc.get("file_label", doc_id),
                    filename=gen_filename,
                    content=comp_bytes,
                    doc_title=doc.get("title", ""),
                )
                processed_files.append(pf)

        # Step D: Grouping & Bin-packing into Email Chunks
        chunk_res = chunking.pack_into_email_parts(processed_files)
        self.assertTrue(chunk_res.ok)
        self.assertGreater(len(chunk_res.parts), 0)

        # Step E: Email delivery via DocsMailer with MockMailProvider
        provider = emailer.MockMailProvider(should_succeed=True)
        mailer = emailer.DocsMailer(provider=provider, from_addr="hr-bot@test.com")
        hr_to = "hr@smart-solutions.ua"

        email_messages = []
        total_parts = len(chunk_res.parts)

        for part in chunk_res.parts:
            subject = f"Документи для працевлаштування — {pib_str}"
            body_text = f"Кандидат: {pib_str}\n\n{part.manifest_text}"
            attachments = [
                {"filename": pf.filename, "content": pf.content, "mime_type": None}
                for pf in part.files
            ]
            msg = emailer.build_email_message(
                from_addr=mailer.from_addr,
                to_addr=hr_to,
                subject=subject,
                body_text=body_text,
                attachments=attachments,
            )
            email_messages.append(msg)

        sent_parts = st.session_state["sent_parts"]
        send_results = mailer.send_parts(
            hr_to=hr_to,
            parts=email_messages,
            sent_parts=sent_parts,
        )

        self.assertEqual(len(send_results), total_parts)
        self.assertTrue(all(r.ok for r in send_results))
        self.assertEqual(sent_parts, set(range(total_parts)))
        self.assertEqual(len(provider.sent_messages), total_parts)

        # Post-submit Cleanup
        uploads.clear_upload_session_state()
        self.assertEqual(len(st.session_state.get("uploaded_docs", {})), 0)
        self.assertNotIn("sent_parts", st.session_state)

    def test_03_step8_submit_pipeline_partial_failure_and_retry(self):
        """
        Challenge Step 8 submit pipeline in partial failure scenario with retry tracking set (sent_parts).
        """
        large_bytes = b"X" * (7 * 1024 * 1024)
        pf1 = chunking.ProcessedFile(doc_id="d1", file_label="Doc1", filename="ivanenko_doc1.pdf", content=large_bytes, doc_title="Title 1")
        pf2 = chunking.ProcessedFile(doc_id="d2", file_label="Doc2", filename="ivanenko_doc2.pdf", content=large_bytes, doc_title="Title 2")
        pf3 = chunking.ProcessedFile(doc_id="d3", file_label="Doc3", filename="ivanenko_doc3.pdf", content=large_bytes, doc_title="Title 3")

        chunk_res = chunking.pack_into_email_parts([pf1, pf2, pf3])
        self.assertGreaterEqual(len(chunk_res.parts), 2, "Expected at least 2 parts for partial failure test")

        email_messages = []
        total_parts = len(chunk_res.parts)
        for part in chunk_res.parts:
            msg = emailer.build_email_message(
                from_addr="hr-bot@test.com",
                to_addr="hr@test.com",
                subject=f"Part {part.part_number}/{total_parts}",
                body_text="Body",
                attachments=[{"filename": pf.filename, "content": pf.content, "mime_type": None} for pf in part.files],
            )
            email_messages.append(msg)

        # Attempt 1: Provider fails on part index 1 (second part)
        flaky_provider = CustomFlakyMailProvider(fail_on_part_index=1)
        mailer_flaky = emailer.DocsMailer(provider=flaky_provider, from_addr="hr-bot@test.com")

        sent_parts = set()
        results_attempt1 = mailer_flaky.send_parts("hr@test.com", email_messages, sent_parts=sent_parts)

        self.assertEqual(len(results_attempt1), 2)
        self.assertTrue(results_attempt1[0].ok)
        self.assertFalse(results_attempt1[1].ok)
        self.assertEqual(results_attempt1[1].error_type, "RuntimeError")
        self.assertEqual(sent_parts, {0})
        self.assertEqual(len(flaky_provider.sent_messages), 1)

        # Attempt 2 (Retry): Provider is now working normally (should_succeed=True)
        good_provider = emailer.MockMailProvider(should_succeed=True)
        mailer_retry = emailer.DocsMailer(provider=good_provider, from_addr="hr-bot@test.com")

        results_attempt2 = mailer_retry.send_parts("hr@test.com", email_messages, sent_parts=sent_parts)

        self.assertEqual(len(results_attempt2), total_parts)
        self.assertTrue(all(r.ok for r in results_attempt2))
        self.assertEqual(sent_parts, set(range(total_parts)))
        self.assertEqual(len(good_provider.sent_messages), total_parts - 1)


if __name__ == "__main__":
    unittest.main()
