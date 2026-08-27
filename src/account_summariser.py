# src/account_summariser.py
"""Task 2 — TAM Account Health Summariser.
Pipeline: fetch account + tickets -> chain of 3 prompts -> deterministic brief.
Determinism achieved via temperature=0."""

import json
import re
from typing import Optional
import google.generativeai as genai
from pydantic import BaseModel, Field

from src.data_loader import get_account, get_account_tickets
from src.prompts import (
    tam_executive_summary_prompt, TAM_SUMMARY_VERSION,
    tam_risks_prompt,
    tam_talking_points_prompt,
)


class ChurnRisk(BaseModel):
    churn_risk: bool
    churn_risk_score: float
    risks: list[dict]


class TalkingPoint(BaseModel):
    topic: str
    detail: str
    suggested_action: str


class AccountBrief(BaseModel):
    account_id: str
    company: str
    tam: str
    health_status: str
    renewal_date: str
    executive_summary: str
    churn_risk: bool
    churn_risk_score: float
    flagged_risks: list[dict]
    talking_points: list[dict]
    tickets_analysed: int
    data_freshness_days: int = 90
    prompt_versions: dict = Field(default_factory=dict)


def _call_gemini_deterministic(prompt: str, max_retries: int = 4) -> str:
    import time as _time
    model = genai.GenerativeModel(
        model_name="models/gemini-3.5-flash-lite",
        generation_config=genai.types.GenerationConfig(
            temperature=0.0,
            max_output_tokens=2048,
            top_p=1.0,
            top_k=1,
        ),
    )
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                wait = 15 * (attempt + 1)
                print(f"  [Rate Limit] 429 error, retrying in {wait}s...")
                _time.sleep(wait)
            else:
                raise


def _parse_json_safely(text: str) -> dict:
    fence = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if fence:
        text = fence.group(1).strip()
    start = text.find('{')
    if start == -1:
        raise ValueError(f"No JSON in: {text[:200]}")
    try:
        return json.loads(text[start:])
    except json.JSONDecodeError:
        end = text.rfind('}')
        if end != -1:
            return json.loads(text[start:end + 1])
        raise


def _summarise_tickets(tickets: list[dict]) -> str:
    if not tickets:
        return "No tickets found in the last 90 days."
    lines = []
    for t in tickets[:20]:
        body_preview = (t.get("body", "")[:200] + "...") if len(t.get("body", "")) > 200 else t.get("body", "")
        lines.append(
            f"[{t['ticket_id']}] [{t['urgency']}] [{t['status']}] [{t['category']}]\n"
            f"Subject: {t['subject']}\n"
            f"Body: {body_preview}\n"
        )
    return "\n---\n".join(lines)


def generate_account_brief(account_id: str) -> AccountBrief:
    account = get_account(account_id)
    if account is None:
        raise ValueError(f"Account {account_id} not found in accounts.json")
    tickets = get_account_tickets(account_id, days=90)
    ticket_summaries = _summarise_tickets(tickets)
    escalation_notes = account.get("escalation_notes", [])

    # Step 1: Executive Summary
    exec_prompt = tam_executive_summary_prompt(account, ticket_summaries)
    executive_summary = _call_gemini_deterministic(exec_prompt)

    # Step 2: Risk Detection
    risks_prompt_text = tam_risks_prompt(account, ticket_summaries, escalation_notes)
    raw_risks = _call_gemini_deterministic(risks_prompt_text)
    try:
        risks_data = _parse_json_safely(raw_risks)
    except (ValueError, json.JSONDecodeError):
        risks_data = {
            "churn_risk": account.get("health_status") in ("Churning", "At Risk"),
            "churn_risk_score": 0.7 if account.get("health_status") == "Churning" else 0.4,
            "risks": [{"risk_type": "Parse Error", "description": "Risk analysis unavailable.", "evidence_quote": ""}],
        }

    # Step 3: Talking Points
    talking_prompt = tam_talking_points_prompt(account, risks_data, ticket_summaries)
    raw_talking = _call_gemini_deterministic(talking_prompt)
    try:
        talking_data = _parse_json_safely(raw_talking)
        talking_points = talking_data.get("talking_points", [])
    except (ValueError, json.JSONDecodeError):
        talking_points = [{"topic": "Review Required", "detail": "Could not generate talking points.", "suggested_action": "Manual review."}]

    return AccountBrief(
        account_id=account_id,
        company=account["company"],
        tam=account.get("tam", "Unassigned"),
        health_status=account["health_status"],
        renewal_date=account.get("renewal_date", "Unknown"),
        executive_summary=executive_summary,
        churn_risk=risks_data.get("churn_risk", False),
        churn_risk_score=float(risks_data.get("churn_risk_score", 0.0)),
        flagged_risks=risks_data.get("risks", []),
        talking_points=talking_points,
        tickets_analysed=len(tickets),
        prompt_versions={
            "tam_executive_summary": TAM_SUMMARY_VERSION,
            "tam_risks": TAM_SUMMARY_VERSION,
            "tam_talking_points": TAM_SUMMARY_VERSION,
        },
    )
