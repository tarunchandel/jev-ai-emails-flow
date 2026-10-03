"""Unit tests for Corporate Actions workflow solution and Jev AI decisions."""

from pathlib import Path
from src.parser import load_emails_from_directory
from src.jev_client import JevEmailClassifier, build_email_questions
from src.workflow_engine import WorkflowEngine, CORPORATE_ACTIONS_QUEUE_MAP
from src.dataset_generator import CORPORATE_ACTIONS_DIR, generate_corporate_actions_dataset


def test_corporate_actions_dataset_loaded():
    """Verify corporate actions emails are generated and loadable."""
    if not CORPORATE_ACTIONS_DIR.exists() or not list(CORPORATE_ACTIONS_DIR.glob("*")):
        generate_corporate_actions_dataset(CORPORATE_ACTIONS_DIR)

    emails = load_emails_from_directory(CORPORATE_ACTIONS_DIR)
    assert len(emails) >= 10
    subjects = [e.subject for e in emails]
    assert any("Tender Offer" in s for s in subjects)
    assert any("Cash Dividend" in s or "DIVIDEND" in s for s in subjects)
    assert any("Rights Issue" in s or "RIGHTS" in s for s in subjects)
    assert any("Reconciliation Break" in s or "BREAK" in s for s in subjects)


def test_corporate_actions_questions_schema():
    """Verify questions configuration for corporate actions."""
    questions = build_email_questions(domain="corporate_actions")
    assert "category" in questions
    assert "urgency" in questions
    assert "severity_priority" in questions
    assert "requires_human_escalation" in questions
    assert "suggested_action" in questions

    criteria = questions["category"].criteria
    assert "voluntary_corporate_action" in criteria
    assert "mandatory_corporate_action" in criteria
    assert "reconciliation_exception" in criteria
    assert "proxy_voting_agm" in criteria


def test_corporate_actions_classification_and_routing():
    """Verify end-to-end classification and desk routing for corporate action events."""
    classifier = JevEmailClassifier(force_mock=True, domain="corporate_actions")
    engine = WorkflowEngine(domain="corporate_actions")

    emails = load_emails_from_directory(CORPORATE_ACTIONS_DIR)
    email_map = {Path(e.source_file).name if e.source_file else e.id: e for e in emails}

    # 1. Voluntary Tender Offer
    tender_email = email_map.get("01_voluntary_tender_offer_deadline.eml")
    assert tender_email is not None
    tender_decision = classifier.classify_email(tender_email)
    assert tender_decision.category == "voluntary_corporate_action"
    assert tender_decision.suggested_action == "solicit_pm_election"
    assert tender_decision.urgency_probability >= 0.80
    assert tender_decision.severity_score >= 4

    tender_rec = engine.process(tender_email, tender_decision)
    assert tender_rec.workflow.target_queue == CORPORATE_ACTIONS_QUEUE_MAP["voluntary_corporate_action"]
    assert tender_rec.workflow.escalate_to_human is True

    # 2. Mandatory Cash Dividend
    div_email = email_map.get("02_cash_dividend_declaration.eml")
    assert div_email is not None
    div_decision = classifier.classify_email(div_email)
    assert div_decision.category == "mandatory_corporate_action"
    assert div_decision.suggested_action == "book_entitlement_accounting"
    assert div_decision.severity_score <= 2

    div_rec = engine.process(div_email, div_decision)
    assert div_rec.workflow.target_queue == CORPORATE_ACTIONS_QUEUE_MAP["mandatory_corporate_action"]
    assert div_rec.workflow.escalate_to_human is False

    # 3. Critical Reconciliation Break
    recon_email = email_map.get("07_custodian_reconciliation_break.eml")
    assert recon_email is not None
    recon_decision = classifier.classify_email(recon_email)
    assert recon_decision.category == "reconciliation_exception"
    assert recon_decision.suggested_action == "escalate_custodian_break"
    assert recon_decision.severity_score == 5
    assert recon_decision.urgency_probability >= 0.90

    recon_rec = engine.process(recon_email, recon_decision)
    assert recon_rec.workflow.target_queue == CORPORATE_ACTIONS_QUEUE_MAP["reconciliation_exception"]
    assert recon_rec.workflow.alert_level == "CRITICAL"
    assert recon_rec.workflow.escalate_to_human is True
    assert "SEV-1-CRITICAL" in recon_rec.workflow.tags

    # 4. Proxy Voting AGM
    proxy_email = email_map.get("05_proxy_voting_agm_resolutions.json")
    assert proxy_email is not None
    proxy_decision = classifier.classify_email(proxy_email)
    assert proxy_decision.category == "proxy_voting_agm"
    assert proxy_decision.suggested_action == "submit_proxy_ballot"

    proxy_rec = engine.process(proxy_email, proxy_decision)
    assert proxy_rec.workflow.target_queue == CORPORATE_ACTIONS_QUEUE_MAP["proxy_voting_agm"]

    # 5. Financial Spam Filtering
    spam_email = email_map.get("10_unsolicited_financial_newsletter_spam.txt")
    assert spam_email is not None
    spam_decision = classifier.classify_email(spam_email)
    assert spam_decision.category == "general_inquiry_spam"
    assert spam_decision.suggested_action == "auto_archive"
    assert spam_decision.urgency_probability < 0.15

    spam_rec = engine.process(spam_email, spam_decision)
    assert spam_rec.workflow.target_queue == CORPORATE_ACTIONS_QUEUE_MAP["general_inquiry_spam"]
    assert spam_rec.workflow.escalate_to_human is False
