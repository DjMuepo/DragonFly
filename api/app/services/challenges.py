from __future__ import annotations
import os, json, time, uuid
from typing import Dict, Any, List

CHALLENGES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "design_challenges.json"))

def _load() -> Dict[str, list]:
    if not os.path.exists(CHALLENGES_PATH):
        seed = {"challenges": [], "submissions": []}
        with open(CHALLENGES_PATH, "w", encoding="utf-8") as f:
            json.dump(seed, f, ensure_ascii=False, indent=2)
        return seed
    with open(CHALLENGES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(data: Dict[str, list]) -> None:
    with open(CHALLENGES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"

def seed_if_empty() -> None:
    data = _load()
    if data["challenges"]:
        return
    data["challenges"] = [
        {"id": _id("chal"), "title": "Strengthen This Hook", "description": "Improve a weak hook so it can hold more load without failing.", "type": "structural", "difficulty": "easy", "prize": "100 XP", "deadline": None, "seed_family": "hook", "seed_object_dna": {"geometry": {"family": "hook"}}, "created_at": int(time.time()), "status": "open"},
        {"id": _id("chal"), "title": "Fix This Broken Hinge", "description": "Create a printable replacement for a broken hinge-like part.", "type": "repair", "difficulty": "medium", "prize": "250 XP", "deadline": None, "seed_family": "bracket", "seed_object_dna": {"geometry": {"family": "bracket"}}, "created_at": int(time.time()), "status": "open"},
        {"id": _id("chal"), "title": "Lighter Phone Stand", "description": "Reduce material usage while keeping the stand stable.", "type": "efficiency", "difficulty": "medium", "prize": "150 XP", "deadline": None, "seed_family": "support", "seed_object_dna": {"geometry": {"family": "support"}}, "created_at": int(time.time()), "status": "open"},
    ]
    _save(data)

def list_challenges() -> List[Dict[str, Any]]:
    seed_if_empty()
    return _load()["challenges"]

def get_challenge(challenge_id: str) -> Dict[str, Any] | None:
    seed_if_empty()
    return next((c for c in _load()["challenges"] if c["id"] == challenge_id), None)

def list_submissions(challenge_id: str) -> List[Dict[str, Any]]:
    return [s for s in _load()["submissions"] if s["challenge_id"] == challenge_id]

def submit_challenge_entry(challenge_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = _load()
    submission = {"id": _id("sub"), "challenge_id": challenge_id, "creator": payload.get("creator") or "Anonymous", "design_title": payload.get("design_title") or "Untitled Submission", "object_dna": payload.get("object_dna") or {}, "score": float(payload.get("score", 0) or 0), "likes": int(payload.get("likes", 0) or 0), "created_at": int(time.time())}
    data["submissions"].append(submission)
    _save(data)
    return submission

def get_leaderboard(challenge_id: str) -> List[Dict[str, Any]]:
    items = list_submissions(challenge_id)
    items.sort(key=lambda x: (x.get("score", 0), x.get("likes", 0)), reverse=True)
    return items[:20]
