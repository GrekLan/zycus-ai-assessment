# main.py
"""FastAPI application — Zycus AI Assessment.
Exposes endpoints for ticket triage and account health summarisation."""

import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import google.generativeai as genai

load_dotenv()

# ── Request/Response Models ──
class TriageRequest(BaseModel):
    subject: str = Field(..., description="Ticket subject line")
    body: str = Field(..., description="Full ticket body text")
    ticket_id: Optional[str] = Field(None, description="Optional ticket ID")

class AccountSummaryRequest(BaseModel):
    days: int = Field(90, description="Number of days to look back for tickets")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: configure Gemini API key and build KB index."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment. Copy .env.example to .env and add your key.")
    genai.configure(api_key=api_key)
    from src.kb_index import build_index
    build_index(api_key)
    print("[Startup] KB index built. API ready.")
    yield


app = FastAPI(
    title="Zycus AI Assessment — Support Intelligence API",
    description="AI-powered ticket triage and account health summarisation.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """System health check."""
    from src.kb_index import _collection
    return {
        "status": "healthy",
        "kb_chunks": _collection.count() if _collection else 0,
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
    }


@app.get("/accounts")
async def list_accounts():
    """List all customer accounts."""
    from src.data_loader import get_all_accounts
    accounts = get_all_accounts()
    return {
        "total": len(accounts),
        "accounts": [
            {
                "account_id": a["account_id"],
                "company": a["company"],
                "tam": a.get("tam"),
                "health_status": a["health_status"],
                "plan_tier": a["plan_tier"],
                "arr_usd": a.get("arr_usd"),
                "open_tickets": a.get("open_tickets"),
                "renewal_date": a.get("renewal_date"),
            }
            for a in accounts
        ],
    }


@app.post("/triage")
async def triage_ticket(request: TriageRequest):
    """Triage a support ticket using RAG + LLM."""
    try:
        from src.triage_agent import run_triage
        result = run_triage(
            subject=request.subject,
            body=request.body,
            ticket_id=request.ticket_id,
        )
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Triage failed: {str(e)[:200]}")


@app.post("/summarise/{account_id}")
async def summarise_account(account_id: str):
    """Generate account health summary."""
    try:
        from src.account_summariser import generate_account_brief
        brief = generate_account_brief(account_id)
        return brief.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarisation failed: {str(e)[:200]}")
