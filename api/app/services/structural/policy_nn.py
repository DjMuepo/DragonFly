from __future__ import annotations

import os
import json
import time
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import torch
import torch.nn as nn

ACTIONS = ["add_rib", "add_fillet", "thicken", "change_joint", "no_change"]
JOINTS = ["unknown","snap-fit","press-fit","threaded","bolt-through","adhesive","pin","magnetic","friction"]
LOADS = ["Unknown","Compression","Tension","Shear","Bending","Torsion","Multi-axis"]

def _onehot(val: str, vocab: List[str]) -> np.ndarray:
    arr = np.zeros(len(vocab), dtype=np.float32)
    try:
        i = vocab.index(val)
    except ValueError:
        i = 0
    arr[i] = 1.0
    return arr

def encode_features(params: Dict[str, Any], report: Optional[Dict[str, Any]] = None) -> np.ndarray:
    report = report or {}
    thickness = float(params.get("thickness", 1.0))
    has_rib = 1.0 if bool(params.get("has_rib", False)) else 0.0
    has_fillet = 1.0 if bool(params.get("has_fillet", False)) else 0.0
    hole_count = float(params.get("hole_count", 0))
    cantilever = float(params.get("cantilever", 0.0))
    aspect_ratio = float(params.get("aspect_ratio", 1.0))
    overhang = float(params.get("overhang_risk", 0.0))
    joint = str(params.get("joint_type", "unknown"))
    load_type = str(report.get("load_type", "Unknown"))
    conf = float(report.get("confidence", 0.0))
    stress = float(report.get("stress_risk", 0.0))
    print_risk = float(report.get("printability_risk", 0.0))

    v = np.array([thickness, has_rib, has_fillet, hole_count, cantilever, aspect_ratio, overhang, conf, stress, print_risk], dtype=np.float32)
    vj = _onehot(joint, JOINTS)
    vl = _onehot(load_type, LOADS)
    return np.concatenate([v, vj, vl], axis=0)

class PolicyNet(nn.Module):
    def __init__(self, in_dim: int, hidden: int = 64, out_dim: int = len(ACTIONS)):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, out_dim),
        )

    def forward(self, x):
        return self.net(x)

@dataclass
class PolicyDecision:
    action: str
    probs: Dict[str, float]

def predict_action(model: PolicyNet, feats: np.ndarray) -> PolicyDecision:
    model.eval()
    with torch.no_grad():
        x = torch.from_numpy(feats).unsqueeze(0)
        logits = model(x)
        p = torch.softmax(logits, dim=-1).squeeze(0).cpu().numpy().astype(float)
    probs = {ACTIONS[i]: float(p[i]) for i in range(len(ACTIONS))}
    action = ACTIONS[int(np.argmax(p))]
    return PolicyDecision(action=action, probs=probs)

def apply_action(params: Dict[str, Any], action: str) -> Dict[str, Any]:
    params = dict(params)
    if action == "add_rib":
        params["has_rib"] = True
    elif action == "add_fillet":
        params["has_fillet"] = True
    elif action == "thicken":
        params["thickness"] = float(params.get("thickness", 1.0)) * 1.12
    elif action == "change_joint":
        # naive upgrade path
        jt = str(params.get("joint_type","unknown"))
        if jt in ["unknown","snap-fit","press-fit"]:
            params["joint_type"] = "bolt-through"
        else:
            params["joint_type"] = "threaded"
    elif action == "no_change":
        pass
    return params

def infer_action_from_diff(before: Dict[str, Any], after: Dict[str, Any]) -> str:
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

def load_events_jsonl(path: str) -> List[Dict[str, Any]]:
    events = []
    if not os.path.exists(path):
        return events
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                continue
    return events

def build_training_rows(events: List[Dict[str, Any]]) -> List[Tuple[np.ndarray, int, float]]:
    # session-aware merge usefulness/outcome/review; focus on structural_strengthen examples
    by_session: Dict[str, List[Dict[str, Any]]] = {}
    for e in events:
        sid = e.get("session_id") or "nosession"
        by_session.setdefault(sid, []).append(e)

    rows: List[Tuple[np.ndarray, int, float]] = []
    for sid, evs in by_session.items():
        evs.sort(key=lambda x: x.get("ts") or 0)
        useful = None
        outcome = None
        rating = None
        for e in evs:
            if e.get("event") == "useful_yes":
                useful = True
            elif e.get("event") == "useful_no":
                useful = False
            elif e.get("event") == "print_outcome_success":
                outcome = "success"
            elif e.get("event") == "print_outcome_fail":
                outcome = "fail"
            elif e.get("event") == "review_submit":
                p = e.get("payload") or {}
                rating = p.get("rating")

        # reward shaping: encourage actions that led to success + good ratings
        reward = 1.0
        if useful is False:
            reward *= 0.5
        if outcome == "success":
            reward *= 1.2
        if outcome == "fail":
            reward *= 0.7
        if isinstance(rating, (int, float)):
            reward *= float(rating) / 5.0

        for e in evs:
            if e.get("event") != "structural_strengthen":
                continue
            p = e.get("payload") or {}
            before = p.get("before") or {}
            after = p.get("after") or {}
            rep = p.get("report") or {}
            action = infer_action_from_diff(before, after)
            y = ACTIONS.index(action) if action in ACTIONS else ACTIONS.index("no_change")
            x = encode_features(before, rep)
            rows.append((x, y, reward))
    return rows

def train_policy(
    rows: List[Tuple[np.ndarray, int, float]],
    *,
    epochs: int = 12,
    lr: float = 1e-3,
    hidden: int = 64,
    device: str = "cpu",
) -> PolicyNet:
    if not rows:
        raise ValueError("No training rows")
    X = np.stack([r[0] for r in rows], axis=0)
    y = np.array([r[1] for r in rows], dtype=np.int64)
    w = np.array([r[2] for r in rows], dtype=np.float32)

    in_dim = X.shape[1]
    model = PolicyNet(in_dim=in_dim, hidden=hidden).to(device)

    x_t = torch.from_numpy(X).to(device)
    y_t = torch.from_numpy(y).to(device)
    w_t = torch.from_numpy(w).to(device)

    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.CrossEntropyLoss(reduction="none")

    model.train()
    for _ in range(epochs):
        opt.zero_grad()
        logits = model(x_t)
        losses = loss_fn(logits, y_t)
        loss = (losses * w_t).mean()
        loss.backward()
        opt.step()
    return model

def save_model(model: PolicyNet, path: str, meta: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "meta": meta}, path)

def load_model(path: str, in_dim: int, device: str = "cpu") -> Optional[PolicyNet]:
    if not os.path.exists(path):
        return None
    obj = torch.load(path, map_location=device)
    model = PolicyNet(in_dim=in_dim).to(device)
    model.load_state_dict(obj["state_dict"])
    model.eval()
    return model

def latest_model_path(base_dir: str) -> str:
    return os.path.join(base_dir, "structural_policy.pt")

def versioned_model_path(base_dir: str) -> str:
    ts = time.strftime("%Y%m%d%H%M%S", time.gmtime())
    return os.path.join(base_dir, f"structural_policy_{ts}.pt")
