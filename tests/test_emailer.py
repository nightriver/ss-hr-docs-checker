"""
tests/test_emailer.py — Unit tests for emailer.py in HR Docs Checker v2.2
"""

from email.message import EmailMessage
import socket
import unittest
from unittest.mock import MagicMock, patch

from emailer import (
    DocsMailer,
    GmailSMTPProvider,
    MockMailProvider,
    SendResult,
    build_email_message,
    create_mailer_from_secrets,
)


class TestSendResult(unittest.TestCase):
    def test_send_result_instantiation(self):
        res_ok = SendResult(ok=True)
        self.assertTrue(res_ok.ok)
        self.assertIsNone(res_ok.error_type)

        res_err = SendResult(ok=False, error_type="SMTPAuthenticationError")
        self.assertFalse(res_err.ok)
        self.assertEqual(res_err.error_type, "SMTPAuthenticationError")


class TestMockMailProvider(unittest.TestCase):
    def test_mock_provider_success(self):
        msg = EmailMessage()
        provider = MockMailProvider(should_succeed=True)
        self.assertTrue(provider.send(msg))
        self.assertEqual(len(provider.sent_messages), 1)

    def test_mock_provider_failure(self):
        msg = EmailMessage()
        provider = MockMailProvider(should_succeed=False)
        self.assertFalse(provider.send(msg))
        self.assertEqual(len(provider.sent_messages), 0)

    def test_mock_provider_exception(self):
        msg = EmailMessage()
        provider = MockMailProvider(raise_exception=RuntimeError("SMTP down"))
        with self.assertRaises(RuntimeError):
            provider.send(msg)


class TestGmailSMTPProvider(unittest.TestCase):
    @patch("smtplib.SMTP")
    def test_gmail_provider_success(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        provider = GmailSMTPProvider("test_user", "test_pass")
        msg = EmailMessage()
        res = provider.send(msg)

        self.assertTrue(res)
        mock_smtp_cls.assert_called_once_with("smtp.gmail.com", 587, timeout=30)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test_user", "test_pass")
        mock_server.send_message.assert_called_once_with(msg)


class TestDocsMailer(unittest.TestCase):
    def test_docs_mailer_single_part(self):
        provider = MockMailProvider(should_succeed=True)
        mailer = DocsMailer(provider, "from@test.com")
        msg = EmailMessage()

        results = mailer.send_parts("hr@test.com", [msg])
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].ok)
        self.assertEqual(msg["From"], "from@test.com")
        self.assertEqual(msg["To"], "hr@test.com")

    def test_docs_mailer_retry_logic(self):
        msg1 = EmailMessage()
        msg2 = EmailMessage()

        # Step 1: Provider fails on 2nd part
        call_count = 0
        def side_effect(m):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise socket.timeout("Timed out")
            return True

        provider = MockMailProvider()
        provider.send = side_effect

        mailer = DocsMailer(provider, "from@test.com")
        sent_parts: set[int] = set()

        results1 = mailer.send_parts("hr@test.com", [msg1, msg2], sent_parts=sent_parts)
        self.assertEqual(len(results1), 2)
        self.assertTrue(results1[0].ok)
        self.assertFalse(results1[1].ok)
        self.assertEqual(results1[1].error_type, "TimeoutError")
        self.assertEqual(sent_parts, {0})

        # Step 2: Retry with sent_parts={0} and working provider
        provider_retry = MockMailProvider(should_succeed=True)
        mailer_retry = DocsMailer(provider_retry, "from@test.com")
        results2 = mailer_retry.send_parts("hr@test.com", [msg1, msg2], sent_parts=sent_parts)

        self.assertEqual(len(results2), 2)
        self.assertTrue(results2[0].ok)
        self.assertTrue(results2[1].ok)
        self.assertEqual(sent_parts, {0, 1})
        self.assertEqual(len(provider_retry.sent_messages), 1)


class TestBuildEmailMessage(unittest.TestCase):
    def test_build_email_message(self):
        msg = build_email_message(
            from_addr="from@test.com",
            to_addr="to@test.com",
            subject="Test Subject",
            body_text="Test Body Text",
            attachments=[
                {"filename": "doc.pdf", "content": b"%PDF-1.4", "mime_type": None},
                {"filename": "photo.jpg", "content": b"\xff\xd8\xff", "mime_type": "image/jpeg"},
            ],
        )

        self.assertEqual(msg["Subject"], "Test Subject")
        self.assertEqual(msg["From"], "from@test.com")
        self.assertEqual(msg["To"], "to@test.com")
        self.assertEqual(msg.get_body(preferencelist=("plain",)).get_content().strip(), "Test Body Text")

        attachments = list(msg.iter_attachments())
        self.assertEqual(len(attachments), 2)
        self.assertEqual(attachments[0].get_filename(), "doc.pdf")
        self.assertEqual(attachments[0].get_content_type(), "application/pdf")
        self.assertEqual(attachments[1].get_filename(), "photo.jpg")
        self.assertEqual(attachments[1].get_content_type(), "image/jpeg")


class TestLoggingPrivacy(unittest.TestCase):
    def test_anonymized_logging_no_pii(self):
        provider = MockMailProvider(should_succeed=True)
        mailer = DocsMailer(provider, "from@test.com")
        msg = EmailMessage()
        msg["Subject"] = "Private candidate Petro Ivanenko"

        with self.assertLogs("emailer", level="INFO") as cm:
            mailer.send_parts("candidate@secret.com", [msg])

        log_output = "\n".join(cm.output)
        self.assertIn("send_attempt", log_output)
        self.assertIn("send_success", log_output)
        self.assertNotIn("Petro", log_output)
        self.assertNotIn("Ivanenko", log_output)
        self.assertNotIn("candidate@secret.com", log_output)


class TestCreateMailerFromSecrets(unittest.TestCase):
    def test_create_mailer_mock(self):
        secrets_mock = {
            "smtp": {
                "use_mock": True,
                "from_addr": "bot@test.com",
                "hr_to": "hr@test.com",
            }
        }
        mailer, hr_to = create_mailer_from_secrets(secrets_mock)
        self.assertIsInstance(mailer.provider, MockMailProvider)
        self.assertEqual(hr_to, "hr@test.com")

    def test_create_mailer_gmail(self):
        secrets_real = {
            "smtp": {
                "use_mock": False,
                "username": "user",
                "password": "pass",
                "from_addr": "bot@test.com",
                "hr_to": "hr@test.com",
            }
        }
        mailer, hr_to = create_mailer_from_secrets(secrets_real)
        self.assertIsInstance(mailer.provider, GmailSMTPProvider)
        self.assertEqual(hr_to, "hr@test.com")


if __name__ == "__main__":
    unittest.main()
