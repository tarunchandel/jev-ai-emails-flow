"""Streamlit interactive dashboard for Jev AI Email Classification & Corporate Actions Workflow.

Implements the complete 4-stage intelligent pipeline:
1. JEV AI Ingestion Gate (Noul: requires_heavy_ocr)
2. Conditional Gemini LLM / Vision OCR (PDF/Image flattening to Normalized Text)
3. JEV AI Core Decision (Choice: event_type, Noul: is_actionable, Score: urgency 1-10)
4. Application Router (Urgency priority queue, Gemini Draft Client Notice, Human-in-the-Loop Queue)
"""

from __future__ import annotations
import os
from pathlib import Path
import streamlit as st
import pandas as pd

from src.models import (
    CorporateActionFlowResult,
    EmailAttachment,
    EmailMessage,
    JevDecisionDetails,
    ProcessedEmailRecord,
)
from src.parser import load_emails_from_directory, parse_raw_text
from src.jev_client import (
    JevEmailClassifier,
    build_ingestion_gate_questions,
    build_core_decision_questions,
)
from src.gemini_service import GeminiService
from src.flow_orchestrator import CorporateActionsFlowOrchestrator
from src.workflow_engine import (
    WorkflowEngine,
    CORPORATE_ACTIONS_QUEUE_MAP,
    GENERAL_QUEUE_MAP,
)
from src.dataset_generator import (
    generate_corporate_actions_dataset,
    generate_sample_dataset,
    CORPORATE_ACTIONS_DIR,
    SAMPLE_DIR,
)

