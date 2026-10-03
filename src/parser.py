"""Email parsing module supporting .eml, .json, and raw text files with attachment detection."""

from __future__ import annotations
import email
from email import policy
from email.message import EmailMessage as PyEmailMessage
import json
from pathlib import Path
import re
from typing import List, Optional, Union
import uuid

from src.models import EmailAttachment, EmailMessage


def _strip_html(html_content: str) -> str:
    """Strip basic HTML tags and normalize whitespace."""
    clean = re.sub(r"<[^>]+>", " ", html_content)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def _infer_attachments_from_text(body: str, subject: str) -> List[EmailAttachment]:
    """Detect explicit mentions of attached PDFs or documents in context."""
    text = f"{subject}\n{body}".lower()
    inferred: List[EmailAttachment] = []

    # Check for explicit PDF/image attachment cues
    pdf_match = re.search(r"attached\s+([a-zA-Z0-9_\-\s]{3,35}\.(?:pdf|png|jpg|tiff|tif|docx))", text, re.IGNORECASE)
    if pdf_match:
        fn = pdf_match.group(1).strip()
        inferred.append(EmailAttachment(filename=fn, content_type="application/pdf", is_mock=True))
    elif re.search(r"\b(attached\s+(corporate\s+proxy\s+document|tender\s+document|prospectus|ballot|pdf|file|form))\b", text, re.IGNORECASE):
        # Specific name extraction
        if "proxy" in text:
            fn = "corporate_proxy_restructuring_document.pdf"
        elif "tender" in text:
            fn = "tender_offer_terms_prospectus.pdf"
        elif "rights" in text:
            fn = "rights_offering_circular.pdf"
        elif "merger" in text:
            fn = "merger_proxy_statement.pdf"
        else:
            fn = "corporate_action_details.pdf"
        inferred.append(EmailAttachment(filename=fn, content_type="application/pdf", is_mock=True))

    return inferred


def parse_eml_bytes(data: bytes, file_path: Optional[str] = None) -> EmailMessage:
    """Parse raw bytes of an .eml RFC 822 / MIME email."""
    msg: PyEmailMessage = email.message_from_bytes(data, policy=policy.default)

    subject = str(msg.get("subject", "") or "")
    sender = str(msg.get("from", "") or "")
    recipient = str(msg.get("to", "") or "")
    date_str = str(msg.get("date", "") or "")

    headers = {k: str(v) for k, v in msg.items()}

    body_text = ""
    attachments: List[EmailAttachment] = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition") or "")
            filename = part.get_filename()

            if "attachment" in content_disposition.lower() or filename:
                att_fn = filename or f"attachment_{len(attachments)+1}.pdf"
                payload = part.get_payload(decode=True)
                size_bytes = len(payload) if payload else 0
                attachments.append(
                    EmailAttachment(
                        filename=att_fn,
                        content_type=content_type or "application/pdf",
                        size_bytes=size_bytes,
                    )
                )
                continue

            if content_type == "text/plain":
                part_body = part.get_content()
                if isinstance(part_body, str):
                    body_text += part_body + "\n"
            elif content_type == "text/html" and not body_text:
                part_body = part.get_content()
                if isinstance(part_body, str):
                    body_text += _strip_html(part_body) + "\n"
    else:
        content_type = msg.get_content_type()
        part_body = msg.get_content()
        if isinstance(part_body, str):
            if content_type == "text/html":
                body_text = _strip_html(part_body)
            else:
                body_text = part_body

    msg_id = headers.get("Message-ID") or f"eml-{uuid.uuid4().hex[:8]}"
    cleaned_body = body_text.strip()

    if not attachments:
        attachments = _infer_attachments_from_text(cleaned_body, subject)

    return EmailMessage(
        id=str(msg_id).strip("<> "),
        subject=subject.strip(),
        sender=sender.strip(),
        recipient=recipient.strip(),
        date=date_str.strip() or None,
        body=cleaned_body,
        raw_headers=headers,
        source_file=file_path,
        attachments=attachments,
    )


