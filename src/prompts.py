# src/prompts.py
"""Versioned prompt library.
Every prompt has a VERSION, CHANGELOG, and a builder function.
This provides full traceability: log prompt_id + version per API call."""

from typing import Optional

# ── TASK 1 — TRIAGE PROMPTS ──

TRIAGE_CLASSIFY_VERSION = "1.0.0"
TRIAGE_CLASSIFY_CHANGELOG = "v1.0.0 — Initial release. Classifies product, category, urgency with CoT reasoning."

def triage_classify_prompt(
    subject: str, body: str, kb_context: str,
    products: list[str], categories: list[str],
) -> str:
    return f"""You are an expert support ticket classifier for a B2B SaaS platform.

Classify the ticket below and return ONLY valid JSON — no explanation, no markdown fences.

## Allowed values
Products: {products}
Categories: {categories}
Urgency: P1 (critical, business stopped), P2 (major, workaround needed), P3 (moderate, workaround available), P4 (low, cosmetic)
Responder teams: tier1-general, tier1-billing, tier2-engineering, tier2-data, escalation-tam

## Knowledge base context (use only if relevant)
{kb_context}

## Ticket
Subject: {subject}
Body: {body}

## Required JSON output
{{{{
  "product": "<one of the allowed products>",
  "product_area": "<specific module or area>",
  "category": "<one of the allowed categories>",
  "urgency": "<P1|P2|P3|P4>",
  "urgency_reasoning": "<1-2 sentences explaining urgency choice>",
  "kb_match": {{{{
    "matched": <true|false>,
    "source": "<file path or null>",
    "heading": "<section heading or null>",
    "relevance": "<1 sentence on why this KB section applies, or null>"
  }}}},
  "responder_team": "<one of the allowed teams>",
  "routing_reasoning": "<1 sentence explaining team choice>"
}}}}"""


TRIAGE_DRAFT_VERSION = "1.0.0"
TRIAGE_DRAFT_CHANGELOG = "v1.0.0 — Initial release. Generates draft first-response email."

def triage_draft_prompt(
    subject: str, body: str, classification: dict, kb_context: str,
) -> str:
    return f"""You are a senior support engineer writing a first-response email.

Write a professional, empathetic, and actionable first-response draft.
- Acknowledge the issue specifically (mention the product and symptom).
- Reference relevant KB steps if applicable.
- Do NOT invent solutions — only suggest steps from the KB context or known safe advice.
- Keep it under 150 words.
- Return ONLY the email body text — no subject line, no JSON wrapper.

## Classification
Product: {classification.get('product')}
Category: {classification.get('category')}
Urgency: {classification.get('urgency')}

## Knowledge base context
{kb_context}

## Original ticket
Subject: {subject}
Body: {body}

Draft email body:"""


# ── TASK 2 — TAM ACCOUNT SUMMARISER PROMPTS ──

TAM_SUMMARY_VERSION = "1.0.0"
TAM_SUMMARY_CHANGELOG = "v1.0.0 — Initial release. 3-section account brief."

def tam_executive_summary_prompt(account: dict, ticket_summaries: str) -> str:
    return f"""You are a Technical Account Manager assistant generating a pre-QBR brief.

Write a 3-5 sentence executive summary of this account's current health.
Be direct and data-driven. Reference specific numbers (ARR, seats, ticket counts).
Return ONLY the paragraph text — no JSON, no headers.

## Account data
Company: {account.get('company')}
Plan: {account.get('plan_tier')} | ARR: ${account.get('arr_usd', 0):,}
Seats licensed: {account.get('seats_licensed')} | Seats active: {account.get('seats_active')}
Health status: {account.get('health_status')} | Usage trend: {account.get('usage_trend')}
Open tickets: {account.get('open_tickets')} | P1 tickets (last 30d): {account.get('p1_tickets_last_30d')}
NPS score: {account.get('nps_score', 'Not submitted')}
Renewal date: {account.get('renewal_date')}
Customer since: {account.get('customer_since')}
Products: {', '.join(account.get('products', []))}

## Recent ticket context (last 90 days)
{ticket_summaries}

Executive summary:"""


def tam_risks_prompt(account: dict, ticket_summaries: str, escalation_notes: list) -> str:
    return f"""You are a Technical Account Manager assistant.

Identify open risks and escalation signals for this account.
For each risk, quote the EXACT text from ticket bodies or escalation notes as evidence.
Return ONLY valid JSON — no markdown, no explanation outside the JSON.

## Account data
Company: {account.get('company')} | Health: {account.get('health_status')} | Trend: {account.get('usage_trend')}
P1 tickets (last 30d): {account.get('p1_tickets_last_30d')}
Escalation notes: {escalation_notes}

## Recent tickets (last 90 days)
{ticket_summaries}

## Required JSON output
{{{{
  "churn_risk": <true|false>,
  "churn_risk_score": <0.0-1.0>,
  "risks": [
    {{{{
      "risk_type": "<Churn Signal|Technical Escalation|Billing Concern|Adoption Gap|Executive Attention>",
      "description": "<1-2 sentences>",
      "evidence_quote": "<exact quote from ticket body or escalation notes>"
    }}}}
  ]
}}}}"""


def tam_talking_points_prompt(account: dict, risks: dict, ticket_summaries: str) -> str:
    return f"""You are a Technical Account Manager preparing for a Quarterly Business Review.

Generate 3-5 specific, actionable talking points for the QBR conversation.
Each point should reference specific data. Avoid generic advice.
Return ONLY valid JSON.

## Account
Company: {account.get('company')} | ARR: ${account.get('arr_usd', 0):,}
Renewal: {account.get('renewal_date')} | Health: {account.get('health_status')}
Products: {', '.join(account.get('products', []))}

## Identified risks
{risks}

## Ticket context
{ticket_summaries}

## Required JSON output
{{{{
  "talking_points": [
    {{{{
      "topic": "<short title>",
      "detail": "<1-2 sentence specific talking point>",
      "suggested_action": "<concrete next step>"
    }}}}
  ]
}}}}"""
