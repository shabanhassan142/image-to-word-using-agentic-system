"""
Agent Memory Module
Short-term: current session context
Long-term: persisted preferences per document type (metadata only, never text content)
"""

import json
import os
from datetime import datetime

MEMORY_FILE = "agent_memory.json"


def load_long_term_memory() -> dict:
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"preferences": {}, "history": []}


def save_long_term_memory(memory: dict):
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(memory, f, indent=2)
    except Exception:
        pass


def get_preference(doc_type: str) -> dict:
    """Retrieve learned preprocessing preference for a document type."""
    mem = load_long_term_memory()
    return mem["preferences"].get(doc_type, {})


def update_preference(doc_type: str, strategy: str, success: bool):
    """Update long-term preference based on user feedback. Stores metadata only."""
    mem = load_long_term_memory()
    if doc_type not in mem["preferences"]:
        mem["preferences"][doc_type] = {"strategy": strategy, "success_count": 0, "fail_count": 0}
    if success:
        mem["preferences"][doc_type]["success_count"] += 1
        mem["preferences"][doc_type]["strategy"] = strategy  # reinforce
    else:
        mem["preferences"][doc_type]["fail_count"] += 1
    mem["history"].append({
        "timestamp": datetime.now().isoformat(),
        "doc_type": doc_type,
        "strategy": strategy,
        "success": success
    })
    # Keep history to last 50 entries
    mem["history"] = mem["history"][-50:]
    save_long_term_memory(mem)


def get_history_summary() -> list:
    mem = load_long_term_memory()
    return mem["history"][-10:]