def parse_json_data(data: Union[str, dict], file_path: Optional[str] = None) -> List[EmailMessage]:
    """Parse JSON string or dictionary / list of dictionaries into EmailMessage objects."""
    if isinstance(data, str):
        parsed = json.loads(data)
    else:
        parsed = data

    items = parsed if isinstance(parsed, list) else [parsed]
    results: List[EmailMessage] = []

    for idx, item in enumerate(items):
        msg_id = (
            item.get("id")
            or item.get("message_id")
            or f"json-{uuid.uuid4().hex[:8]}"
        )
        body = item.get("body") or item.get("content", "")
        subject = item.get("subject", "")

        attachments: List[EmailAttachment] = []
        raw_att = item.get("attachments", [])
        for att in raw_att:
            if isinstance(att, dict):
                attachments.append(
                    EmailAttachment(
                        filename=att.get("filename", "document.pdf"),
                        content_type=att.get("content_type", "application/pdf"),
                        size_bytes=att.get("size_bytes", 0),
                        extracted_text=att.get("extracted_text"),
                    )
                )
            elif isinstance(att, str):
                attachments.append(EmailAttachment(filename=att))

        if not attachments:
            attachments = _infer_attachments_from_text(body, subject)

        msg = EmailMessage(
            id=str(msg_id),
            subject=subject,
            sender=item.get("sender") or item.get("from", ""),
            recipient=item.get("recipient") or item.get("to", ""),
            date=item.get("date"),
            body=body,
            raw_headers=item.get("headers", {}),
            source_file=file_path,
            attachments=attachments,
        )
        results.append(msg)

    return results


def parse_raw_text(text: str, file_path: Optional[str] = None) -> EmailMessage:
    """Parse raw text string, attempting basic header extraction (Subject:, From:, etc.)."""
    lines = text.strip().splitlines()
    headers = {}
    body_lines = []
    in_headers = True

    for line in lines:
        if in_headers:
            if not line.strip():
                in_headers = False
                continue
            if ":" in line:
                key, val = line.split(":", 1)
                headers[key.strip().lower()] = val.strip()
            else:
                in_headers = False
                body_lines.append(line)
        else:
            body_lines.append(line)

    subject = headers.get("subject", "")
    sender = headers.get("from", "")
    recipient = headers.get("to", "")
    date_str = headers.get("date")

    body = "\n".join(body_lines).strip()
    if not body and not headers:
        body = text.strip()

    if not subject and body:
        first_line = body.splitlines()[0]
        subject = first_line[:60]

    attachments = _infer_attachments_from_text(body, subject)

    return EmailMessage(
        id=f"txt-{uuid.uuid4().hex[:8]}",
        subject=subject,
        sender=sender,
        recipient=recipient,
        date=date_str,
        body=body,
        raw_headers=headers,
        source_file=file_path,
        attachments=attachments,
    )


def load_email_file(file_path: Union[str, Path]) -> List[EmailMessage]:
    """Detect file extension and parse into EmailMessage(s)."""
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = p.suffix.lower()
    if ext == ".eml":
        return [parse_eml_bytes(p.read_bytes(), file_path=str(p))]
    elif ext == ".json":
        return parse_json_data(p.read_text(encoding="utf-8"), file_path=str(p))
    elif ext in [".txt", ".msg"]:
        return [parse_raw_text(p.read_text(encoding="utf-8", errors="ignore"), file_path=str(p))]
    else:
        return [parse_raw_text(p.read_text(encoding="utf-8", errors="ignore"), file_path=str(p))]


def load_emails_from_directory(dir_path: Union[str, Path]) -> List[EmailMessage]:
    """Scan directory recursively for supported email files and parse them."""
    p = Path(dir_path)
    if not p.exists() or not p.is_dir():
        return []

    emails: List[EmailMessage] = []
    for ext in ("*.eml", "*.json", "*.txt"):
        for file in sorted(p.glob(ext)):
            try:
                emails.extend(load_email_file(file))
            except Exception as err:
                print(f"Warning: could not parse {file}: {err}")

    return emails
