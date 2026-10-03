"""Unit tests for Jev AI client and question configuration."""

from src.models import EmailMessage
from src.jev_client import JevEmailClassifier, build_email_questions


def test_build_email_questions():
    questions = build_email_questions()
    assert "category" in questions
    assert "urgency" in questions
    assert "severity_priority" in questions
    assert "requires_human_escalation" in questions
    assert "suggested_action" in questions


def test_jev_classifier_simulator_security():
    classifier = JevEmailClassifier(force_mock=True)
    assert not classifier.is_live

    msg = EmailMessage(
        id="test-sec-1",
        subject="URGENT: Database breach and credential leak detected",
        body="Plaintext passwords leaked on pastebin. Immediate password reset required.",
    )

    decision = classifier.classify_email(msg)
    assert decision.category == "account_security"
    assert decision.severity_score >= 4
    assert decision.urgency_probability > 0.8
    assert decision.escalation_probability > 0.7
    assert decision.suggested_action == "immediate_security_lockout"
    assert decision.latency_ms > 0


def test_jev_classifier_simulator_feature_request():
    classifier = JevEmailClassifier(force_mock=True)

    msg = EmailMessage(
        id="test-feat-1",
        subject="Feature idea: Support dark mode theme",
        body="Would love to have an option to switch to a darker color palette.",
    )

    decision = classifier.classify_email(msg)
    assert decision.category == "feature_request"
    assert decision.severity_score <= 2
    assert decision.urgency_probability < 0.3
    assert decision.suggested_action == "add_to_product_backlog"
