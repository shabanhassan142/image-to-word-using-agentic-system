"""
Agent Audit Logger
Logs every agent decision for transparency and explainability.
"""

import json
import os
from datetime import datetime

LOG_FILE = "agent_audit_log.json"


def log_event(event_type: str, details: dict):
    """Append a structured log entry."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        **details
    }
    logs = _load()
    logs.append(entry)
    logs = logs[-200:]  # keep last 200 entries
    try:
        with open(LOG_FILE, "w") as f:
            json.dump(logs, f, indent=2)
    except Exception:
        pass


def get_session_log(session_id: str) -> list:
    logs = _load()
    return [e for e in logs if e.get("session_id") == session_id]


def _load() -> list:
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []
