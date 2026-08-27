# app.py
"""Streamlit UI — Bonus.
Multi-tab interface for ticket triage, account health, KB explorer, and evaluation."""

import os
import json
import streamlit as st
import httpx
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Zycus AI Support Intelligence",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #2a2a4a;
    }
    .risk-high { color: #ff4444; font-weight: bold; }
    .risk-low { color: #44ff44; font-weight: bold; }
    .header-gradient {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="header-gradient">🤖 Zycus AI Support Intelligence</p>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["🎫 Ticket Triage", "📊 Account Health", "📚 KB Explorer", "📈 Evaluation"])

with tab1:
    st.header("Intelligent Ticket Triage")
    st.markdown("Submit a support ticket for AI-powered classification, KB matching, and draft response generation.")

    col1, col2 = st.columns([1, 1])

    with col1:
        with st.form("triage_form"):
            ticket_id = st.text_input("Ticket ID (optional)", placeholder="TKT-XXXXX")
            subject = st.text_input("Subject", placeholder="Describe the issue briefly")
            body = st.text_area("Description", height=200, placeholder="Full ticket body...")
            submitted = st.form_submit_button("🔍 Triage Ticket", type="primary", use_container_width=True)

    with col2:
        if submitted and subject and body:
            with st.spinner("Analysing ticket with AI..."):
                try:
                    response = httpx.post(
                        f"{API_BASE}/triage",
                        json={"subject": subject, "body": body, "ticket_id": ticket_id or None},
                        timeout=60.0,
                    )
                    if response.status_code == 200:
                        result = response.json()

                        # Classification
                        st.subheader("📋 Classification")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Product", result.get("product", "N/A"))
                        c2.metric("Category", result.get("category", "N/A"))
                        urgency = result.get("urgency", "N/A")
                        c3.metric("Urgency", urgency)

                        st.info(f"**Urgency Reasoning:** {result.get('urgency_reasoning', 'N/A')}")

                        # Routing
                        st.subheader("🔀 Routing")
                        st.success(f"**Team:** {result.get('responder_team', 'N/A')}")
                        st.caption(result.get("routing_reasoning", ""))

                        # KB Match
                        kb = result.get("kb_match", {})
                        if kb.get("matched"):
                            st.subheader("📚 KB Match")
                            st.info(f"**Source:** {kb.get('source')} — {kb.get('heading')}")
                            st.caption(kb.get("relevance", ""))

                        # Draft Response
                        st.subheader("✉️ Draft Response")
                        st.text_area("Draft email", result.get("draft_response", ""), height=150, disabled=True)

                        # Raw JSON
                        with st.expander("📄 Raw JSON"):
                            st.json(result)
                    else:
                        st.error(f"API Error: {response.status_code} — {response.text[:200]}")
                except httpx.ConnectError:
                    st.error("Cannot connect to API. Start the server: `uvicorn main:app --reload`")
                except Exception as e:
                    st.error(f"Error: {str(e)[:200]}")
        elif submitted:
            st.warning("Please fill in both Subject and Description.")

with tab2:
    st.header("Account Health 360°")

    try:
        acct_response = httpx.get(f"{API_BASE}/accounts", timeout=10.0)
        if acct_response.status_code == 200:
            accounts_data = acct_response.json()
            accounts_list = accounts_data.get("accounts", [])

            options = {f"{a['company']} ({a['account_id']})": a["account_id"] for a in accounts_list}
            selected = st.selectbox("Select Account", list(options.keys()))

            if selected:
                account_id = options[selected]

                if st.button("📊 Generate Health Brief", type="primary"):
                    with st.spinner("Generating account brief..."):
                        try:
                            resp = httpx.post(f"{API_BASE}/summarise/{account_id}", timeout=120.0)
                            if resp.status_code == 200:
                                brief = resp.json()

                                # Metrics row
                                m1, m2, m3, m4 = st.columns(4)
                                m1.metric("Health", brief.get("health_status", "N/A"))
                                m2.metric("Churn Risk", f"{brief.get('churn_risk_score', 0):.0%}")
                                m3.metric("Tickets Analysed", brief.get("tickets_analysed", 0))
                                m4.metric("Renewal", brief.get("renewal_date", "N/A"))

                                # Executive Summary
                                st.subheader("📝 Executive Summary")
                                st.write(brief.get("executive_summary", "N/A"))

                                # Risks
                                st.subheader("⚠️ Flagged Risks")
                                risks = brief.get("flagged_risks", [])
                                if risks:
                                    for risk in risks:
                                        with st.expander(f"{risk.get('risk_type', 'Risk')}"):
                                            st.write(risk.get("description", ""))
                                            if risk.get("evidence_quote"):
                                                st.caption(f'Evidence: "{risk["evidence_quote"]}"')
                                else:
                                    st.success("No significant risks detected.")

                                # Talking Points
                                st.subheader("💬 QBR Talking Points")
                                for tp in brief.get("talking_points", []):
                                    st.markdown(f"**{tp.get('topic', '')}**")
                                    st.write(tp.get("detail", ""))
                                    st.caption(f"Action: {tp.get('suggested_action', '')}")
                                    st.divider()

                                with st.expander("📄 Raw JSON"):
                                    st.json(brief)
                            else:
                                st.error(f"Error: {resp.status_code} — {resp.text[:200]}")
                        except Exception as e:
                            st.error(f"Error: {str(e)[:200]}")
        else:
            st.error("Cannot load accounts from API.")
    except httpx.ConnectError:
        st.error("Cannot connect to API. Start the server: `uvicorn main:app --reload`")
    except Exception as e:
        st.error(f"Error: {str(e)[:200]}")

with tab3:
    st.header("Knowledge Base Explorer")
    st.markdown("Query the vector database to inspect indexed KB chunks and similarity scores.")

    query = st.text_input("Search query", placeholder="e.g., SSO SAML configuration error")
    top_k = st.slider("Results", 1, 10, 3)

    if query:
        with st.spinner("Searching KB..."):
            try:
                from src.kb_index import search_kb, build_index, _collection
                # Build the index once per Streamlit session
                if _collection is None:
                    api_key = os.getenv("GEMINI_API_KEY")
                    if not api_key:
                        st.error("GEMINI_API_KEY not set. Add it to your .env file.")
                    else:
                        with st.status("Building KB index (first time only)..."):
                            build_index(api_key)
                from src.kb_index import _collection as col
                if col is not None:
                    results = search_kb(query, top_k=top_k)
                    if results:
                        for i, r in enumerate(results):
                            with st.expander(f"#{i+1} — {r['heading']} (Score: {r['score']:.4f})"):
                                st.caption(f"Source: {r['source']}")
                                st.markdown(r["text"][:500])
                    else:
                        st.info("No matching KB chunks found.")
                else:
                    st.warning("KB index could not be built. Check your API key.")
            except Exception as e:
                st.error(f"KB search error: {str(e)[:200]}")

with tab4:
    st.header("Evaluation Dashboard")
    st.markdown("View the latest evaluation report.")

    if os.path.exists("eval_report.md"):
        with open("eval_report.md", "r", encoding="utf-8") as f:
            st.markdown(f.read())
    else:
        st.info("No evaluation report found. Run `python run_eval.py` to generate one.")

    if st.button("🔄 Run Evaluation Now", type="secondary"):
        st.warning("Run evaluation from the terminal: `python run_eval.py`")
