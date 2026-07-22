"""
tests/test_uploads.py — Unit tests for uploads.py module functions.
"""

import unittest
from unittest.mock import patch
import streamlit as st
import uploads
from validators import ValidationResult
from documents import build_documents


class MockSessionState(dict):
    """Simple dictionary wrapper mocking Streamlit's st.session_state for unit tests."""
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


class TestUploadsModule(unittest.TestCase):
    def setUp(self):
        self.session_patcher = patch.object(st, "session_state", MockSessionState())
        self.mock_state = self.session_patcher.start()

    def tearDown(self):
        self.session_patcher.stop()

    def test_init_upload_session_state(self):
        """Verify session state structures initialization."""
        uploads.init_upload_session_state()
        self.assertIn("uploaded_docs", st.session_state)
        self.assertIn("toasted_errors", st.session_state)
        self.assertIn("sent_parts", st.session_state)
        self.assertEqual(st.session_state["uploaded_docs"], {})
        self.assertEqual(st.session_state["toasted_errors"], set())

    def test_get_upload_summary_empty(self):
        """Verify get_upload_summary returns not ready when mandatory docs missing."""
        docs = build_documents({"military_liable": "Ні"})
        uploads.init_upload_session_state()
        summary = uploads.get_upload_summary(docs)

        self.assertEqual(summary["uploaded_docs_count"], 0)
        self.assertGreater(summary["missing_mandatory_count"], 0)
        self.assertFalse(summary["is_ready_for_submission"])

    def test_get_upload_summary_completed(self):
        """Verify summary calculation when mandatory docs are uploaded."""
        docs = [
            {
                "doc_id": "pasport",
                "title": "Паспорт",
                "important": True,
                "min_files": 1,
                "upload_enabled": True,
            },
            {
                "doc_id": "ipn",
                "title": "ІПН",
                "important": True,
                "min_files": 1,
                "upload_enabled": True,
            },
            {
                "doc_id": "photo",
                "title": "Фото 3x4",
                "important": True,
                "min_files": 0,
                "upload_enabled": False,
            },
        ]
        uploads.init_upload_session_state()
        st.session_state["uploaded_docs"] = {
            "pasport": [
                {
                    "bytes": b"passport content",
                    "filename": "pasport.pdf",
                    "size": 1000,
                    "validation": ValidationResult(ok=True, blocking=False),
                }
            ],
            "ipn": [
                {
                    "bytes": b"ipn content",
                    "filename": "ipn.pdf",
                    "size": 500,
                    "validation": ValidationResult(ok=True, blocking=False),
                }
            ],
        }

        summary = uploads.get_upload_summary(docs)
        self.assertEqual(summary["uploaded_docs_count"], 2)
        self.assertEqual(summary["missing_mandatory_count"], 0)
        self.assertEqual(summary["blocking_errors_count"], 0)
        self.assertEqual(summary["total_size_bytes"], 1500)
        self.assertTrue(summary["is_ready_for_submission"])

    def test_validate_all_uploads_missing_mandatory(self):
        """Verify validate_all_uploads returns errors when mandatory docs missing."""
        docs = [
            {
                "doc_id": "pasport",
                "title": "Паспорт або ID-карта",
                "important": True,
                "min_files": 1,
                "upload_enabled": True,
            }
        ]
        uploads.init_upload_session_state()
        is_valid, errors = uploads.validate_all_uploads(docs)
        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)
        self.assertIn("Паспорт або ID-карта", errors[0])

    def test_validate_all_uploads_valid(self):
        """Verify validate_all_uploads returns True when all mandatory uploads are present and valid."""
        docs = [
            {
                "doc_id": "pasport",
                "title": "Паспорт",
                "important": True,
                "min_files": 1,
                "upload_enabled": True,
            }
        ]
        uploads.init_upload_session_state()
        st.session_state["uploaded_docs"] = {
            "pasport": [
                {
                    "bytes": b"content",
                    "filename": "p.pdf",
                    "size": 100,
                    "validation": ValidationResult(ok=True, blocking=False),
                }
            ]
        }
        is_valid, errors = uploads.validate_all_uploads(docs)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_all_uploads_blocking_error(self):
        """Verify validate_all_uploads returns errors when an uploaded file has blocking validation error."""
        docs = [
            {
                "doc_id": "pasport",
                "title": "Паспорт",
                "important": True,
                "min_files": 1,
                "upload_enabled": True,
            }
        ]
        uploads.init_upload_session_state()
        st.session_state["uploaded_docs"] = {
            "pasport": [
                {
                    "bytes": b"invalid content",
                    "filename": "p.exe",
                    "size": 100,
                    "validation": ValidationResult(ok=False, blocking=True, reason="Недозволений формат"),
                }
            ]
        }
        is_valid, errors = uploads.validate_all_uploads(docs)
        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)
        self.assertIn("Недозволений формат", errors[0])

    def test_clear_upload_session_state(self):
        """Verify clear_upload_session_state resets session state structures."""
        uploads.init_upload_session_state()
        st.session_state["uploaded_docs"] = {"pasport": [{"bytes": b"123"}]}
        st.session_state["toasted_errors"] = {"err1"}
        st.session_state["sent_parts"] = {0}

        uploads.clear_upload_session_state()
        self.assertEqual(st.session_state["uploaded_docs"], {})
        self.assertEqual(st.session_state["toasted_errors"], set())
        self.assertNotIn("sent_parts", st.session_state)


if __name__ == "__main__":
    unittest.main()
