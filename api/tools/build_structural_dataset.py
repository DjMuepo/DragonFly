from __future__ import annotations
import argparse, json
from typing import Dict, Any, List

def infer_action(before: Dict[str, Any], after: Dict[str, Any]) -> str:
    if bool(after.get("has_rib")) and not bool(before.get("has_rib")):
        return "add_rib"
    if bool(after.get("has_fillet")) and not bool(before.get("has_fillet")):
        return "add_fillet"
    bt = float(before.get("thickness", 1.0) or 1.0)
    at = float(after.get("thickness", bt) or bt)
    if at > bt * 1.001:
        return "thicken"
    if str(after.get("joint_type","unknown")) != str(before.get("joint_type","unknown")):
        return "change_joint"
    return "no_change"

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="events.jsonl")
    ap.add_argument("--out", default="structural_dataset.jsonl")
    args = ap.parse_args()

    sessions: Dict[str, List[Dict[str, Any]]] = {}
    with open(args.inp, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            sid = e.get("session_id") or "nosession"
            sessions.setdefault(sid, []).append(e)

    n = 0
    with open(args.out, "w", encoding="utf-8") as o:
        for sid, evs in sessions.items():
            evs.sort(key=lambda x: x.get("ts") or 0)
            useful = None
            outcome = None
            failure = None
            review = None
            family_correction = None
            draft_rejected = False
            draft_accepted = False

            for e in evs:
                evt = e.get("event")
                if evt == "useful_yes":
                    useful = True
                elif evt == "useful_no":
                    useful = False
                elif evt == "print_outcome_success":
                    outcome = "success"
                elif evt == "print_outcome_fail":
                    outcome = "fail"
                elif evt == "review_submit":
                    review = (e.get("payload") or {})
                elif evt == "print_feedback":
                    p = e.get("payload") or {}
                    failure = p.get("failure")
                    if failure and failure != "none":
                        outcome = outcome or "fail"
                elif evt == "family_correction":
                    family_correction = e.get("payload") or {}
                elif evt == "draft_reject":
                    draft_rejected = True
                elif evt == "draft_accept":
                    draft_accepted = True

            for e in evs:
                if e.get("event") != "structural_strengthen":
                    continue
                p = e.get("payload") or {}
                before = p.get("before") or {}
                after = p.get("after") or {}
                rep = p.get("report") or {}
                delta = p.get("delta")
                action = infer_action(before, after)
                example = {
                    "ts": e.get("ts"),
                    "session_id": sid,
                    "x": {"params": before},
                    "y": {
                        "action": action,
                        "delta": delta,
                        "after_confidence": rep.get("confidence"),
                        "band": rep.get("band"),
                        "primary_risk": rep.get("primary_risk"),
                        "useful": useful,
                        "print_outcome": outcome,
                        "failure": failure,
                        "review": review,
                        "family_correction": family_correction,
                        "draft_rejected": draft_rejected,
                        "draft_accepted": draft_accepted
                    }
                }
                o.write(json.dumps(example, ensure_ascii=False) + "\n")
                n += 1
    print(f"Wrote {n} examples to {args.out}")

if __name__ == "__main__":
    main()
