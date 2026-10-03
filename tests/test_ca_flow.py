"""Tests for Corporate Actions End-to-End Flow: Jev Ingestion Gate, Gemini OCR, Jev Core Decision, and Router."""

import pytest
from src.models import EmailMessage, EmailAttachment
from src.jev_client import JevEmailClassifier, build_ingestion_gate_questions, build_core_decision_questions
from src.gemini_service import GeminiService
from src.flow_orchestrator import CorporateActionsFlowOrchestrator


def test_ingestion_gate_questions_schema():
    """Verify Stage 1 question schema for Jev AI Ingestion Gate."""
    questions = build_ingestion_gate_questions()
    assert "requires_heavy_ocr" in questions
    assert questions["requires_heavy_ocr"].type == "noul"
    assert "attached PDF or image" in questions["requires_heavy_ocr"].instructions


def test_core_decision_questions_schema():
    """Verify Stage 3 questions schema for Jev AI Core Decision matrix."""
    questions = build_core_decision_questions()
    assert "event_type" in questions
    assert questions["event_type"].type == "choice"
    criteria = questions["event_type"].criteria
    assert "Cash_Dividend" in criteria
    assert "Stock_Dividend" in criteria
    assert "Merger_Acquisition" in criteria
    assert "Ticker_Change" in criteria
    assert "Spam_Or_Irrelevant" in criteria

    assert "is_actionable" in questions
    assert questions["is_actionable"].type == "noul"

    assert "urgency" in questions
    assert questions["urgency"].type == "score"
    assert len(questions["urgency"].criteria) == 10


def test_ingestion_gate_ocr_decision():
    """Verify Ingestion Gate evaluates attachment requirement correctly."""
    classifier = JevEmailClassifier(force_mock=True)

    # 1. Context lacking actionable terms, referring to attached document -> OCR Required
    email_with_pdf = EmailMessage(
        id="gate-test-01",
        sender="proxy-alerts@custodian.com",
        subject="Urgent: Action Required for ABC Corp Merger",
        body="Please review the attached corporate proxy document for restructuring options.",
    )
    result_with_pdf = classifier.evaluate_ingestion_gate(email_with_pdf)
    assert result_with_pdf.requires_heavy_ocr is True
    assert result_with_pdf.ocr_probability > 0.50

    # 2. Context with complete terms in body -> No OCR required (Raw Text Envelope)
    email_full_text = EmailMessage(
        id="gate-test-02",
        sender="ca-announcements@euroclear.com",
        subject="MANDATORY CASH DIVIDEND: Novo Nordisk A/S",
        body="Gross Dividend Rate: DKK 6.400000 per share. Ex-Date: 10-OCT-2026. Payment Date: 20-OCT-2026.",
    )
    result_full_text = classifier.evaluate_ingestion_gate(email_full_text)
    assert result_full_text.requires_heavy_ocr is False
    assert result_full_text.ocr_probability <= 0.50


def test_gemini_ocr_flattening():
    """Verify Gemini OCR flattens attached document to structured text."""
    gemini = GeminiService(force_mock=True)
    email = EmailMessage(
        id="ocr-test",
        sender="proxy-alerts@custodian.com",
        subject="Urgent: Action Required for ABC Corp Merger",
        body="Please review the attached corporate proxy document for restructuring options.",
        attachments=[EmailAttachment(filename="abc_corp_merger_proxy.pdf")],
    )
    ocr_text = gemini.perform_ocr(email)
    assert "ABC CORP" in ocr_text or "MERGER" in ocr_text.upper()
    assert "Option 1" in ocr_text or "Cash" in ocr_text


def test_core_decision_matrix():
    """Verify Jev Core Decision returns Choice, Noul, and Score (Scale 1-10)."""
    classifier = JevEmailClassifier(force_mock=True)

    # Tender Offer (Urgent voluntary merger/tender)
    tender_context = (
        "Voluntary Tender Offer / Takeover Bid. Security: Quantum Dynamics. "
        "Offer Terms: USD 54.00 Cash OR 1.25 Hyperion Common Shares. "
        "Custodian Cutoff: 04-OCT-2026 17:00 EST within 48 hours."
    )
    dec = classifier.evaluate_core_decision(
        EmailMessage(id="core-01", subject="Tender", body=tender_context),
        tender_context,
    )
    assert dec.event_type == "Merger_Acquisition"
    assert dec.is_actionable is True
    assert dec.urgency_score == 10

    # Mandatory Cash Dividend
    div_context = (
        "Mandatory Cash Dividend (DVCA). Gross Dividend: DKK 6.40 per share. "
        "Ex-Date: 10-OCT-2026. Payment Date: 20-OCT-2026."
    )
    dec_div = classifier.evaluate_core_decision(
        EmailMessage(id="core-02", subject="Div", body=div_context),
        div_context,
    )
    assert dec_div.event_type == "Cash_Dividend"
    assert dec_div.is_actionable is False
    assert dec_div.urgency_score <= 5

    # Spam
    spam_context = "Claim your 1000% APY crypto arbitrage bot guaranteed today!"
    dec_spam = classifier.evaluate_core_decision(
        EmailMessage(id="core-03", subject="Spam", body=spam_context),
        spam_context,
    )
    assert dec_spam.event_type == "Spam_Or_Irrelevant"
    assert dec_spam.is_actionable is False
    assert dec_spam.urgency_score == 1


