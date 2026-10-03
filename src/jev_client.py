"""Jev AI client module integrating TypeSafe AI System One decision engine with simulator fallback.

Supports:
1. Ingestion Gate (Stage 1): Evaluating attachments/OCR requirement (Noul: requires_heavy_ocr)
2. Core Decision (Stage 3): Event Type (Choice), Is Actionable (Noul), Urgency (Score 1-10)
3. Legacy Desk Classifier: Full backward compatibility for operational desk routing
"""

from __future__ import annotations
import os
import re
import time
from typing import Any, Dict, Optional
from dotenv import load_dotenv

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient
from typesafe_sdk import ChoiceAnswer, NoulAnswer, ScoreAnswer
from src.models import (
    CoreDecisionResult,
    EmailMessage,
    IngestionGateResult,
    JevDecisionDetails,
)

load_dotenv()


def build_ingestion_gate_questions() -> Dict[str, Any]:
    """Define the structured question for Jev AI Ingestion Gate (Stage 1)."""
    return {
        "requires_heavy_ocr": Noul(
            instructions="True if the context lacks actionable dates/terms and explicitly points to an attached PDF or image file for full details."
        )
    }


def build_core_decision_questions() -> Dict[str, Any]:
    """Define the structured questions for Jev AI Core Decision (Stage 3)."""
    return {
        "event_type": Choice(
            instructions="Based on the complete text matrix, select the corporate action event type:",
            criteria={
                "Cash_Dividend": "Mandatory or cash dividend distribution declaration or dividend payment.",
                "Stock_Dividend": "Stock dividend, scrip dividend, bonus share issue, or equity distribution.",
                "Merger_Acquisition": "Merger, acquisition, voluntary tender offer, takeover bid, or restructuring.",
                "Ticker_Change": "Security ticker symbol, name, or ISIN/CUSIP reclassification, split, or spin-off.",
                "Spam_Or_Irrelevant": "Unsolicited promotional sales, newsletter, spam, or non-corporate action notice.",
            },
        ),
        "is_actionable": Noul(
            instructions="True if our operations desk must respond, submit an election, or alert clients. False if it is just an FYI update."
        ),
        "urgency": Score(
            instructions="Scale 1-10 of how critical the timeline is. A 10 means the deadline is within 48 hours.",
            criteria=[
                "1 - Non-actionable or timeline > 30 days",
                "2 - Timeline > 21 days with standard settlement",
                "3 - Timeline 15-20 days",
                "4 - Timeline 10-14 days",
                "5 - Timeline 7-9 days",
                "6 - Timeline 5-6 days",
                "7 - Timeline 3-4 days",
                "8 - Timeline within 72 hours (< 3 days)",
                "9 - Timeline within 48 hours requiring expedited instructions",
                "10 - Critical cutoff within 24-48 hours requiring immediate execution",
            ],
        ),
    }


