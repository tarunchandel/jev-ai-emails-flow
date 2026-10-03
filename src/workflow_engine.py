"""Workflow automation engine that routes emails and triggers alerts based on Jev AI decisions."""

from __future__ import annotations
import os
from typing import Dict, List, Optional
from src.models import (
    EmailMessage,
    JevDecisionDetails,
    ProcessedEmailRecord,
    WorkflowAction,
)

CORPORATE_ACTIONS_QUEUE_MAP: Dict[str, str] = {
    "voluntary_corporate_action": "Voluntary Actions & PM Elections Desk",
    "mandatory_corporate_action": "Mandatory Actions & Entitlements Desk",
    "mandatory_with_options": "Optional Dividend & DRIP Elections Desk",
    "proxy_voting_agm": "Proxy Voting & Shareholder Governance Desk",
    "reconciliation_exception": "Corporate Actions Reconciliation & Exceptions Desk",
    "general_inquiry_spam": "Automated Archive / Noise Queue",
}

GENERAL_QUEUE_MAP: Dict[str, str] = {
    "account_security": "Security Incident Response Queue",
    "technical_support": "Tier-2 Engineering Support Queue",
    "billing_invoice": "Finance & Accounts Receivable Queue",
    "sales_inquiry": "Enterprise Sales Pipeline Queue",
    "feature_request": "Product Management Backlog Queue",
    "general_spam": "Automated Archive / Junk Queue",
}

# Unified queue map for lookup fallback
QUEUE_MAP: Dict[str, str] = {**CORPORATE_ACTIONS_QUEUE_MAP, **GENERAL_QUEUE_MAP}


class WorkflowEngine:
    """Evaluates Jev decisions and executes routing, tagging, and human escalation policies."""

    def __init__(
        self,
        urgency_threshold: Optional[float] = None,
        escalation_threshold: Optional[float] = None,
        severity_threshold: Optional[int] = None,
        domain: Optional[str] = None,
    ):
        self.urgency_threshold = (
            urgency_threshold
            if urgency_threshold is not None
            else float(os.getenv("URGENCY_THRESHOLD", 0.75))
        )
        self.escalation_threshold = (
            escalation_threshold
            if escalation_threshold is not None
            else float(os.getenv("ESCALATION_THRESHOLD", 0.70))
        )
        self.severity_threshold = (
            severity_threshold
            if severity_threshold is not None
            else int(os.getenv("SEVERITY_THRESHOLD", 4))
        )
        self.domain = domain or os.getenv("WORKFLOW_DOMAIN", "corporate_actions").strip()

    def process(
        self, email_msg: EmailMessage, decision: JevDecisionDetails
    ) -> ProcessedEmailRecord:
        """Evaluate Jev AI decision against workflow rules and return complete execution record."""
        desk_map = (
            CORPORATE_ACTIONS_QUEUE_MAP
            if self.domain == "corporate_actions"
            else GENERAL_QUEUE_MAP
        )
        target_queue = desk_map.get(
            decision.category,
            QUEUE_MAP.get(decision.category, "General Triage Queue"),
        )

        tags: List[str] = []
        reasoning: List[str] = []
        escalate_to_human = False
        alert_level = "INFO"

        # 1. Category Tagging
        cat_tag = decision.category.upper().replace("_", "-")
        tags.append(cat_tag)
        reasoning.append(
            f"Categorized as '{decision.category}' with {decision.category_confidence:.1%} confidence."
        )

        # 2. Priority Rating & Tagging
        if decision.severity_score >= 5:
            tags.append("SEV-1-CRITICAL")
        elif decision.severity_score == 4:
            tags.append("SEV-2-HIGH")
        elif decision.severity_score == 3:
            tags.append("SEV-3-MEDIUM")
        else:
            tags.append("SEV-4-LOW")
        reasoning.append(f"Assigned severity score {decision.severity_score}/5.")

        # 3. Urgency Evaluation (Noul Probability)
        is_urgent = decision.urgency_probability >= self.urgency_threshold
        if is_urgent:
            tags.append("URGENT-ATTENTION")
            reasoning.append(
                f"Urgency probability ({decision.urgency_probability:.1%}) met or exceeded threshold ({self.urgency_threshold:.1%})."
            )

        # 4. Human Escalation Evaluation (Noul Probability + Severity + Policy)
        reasons_escalate = []
        if decision.escalation_probability >= self.escalation_threshold:
            reasons_escalate.append(
                f"Escalation probability ({decision.escalation_probability:.1%}) exceeded threshold ({self.escalation_threshold:.1%})"
            )
        if decision.severity_score >= self.severity_threshold:
            reasons_escalate.append(
                f"Severity score ({decision.severity_score}) reached or exceeded {self.severity_threshold}"
            )
        if decision.category == "account_security":
            reasons_escalate.append("Critical account security policy triggered")
        elif decision.category == "reconciliation_exception":
            reasons_escalate.append("Critical financial reconciliation break requiring custodian ops resolution")
        elif decision.category == "voluntary_corporate_action" and is_urgent:
            reasons_escalate.append("Time-critical voluntary corporate election cutoff requires portfolio manager action")

        if reasons_escalate:
            escalate_to_human = True
            tags.append("HUMAN-ESCALATION-REQUIRED")
            reasoning.append(
                f"Escalated to human-in-the-loop review: {'; '.join(reasons_escalate)}."
            )

        # 5. Alert Level Determination
        if escalate_to_human and (decision.severity_score == 5 or decision.urgency_probability >= 0.85):
            alert_level = "CRITICAL"
        elif escalate_to_human or is_urgent:
            alert_level = "WARNING"
        else:
            alert_level = "INFO"

        # 6. Action Tagging
        action_tag = f"ACTION-{decision.suggested_action.upper().replace('_', '-')}"
        tags.append(action_tag)
        reasoning.append(f"Suggested action: {decision.suggested_action}.")

        workflow_action = WorkflowAction(
            target_queue=target_queue,
            tags=tags,
            escalate_to_human=escalate_to_human,
            alert_level=alert_level,
            reasoning=reasoning,
            suggested_action=decision.suggested_action,
            status="ESCALATED" if escalate_to_human else "ROUTED",
        )

        return ProcessedEmailRecord(
            email=email_msg,
            classification=decision,
            workflow=workflow_action,
        )

    def process_batch(
        self, items: List[tuple[EmailMessage, JevDecisionDetails]]
    ) -> List[ProcessedEmailRecord]:
        """Process a batch of email-decision pairs."""
        return [self.process(msg, decision) for msg, decision in items]
