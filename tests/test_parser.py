"""Unit tests for email parsing functionality."""

from src.parser import parse_raw_text, parse_json_data, parse_eml_bytes


def test_parse_raw_text():
    text = """Subject: Test Subject
From: sender@example.com
To: receiver@example.com
Date: Sat, 03 Oct 2026 10:00:00 +0000

This is the body of the test email.
It has two lines."""

    msg = parse_raw_text(text)
    assert msg.subject == "Test Subject"
    assert msg.sender == "sender@example.com"
    assert msg.recipient == "receiver@example.com"
    assert "This is the body" in msg.body
    assert "two lines" in msg.body


def test_parse_json_data():
    raw_json = """[
        {
            "id": "MSG-001",
            "subject": "Invoice Question",
            "from": "user@client.org",
            "to": "billing@saas.com",
            "body": "Can you resend invoice #102?"
        }
    ]"""

    msgs = parse_json_data(raw_json)
    assert len(msgs) == 1
    msg = msgs[0]
    assert msg.id == "MSG-001"
    assert msg.subject == "Invoice Question"
    assert msg.sender == "user@client.org"
    assert msg.body == "Can you resend invoice #102?"


def test_parse_eml_bytes():
    from email.message import EmailMessage as PyEmailMessage

    py_msg = PyEmailMessage()
    py_msg["Subject"] = "System Notification"
    py_msg["From"] = "sys@domain.com"
    py_msg["To"] = "admin@domain.com"
    py_msg.set_content("Server CPU load above 95%.")

    raw_bytes = py_msg.as_bytes()
    msg = parse_eml_bytes(raw_bytes)

    assert msg.subject == "System Notification"
    assert msg.sender == "sys@domain.com"
    assert msg.recipient == "admin@domain.com"
    assert "Server CPU load above 95%" in msg.body
