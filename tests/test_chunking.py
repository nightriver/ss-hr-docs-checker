"""
tests/test_chunking.py — Unit tests for chunking.py in HR Docs Checker v2.2
"""

import unittest

from chunking import (
    HARD_LIMIT_BYTES,
    ChunkResult,
    EmailPart,
    ProcessedFile,
    calculate_group_size,
    generate_manifest_text,
    group_by_document,
    pack_into_email_parts,
)


class TestChunking(unittest.TestCase):
    def test_group_by_document_ordering(self):
        f1 = ProcessedFile(doc_id="passport", file_label="Pasport", filename="p1.jpg", content=b"123", doc_title="Паспорт")
        f2 = ProcessedFile(doc_id="ipn", file_label="IPN", filename="ipn.pdf", content=b"456", doc_title="ІПН")
        f3 = ProcessedFile(doc_id="passport", file_label="Pasport", filename="p2.jpg", content=b"789", doc_title="Паспорт")
        f4 = ProcessedFile(doc_id="education", file_label="Osvita", filename="osv.pdf", content=b"abc", doc_title="Диплом")

        grouped = group_by_document([f1, f2, f3, f4])
        self.assertEqual(list(grouped.keys()), ["passport", "ipn", "education"])
        self.assertEqual(len(grouped["passport"]), 2)
        self.assertEqual(len(grouped["ipn"]), 1)
        self.assertEqual(len(grouped["education"]), 1)

    def test_calculate_group_size(self):
        f1 = ProcessedFile(doc_id="passport", file_label="Pasport", filename="p1.jpg", content=b"12345")
        f2 = ProcessedFile(doc_id="passport", file_label="Pasport", filename="p2.jpg", content=b"67890")
        self.assertEqual(calculate_group_size([f1, f2]), 10)

    def test_single_document_oversize_blocking(self):
        oversized_bytes = b"X" * (19 * 1024 * 1024)  # 19 MB
        f1 = ProcessedFile(
            doc_id="passport",
            file_label="Pasport",
            filename="large_passport.jpg",
            content=oversized_bytes,
            doc_title="Паспорт або ID-карта",
        )

        result = pack_into_email_parts([f1])
        self.assertFalse(result.ok)
        self.assertEqual(result.oversized_doc_id, "passport")
        self.assertEqual(result.oversized_doc_title, "Паспорт або ID-карта")
        self.assertIn("завеликий", result.error_message)
        self.assertIn("19.0 MB", result.error_message)
        self.assertIn("300", result.error_message)

    def test_single_pdf_document_oversize_blocking(self):
        oversized_bytes = b"X" * (16 * 1024 * 1024)  # 16 MB
        f1 = ProcessedFile(
            doc_id="reserve_plus",
            file_label="Reserve_plus",
            filename="large_reserve.pdf",
            content=oversized_bytes,
            doc_title="Витяг з Резерв+",
        )

        result = pack_into_email_parts([f1])
        self.assertFalse(result.ok)
        self.assertEqual(result.oversized_doc_id, "reserve_plus")
        self.assertIn("меншого розміру", result.error_message)

    def test_multi_file_document_oversize_blocking(self):
        ten_mb = b"X" * (10 * 1024 * 1024)
        f1 = ProcessedFile(doc_id="passport", file_label="Pasport", filename="p1.jpg", content=ten_mb, doc_title="Паспорт")
        f2 = ProcessedFile(doc_id="passport", file_label="Pasport", filename="p2.jpg", content=ten_mb, doc_title="Паспорт")

        result = pack_into_email_parts([f1, f2])
        self.assertFalse(result.ok)
        self.assertEqual(result.oversized_doc_id, "passport")

    def test_bin_packing_single_part(self):
        five_mb = b"X" * (5 * 1024 * 1024)
        f1 = ProcessedFile(doc_id="ipn", file_label="IPN", filename="ipn.pdf", content=five_mb, doc_title="ІПН")
        f2 = ProcessedFile(doc_id="passport", file_label="Pasport", filename="p1.jpg", content=five_mb, doc_title="Паспорт")

        result = pack_into_email_parts([f1, f2])
        self.assertTrue(result.ok)
        self.assertEqual(len(result.parts), 1)
        self.assertEqual(result.parts[0].part_number, 1)
        self.assertEqual(result.parts[0].total_parts, 1)

    def test_bin_packing_atomic_group_integrity(self):
        # passport group = 10 MB (2 files x 5 MB)
        # ipn group = 4 MB
        # etk group = 6 MB
        five_mb = b"X" * (5 * 1024 * 1024)
        four_mb = b"X" * (4 * 1024 * 1024)
        six_mb = b"X" * (6 * 1024 * 1024)

        f_pass1 = ProcessedFile(doc_id="passport", file_label="Pasport", filename="p1.jpg", content=five_mb, doc_title="Паспорт")
        f_pass2 = ProcessedFile(doc_id="passport", file_label="Pasport", filename="p2.jpg", content=five_mb, doc_title="Паспорт")
        f_ipn = ProcessedFile(doc_id="ipn", file_label="IPN", filename="ipn.pdf", content=four_mb, doc_title="ІПН")
        f_etk = ProcessedFile(doc_id="etk", file_label="ETK", filename="etk.pdf", content=six_mb, doc_title="Трудова книжка")

        result = pack_into_email_parts([f_pass1, f_pass2, f_ipn, f_etk])
        self.assertTrue(result.ok)
        self.assertEqual(len(result.parts), 2)

        # Part 1: passport (10MB) + ipn (4MB) = 14MB <= 18MB
        # Part 2: etk (6MB) = 6MB <= 18MB
        self.assertEqual(result.parts[0].doc_ids, ["passport", "ipn"])
        self.assertEqual(len(result.parts[0].files), 3)

        self.assertEqual(result.parts[1].doc_ids, ["etk"])
        self.assertEqual(len(result.parts[1].files), 1)

    def test_manifest_text_formatting(self):
        f1 = ProcessedFile(doc_id="ipn", file_label="IPN", filename="ipn.pdf", content=b"123", doc_title="ІПН")
        f2 = ProcessedFile(doc_id="passport", file_label="Pasport", filename="p1.jpg", content=b"456", doc_title="Паспорт або ID-карта")
        f3 = ProcessedFile(doc_id="passport", file_label="Pasport", filename="p2.jpg", content=b"789", doc_title="Паспорт або ID-карта")

        all_grouped = group_by_document([f1, f2, f3])
        manifest = generate_manifest_text(
            part_number=1,
            total_parts=2,
            part_files=[f1, f2, f3],
            all_grouped_files=all_grouped,
        )

        self.assertIn("Вміст частини 1/2:", manifest)
        self.assertIn(" - ІПН (1 файл)", manifest)
        self.assertIn(" - Паспорт або ID-карта (2 файл(ів))", manifest)
        self.assertIn("Усього документів у пакеті: ІПН, Паспорт або ID-карта (2 стор.)", manifest)

    def test_empty_files_list(self):
        result = pack_into_email_parts([])
        self.assertTrue(result.ok)
        self.assertEqual(result.parts, [])


if __name__ == "__main__":
    unittest.main()
