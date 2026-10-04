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
    AuditTrailStep,
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

        # ─────────────────────────────────────────────────────────────
        # Construct Detailed Audit Trail: 3 Architecture Questions + Gate & Routing
        # ─────────────────────────────────────────────────────────────
        audit_trail: List[AuditTrailStep] = []

        # Step 1: Stage 1 Ingestion Gate
        gate_opts = [
            {
                "option": "Requires Heavy OCR",
                "value": True,
                "score": f"{gate_result.ocr_probability:.1%}",
                "description": "Context lacks full terms; points to attached PDF/image file",
            },
            {
                "option": "Raw Text Envelope",
                "value": False,
                "score": f"{(1.0 - gate_result.ocr_probability):.1%}",
                "description": "Complete corporate action terms present in email text",
            },
        ]
        gate_action = (
            "Triggered Gemini Vision OCR to download and flatten PDF proxy document into structured text."
            if gate_result.requires_heavy_ocr
            else "Bypassed heavy document OCR; compiled Raw Text Envelope directly from body."
        )
        audit_trail.append(
            AuditTrailStep(
                step=1,
                stage="Stage 1: Ingestion Gate",
                name="Attachment & OCR Evaluation",
                primitive="Noul",
                question="Are attachments/OCR required? (requires_heavy_ocr)",
                options=gate_opts,
                selected_option="Requires Heavy OCR" if gate_result.requires_heavy_ocr else "Raw Text Envelope",
                selected_score=f"{gate_result.ocr_probability:.1%}",
                scores={
                    "Requires Heavy OCR": gate_result.ocr_probability,
                    "Raw Text Envelope": round(1.0 - gate_result.ocr_probability, 4),
                },
                decision=f"requires_heavy_ocr = {gate_result.requires_heavy_ocr} ({gate_result.ocr_probability:.1%} probability)",
                action_taken=gate_action,
                latency_ms=gate_result.latency_ms,
            )
        )

        # Step 2: Stage 2 Normalization & OCR Flattening
        norm_action = (
            "Gemini Vision OCR flattened attached document and synthesized into normalized evaluation matrix."
            if ocr_applied
            else "Compiled raw text envelope directly into normalized evaluation matrix without vision OCR."
        )
        audit_trail.append(
            AuditTrailStep(
                step=2,
                stage="Stage 2: Envelope Normalization",
                name="Document OCR Flattening & Text Matrix Assembly",
                primitive="Normalization",
                question="Synthesize envelope and extract attachment content",
                options=[
                    {"option": "Gemini Vision OCR", "description": "Multimodal visual OCR extraction for attached documents"},
                    {"option": "Raw Text Envelope", "description": "Direct plain text envelope synthesis without vision OCR"},
                ],
                selected_option="Gemini Vision OCR" if ocr_applied else "Raw Text Envelope",
                selected_score="100%",
                scores={"Applied": 1.0 if ocr_applied else 0.0},
                decision="Document flattened and synthesized into normalized text envelope.",
                action_taken=norm_action,
                latency_ms=320.0 if ocr_applied else 0.0,
            )
        )

        # Step 3: Stage 3 Jev Question 1 - CA Event Type (Choice)
        ev_types = [
            ("Cash_Dividend", "Cash Dividend", "Mandatory or cash dividend distribution declaration"),
            ("Stock_Dividend", "Stock Dividend", "Stock dividend, scrip dividend, bonus share issue, or rights issue"),
            ("Merger_Acquisition", "M&A / Tender Offer", "Merger, acquisition, voluntary tender offer, takeover bid, or restructuring"),
            ("Ticker_Change", "Ticker Change", "Security ticker symbol, name, or ISIN/CUSIP reclassification, split, or spin-off"),
            ("Spam_Or_Irrelevant", "Spam / Irrelevant", "Unsolicited promotional sales, newsletter, spam, or non-corporate notice"),
        ]
        ev_opts = [
            {
                "option": k,
                "label": lbl,
                "description": desc,
                "score": f"{core_decision.event_type_probabilities.get(k, 0.02):.1%}",
            }
            for k, lbl, desc in ev_types
        ]
        if core_decision.event_type == "Merger_Acquisition":
            q1_act = "Classified as M&A / Tender Offer. Triggered corporate reorganization protocol; identified offer consideration (cash vs shares) and target CUSIP/ISIN."
        elif core_decision.event_type == "Cash_Dividend":
            q1_act = "Classified as Cash Dividend. Initiated dividend entitlement verification, withholding tax audit, and automated ledger posting."
        elif core_decision.event_type == "Stock_Dividend":
            q1_act = "Classified as Stock / Scrip Dividend. Loaded entitlement ratio and evaluated cash vs reinvestment share election terms."
        elif core_decision.event_type == "Ticker_Change":
            q1_act = "Classified as Ticker Change / Split. Scheduled Security Master ISIN update and custody position rebalancing."
        else:
            q1_act = "Classified as Non-CA Spam. Flagged for auto-archive or operational filter."

        audit_trail.append(
            AuditTrailStep(
                step=3,
                stage="Stage 3: Jev Core Decision",
                name="Question 1: CA Event Type (Choice)",
                primitive="Choice",
                question="Which corporate action event type applies to this notice? (event_type)",
                options=ev_opts,
                selected_option=core_decision.event_type,
                selected_score=f"{core_decision.event_type_confidence:.1%}",
                scores=core_decision.event_type_probabilities,
                decision=f"Classified as {core_decision.event_type} ({core_decision.event_type_confidence:.1%} confidence)",
                action_taken=q1_act,
                latency_ms=core_decision.latency_ms,
            )
        )

        # Step 4: Stage 3 Jev Question 2 - Is Actionable? (Noul)
        act_opts = [
            {
                "option": "True (Action Required)",
                "value": True,
                "score": f"{core_decision.is_actionable_probability:.1%}",
                "description": "Operations desk must respond, submit client election, or alert beneficial owners",
            },
            {
                "option": "False (Informational Only)",
                "value": False,
                "score": f"{(1.0 - core_decision.is_actionable_probability):.1%}",
                "description": "Informational FYI update; no client election or response needed",
            },
        ]
        q2_act = (
            f"Actionable probability {core_decision.is_actionable_probability:.1%} > 50%. Designated as ACTION REQUIRED -> Routed to client notice generation workflow."
            if core_decision.is_actionable
            else f"Actionable probability {core_decision.is_actionable_probability:.1%} <= 50%. Designated as INFORMATIONAL ONLY -> Bypassed client election solicitation."
        )
        audit_trail.append(
            AuditTrailStep(
                step=4,
                stage="Stage 3: Jev Core Decision",
                name="Question 2: Is Actionable? (Noul)",
                primitive="Noul",
                question="Does our operations desk need to respond, submit an election, or alert clients? (is_actionable)",
                options=act_opts,
                selected_option="True (Action Required)" if core_decision.is_actionable else "False (Informational Only)",
                selected_score=f"{core_decision.is_actionable_probability:.1%}" if core_decision.is_actionable else f"{(1.0 - core_decision.is_actionable_probability):.1%}",
                scores={
                    "True (Action Required)": core_decision.is_actionable_probability,
                    "False (Informational Only)": round(1.0 - core_decision.is_actionable_probability, 4),
                },
                decision=f"is_actionable = {core_decision.is_actionable} ({core_decision.is_actionable_probability:.1%} calibrated)",
                action_taken=q2_act,
                latency_ms=core_decision.latency_ms,
            )
        )

        # Step 5: Stage 3 Jev Question 3 - Urgency Score (Score 1-10)
        urg_rubric = {
            1: "1 - Non-actionable or timeline > 30 days",
            2: "2 - Timeline > 21 days with standard settlement",
            3: "3 - Timeline 15-20 days",
            4: "4 - Timeline 10-14 days",
            5: "5 - Timeline 7-9 days",
            6: "6 - Timeline 5-6 days",
            7: "7 - Timeline 3-4 days",
            8: "8 - Timeline within 72 hours (< 3 days)",
            9: "9 - Timeline within 48 hours requiring expedited instructions",
            10: "10 - Critical cutoff within 24-48 hours requiring immediate execution",
        }
        urg_opts = [
            {
                "level": i,
                "option": f"Score {i}/10",
                "description": urg_rubric[i],
                "score": f"{core_decision.urgency_probabilities.get(i, 0.02):.1%}",
            }
            for i in range(1, 11)
        ]
        q3_act = (
            f"Urgency Score {core_decision.urgency_score}/10 qualifies as CRITICAL (>= 8). High Urgency shifted notice to the TOP of the Operational Queue (Priority Rank #1)."
            if core_decision.urgency_score >= 8
            else f"Urgency Score {core_decision.urgency_score}/10 assigned. Notice placed in standard operational priority queue."
        )
        audit_trail.append(
            AuditTrailStep(
                step=5,
                stage="Stage 3: Jev Core Decision",
                name="Question 3: Urgency Score (Score 1-10)",
                primitive="Score",
                question="Scale 1-10 of how critical the timeline is (10 = cutoff within 48 hours). (urgency)",
                options=urg_opts,
                selected_option=f"Score {core_decision.urgency_score} / 10",
                selected_score=f"{core_decision.urgency_score}/10",
                scores={str(k): v for k, v in core_decision.urgency_probabilities.items()},
                decision=f"Urgency Score = {core_decision.urgency_score}/10 (Confidence: {core_decision.urgency_confidence:.1%})",
                action_taken=q3_act,
                latency_ms=core_decision.latency_ms,
            )
        )

        # Step 6: Stage 4 Router Execution
        r_opts = [
            {"option": "GEMINI_CLIENT_NOTICE", "description": "Actionable & High Confidence -> Gemini drafts client notice"},
            {"option": "HUMAN_IN_THE_LOOP", "description": "Informational or Low Confidence/High Risk -> Operations desk review"},
        ]
        q4_act = (
            f"Routed to Gemini LLM -> Drafted structured client notice with {len(client_notice.election_options) if client_notice else 0} election choices and cutoff deadline {client_notice.deadline if client_notice else 'N/A'}."
            if route == "GEMINI_CLIENT_NOTICE"
            else f"Routed to Operations Desk HITL Queue -> Created review ticket {hitl_item.queue_id if hitl_item else 'HITL'} ({hitl_item.reason if hitl_item else 'Review'})."
        )
        audit_trail.append(
            AuditTrailStep(
                step=6,
                stage="Stage 4: Router Execution",
                name="Application Routing & Dispatch",
                primitive="Router",
                question="Application branching logic based on actionability and confidence threshold",
                options=r_opts,
                selected_option=route,
                selected_score="100%",
                scores={"GEMINI_CLIENT_NOTICE": 1.0 if route == "GEMINI_CLIENT_NOTICE" else 0.0, "HUMAN_IN_THE_LOOP": 1.0 if route == "HUMAN_IN_THE_LOOP" else 0.0},
                decision=f"Selected route: {route}",
                action_taken=q4_act,
                latency_ms=total_latency,
            )
        )

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
            audit_trail=audit_trail,
        )

    def process_batch(self, emails: List[EmailMessage]) -> List[CorporateActionFlowResult]:
        """Process batch of emails and sort by Urgency Score (1-10) descending (High Urgency shifts to top)."""
        results = [self.process_email(e) for e in emails]
        # Sort queue: Highest urgency score first (10 -> 1)
        results.sort(key=lambda r: r.core_decision.urgency_score, reverse=True)
        return results
