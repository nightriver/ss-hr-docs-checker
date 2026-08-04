"""
emailer.py — Anonymized email delivery module for HR Docs Checker v2.2.

Provides:
- SendResult data structure
- MailProvider Protocol
- MockMailProvider & GmailSMTPProvider implementations
- DocsMailer orchestrator with sent_parts tracking & PII-free anonymized logging
- build_email_message helper for UTF-8 MIME email construction
- create_mailer_from_secrets factory function
"""

from dataclasses import dataclass
from email.message import EmailMessage
import logging
import mimetypes
import smtplib
import ssl
from typing import Optional, Protocol, Sequence, TypedDict

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SendResult:
    """
    Represents the result of an email sending attempt.

    Attributes:
        ok: True if transmission succeeded.
        error_type: Name of exception class or failure indicator if unsuccessful.
                    Contains NO PII or sensitive message details.
    """
    ok: bool
    error_type: Optional[str] = None


class MailProvider(Protocol):
    """
    Protocol defining interface for email transmission backends.
    """
    def send(self, msg: EmailMessage) -> bool:
        """
        Sends a single EmailMessage object.

        :param msg: Prepared EmailMessage object
        :return: True if sent successfully
        :raises Exception: On network, auth, or protocol failure
        """
        ...


class MockMailProvider:
    """
    Mock implementation of MailProvider for testing and offline execution.
    """
    def __init__(
        self,
        should_succeed: bool = True,
        raise_exception: Optional[Exception] = None,
    ):
        self.should_succeed = should_succeed
        self.raise_exception = raise_exception
        self.sent_messages: list[EmailMessage] = []

    def send(self, msg: EmailMessage) -> bool:
        if self.raise_exception:
            raise self.raise_exception
        if self.should_succeed:
            self.sent_messages.append(msg)
            return True
        return False


class GmailSMTPProvider:
    """
    Gmail SMTP implementation using STARTTLS on port 587.
    """
    def __init__(
        self,
        username: str,
        password: str,
        host: str = "smtp.gmail.com",
        port: int = 587,
        timeout: int = 30,
    ):
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.timeout = timeout

    def send(self, msg: EmailMessage) -> bool:
        context = ssl.create_default_context()
        with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
            server.starttls(context=context)
            server.login(self.username, self.password)
            server.send_message(msg)
        return True


class DocsMailer:
    """
    Orchestrates sending single or multi-part document emails to HR with retry awareness.
    Enforces strict PII-free logging (§2 & §9).
    """
    def __init__(self, provider: MailProvider, from_addr: str):
        self.provider = provider
        self.from_addr = from_addr

    def send_parts(
        self,
        hr_to: str,
        parts: list[EmailMessage],
        sent_parts: Optional[set[int]] = None,
    ) -> list[SendResult]:
        """
        Sends sequence of EmailMessage parts, skipping any 0-based indices present in sent_parts.
        Updates sent_parts set in-place upon successful transmission of each part.
        Stops immediately on the first failed part to maintain sequence integrity.
        """
        results: list[SendResult] = []
        total = len(parts)

        for i, msg in enumerate(parts):
            if sent_parts is not None and i in sent_parts:
                logger.info("send_skip part=%d/%d already_sent=True", i + 1, total)
                results.append(SendResult(ok=True))
                continue

            if "From" not in msg:
                msg["From"] = self.from_addr
            if "To" not in msg:
                msg["To"] = hr_to

            logger.info("send_attempt part=%d/%d", i + 1, total)

            try:
                ok = self.provider.send(msg)
                if ok:
                    logger.info("send_success part=%d/%d", i + 1, total)
                    if sent_parts is not None:
                        sent_parts.add(i)
                    results.append(SendResult(ok=True))
                else:
                    logger.warning("send_failed part=%d/%d error_type=ProviderReturnedFalse", i + 1, total)
                    results.append(SendResult(ok=False, error_type="ProviderReturnedFalse"))
                    break
            except Exception as e:
                err_name = type(e).__name__
                logger.warning("send_failed part=%d/%d error_type=%s", i + 1, total, err_name)
                results.append(SendResult(ok=False, error_type=err_name))
                break

        return results


class AttachmentDict(TypedDict):
    filename: str
    content: bytes
    mime_type: Optional[str]


def build_email_message(
    from_addr: str,
    to_addr: str,
    subject: str,
    body_text: str,
    attachments: Optional[Sequence[AttachmentDict]] = None,
) -> EmailMessage:
    """
    Constructs an EmailMessage with UTF-8 plain text body and MIME attachments.
    """
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(body_text, charset="utf-8")

    if attachments:
        for att in attachments:
            fname = att["filename"]
            content = att["content"]
            mime_str = att.get("mime_type")

            if not mime_str:
                mime_str, _ = mimetypes.guess_type(fname)
            if not mime_str:
                ext = fname.split(".")[-1].lower() if "." in fname else ""
                if ext in ("jpg", "jpeg"):
                    mime_str = "image/jpeg"
                elif ext == "png":
                    mime_str = "image/png"
                elif ext == "pdf":
                    mime_str = "application/pdf"
                else:
                    mime_str = "application/octet-stream"

            maintype, subtype = mime_str.split("/", 1)
            msg.add_attachment(
                content,
                maintype=maintype,
                subtype=subtype,
                filename=fname,
            )

    return msg


def create_mailer_from_secrets(secrets: dict) -> tuple[DocsMailer, str]:
    """
    Creates DocsMailer instance and recipient HR email address from Streamlit secrets dictionary.
    Supports single email string, comma-separated string of multiple emails, or a list of emails.

    Expected secrets.toml structure:
        [smtp]
        provider = "gmail"
        username = "hr-bot@gmail.com"
        password = "xxxx xxxx xxxx xxxx"
        from_addr = "hr-bot@gmail.com"
        hr_to = "hr@smart-solutions.ua, hr2@smart-solutions.ua"
        use_mock = false
    """
    smtp_sec = secrets.get("smtp", {})
    use_mock = smtp_sec.get("use_mock", False)
    from_addr = smtp_sec.get("from_addr", "noreply@smart-solutions.ua")
    raw_hr_to = smtp_sec.get("hr_to", "")

    if isinstance(raw_hr_to, (list, tuple)):
        hr_to = ", ".join(str(addr).strip() for addr in raw_hr_to if addr)
    else:
        hr_to = str(raw_hr_to).strip()

    if not hr_to:
        raise ValueError("Адресу отримувача HR (hr_to) не вказано або вона порожня у налаштуваннях secrets.")

    if use_mock:
        provider: MailProvider = MockMailProvider(should_succeed=True)
    else:
        username = smtp_sec.get("username", "")
        password = smtp_sec.get("password", "")
        if not username or not password:
            raise ValueError("SMTP username or password missing in secrets config.")
        provider = GmailSMTPProvider(username=username, password=password)

    return DocsMailer(provider=provider, from_addr=from_addr), hr_to
