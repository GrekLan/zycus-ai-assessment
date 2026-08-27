# src/triage_agent.py
"""Task 1 — Intelligent Ticket Triage Agent.
Pipeline: embed ticket -> retrieve KB docs -> classify -> draft response.
Returns a structured TriageResult dict."""

import json
import os
import re
from typing import Optional
import google.generativeai as genai
from pydantic import BaseModel, Field

from src.kb_index import search_kb
from src.prompts import (
    triage_classify_prompt, TRIAGE_CLASSIFY_VERSION,
    triage_draft_prompt, TRIAGE_DRAFT_VERSION,
)

PRODUCTS = ["DataBridge Pro", "CloudSync", "AnalyticsHub", "SecureVault", "WorkflowEngine"]
CATEGORIES = ["Bug", "Feature Request", "How-To", "Performance", "Billing",
              "Integration", "Onboarding", "Data Loss"]
URGENCIES = ["P1", "P2", "P3", "P4"]


class KBMatch(BaseModel):
    matched: bool
    source: Optional[str] = None
    heading: Optional[str] = None
    relevance: Optional[str] = None


class TriageResult(BaseModel):
    ticket_id: Optional[str] = None
    product: str
    product_area: str
    category: str
    urgency: str
    urgency_reasoning: str
    kb_match: KBMatch
    responder_team: str
    routing_reasoning: str
    draft_response: str
    prompt_versions: dict = Field(default_factory=dict)


def _call_gemini(prompt: str, temperature: float = 0.2, max_retries: int = 4) -> str:
    import time as _time
    model = genai.GenerativeModel(
        model_name="models/gemini-3.5-flash-lite",
        generation_config=genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=1024,
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
        raise ValueError(f"No JSON object found in response: {text[:200]}")
    try:
        return json.loads(text[start:])
    except json.JSONDecodeError:
        end = text.rfind('}')
        if end != -1:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Failed to parse JSON: {text[:300]}")


def run_triage(
    subject: str, body: str, ticket_id: Optional[str] = None,
) -> TriageResult:
    # Step 1: Retrieve relevant KB docs
    search_query = f"{subject}\n{body[:500]}"
    kb_results = search_kb(search_query, top_k=3)
    kb_context = ""
    if kb_results:
        sections = []
        for r in kb_results:
            sections.append(
                f"[Source: {r['source']} | {r['heading']} | Relevance: {r['score']}]\n{r['text'][:800]}"
            )
        kb_context = "\n\n---\n\n".join(sections)
    else:
        kb_context = "No relevant knowledge base articles found."

    # Step 2: Classify the ticket
    classify_prompt = triage_classify_prompt(
        subject=subject, body=body, kb_context=kb_context,
        products=PRODUCTS, categories=CATEGORIES,
    )
    raw_classification = _call_gemini(classify_prompt, temperature=0.1)
    try:
        classification = _parse_json_safely(raw_classification)
    except ValueError as e:
        classification = {
            "product": "Unknown", "product_area": "Unknown",
            "category": "Bug", "urgency": "P3",
            "urgency_reasoning": f"Classification failed: {str(e)[:100]}",
            "kb_match": {"matched": False},
            "responder_team": "tier1-general",
            "routing_reasoning": "Default routing due to classification error.",
        }

    # Step 3: Validate enum values
    if classification.get("product") not in PRODUCTS:
        classification["product"] = "DataBridge Pro"
    if classification.get("category") not in CATEGORIES:
        classification["category"] = "Bug"
    if classification.get("urgency") not in URGENCIES:
        classification["urgency"] = "P3"

    # Step 4: Generate draft response
    draft_prompt = triage_draft_prompt(
        subject=subject, body=body,
        classification=classification, kb_context=kb_context,
    )
    draft_response = _call_gemini(draft_prompt, temperature=0.3)

    # Step 5: Build TriageResult
    kb_match_data = classification.get("kb_match", {})
    return TriageResult(
        ticket_id=ticket_id,
        product=classification["product"],
        product_area=classification.get("product_area", "General"),
        category=classification["category"],
        urgency=classification["urgency"],
        urgency_reasoning=classification.get("urgency_reasoning", ""),
        kb_match=KBMatch(
            matched=kb_match_data.get("matched", False),
            source=kb_match_data.get("source"),
            heading=kb_match_data.get("heading"),
            relevance=kb_match_data.get("relevance"),
        ),
        responder_team=classification.get("responder_team", "tier1-general"),
        routing_reasoning=classification.get("routing_reasoning", ""),
        draft_response=draft_response,
        prompt_versions={
            "triage_classify": TRIAGE_CLASSIFY_VERSION,
            "triage_draft": TRIAGE_DRAFT_VERSION,
        },
    )