def build_email_questions(domain: str = "corporate_actions") -> Dict[str, Any]:
    """Define the structured questions for Jev AI System One legacy desk classifier."""
    if domain == "corporate_actions":
        return {
            "category": Choice(
                instructions="Based on `email.subject` and `email.body`, select the primary corporate action event type or category this notification belongs to:",
                criteria={
                    "voluntary_corporate_action": "Voluntary corporate events requiring an active election by security holders before an expiration deadline (e.g. tender offers, rights offerings, takeover bids, buyback offers, warrant exercises).",
                    "mandatory_corporate_action": "Mandatory corporate events automatically applied across all security holders without election (e.g. mandatory cash dividends, forward/reverse stock splits, spin-offs, capital reductions, mandatory mergers).",
                    "mandatory_with_options": "Mandatory corporate events offering choice of entitlement (e.g. optional dividend electing between cash vs. scrip/stock shares, DRIP reinvestment plans).",
                    "proxy_voting_agm": "Shareholder meetings, Annual General Meetings (AGM), Extraordinary General Meetings (EGM), proxy ballots, and corporate governance voting resolutions.",
                    "reconciliation_exception": "Settlement discrepancies, withholding tax rate mismatches, dividend entitlement breaks, or custodian cash/position breaks requiring operational escalation.",
                    "general_inquiry_spam": "Unsolicited cold sales pitches, newsletters, irrelevant marketing spam, or non-actionable inquiries.",
                },
            ),
            "urgency": Noul(
                instructions="Does `email.body` or `email.subject` describe an urgent corporate action deadline (e.g. election cutoff within 24-48 hours) or a critical financial discrepancy requiring immediate action?",
            ),
            "severity_priority": Score(
                instructions="Rate the operational financial exposure and execution criticality of `email` on a 5-point rubric:",
                criteria=[
                    "1 - Minimal: Routine informational notice, non-urgent filing, or irrelevant marketing spam",
                    "2 - Low: Standard mandatory corporate action with automated processing (routine cash dividend, stock split)",
                    "3 - Medium: Voluntary election or proxy ballot with standard notice period (> 7 business days)",
                    "4 - High: Imminent voluntary election cutoff (< 48h), complex spin-off restructuring, or rights subscription",
                    "5 - Critical: Expiring tender offer cutoff (< 24h), severe reconciliation cash break, or erroneous withholding tax impacting NAV",
                ],
            ),
            "requires_human_escalation": Noul(
                instructions="Does `email` require immediate manual intervention or review by a portfolio manager, trader, or corporate actions operations specialist?",
            ),
            "suggested_action": Choice(
                instructions="What is the best immediate operational next step for processing `email`?",
                criteria={
                    "solicit_pm_election": "Notify Portfolio Managers and trading desk to capture investment elections before cutoff",
                    "book_entitlement_accounting": "Schedule and post automated entitlement into fund accounting and custody ledgers",
                    "setup_new_security_master": "Create new ISIN/CUSIP security master record and configure corporate event schedule",
                    "submit_proxy_ballot": "Cast proxy voting ballot in accordance with fund governance guidelines",
                    "escalate_custodian_break": "Open high-priority investigation ticket with custodian bank ops for cash/position mismatch",
                    "auto_archive": "Archive or file notice without operational intervention",
                },
            ),
        }

    return {
        "category": Choice(
            instructions="Based on `email.subject` and `email.body`, select the primary operational department/category this email belongs to:",
            criteria={
                "billing_invoice": "Invoices, payment receipts, subscription renewals, chargebacks, or refund disputes.",
                "technical_support": "Software bugs, service errors, API integration failures, or broken functionality.",
                "feature_request": "Ideas for new features, UX improvements, capability requests, or enhancements.",
                "sales_inquiry": "Enterprise pricing, demo requests, partnership proposals, or volume licensing.",
                "account_security": "Unauthorized access, suspicious activity, credential leaks, or security vulnerability alerts.",
                "general_spam": "Unsolicited cold outreach, promotional newsletters, marketing spam, or auto-replies.",
            },
        ),
        "urgency": Noul(
            instructions="Does `email.body` or `email.subject` describe an urgent or time-critical issue requiring immediate operational attention?",
        ),
        "severity_priority": Score(
            instructions="Rate the operational severity and customer impact of `email` on a 5-point rubric:",
            criteria=[
                "1 - Minimal: Routine notification, casual inquiry, or harmless spam",
                "2 - Low: Minor issue with workaround available, non-urgent feature question",
                "3 - Medium: Standard issue affecting user workflow or standard invoice check",
                "4 - High: Major blocker, VIP customer escalation, or significant payment failure",
                "5 - Critical: Security breach, system-wide outage, data loss, or legal emergency",
            ],
        ),
        "requires_human_escalation": Noul(
            instructions="Does `email` require immediate human specialist review rather than an automated workflow or queue?",
        ),
        "suggested_action": Choice(
            instructions="What is the best immediate operational action for processing `email`?",
            criteria={
                "route_to_finance": "Forward to billing and accounts receivable team",
                "create_jira_bug": "Log bug ticket for engineering investigation",
                "add_to_product_backlog": "Save into product feedback backlog",
                "assign_sales_rep": "Assign lead to sales executive for follow-up",
                "immediate_security_lockout": "Alert security operations and isolate compromised entities",
                "auto_archive": "Archive silently without agent intervention",
            },
        ),
    }


