from __future__ import annotations
import argparse, json, os, sqlite3
from app.services.telemetry.logger import DB_PATH, ensure_schema

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="events.jsonl")
    ap.add_argument("--limit", type=int, default=100000)
    args = ap.parse_args()

    ensure_schema()
    if not os.path.exists(DB_PATH):
        print("No events db found.")
        return
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM events ORDER BY ts ASC LIMIT ?", (args.limit,)).fetchall()
    with open(args.out, "w", encoding="utf-8") as f:
        for r in rows:
            obj = {
                "ts": r["ts"],
                "session_id": r["session_id"],
                "user_id": r["user_id"],
                "event": r["event"],
                "job_id": r["job_id"],
                "model_id": r["model_id"],
                "payload": json.loads(r["payload_json"] or "{}"),
            }
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} events to {args.out}")

if __name__ == "__main__":
    main()
