"""Corporate Actions Flow Orchestrator implementing the full end-to-end intelligent pipeline.

Pipeline stages:
1. JEV AI Ingestion Gate:
   Evaluates Subject, Body & Meta -> Q: "Are attachments/OCR required?" (Noul: requires_heavy_ocr)
2. Branch:
   - No / Prob <= 0.50: Raw Text Envelope
   - Yes / Prob > 0.50: Gemini LLM / Vision downloads PDF/Img, performs OCR, flattens to Text -> Normalized Text + PDF
3. JEV AI Core Decision:
   Evaluates complete text matrix -> Choice (CA Event Type), Noul (Is Actionable?), Score (Urgency Score 1-10)
4. Application Router Code:
   - High Urgency shifts items to top of queue (Urgency 1-10 sort)
   - If Actionable & High Confidence:
       -> Gemini: Draft Client Notice (Generates localized, structured election email to send to clients)
   - If Informational OR Low Confidence / High Risk:
       -> Human-in-the-Loop Queue (Manual exception handling / clarification with sender)
"""

from __future__ import annotations
import time
from typing import List, Optional
import uuid

from src.models import (
    ClientNoticeDraft,
    CoreDecisionResult,
    CorporateActionFlowResult,
    EmailMessage,
    HumanInTheLoopItem,
    IngestionGateResult,
)
from src.jev_client import JevEmailClassifier
from src.gemini_service import GeminiService


class CorporateActionsFlowOrchestrator:
    """Orchestrates the 4-stage Corporate Action email evaluation, OCR, decision, and routing flow."""

    def __init__(
        self,
        jev_classifier: Optional[JevEmailClassifier] = None,
        gemini_service: Optional[GeminiService] = None,
        confidence_threshold: float = 0.70,
    ):
        self.jev_classifier = jev_classifier or JevEmailClassifier(domain="corporate_actions")
        self.gemini_service = gemini_service or GeminiService()
        self.confidence_threshold = confidence_threshold

    def process_email(self, email_msg: EmailMessage) -> CorporateActionFlowResult:
        """Execute the complete end-to-end flow for a single email."""
        start_time = time.perf_counter()

        # ─────────────────────────────────────────────────────────────
        # STAGE 1: JEV AI Ingestion Gate
        # ─────────────────────────────────────────────────────────────
        gate_result: IngestionGateResult = self.jev_classifier.evaluate_ingestion_gate(email_msg)

        # ─────────────────────────────────────────────────────────────
        # STAGE 2: Envelope Normalization & Conditional Gemini OCR
        # ─────────────────────────────────────────────────────────────
        if gate_result.ocr_probability > 0.50:
            # Trigger Gemini LLM / Vision OCR
            ocr_text = self.gemini_service.perform_ocr(email_msg)
            email_msg.ocr_applied = True
            email_msg.ocr_extracted_text = ocr_text

            # Normalized Text + PDF
            normalized_matrix = (
                f"{email_msg.body.strip()}\n\n"
                f"--- [FLATTENED ATTACHMENT TEXT (GEMINI VISION OCR)] ---\n"
                f"{ocr_text.strip()}"
            )
            email_msg.normalized_text = normalized_matrix
            ocr_applied = True
        else:
            # Raw Text Envelope directly
            email_msg.ocr_applied = False
            email_msg.ocr_extracted_text = ""
            email_msg.normalized_text = email_msg.body.strip()
            ocr_applied = False

        # ─────────────────────────────────────────────────────────────
        # STAGE 3: JEV AI Core Decision (Choice, Noul, Score 1-10)
        # ─────────────────────────────────────────────────────────────
        core_decision: CoreDecisionResult = self.jev_classifier.evaluate_core_decision(
            email_msg, email_msg.normalized_text
        )

        # ─────────────────────────────────────────────────────────────
        # STAGE 4: Application Router Code
        # ─────────────────────────────────────────────────────────────
        # High-Risk indicators: e.g. low event confidence, reconciliation breaks
        is_high_risk = (
            core_decision.event_type_confidence < self.confidence_threshold
            or "reconciliation" in email_msg.subject.lower()
            or "variance" in email_msg.body.lower()
        )

        is_actionable = core_decision.is_actionable and core_decision.is_actionable_probability > 0.50
        is_high_confidence = core_decision.event_type_confidence >= self.confidence_threshold

        client_notice: Optional[ClientNoticeDraft] = None
        hitl_item: Optional[HumanInTheLoopItem] = None

        if is_actionable and is_high_confidence and not is_high_risk:
            # Branch A: If Actionable & High Confidence -> Gemini: Draft Client Notice
            route = "GEMINI_CLIENT_NOTICE"
            client_notice = self.gemini_service.draft_client_notice(
                email_msg, core_decision, email_msg.normalized_text
            )
        else:
            # Branch B: If Informational OR Low Confidence / High Risk -> Human-in-the-Loop Queue
            route = "HUMAN_IN_THE_LOOP"

            if not is_actionable:
                reason = "Informational Notice (No beneficial election required)"
                risk_level = "LOW" if core_decision.event_type != "Spam_Or_Irrelevant" else "INFO"
                clarification = "Verify entitlement schedule and auto-post to custody/accounting ledger."
                suggested_act = "Auto-archive or verify automated entitlement schedule."
            elif is_high_risk:
                reason = "High Risk / Discrepancy Exception (Operational Review Required)"
                risk_level = "CRITICAL" if core_decision.urgency_score >= 8 else "HIGH"
                clarification = "Investigate reconciliation variance or ambiguous terms directly with custodian."
                suggested_act = "Open investigation ticket with custodian desk and review account position."
            else:
                reason = f"Low Confidence Classification ({core_decision.event_type_confidence:.1%} < {self.confidence_threshold:.0%})"
                risk_level = "MEDIUM"
                clarification = "Manual review required to verify event classification and terms before client solicitation."
                suggested_act = "Desk operator to confirm corporate action type and manually authorize solicitation."

            hitl_item = HumanInTheLoopItem(
                queue_id=f"HITL-{uuid.uuid4().hex[:6].upper()}",
                reason=reason,
                risk_level=risk_level,
                clarification_needed=clarification,
                suggested_action=suggested_act,
            )

        total_latency = round((time.perf_counter() - start_time) * 1000, 2)

        return CorporateActionFlowResult(
            email_id=email_msg.id,
            subject=email_msg.subject,
            sender=email_msg.sender,
            ingestion_gate=gate_result,
            ocr_applied=ocr_applied,
            normalized_text_preview=email_msg.normalized_text[:180] + ("..." if len(email_msg.normalized_text) > 180 else ""),
            core_decision=core_decision,
            route=route,
            client_notice=client_notice,
            hitl_item=hitl_item,
            total_latency_ms=total_latency,
        )

    def process_batch(self, emails: List[EmailMessage]) -> List[CorporateActionFlowResult]:
        """Process batch of emails and sort by Urgency Score (1-10) descending (High Urgency shifts to top)."""
        results = [self.process_email(e) for e in emails]
        # Sort queue: Highest urgency score first (10 -> 1)
        results.sort(key=lambda r: r.core_decision.urgency_score, reverse=True)
        return results
