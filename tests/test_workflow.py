"""Unit tests for workflow engine routing and escalation rules."""

from src.models import EmailMessage, JevDecisionDetails
from src.workflow_engine import WorkflowEngine


def test_workflow_critical_escalation():
    engine = WorkflowEngine(
        urgency_threshold=0.75,
        escalation_threshold=0.70,
        severity_threshold=4,
    )

    msg = EmailMessage(
        id="msg-crit",
        subject="CRITICAL Outage",
        body="Major system failure",
    )

    decision = JevDecisionDetails(
        category="account_security",
        category_confidence=0.95,
        urgency_probability=0.92,
        severity_score=5,
        severity_confidence=0.90,
        escalation_probability=0.94,
        suggested_action="immediate_security_lockout",
        suggested_action_confidence=0.92,
    )

    record = engine.process(msg, decision)

    assert record.workflow.escalate_to_human is True
    assert record.workflow.alert_level == "CRITICAL"
    assert record.workflow.target_queue == "Security Incident Response Queue"
    assert "SEV-1-CRITICAL" in record.workflow.tags
    assert "URGENT-ATTENTION" in record.workflow.tags
    assert "HUMAN-ESCALATION-REQUIRED" in record.workflow.tags
    assert "ACTION-IMMEDIATE-SECURITY-LOCKOUT" in record.workflow.tags


def test_workflow_standard_routing():
    engine = WorkflowEngine(
        urgency_threshold=0.75,
        escalation_threshold=0.70,
        severity_threshold=4,
    )

    msg = EmailMessage(
        id="msg-feat",
        subject="Feature request",
        body="Can we add export to CSV?",
    )

    decision = JevDecisionDetails(
        category="feature_request",
        category_confidence=0.88,
        urgency_probability=0.10,
        severity_score=1,
        severity_confidence=0.80,
        escalation_probability=0.05,
        suggested_action="add_to_product_backlog",
        suggested_action_confidence=0.85,
    )

    record = engine.process(msg, decision)

    assert record.workflow.escalate_to_human is False
    assert record.workflow.alert_level == "INFO"
    assert record.workflow.target_queue == "Product Management Backlog Queue"
    assert "FEATURE-REQUEST" in record.workflow.tags
    assert "SEV-4-LOW" in record.workflow.tags
    assert "HUMAN-ESCALATION-REQUIRED" not in record.workflow.tags