def test_end_to_end_orchestration_user_payload():
    """Verify the exact user payload through the full 4-stage pipeline."""
    orchestrator = CorporateActionsFlowOrchestrator()

    # Exact user example payload
    email = EmailMessage(
        id="payload-example",
        sender="proxy-alerts@custodian.com",
        subject="Urgent: Action Required for ABC Corp Merger",
        body="Please review the attached corporate proxy document for restructuring options.",
    )

    flow_result = orchestrator.process_email(email)

    # 1. Ingestion Gate
    assert flow_result.ingestion_gate.requires_heavy_ocr is True
    assert flow_result.ingestion_gate.ocr_probability > 0.50

    # 2. Gemini OCR ran
    assert flow_result.ocr_applied is True
    assert "GEMINI VISION OCR" in email.normalized_text

    # 3. Core Decision
    assert flow_result.core_decision.event_type == "Merger_Acquisition"
    assert flow_result.core_decision.is_actionable is True
    assert flow_result.core_decision.urgency_score == 10

    # 4. Router: Actionable & High Confidence -> Gemini Draft Client Notice
    assert flow_result.route == "GEMINI_CLIENT_NOTICE"
    assert flow_result.client_notice is not None
    assert "ACTION REQUIRED" in flow_result.client_notice.subject
    assert len(flow_result.client_notice.election_options) >= 2


def test_end_to_end_orchestration_informational_hitl():
    """Verify informational notice routes to Human-in-the-Loop queue."""
    orchestrator = CorporateActionsFlowOrchestrator()

    email = EmailMessage(
        id="informational-email",
        sender="ca-announcements@euroclear.com",
        subject="MANDATORY CASH DIVIDEND: Novo Nordisk A/S",
        body="EVENT NOTIFICATION: Mandatory Cash Dividend (DVCA). Gross Rate: DKK 6.40. Auto-credit on value date 20-OCT-2026.",
    )

    flow_result = orchestrator.process_email(email)

    # 1. Ingestion Gate (No OCR needed)
    assert flow_result.ingestion_gate.requires_heavy_ocr is False
    assert flow_result.ocr_applied is False

    # 2. Core Decision
    assert flow_result.core_decision.event_type == "Cash_Dividend"
    assert flow_result.core_decision.is_actionable is False

    # 3. Router: Informational -> Human-in-the-Loop Queue
    assert flow_result.route == "HUMAN_IN_THE_LOOP"
    assert flow_result.hitl_item is not None
    assert "Informational Notice" in flow_result.hitl_item.reason


def test_batch_processing_and_urgency_sorting():
    """Verify that batch processing shifts high urgency items to the top of the queue."""
    orchestrator = CorporateActionsFlowOrchestrator()

    emails = [
        EmailMessage(
            id="low-urgency",
            sender="dtcc@dtcc.com",
            subject="Stock Split 3-for-1",
            body="Forward stock split payable 15-OCT-2026. Routine ledger adjustment.",
        ),
        EmailMessage(
            id="high-urgency",
            sender="custody@bnymellon.com",
            subject="Urgent Tender Offer Expiring Tomorrow",
            body="Voluntary Tender Offer. Custodian Cutoff: 04-OCT-2026 17:00 EST. Strict 24-48 hours deadline.",
        ),
        EmailMessage(
            id="spam",
            sender="spam@bot.biz",
            subject="1000% APY crypto bot",
            body="Unsubscribe if you do not want crypto trading bots.",
        ),
    ]

    results = orchestrator.process_batch(emails)

    assert len(results) == 3
    # Top item must be high urgency
    assert results[0].email_id == "high-urgency"
    assert results[0].core_decision.urgency_score == 10
    # Bottom item must be lowest urgency (spam)
    assert results[-1].email_id == "spam"
    assert results[-1].core_decision.urgency_score == 1