st.set_page_config(
    page_title="Jev AI Corporate Actions & Email Automation",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Sidebar ---
st.sidebar.title("⚡ Jev AI Control Panel")
st.sidebar.caption("TypeSafe AI 'System One' Decision Engine & Gemini Vision Flow")

# Workflow Solution Selection
st.sidebar.subheader("🎯 Workflow Solution")
solution_options = [
    "🏦 Corporate Actions Workflow",
    "💻 General IT & Support Workflow",
    "📁 Custom Directory",
]
selected_solution = st.sidebar.selectbox(
    "Active Workflow Solution",
    solution_options,
    index=0,
    help="Select the operational workflow domain and dataset to execute.",
)

if selected_solution == "🏦 Corporate Actions Workflow":
    current_dir = CORPORATE_ACTIONS_DIR
    active_domain = "corporate_actions"
    domain_label = "Corporate Actions"
    if not current_dir.exists() or not list(current_dir.glob("*")):
        generate_corporate_actions_dataset()
elif selected_solution == "💻 General IT & Support Workflow":
    current_dir = SAMPLE_DIR
    active_domain = "general"
    domain_label = "General IT / Ops"
    if not current_dir.exists() or not list(current_dir.glob("*")):
        generate_sample_dataset()
else:
    custom_path_str = st.sidebar.text_input(
        "Folder Path",
        value=str(CORPORATE_ACTIONS_DIR),
        help="Provide an absolute or relative path to email folder.",
    )
    current_dir = Path(custom_path_str)
    domain_choice = st.sidebar.radio(
        "Domain Schema for Custom Emails",
        ["Corporate Actions", "General IT / Ops"],
        index=0,
    )
    active_domain = "corporate_actions" if domain_choice == "Corporate Actions" else "general"
    domain_label = f"Custom ({domain_choice})"

# Manage Session State
current_folder_key = f"{selected_solution}:{str(current_dir)}"
if "active_folder_key" not in st.session_state or st.session_state.active_folder_key != current_folder_key:
    st.session_state.active_folder_key = current_folder_key
    st.session_state.emails = load_emails_from_directory(current_dir)
    st.session_state.processed_records = {}
    st.session_state.ca_flow_results = {}

st.sidebar.caption(f"📁 Active Folder: `{current_dir.name}` ({len(st.session_state.emails)} emails)")

# API Configuration
st.sidebar.divider()
st.sidebar.subheader("🔑 AI Model Credentials")

typesafe_key_input = st.sidebar.text_input(
    "TypeSafe API Key (Jev AI)",
    value=os.getenv("TYPESAFE_API_KEY", ""),
    type="password",
    help="TYPESAFE_API_KEY for live Jev AI System One. Leave blank for deterministic simulator.",
)

gemini_key_input = st.sidebar.text_input(
    "Gemini API Key (OCR & Notices)",
    value=os.getenv("GEMINI_API_KEY", ""),
    type="password",
    help="GEMINI_API_KEY for live Gemini Vision OCR and Notice drafting. Leave blank for simulator.",
)

execution_mode = st.sidebar.radio(
    "Execution Mode",
    ["Auto-detect", "Force Simulator", "Force Live API"],
    index=0,
)

force_mock = None
if execution_mode == "Force Simulator":
    force_mock = True
elif execution_mode == "Force Live API":
    force_mock = False

st.sidebar.divider()
st.sidebar.subheader("⚙️ Routing Thresholds")
confidence_threshold = st.sidebar.slider(
    "Actionable Confidence Threshold",
    min_value=0.50,
    max_value=0.95,
    value=0.70,
    step=0.05,
    help="Minimum event classification confidence to route to automated Gemini Client Notice.",
)

urgency_thresh = st.sidebar.slider(
    "Urgency Threshold (Noul)",
    min_value=0.1,
    max_value=1.0,
    value=float(os.getenv("URGENCY_THRESHOLD", 0.75)),
    step=0.05,
    help="Calibrated probability threshold at which an email triggers an URGENT priority tag.",
)

col_reload1, col_reload2 = st.sidebar.columns(2)
with col_reload1:
    if st.button("🔄 Reload"):
        st.session_state.emails = load_emails_from_directory(current_dir)
        st.session_state.processed_records = {}
        st.session_state.ca_flow_results = {}
        st.sidebar.success("Reloaded!")
with col_reload2:
    if st.button("⚡ Regenerate"):
        if active_domain == "corporate_actions":
            generate_corporate_actions_dataset(current_dir)
        else:
            generate_sample_dataset(current_dir)
        st.session_state.emails = load_emails_from_directory(current_dir)
        st.session_state.processed_records = {}
        st.session_state.ca_flow_results = {}
        st.sidebar.success("Generated & reloaded!")

# Initialize services
classifier = JevEmailClassifier(
    api_key=typesafe_key_input,
    force_mock=force_mock,
    domain=active_domain,
)
gemini_service = GeminiService(
    api_key=gemini_key_input,
    force_mock=force_mock,
)
orchestrator = CorporateActionsFlowOrchestrator(
    jev_classifier=classifier,
    gemini_service=gemini_service,
    confidence_threshold=confidence_threshold,
)
engine = WorkflowEngine(
    urgency_threshold=urgency_thresh,
    domain=active_domain,
)

# Header
st.title("⚡ Jev AI + Gemini: Corporate Actions Intelligent Flow")
st.markdown(
    """
    **Autonomous Asset Servicing Pipeline**: Combines **Jev AI System One** (sub-100ms structured decision primitives: `Choice`, `Noul`, `Score`) 
    with **Gemini Vision/LLM** (multimodal OCR & structured client notice generation) and **Urgency-Prioritized Routing**.
    """
)

jev_badge = "🟢 Live TypeSafe API" if classifier.is_live else "🟡 Jev Simulator (High-Fidelity)"
gemini_badge = "🟢 Live Gemini API" if gemini_service.is_live else "🟡 Gemini Simulator (Multimodal OCR)"
st.info(f"**Jev AI Status:** {jev_badge} | **Gemini Status:** {gemini_badge} | **Loaded Emails:** {len(st.session_state.emails)}")

# Main Tabs
tab_pipeline, tab_inbox, tab_inspector, tab_workflow = st.tabs([
    "🚀 4-Stage Corporate Actions Pipeline",
    "📬 Inbox & Email Explorer",
    "🔬 Jev AI Decision Inspector",
    "🚦 Operational Desk Board",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: 4-STAGE CORPORATE ACTIONS PIPELINE (NEW PRIMARY WORKFLOW)
# ─────────────────────────────────────────────────────────────────────────────
with tab_pipeline:
    st.subheader("🏦 End-to-End Corporate Action Architecture")
    
    with st.expander("🗺️ View Interactive Architecture Diagram & Payloads", expanded=False):
        st.markdown(
            """
```mermaid
flowchart TD
    A["Incoming Corporate Action Email"] --> B["JEV AI: Ingestion Gate<br/>- Evaluates Subject, Body & Meta<br/>- Q: Are attachments/OCR required? (Noul)"]
    
    B -->|No / Prob <= 0.50| C1["Raw Text Envelope"]
    B -->|Yes / Prob > 0.50| C2["Gemini LLM / Vision<br/>- Downloads PDF/Img<br/>- Performs OCR<br/>- Flattens to Text"]
    
    C2 --> D2["Normalized Text + PDF"]
    C1 --> E["JEV AI: Core Decision<br/>Evaluates complete text matrix"]
    D2 --> E
    
    E --> F1["CA Event Type (Choice)<br/>- Cash Dividend<br/>- M&A / Tender Offer<br/>- Stock Dividend<br/>- Ticker Change<br/>- Spam / Irrelevant"]
    E --> F2["Is Actionable? (Noul)<br/>- True: Needs reply / election<br/>- False: Informational only"]
    E --> F3["Urgency Score (Score 1-10)<br/>- 10 = Deadline within 48h<br/>- Shifts to top of queue"]
    
    F1 & F2 & F3 --> G["Application Router Code"]
    
    G -->|If Actionable & High Conf| H1["Gemini: Draft Client Notice<br/>Generates localized, structured election email"]
    G -->|If Informational OR Low Conf / High Risk| H2["Human-in-the-Loop Queue<br/>Manual exception handling / clarification with sender"]
```
            """
        )

        st.markdown("#### 📦 Payload Contracts to Jev AI")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown("**1. Ingestion Gate Payload to Jev:**")
            st.code(
                """{
  "context": "From: proxy-alerts@custodian.com\\nSubject: Urgent: Action Required for ABC Corp Merger\\nBody: Please review the attached corporate proxy document for restructuring options.",
  "questions": {
    "requires_heavy_ocr": {
      "type": "Noul",
      "description": "True if the context lacks actionable dates/terms and explicitly points to an attached PDF or image file for full details."
    }
  }
}""",
                language="json",
            )
        with col_p2:
            st.markdown("**2. Core Decision Payload to Jev:**")
            st.code(
                """{
  "context": "[Email Body + Flattened Attachment Text]",
  "questions": {
    "event_type": {
      "type": "Choice",
      "choices": ["Cash_Dividend", "Stock_Dividend", "Merger_Acquisition", "Ticker_Change", "Spam_Or_Irrelevant"]
    },
    "is_actionable": {
      "type": "Noul",
      "description": "True if our operations desk must respond, submit an election, or alert clients. False if it is just an FYI update."
    },
    "urgency": {
      "type": "Score",
      "description": "Scale 1-10 of how critical the timeline is. A 10 means the deadline is within 48 hours."
    }
  }
}""",
                language="json",
            )

    st.divider()

    # Interactive Runner Controls
    st.subheader("⚡ Execute Pipeline")
    run_col1, run_col2, run_col3 = st.columns([1.5, 1.5, 3])

    if st.session_state.emails:
        email_map_flow = {
            f"[{e.id}] {e.subject[:50]}... ({e.sender or 'Unknown'})": e
            for e in st.session_state.emails
        }
        selected_flow_key = st.selectbox(
            "Select email from inbox to run through pipeline:",
            list(email_map_flow.keys()),
            key="flow_email_select",
        )
        flow_target_email = email_map_flow[selected_flow_key]
    else:
        flow_target_email = None

    with run_col1:
        btn_run_single = st.button("▶️ Run Single Email", type="primary", use_container_width=True)
    with run_col2:
        btn_run_all = st.button("🚀 Run All & Sort By Urgency", use_container_width=True)

    # Custom Email Tester (Pre-populated with user prompt example)
    with st.expander("🧪 Test with Custom Payload (e.g. ABC Corp Merger Example)", expanded=False):
        c_from_val = st.text_input("Sender", "proxy-alerts@custodian.com", key="custom_from")
        c_subj_val = st.text_input("Subject", "Urgent: Action Required for ABC Corp Merger", key="custom_subj")
        c_body_val = st.text_area(
            "Body",
            "Please review the attached corporate proxy document for restructuring options.",
            height=80,
            key="custom_body",
        )
        c_att_val = st.text_input("Attached Document Filename", "abc_corp_merger_proxy.pdf", key="custom_att")
        
        if st.button("⚡ Run Pipeline on Custom Payload"):
            att_obj = EmailAttachment(filename=c_att_val) if c_att_val else None
            custom_msg = EmailMessage(
                id="custom-test-payload",
                sender=c_from_val,
                subject=c_subj_val,
                body=c_body_val,
                attachments=[att_obj] if att_obj else [],
            )
            flow_res = orchestrator.process_email(custom_msg)
            st.session_state.ca_flow_results[custom_msg.id] = flow_res
            flow_target_email = custom_msg
            btn_run_single = True

    # Execution logic
    if btn_run_single and flow_target_email:
        with st.spinner("Processing through 4-stage pipeline..."):
            flow_res = orchestrator.process_email(flow_target_email)
            st.session_state.ca_flow_results[flow_target_email.id] = flow_res
            st.success(f"Pipeline executed in {flow_res.total_latency_ms} ms!")

    if btn_run_all and st.session_state.emails:
        with st.spinner(f"Processing all {len(st.session_state.emails)} emails through the pipeline..."):
            all_results = orchestrator.process_batch(st.session_state.emails)
            for res in all_results:
                st.session_state.ca_flow_results[res.email_id] = res
            st.success(f"Processed {len(all_results)} emails! Sorted queue by Urgency Score.")

    # Display Current Single Email Inspection
    if flow_target_email and flow_target_email.id in st.session_state.ca_flow_results:
        res: CorporateActionFlowResult = st.session_state.ca_flow_results[flow_target_email.id]
        
        st.markdown(f"### 📋 Execution Report: *{res.subject}*")
        
        # High Level Metric Cards
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Stage 1: OCR Required?", "YES (Prob > 0.50)" if res.ingestion_gate.requires_heavy_ocr else "NO (Raw Text)")
        m_col2.metric("Stage 3: Event Type", res.core_decision.event_type)
        m_col3.metric("Stage 3: Urgency Score", f"{res.core_decision.urgency_score} / 10", delta="High Urgency" if res.core_decision.urgency_score >= 8 else None)
        route_label = "Gemini Client Notice" if res.route == "GEMINI_CLIENT_NOTICE" else "Human-in-the-Loop"
        m_col4.metric("Stage 4: Router Target", route_label)

        # 4 Stage Step-by-Step Breakdown
        s1, s2, s3, s4 = st.columns(4)

        # Stage 1 Card
        with s1:
            with st.container(border=True):
                st.markdown("#### 1️⃣ JEV Ingestion Gate")
                st.caption("Q: Are attachments/OCR required?")
                prob = res.ingestion_gate.ocr_probability
                st.progress(float(prob))
                st.write(f"**OCR Probability:** `{prob:.1%}`")
                if res.ingestion_gate.requires_heavy_ocr:
                    st.warning("⚡ Prob > 0.50: Triggers Gemini OCR")
                else:
                    st.info("📄 Prob <= 0.50: Raw Text Envelope")
                st.caption(f"Reasoning: {res.ingestion_gate.reasoning}")
                st.caption(f"Gate Latency: {res.ingestion_gate.latency_ms} ms")

        # Stage 2 Card
        with s2:
            with st.container(border=True):
                st.markdown("#### 2️⃣ Envelope & OCR")
                if res.ocr_applied:
                    st.success("✅ Gemini Vision OCR executed")
                    st.caption("Extracted and flattened PDF document text into normalized matrix.")
                    with st.expander("View Flattened OCR"):
                        st.text(flow_target_email.ocr_extracted_text)
                else:
                    st.info("📄 Raw Text Envelope used")
                    st.caption("Complete corporate action dates present directly in body.")

        # Stage 3 Card
        with s3:
            with st.container(border=True):
                st.markdown("#### 3️⃣ JEV Core Decision")
                st.write(f"**Event:** `{res.core_decision.event_type}`")
                st.write(f"**Confidence:** `{res.core_decision.event_type_confidence:.1%}`")
                is_act_str = "✅ True (Actionable)" if res.core_decision.is_actionable else "ℹ️ False (Informational)"
                st.write(f"**Is Actionable:** {is_act_str}")
                st.write(f"**Urgency:** `{res.core_decision.urgency_score}/10`")
                st.caption(f"Decision Latency: {res.core_decision.latency_ms} ms")

        # Stage 4 Card
        with s4:
            with st.container(border=True):
                st.markdown("#### 4️⃣ Application Router")
                if res.route == "GEMINI_CLIENT_NOTICE":
                    st.success("🎯 **Gemini Draft Client Notice**")
                    st.caption("Actionable event with high confidence. Generated structured election notice.")
                else:
                    st.warning("🧑‍💼 **Human-in-the-Loop Queue**")
                    st.caption("Informational notice or operational break requiring manual review.")

        # Stage 4 Execution Detail
        st.divider()
        if res.route == "GEMINI_CLIENT_NOTICE" and res.client_notice:
            st.markdown("### ✉️ Gemini: Structured Client Election Notice Draft")
            st.caption("Automated client advisory ready for Portfolio Managers and Beneficial Owners:")
            with st.container(border=True):
                st.markdown(f"**Subject:** `{res.client_notice.subject}`")
                st.markdown(f"**Recipient Role:** `{res.client_notice.recipient_role}`")
                st.markdown(f"**Critical Client Deadline:** `{res.client_notice.deadline}`")
                
                st.markdown("**Election Options Identified:**")
                for opt in res.client_notice.election_options:
                    st.markdown(f"- {opt}")
                
                with st.expander("📄 View Full Drafted Client Notice Email", expanded=True):
                    st.text_area("Client Notice Body", res.client_notice.full_email_body, height=280)
        
        elif res.route == "HUMAN_IN_THE_LOOP" and res.hitl_item:
            st.markdown("### 🧑‍💼 Human-in-the-Loop Operational Exception")
            with st.container(border=True):
                r_badge = {
                    "CRITICAL": "red",
                    "HIGH": "orange",
                    "MEDIUM": "blue",
                    "LOW": "green",
                    "INFO": "grey",
                }.get(res.hitl_item.risk_level, "blue")
                st.markdown(f":{r_badge}[● **Risk Level: {res.hitl_item.risk_level}**]")
                st.write(f"**Ticket ID:** `{res.hitl_item.queue_id}`")
                st.write(f"**Reason for Review:** {res.hitl_item.reason}")
                st.write(f"**Clarification Needed:** {res.hitl_item.clarification_needed}")
                st.write(f"**Recommended Operations Action:** `{res.hitl_item.suggested_action}`")

    # Dynamic Urgency-Sorted Queue
    if st.session_state.ca_flow_results:
        st.divider()
        st.subheader("📊 Dynamic Operational Queue (Sorted by Urgency Score: 10 → 1)")
        
        all_sorted = sorted(
            list(st.session_state.ca_flow_results.values()),
            key=lambda r: r.core_decision.urgency_score,
            reverse=True,
        )

        q_table = []
        for rank, r in enumerate(all_sorted, 1):
            q_table.append({
                "Rank": f"#{rank}",
                "Urgency Score": f"{r.core_decision.urgency_score}/10",
                "Subject": r.subject[:45] + "...",
                "Event Type": r.core_decision.event_type,
                "Actionable?": "YES" if r.core_decision.is_actionable else "NO",
                "OCR Applied?": "⚡ YES (Gemini)" if r.ocr_applied else "NO",
                "Router Decision": "✉️ Gemini Client Notice" if r.route == "GEMINI_CLIENT_NOTICE" else "🧑‍💼 HITL Queue",
                "Latency (ms)": f"{r.total_latency_ms} ms",
            })
        st.dataframe(pd.DataFrame(q_table), use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: INBOX & EMAIL EXPLORER
# ─────────────────────────────────────────────────────────────────────────────
with tab_inbox:
    col_metrics1, col_metrics2, col_metrics3, col_metrics4 = st.columns(4)
    processed_count = len(st.session_state.processed_records)
    escalated_count = sum(
        1 for r in st.session_state.processed_records.values() if r.workflow.escalate_to_human
    )
    col_metrics1.metric("Total Ingested", len(st.session_state.emails))
    col_metrics2.metric("Processed by Jev", processed_count)
    col_metrics3.metric("Human Escalations", escalated_count)
    col_metrics4.metric("Formats", ".eml, .json, .txt")

    if not st.session_state.emails:
        st.warning(f"No emails found in `{current_dir}`. Click '⚡ Regenerate' in the sidebar.")
    else:
        st.subheader("Select or Ingest Emails")
        email_options = {
            f"[{e.id}] {e.subject[:55]}... ({e.sender or 'Unknown'})": e
            for e in st.session_state.emails
        }

        selected_label = st.selectbox("Select email to inspect", list(email_options.keys()))
        current_email = email_options[selected_label]

        col_view1, col_view2 = st.columns([1, 1])

        with col_view1:
            st.markdown("### 📧 Email Metadata")
            st.write(f"**ID:** `{current_email.id}`")
            st.write(f"**Subject:** {current_email.subject}")
            st.write(f"**From:** `{current_email.sender}`")
            st.write(f"**To:** `{current_email.recipient}`")
            st.write(f"**Date:** {current_email.date or 'N/A'}")
            if current_email.attachments:
                att_names = ", ".join(a.filename for a in current_email.attachments)
                st.write(f"**Attachments:** 📎 `{att_names}`")
            if current_email.source_file:
                st.caption(f"Source file: `{Path(current_email.source_file).name}`")

            with st.expander("Raw Headers"):
                st.json(current_email.raw_headers)

        with col_view2:
            st.markdown("### 📝 Email Content")
            st.text_area("Body", current_email.body, height=280, disabled=True)

    st.divider()
    st.subheader("✍️ Compose / Ingest Custom Email")
    with st.expander("Compose Custom Email"):
        c_subj = st.text_input("Subject", "Urgent: Action Required for ABC Corp Merger", key="inbox_custom_subj")
        c_from = st.text_input("Sender", "proxy-alerts@custodian.com", key="inbox_custom_from")
        c_body = st.text_area("Body", "Please review the attached corporate proxy document for restructuring options.", height=100, key="inbox_custom_body")

        if st.button("➕ Ingest to Inbox"):
            custom_email = parse_raw_text(f"Subject: {c_subj}\nFrom: {c_from}\n\n{c_body}")
            st.session_state.emails.insert(0, custom_email)
            st.success("Custom email ingested to inbox!")
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: JEV AI DECISION INSPECTOR
# ─────────────────────────────────────────────────────────────────────────────
with tab_inspector:
    st.subheader("Run Jev AI 'System One' Decision Engine (Desk Classifier)")
    st.caption(f"Domain model: **{active_domain}** | Model: `jev-system-one`")

    col_btn1, col_btn2 = st.columns([1, 3])
    with col_btn1:
        classify_single = st.button("⚡ Classify Selected Email", type="primary", key="insp_single")
    with col_btn2:
        classify_all = st.button("🚀 Batch Classify All Emails", key="insp_all")

    if st.session_state.emails:
        if classify_single:
            with st.spinner("Invoking Jev AI System One..."):
                decision = classifier.classify_email(current_email)
                record = engine.process(current_email, decision)
                st.session_state.processed_records[current_email.id] = record

        if classify_all:
            progress_bar = st.progress(0)
            for idx, em in enumerate(st.session_state.emails):
                decision = classifier.classify_email(em)
                record = engine.process(em, decision)
                st.session_state.processed_records[em.id] = record
                progress_bar.progress((idx + 1) / len(st.session_state.emails))
            st.success(f"Successfully processed all {len(st.session_state.emails)} emails!")

        if current_email.id in st.session_state.processed_records:
            rec = st.session_state.processed_records[current_email.id]
            dec = rec.classification

            st.divider()
            st.markdown(f"### Classification Results: *{current_email.subject}*")

            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
            col_stat1.metric("Category Choice", dec.category.upper())
            col_stat2.metric("Urgency (Noul)", f"{dec.urgency_probability:.1%}")
            col_stat3.metric("Severity Score", f"{dec.severity_score} / 5")
            col_stat4.metric("Latency", f"{dec.latency_ms} ms")

            col_card1, col_card2, col_card3 = st.columns(3)

            with col_card1:
                st.markdown("#### 🎯 1. `Choice` Primitive")
                st.write(f"**Predicted Category:** `{dec.category}`")
                st.write(f"**Confidence:** `{dec.category_confidence:.1%}`")
                st.write(f"**Suggested Action:** `{dec.suggested_action}`")
                if dec.category_probabilities:
                    df_cat = pd.DataFrame(
                        list(dec.category_probabilities.items()),
                        columns=["Category", "Probability"],
                    ).sort_values(by="Probability", ascending=False)
                    st.caption("Choice Probability Distribution:")
                    st.bar_chart(df_cat.set_index("Category"))

            with col_card2:
                st.markdown("#### ⚖️ 2. `Noul` Primitive (Calibrated)")
                st.write("**Urgency Calibration (0.0 – 1.0):**")
                st.progress(float(dec.urgency_probability))
                st.write(f"Score: **{dec.urgency_probability:.1%}** (Threshold: {urgency_thresh:.1%})")

                st.write("**Human Escalation Probability:**")
                st.progress(float(dec.escalation_probability))
                st.write(f"Score: **{dec.escalation_probability:.1%}**")

                if dec.urgency_probability >= urgency_thresh:
                    st.error("🚨 HIGH URGENCY TRIGGERED")
                else:
                    st.success("✅ Standard Urgency")

            with col_card3:
                st.markdown("#### 📊 3. `Score` Primitive (1–5 Rubric)")
                st.write(f"**Operational Exposure / Severity:** Level {dec.severity_score}/5")
                st.write(f"**Confidence:** `{dec.severity_confidence:.1%}`")
                if dec.severity_probabilities:
                    df_sev = pd.DataFrame(
                        [{"Severity": f"Sev {k+1}", "Probability": v} for k, v in dec.severity_probabilities.items()]
                    )
                    st.caption("Score Rubric Distribution:")
                    st.bar_chart(df_sev.set_index("Severity"))

            with st.expander("🔍 View Raw Jev AI Response Payload"):
                st.json(dec.raw_answers)
        else:
            st.info("Click **'⚡ Classify Selected Email'** or **'🚀 Batch Classify All Emails'** to run Jev AI.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4: OPERATIONAL DESK BOARD
# ─────────────────────────────────────────────────────────────────────────────
with tab_workflow:
    st.subheader("🚦 Operational Desks & Human Escalations")

    if not st.session_state.processed_records:
        st.warning("No emails have been classified yet. Go to the **Decision Inspector** tab and click Classify.")
    else:
        records_list = list(st.session_state.processed_records.values())

        critical_escalations = [r for r in records_list if r.workflow.alert_level == "CRITICAL"]
        warning_escalations = [r for r in records_list if r.workflow.alert_level == "WARNING"]

        if critical_escalations:
            st.error(f"🚨 **{len(critical_escalations)} CRITICAL Escalation(s) Active!** Immediate specialist intervention required.")
        elif warning_escalations:
            st.warning(f"⚠️ **{len(warning_escalations)} Priority Warning(s) Active.** Escalated to operations review.")
        else:
            st.success("🟢 All processed emails routed cleanly without critical escalations.")

        active_desks = (
            CORPORATE_ACTIONS_QUEUE_MAP
            if active_domain == "corporate_actions"
            else GENERAL_QUEUE_MAP
        )

        st.markdown(f"### 📂 Operational Desks: {domain_label}")
        queue_cols = st.columns(3)
        distinct_queues = list(active_desks.values())

        for idx, q_name in enumerate(distinct_queues):
            col_target = queue_cols[idx % 3]
            q_records = [r for r in records_list if r.workflow.target_queue == q_name]

            with col_target:
                with st.container(border=True):
                    st.markdown(f"**{q_name}** ({len(q_records)})")
                    if not q_records:
                        st.caption("No emails in desk queue.")
                    for q_rec in q_records:
                        alert_color = {
                            "CRITICAL": "red",
                            "WARNING": "orange",
                            "INFO": "green",
                        }.get(q_rec.workflow.alert_level, "grey")

                        st.markdown(f":{alert_color}[●] **{q_rec.email.subject[:34]}...**")
                        st.caption(f"Action: `{q_rec.workflow.suggested_action}` | Tags: {', '.join(q_rec.workflow.tags[:2])}")

        st.divider()
        st.markdown("### 📋 Complete Workflow Execution Audit Log")

        log_data = []
        for r in records_list:
            log_data.append({
                "Email ID": r.email.id,
                "Subject": r.email.subject,
                "Category": r.classification.category,
                "Urgency Prob": f"{r.classification.urgency_probability:.1%}",
                "Severity": f"{r.classification.severity_score}/5",
                "Target Desk / Queue": r.workflow.target_queue,
                "Escalated?": "🚨 YES" if r.workflow.escalate_to_human else "NO",
                "Alert Level": r.workflow.alert_level,
                "Suggested Action": r.workflow.suggested_action,
                "Tags": " | ".join(r.workflow.tags),
            })

        st.dataframe(pd.DataFrame(log_data), use_container_width=True)
