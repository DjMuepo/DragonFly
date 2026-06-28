from __future__ import annotations

import os
import sqlite3
import time
import json
from typing import Any, Dict, Optional

DB_PATH = os.getenv("EYE_EVENTS_DB", os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "events.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  session_id TEXT,
  user_id TEXT,
  event TEXT NOT NULL,
  job_id TEXT,
  model_id TEXT,
  payload_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_event ON events(event);
CREATE INDEX IF NOT EXISTS idx_events_job ON events(job_id);
"""

def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    return con

def ensure_schema() -> None:
    with _connect() as con:
        con.executescript(SCHEMA)
        con.commit()

def log_event(
    *,
    event: str,
    payload: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    job_id: Optional[str] = None,
    model_id: Optional[str] = None,
) -> None:
    ensure_schema()
    ts = int(time.time())
    pj = json.dumps(payload or {}, separators=(",", ":"), ensure_ascii=False)
    with _connect() as con:
        con.execute(
            "INSERT INTO events(ts, session_id, user_id, event, job_id, model_id, payload_json) VALUES(?,?,?,?,?,?,?)",
            (ts, session_id, user_id, event, job_id, model_id, pj),
        )
        con.commit()