class JevEmailClassifier:
    """Classifier handling Jev AI System One calls and high-fidelity local simulation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        force_mock: Optional[bool] = None,
        domain: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("TYPESAFE_API_KEY", "").strip()
        self.domain = domain or os.getenv("WORKFLOW_DOMAIN", "auto").strip()

        env_force_mock = os.getenv("JEV_MOCK_MODE", "false").lower() in ("true", "1", "yes")
        if force_mock is not None:
            self.force_mock = force_mock
        else:
            self.force_mock = env_force_mock or not bool(self.api_key)

        self._client: Optional[TypeSafeClient] = None
        if not self.force_mock and self.api_key:
            try:
                self._client = TypeSafeClient(api_key=self.api_key)
            except Exception as e:
                print(f"Warning: Failed to initialize live TypeSafeClient: {e}. Falling back to simulator.")
                self.force_mock = True

    @property
    def is_live(self) -> bool:
        """True if using live TypeSafe AI API."""
        return not self.force_mock and self._client is not None

    def evaluate_ingestion_gate(self, email_msg: EmailMessage) -> IngestionGateResult:
        """Stage 1: Evaluates Subject, Body & Meta. Q: 'Are attachments/OCR required?'"""
        start_time = time.perf_counter()
        context_str = f"From: {email_msg.sender}\nSubject: {email_msg.subject}\nBody: {email_msg.body}"

        if self.is_live:
            try:
                state = {"context": context_str}
                questions = build_ingestion_gate_questions()
                response = self._client.system_one(
                    state=state,
                    questions=questions,
                    model="jev-latest",
                )
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                ocr_ans: Optional[NoulAnswer] = response.answers.get("requires_heavy_ocr")
                ocr_prob = float(ocr_ans.noul) if ocr_ans else 0.5
                return IngestionGateResult(
                    requires_heavy_ocr=ocr_prob > 0.50,
                    ocr_probability=round(ocr_prob, 4),
                    reasoning=f"Ingestion gate evaluated with calibrated probability {ocr_prob:.2f}.",
                    latency_ms=latency_ms,
                    mode="live",
                    raw_answer=ocr_ans.model_dump() if ocr_ans else {},
                )
            except Exception as exc:
                print(f"Live Ingestion Gate API call failed ({exc}); falling back to local simulation.")

        return self._simulate_ingestion_gate(email_msg, context_str, start_time)

    def _simulate_ingestion_gate(
        self, email_msg: EmailMessage, context_str: str, start_time: float
    ) -> IngestionGateResult:
        """Deterministic simulation for Jev AI Ingestion Gate."""
        time.sleep(0.04)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        text = context_str.lower()
        has_explicit_attachment_reference = bool(
            re.search(r"\b(attached\s+(corporate\s+proxy\s+document|tender\s+document|prospectus|ballot|pdf|file|form|document)|review the attached|see attached|for restructuring options)\b", text)
        )
        has_missing_actionable_terms = bool(
            len(email_msg.body.strip().splitlines()) <= 4
            or "review the attached corporate proxy document" in text
            or ("attached" in text and "cutoff" not in text and "ex-date" not in text)
        )

        if has_explicit_attachment_reference and has_missing_actionable_terms:
            prob = 0.94
            reasoning = "Context lacks actionable dates/terms and explicitly points to an attached PDF or image file for full details."
        elif has_explicit_attachment_reference:
            prob = 0.78
            reasoning = "Explicit attachment referenced requiring document OCR flattening."
        elif email_msg.attachments and any(a.content_type == "application/pdf" for a in email_msg.attachments) and len(email_msg.body.strip()) < 180:
            prob = 0.85
            reasoning = "Email includes attached PDF file with truncated body text."
        else:
            prob = 0.08
            reasoning = "Complete corporate action terms and dates are present in raw text body; no OCR required."

        return IngestionGateResult(
            requires_heavy_ocr=prob > 0.50,
            ocr_probability=prob,
            reasoning=reasoning,
            latency_ms=latency_ms,
            mode="simulator",
            raw_answer={"noul": prob},
        )

    def evaluate_core_decision(
        self, email_msg: EmailMessage, normalized_context: str
    ) -> CoreDecisionResult:
        """Stage 3: JEV AI Core Decision evaluating the complete text matrix (Choice, Noul, Score)."""
        start_time = time.perf_counter()

        if self.is_live:
            try:
                state = {"context": normalized_context}
                questions = build_core_decision_questions()
                response = self._client.system_one(
                    state=state,
                    questions=questions,
                    model="jev-latest",
                )
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                answers = response.answers

                # event_type Choice
                ev_ans: Optional[ChoiceAnswer] = answers.get("event_type")
                event_type = ev_ans.choice if ev_ans else "Spam_Or_Irrelevant"
                event_conf = ev_ans.confidence if ev_ans else 0.5
                event_probs = ev_ans.probabilities if ev_ans else {}

                # is_actionable Noul
                act_ans: Optional[NoulAnswer] = answers.get("is_actionable")
                is_act_prob = float(act_ans.noul) if act_ans else 0.5
                is_actionable = is_act_prob > 0.50

                # urgency Score (0-indexed to 1-10)
                urg_ans: Optional[ScoreAnswer] = answers.get("urgency")
                urg_score = int(urg_ans.score) + 1 if urg_ans else 5
                urg_conf = urg_ans.confidence if urg_ans else 0.5
                urg_probs = urg_ans.probabilities if urg_ans else {}

                return CoreDecisionResult(
                    event_type=event_type,
                    event_type_confidence=round(event_conf, 4),
                    event_type_probabilities=event_probs,
                    is_actionable=is_actionable,
                    is_actionable_probability=round(is_act_prob, 4),
                    urgency_score=urg_score,
                    urgency_confidence=round(urg_conf, 4),
                    urgency_probabilities=urg_probs,
                    latency_ms=latency_ms,
                    mode="live",
                    raw_answers={
                        "event_type": ev_ans.model_dump() if ev_ans else {},
                        "is_actionable": act_ans.model_dump() if act_ans else {},
                        "urgency": urg_ans.model_dump() if urg_ans else {},
                    },
                )
            except Exception as exc:
                print(f"Live Core Decision API call failed ({exc}); falling back to local simulation.")

        return self._simulate_core_decision(email_msg, normalized_context, start_time)

    def _simulate_core_decision(
        self, email_msg: EmailMessage, normalized_context: str, start_time: float
    ) -> CoreDecisionResult:
        """Deterministic simulation for Jev AI Core Decision matrix."""
        time.sleep(0.06)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        text = normalized_context.lower()

        # 1. Classify Event Type
        if re.search(r"\b(1000% apy|crypto|arbitrage|bot|guaranteed|unsubscribe|scalps)\b", text):
            event_type = "Spam_Or_Irrelevant"
            event_conf = 0.95
            is_actionable = False
            act_prob = 0.02
            urgency = 1
        elif re.search(r"\b(tender offer|takeover bid|merger|acquisition|restructuring options|hyperion|abc corp merger)\b", text):
            event_type = "Merger_Acquisition"
            event_conf = 0.96
            is_actionable = True
            act_prob = 0.95
            urgency = 10 if ("48 hours" in text or "04-oct" in text or "05-oct" in text or "time critical" in text) else 8
        elif re.search(r"\b(scrip|optional dividend|cash vs scrip|drip|dvop)\b", text):
            event_type = "Stock_Dividend"
            event_conf = 0.92
            is_actionable = True
            act_prob = 0.88
            urgency = 6
        elif re.search(r"\b(cash dividend|interim dividend|dvca|gross dividend|net rate|withholding tax:)\b", text):
            event_type = "Cash_Dividend"
            event_conf = 0.97
            is_actionable = False  # Mandatory cash dividend is informational / auto-posted
            act_prob = 0.12
            urgency = 4
        elif re.search(r"\b(rights offering|rights issue|nil-paid|subscribe in full)\b", text):
            event_type = "Stock_Dividend"
            event_conf = 0.91
            is_actionable = True
            act_prob = 0.94
            urgency = 9
        elif re.search(r"\b(stock split|spin-off|soff|splf|capital reduction|return of capital|cusip:|sedol:|ticker change)\b", text):
            event_type = "Ticker_Change"
            event_conf = 0.93
            is_actionable = False
            act_prob = 0.18
            urgency = 3
        elif re.search(r"\b(reconciliation|variance|unreconciled break|break:\s*corporate)\b", text):
            event_type = "Merger_Acquisition" if "merger" in text else "Cash_Dividend"
            event_conf = 0.65  # lower confidence flags HITL
            is_actionable = False
            act_prob = 0.40
            urgency = 8
        elif re.search(r"\b(proxy|agm|shareholder meeting|ballot)\b", text):
            event_type = "Merger_Acquisition" if "merger" in text else "Spam_Or_Irrelevant"
            event_conf = 0.72
            is_actionable = True
            act_prob = 0.85
            urgency = 7
        else:
            event_type = "Spam_Or_Irrelevant"
            event_conf = 0.80
            is_actionable = False
            act_prob = 0.05
            urgency = 1

        ev_probs = {
            "Cash_Dividend": 0.02,
            "Stock_Dividend": 0.02,
            "Merger_Acquisition": 0.02,
            "Ticker_Change": 0.02,
            "Spam_Or_Irrelevant": 0.02,
        }
        ev_probs[event_type] = event_conf

        urg_probs = {i: 0.02 for i in range(1, 11)}
        urg_probs[urgency] = 0.82

        return CoreDecisionResult(
            event_type=event_type,
            event_type_confidence=event_conf,
            event_type_probabilities=ev_probs,
            is_actionable=is_actionable,
            is_actionable_probability=act_prob,
            urgency_score=urgency,
            urgency_confidence=0.88,
            urgency_probabilities=urg_probs,
            latency_ms=latency_ms,
            mode="simulator",
            raw_answers={
                "event_type": {"choice": event_type, "confidence": event_conf},
                "is_actionable": {"noul": act_prob},
                "urgency": {"score": urgency - 1, "confidence": 0.88},
            },
        )

    def _resolve_domain(self, content: str) -> str:
        """Determine active domain based on setting or content semantics."""
        if self.domain in ("corporate_actions", "general"):
            return self.domain

        ca_pattern = r"\b(isin|cusip|sedol|dividend|tender offer|rights issue|stock split|proxy|broadridge|euroclear|dtcc|spin-off|scrip|reconciliation break)\b"
        if re.search(ca_pattern, content):
            return "corporate_actions"
        return "general"

    def classify_email(self, email_msg: EmailMessage) -> JevDecisionDetails:
        """Classify an email message using Jev AI System One legacy desk classifier."""
        start_time = time.perf_counter()
        content = f"{email_msg.subject} {email_msg.body}".lower()
        effective_domain = self._resolve_domain(content)

        if self.is_live:
            try:
                return self._classify_live(email_msg, effective_domain, start_time)
            except Exception as exc:
                print(f"Live Jev AI API call failed ({exc}); falling back to local simulation.")

        return self._classify_simulated(email_msg, effective_domain, content, start_time)

    def _classify_live(self, email_msg: EmailMessage, effective_domain: str, start_time: float) -> JevDecisionDetails:
        """Execute live system_one call with TypeSafeClient for legacy desk classifier."""
        state = {
            "email": {
                "id": email_msg.id,
                "subject": email_msg.subject,
                "from": email_msg.sender,
                "to": email_msg.recipient,
                "body": email_msg.body,
            }
        }
        questions = build_email_questions(domain=effective_domain)

        response = self._client.system_one(
            state=state,
            questions=questions,
            model="jev-latest",
        )
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        answers = response.answers
        raw_dict = {}

        fallback_cat = "general_inquiry_spam" if effective_domain == "corporate_actions" else "general_spam"
        cat_ans: Optional[ChoiceAnswer] = answers.get("category")
        category = cat_ans.choice if cat_ans else fallback_cat
        category_conf = cat_ans.confidence if cat_ans else 0.5
        category_probs = cat_ans.probabilities if cat_ans else {}
        if cat_ans:
            raw_dict["category"] = cat_ans.model_dump()

        urg_ans: Optional[NoulAnswer] = answers.get("urgency")
        urgency_prob = float(urg_ans.noul) if urg_ans else 0.1
        if urg_ans:
            raw_dict["urgency"] = urg_ans.model_dump()

        sev_ans: Optional[ScoreAnswer] = answers.get("severity_priority")
        sev_score = int(sev_ans.score) + 1 if sev_ans else 1
        sev_conf = sev_ans.confidence if sev_ans else 0.5
        sev_probs = sev_ans.probabilities if sev_ans else {}
        if sev_ans:
            raw_dict["severity_priority"] = sev_ans.model_dump()

        esc_ans: Optional[NoulAnswer] = answers.get("requires_human_escalation")
        escalation_prob = float(esc_ans.noul) if esc_ans else 0.1
        if esc_ans:
            raw_dict["requires_human_escalation"] = esc_ans.model_dump()

        act_ans: Optional[ChoiceAnswer] = answers.get("suggested_action")
        suggested_action = act_ans.choice if act_ans else "auto_archive"
        act_conf = act_ans.confidence if act_ans else 0.5
        act_probs = act_ans.probabilities if act_ans else {}
        if act_ans:
            raw_dict["suggested_action"] = act_ans.model_dump()

        return JevDecisionDetails(
            category=category,
            category_confidence=round(category_conf, 4),
            category_probabilities=category_probs,
            urgency_probability=round(urgency_prob, 4),
            severity_score=sev_score,
            severity_confidence=round(sev_conf, 4),
            severity_probabilities=sev_probs,
            escalation_probability=round(escalation_prob, 4),
            suggested_action=suggested_action,
            suggested_action_confidence=round(act_conf, 4),
            suggested_action_probabilities=act_probs,
            latency_ms=latency_ms,
            model=getattr(response, "model", "jev-system-one-live"),
            mode="live",
            raw_answers=raw_dict,
        )

    def _classify_simulated(
        self,
        email_msg: EmailMessage,
        effective_domain: str,
        content: str,
        start_time: float,
    ) -> JevDecisionDetails:
        """High-fidelity local simulation reproducing Jev AI structured decision format."""
        time.sleep(0.06)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if effective_domain == "corporate_actions":
            return self._simulate_corporate_actions(content, latency_ms)

        return self._simulate_general_it(content, latency_ms)

    def _simulate_corporate_actions(self, content: str, latency_ms: float) -> JevDecisionDetails:
        """Simulate Jev decisions for Corporate Actions workflow."""
        is_spam = bool(re.search(r"\b(1000% apy|crypto|arbitrage|bot|guaranteed|unsubscribe|scalps)\b", content))
        is_recon_break = bool(re.search(r"\b(reconciliation|discrepancy|variance|unreconciled break|unreconciled|tax variance|break:\s*corporate|entitlement discrepancy)\b", content))
        is_voluntary = bool(re.search(r"\b(tender offer|takeover bid|rights offering|rights issue|nil-paid|buyback|warrant|voluntary|subscription cutoff|consideration)\b", content))
        is_mandatory_choice = bool(re.search(r"\b(optional dividend|scrip|mandatory with choice|cash vs scrip|drip|dvop)\b", content))
        is_proxy = bool(re.search(r"\b(proxy|agm|egm|annual general meeting|shareholder meeting|resolutions|broadridge|stewardship|ballot)\b", content))
        is_spinoff_or_new_asset = bool(re.search(r"\b(spin-off|soff|new isin|allocation ratio|fractional entitlements|security master)\b", content))
        is_mandatory = bool(re.search(r"\b(mandatory|dividend|stock split|split ratio|splf|dvca|capital reduction|return of capital|capr)\b", content))
        is_urgent_text = bool(re.search(r"\b(urgent|critical|deadline|expiration|cutoff|immediate|approaching|time critical)\b", content))

        if is_spam:
            category = "general_inquiry_spam"
            suggested_action = "auto_archive"
            urgency_prob = 0.04
            severity_score = 1
            escalation_prob = 0.02
            cat_conf = 0.94
            cat_probs = {"general_inquiry_spam": 0.94, "mandatory_corporate_action": 0.02, "voluntary_corporate_action": 0.02, "proxy_voting_agm": 0.01, "reconciliation_exception": 0.01}
            sev_probs = {0: 0.88, 1: 0.08, 2: 0.03, 3: 0.01, 4: 0.0}

        elif is_recon_break:
            category = "reconciliation_exception"
            suggested_action = "escalate_custodian_break"
            urgency_prob = 0.95
            severity_score = 5
            escalation_prob = 0.96
            cat_conf = 0.96
            cat_probs = {"reconciliation_exception": 0.95, "voluntary_corporate_action": 0.02, "mandatory_corporate_action": 0.02, "mandatory_with_options": 0.01, "general_inquiry_spam": 0.0}
            sev_probs = {0: 0.0, 1: 0.01, 2: 0.03, 3: 0.16, 4: 0.80}

        elif is_voluntary:
            category = "voluntary_corporate_action"
            suggested_action = "solicit_pm_election"
            urgency_prob = 0.92 if is_urgent_text else 0.70
            severity_score = 4
            escalation_prob = 0.88
            cat_conf = 0.94
            cat_probs = {"voluntary_corporate_action": 0.93, "mandatory_with_options": 0.04, "mandatory_corporate_action": 0.02, "proxy_voting_agm": 0.01, "general_inquiry_spam": 0.0}
            sev_probs = {0: 0.01, 1: 0.04, 2: 0.20, 3: 0.65, 4: 0.10}

        elif is_mandatory_choice:
            category = "mandatory_with_options"
            suggested_action = "solicit_pm_election"
            urgency_prob = 0.72 if is_urgent_text else 0.45
            severity_score = 3
            escalation_prob = 0.62
            cat_conf = 0.91
            cat_probs = {"mandatory_with_options": 0.90, "voluntary_corporate_action": 0.06, "mandatory_corporate_action": 0.03, "proxy_voting_agm": 0.01, "general_inquiry_spam": 0.0}
            sev_probs = {0: 0.02, 1: 0.15, 2: 0.68, 3: 0.12, 4: 0.03}

        elif is_proxy:
            category = "proxy_voting_agm"
            suggested_action = "submit_proxy_ballot"
            urgency_prob = 0.45 if is_urgent_text else 0.28
            severity_score = 2
            escalation_prob = 0.25
            cat_conf = 0.93
            cat_probs = {"proxy_voting_agm": 0.92, "mandatory_corporate_action": 0.04, "voluntary_corporate_action": 0.03, "general_inquiry_spam": 0.01}
            sev_probs = {0: 0.05, 1: 0.70, 2: 0.20, 3: 0.04, 4: 0.01}

        elif is_spinoff_or_new_asset:
            category = "mandatory_corporate_action"
            suggested_action = "setup_new_security_master"
            urgency_prob = 0.55 if is_urgent_text else 0.35
            severity_score = 3
            escalation_prob = 0.42
            cat_conf = 0.92
            cat_probs = {"mandatory_corporate_action": 0.91, "voluntary_corporate_action": 0.05, "mandatory_with_options": 0.03, "general_inquiry_spam": 0.01}
            sev_probs = {0: 0.04, 1: 0.20, 2: 0.65, 3: 0.10, 4: 0.01}

        elif is_mandatory:
            category = "mandatory_corporate_action"
            suggested_action = "book_entitlement_accounting"
            urgency_prob = 0.22 if is_urgent_text else 0.14
            severity_score = 2
            escalation_prob = 0.10
            cat_conf = 0.95
            cat_probs = {"mandatory_corporate_action": 0.94, "mandatory_with_options": 0.03, "voluntary_corporate_action": 0.02, "general_inquiry_spam": 0.01}
            sev_probs = {0: 0.15, 1: 0.75, 2: 0.08, 3: 0.02, 4: 0.0}

        else:
            category = "general_inquiry_spam"
            suggested_action = "auto_archive"
            urgency_prob = 0.08
            severity_score = 1
            escalation_prob = 0.05
            cat_conf = 0.85
            cat_probs = {"general_inquiry_spam": 0.85, "mandatory_corporate_action": 0.08, "voluntary_corporate_action": 0.05, "proxy_voting_agm": 0.02}
            sev_probs = {0: 0.80, 1: 0.15, 2: 0.04, 3: 0.01, 4: 0.0}

        act_probs = {suggested_action: 0.89, "auto_archive": 0.04, "solicit_pm_election": 0.03, "book_entitlement_accounting": 0.02, "escalate_custodian_break": 0.02}

        return JevDecisionDetails(
            category=category,
            category_confidence=cat_conf,
            category_probabilities=cat_probs,
            urgency_probability=urgency_prob,
            severity_score=severity_score,
            severity_confidence=0.88,
            severity_probabilities=sev_probs,
            escalation_probability=escalation_prob,
            suggested_action=suggested_action,
            suggested_action_confidence=0.89,
            suggested_action_probabilities=act_probs,
            latency_ms=latency_ms,
            model="jev-system-one-simulator",
            mode="simulator",
            raw_answers={
                "category": {"choice": category, "confidence": cat_conf},
                "urgency": {"noul": urgency_prob},
                "severity_priority": {"score": severity_score - 1, "confidence": 0.88},
                "requires_human_escalation": {"noul": escalation_prob},
                "suggested_action": {"choice": suggested_action, "confidence": 0.89},
            },
        )

    def _simulate_general_it(self, content: str, latency_ms: float) -> JevDecisionDetails:
        """Simulate Jev decisions for General IT / SaaS workflow."""
        is_security = bool(re.search(r"\b(breach|unauthorized|vulnerability|exploit|leaked|password|credential|hack|attack|cve|phishing)\b", content))
        is_billing = bool(re.search(r"\b(invoice|payment|charge|credit card|receipt|refund|billing|subscription|renewal|stripe|wire)\b", content))
        is_support = bool(re.search(r"\b(bug|crash|error|500|broken|exception|failure|not working|downtime|timeout|glitch)\b", content))
        is_feature = bool(re.search(r"\b(feature|suggestion|request|add support|integration|roadmap|enhancement|would love to have)\b", content))
        is_sales = bool(re.search(r"\b(pricing|quote|sales|enterprise|demo|contract|seats|procurement|talk to sales)\b", content))
        is_urgent_text = bool(re.search(r"\b(urgent|asap|emergency|immediately|critical|production down|severe|blocking)\b", content))

        if is_security:
            category = "account_security"
            suggested_action = "immediate_security_lockout"
            urgency_prob = 0.96 if is_urgent_text else 0.88
            severity_score = 5
            escalation_prob = 0.94
            cat_conf = 0.97
            cat_probs = {"account_security": 0.94, "technical_support": 0.04, "billing_invoice": 0.01, "sales_inquiry": 0.0, "feature_request": 0.0, "general_spam": 0.01}
            sev_probs = {0: 0.0, 1: 0.01, 2: 0.04, 3: 0.15, 4: 0.80}

        elif is_support:
            category = "technical_support"
            suggested_action = "create_jira_bug"
            urgency_prob = 0.82 if is_urgent_text else 0.45
            severity_score = 4 if is_urgent_text else 3
            escalation_prob = 0.76 if is_urgent_text else 0.35
            cat_conf = 0.91
            cat_probs = {"technical_support": 0.89, "account_security": 0.05, "feature_request": 0.04, "billing_invoice": 0.01, "sales_inquiry": 0.0, "general_spam": 0.01}
            sev_probs = {0: 0.02, 1: 0.08, 2: 0.30, 3: 0.50, 4: 0.10} if is_urgent_text else {0: 0.05, 1: 0.20, 2: 0.60, 3: 0.12, 4: 0.03}

        elif is_billing:
            category = "billing_invoice"
            suggested_action = "route_to_finance"
            urgency_prob = 0.65 if is_urgent_text else 0.28
            severity_score = 3 if is_urgent_text else 2
            escalation_prob = 0.55 if is_urgent_text else 0.20
            cat_conf = 0.93
            cat_probs = {"billing_invoice": 0.92, "sales_inquiry": 0.05, "technical_support": 0.02, "account_security": 0.0, "feature_request": 0.0, "general_spam": 0.01}
            sev_probs = {0: 0.05, 1: 0.35, 2: 0.50, 3: 0.08, 4: 0.02}

        elif is_sales:
            category = "sales_inquiry"
            suggested_action = "assign_sales_rep"
            urgency_prob = 0.50 if is_urgent_text else 0.22
            severity_score = 2
            escalation_prob = 0.40
            cat_conf = 0.90
            cat_probs = {"sales_inquiry": 0.88, "feature_request": 0.06, "billing_invoice": 0.04, "technical_support": 0.01, "account_security": 0.0, "general_spam": 0.01}
            sev_probs = {0: 0.10, 1: 0.65, 2: 0.20, 3: 0.04, 4: 0.01}

        elif is_feature:
            category = "feature_request"
            suggested_action = "add_to_product_backlog"
            urgency_prob = 0.12
            severity_score = 1
            escalation_prob = 0.08
            cat_conf = 0.86
            cat_probs = {"feature_request": 0.84, "technical_support": 0.08, "sales_inquiry": 0.05, "billing_invoice": 0.01, "account_security": 0.0, "general_spam": 0.02}
            sev_probs = {0: 0.65, 1: 0.25, 2: 0.08, 3: 0.02, 4: 0.0}

        else:
            category = "general_spam"
            suggested_action = "auto_archive"
            urgency_prob = 0.04
            severity_score = 1
            escalation_prob = 0.02
            cat_conf = 0.88
            cat_probs = {"general_spam": 0.85, "sales_inquiry": 0.08, "feature_request": 0.03, "billing_invoice": 0.02, "technical_support": 0.01, "account_security": 0.01}
            sev_probs = {0: 0.85, 1: 0.10, 2: 0.04, 3: 0.01, 4: 0.0}

        act_probs = {suggested_action: 0.88, "auto_archive": 0.04, "route_to_finance": 0.03, "create_jira_bug": 0.03, "assign_sales_rep": 0.02}

        return JevDecisionDetails(
            category=category,
            category_confidence=cat_conf,
            category_probabilities=cat_probs,
            urgency_probability=urgency_prob,
            severity_score=severity_score,
            severity_confidence=0.85,
            severity_probabilities=sev_probs,
            escalation_probability=escalation_prob,
            suggested_action=suggested_action,
            suggested_action_confidence=0.88,
            suggested_action_probabilities=act_probs,
            latency_ms=latency_ms,
            model="jev-system-one-simulator",
            mode="simulator",
            raw_answers={
                "category": {"choice": category, "confidence": cat_conf},
                "urgency": {"noul": urgency_prob},
                "severity_priority": {"score": severity_score - 1, "confidence": 0.85},
                "requires_human_escalation": {"noul": escalation_prob},
                "suggested_action": {"choice": suggested_action, "confidence": 0.88},
            },
        )
