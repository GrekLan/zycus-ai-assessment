# Zycus AI Assessment — Support Intelligence Platform

An AI-powered support intelligence system featuring **intelligent ticket triage** (RAG + LLM) and **TAM account health summarisation**. Built with FastAPI, Google Gemini 1.5 Flash, ChromaDB, and Streamlit.

---

## Quick Start

```bash
# 1. Clone and setup
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure API key
copy .env.example .env
# Edit .env with your Gemini API key

# 4. Run the API server
uvicorn main:app --reload

# 5. Run Streamlit UI (bonus, separate terminal)
streamlit run app.py

# 6. Run evaluation harness
python run_eval.py --output eval_report.md
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Streamlit UI (app.py)                  │
│  Ticket Triage │ Account Health │ KB Explorer │ Eval      │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTP
┌────────────────────────▼─────────────────────────────────┐
│                 FastAPI Server (main.py)                   │
│  POST /triage  │  POST /summarise/{id}  │  GET /accounts  │
└──┬──────────────────┬─────────────────────┬──────────────┘
   │                  │                     │
   ▼                  ▼                     ▼
┌──────────┐  ┌───────────────┐   ┌────────────────┐
│ Triage   │  │ Account       │   │ Data Loader    │
│ Agent    │  │ Summariser    │   │ (in-memory)    │
│ (Task 1) │  │ (Task 2)      │   │ tickets.json   │
└──┬───┬───┘  └──┬────────────┘   │ accounts.json  │
   │   │         │                 └────────────────┘
   │   ▼         ▼
   │ ┌───────────────────┐
   │ │  Gemini 3.5 Flash │
   │ │  (temperature=0   │
   │ │   for Task 2)     │
   │ └───────────────────┘
   ▼
┌──────────────────────┐
│ ChromaDB (in-memory) │
│ KB embeddings via    │
│ embedding-001        │
└──────────────────────┘
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | System health check (Gemini + ChromaDB status) |
| `GET` | `/accounts` | List all 50 customer accounts |
| `POST` | `/triage` | Classify ticket, match KB, generate draft response |
| `POST` | `/summarise/{account_id}` | Generate account health brief with churn risk |

---

## Task 4 — Design Note

### 1. Failure Modes and Mitigation

**LLM Response Parsing Failures.** The most common failure mode is the LLM returning malformed JSON despite explicit schema instructions. Mitigation: `_parse_json_safely()` handles markdown fences, preamble text, and truncated output by searching for the first `{` to last `}` boundary. If parsing fails entirely, we fall back to safe defaults (P3 urgency, tier1-general routing) rather than crashing — the system degrades gracefully.

**Embedding Service Unavailability.** If Gemini's embedding API is down, ChromaDB queries fail. Mitigation: the KB index is built at startup, so a transient outage during indexing triggers a clear `RuntimeError`. For query-time failures, we catch exceptions and return results without KB context rather than failing the entire triage.

**Hallucinated Classifications.** The LLM may return product names or categories not in the allowed enum set. Mitigation: post-classification enum validation replaces invalid values with safe defaults (e.g., `"DataBridge Pro"` for unknown products), ensuring downstream systems always receive valid data.

**Rate Limiting.** Gemini free tier has RPM limits. The account summariser makes 3 sequential LLM calls per request, so high concurrency exhausts quotas quickly. Mitigation: sequential (not parallel) LLM calls per request, and Task 2 caps ticket context at 20 tickets to control token usage.

### 2. Latency vs. Quality Tradeoffs

| Decision | Latency Impact | Quality Impact |
|----------|---------------|----------------|
| `temperature=0.1` for classification | Minimal | Higher consistency, less creative |
| `temperature=0` for summarisation | Minimal | Deterministic output, reproducible |
| Top-3 KB retrieval (not top-5) | ~40% fewer embedding comparisons | Sufficient for most tickets |
| Ticket body truncated to 500 chars for embedding | Faster embedding | May miss details in long tickets |
| Cap 20 tickets per account summary | Reduces prompt size by ~60% | May miss older patterns |

The system prioritises **consistency over creativity** — for production support, reproducible results are more valuable than varied phrasing.

### 3. PII Handling

The current implementation does **not** strip PII before sending to Gemini. In a production deployment:

- **Pre-processing:** Regex-based detection of emails, phone numbers, IPs, and account numbers. Replace with `[REDACTED_EMAIL]` tokens before LLM calls. Use libraries like `presidio` for entity recognition.
- **Prompt-level:** System prompts instruct the LLM to never echo back PII in responses.
- **Post-processing:** Scan LLM outputs for leaked PII patterns before returning to the client.
- **Audit trail:** Log which fields were redacted and the original hash (not value) for traceability.
- **Data residency:** Gemini API requests leave the user's region. For EU customers, evaluate Vertex AI with region-locked endpoints.

### 4. Scaling to 50K Tickets / 5K Accounts

**Data Layer:** Replace in-memory dicts with PostgreSQL + Redis cache. Index `account_id` and `created_at` for the 90-day ticket filter. Expected query time: <5ms vs current <1ms (still acceptable).

**Vector Store:** Migrate ChromaDB to a managed solution (Pinecone, Weaviate, or Vertex AI Vector Search). Shard by product for parallel retrieval. Add metadata filtering (product, category) to reduce search space.

**LLM Layer:** Move from free-tier Gemini to Vertex AI with provisioned throughput. Implement request queuing with exponential backoff. Cache frequent ticket patterns (e.g., "SSO SAML expired" appears in ~5% of tickets) to skip LLM calls entirely.

**API Layer:** Add rate limiting per API key, request queuing, and async processing. Long-running summarisations should return a job ID with polling endpoint rather than blocking.

**Evaluation:** The harness scales linearly. At 50K tickets, sample-based evaluation (stratified by product + urgency) replaces exhaustive testing.

### 5. Prompt Versioning Strategy

All prompts live in `src/prompts.py` with explicit version strings and changelogs. Every API response includes `prompt_versions` metadata, enabling:
- A/B testing between prompt versions
- Regression detection when prompts change
- Audit trail for compliance reviews

---

## Project Structure

```
├── data/
│   ├── tickets.json          # 500 synthetic support tickets
│   └── accounts.json         # 50 synthetic customer accounts
├── knowledge-base/
│   ├── products/             # 5 product docs
│   ├── troubleshooting/      # 2 troubleshooting guides
│   ├── billing/              # 1 billing doc
│   └── onboarding/           # 1 onboarding guide
├── src/
│   ├── __init__.py
│   ├── data_loader.py        # In-memory data loading + lookups
│   ├── kb_index.py           # ChromaDB RAG index
│   ├── prompts.py            # Versioned prompt library
│   ├── triage_agent.py       # Task 1 — Ticket triage pipeline
│   ├── account_summariser.py # Task 2 — Account health summariser
│   └── evaluation.py         # Task 3 — Evaluation harness
├── main.py                   # FastAPI application
├── app.py                    # Streamlit UI (bonus)
├── run_eval.py               # Evaluation runner CLI
├── requirements.txt
├── .env.example
├── DATA_SCHEMA.md
├── .github/workflows/eval.yml  # CI pipeline (bonus)
└── README.md                 # This file (Task 4)
```

---

## Evaluation

Run the evaluation harness:

```bash
python run_eval.py --output eval_report.md --threshold 0.75 --verbose
```

The harness includes:
- **7 Task 1 tests** (5 standard + 2 adversarial)
- **5 Task 2 tests** (4 standard + 1 adversarial)
- **Rule-based checks** (field presence, enum validation, score thresholds)
- **LLM-as-judge** scoring for quality assessment
- Pass/fail determination with configurable threshold

---

## Tech Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| API | FastAPI | Async, auto-docs, Pydantic integration |
| LLM | Gemini 1.5 Flash | Free tier, fast, structured output support |
| Embeddings | Gemini embedding-001 | Native integration with ChromaDB |
| Vector DB | ChromaDB (in-memory) | Zero-config, sufficient for 8 KB docs |
| UI | Streamlit | Rapid prototyping, built-in components |
| Validation | Pydantic v2 | Type-safe request/response models |
