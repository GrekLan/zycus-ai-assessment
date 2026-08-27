# src/data_loader.py
"""Loads tickets.json and accounts.json once at startup.
All lookups are O(1) from dicts — no repeated file I/O."""

import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data"
TICKETS_PATH = DATA_DIR / "tickets.json"
ACCOUNTS_PATH = DATA_DIR / "accounts.json"

with open(TICKETS_PATH, encoding="utf-8") as f:
    ALL_TICKETS: list[dict] = json.load(f)

with open(ACCOUNTS_PATH, encoding="utf-8") as f:
    ALL_ACCOUNTS: list[dict] = json.load(f)

ACCOUNT_MAP: dict[str, dict] = {a["account_id"]: a for a in ALL_ACCOUNTS}
TICKETS_BY_ACCOUNT: dict[str, list[dict]] = {}

for t in ALL_TICKETS:
    aid = t["account_id"]
    TICKETS_BY_ACCOUNT.setdefault(aid, []).append(t)


def get_account(account_id: str) -> Optional[dict]:
    return ACCOUNT_MAP.get(account_id)


def get_account_tickets(account_id: str, days: int = 90) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    tickets = TICKETS_BY_ACCOUNT.get(account_id, [])
    result = []
    for t in tickets:
        try:
            created = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
            if created > cutoff:
                result.append(t)
        except (KeyError, ValueError):
            continue
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return result


def get_all_tickets() -> list[dict]:
    return ALL_TICKETS


def get_all_accounts() -> list[dict]:
    return ALL_ACCOUNTS
