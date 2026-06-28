from __future__ import annotations
from typing import List, Dict, Any
import math, time, json, os

NODES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "printer_nodes.json"))

SEED_NODES: List[Dict[str, Any]] = [
    {"id": "prt_losangeles_1", "name": "LA Maker Print Hub", "lat": 34.0522, "lon": -118.2437, "materials": ["PLA", "PETG", "ABS"], "max_x": 300, "max_y": 300, "max_z": 300, "same_day": True, "is_online": True, "queue_depth": 2, "last_seen": int(time.time())},
    {"id": "prt_pasadena_1", "name": "Pasadena Prototype Lab", "lat": 34.1478, "lon": -118.1445, "materials": ["PLA", "PETG", "Resin"], "max_x": 220, "max_y": 220, "max_z": 250, "same_day": False, "is_online": True, "queue_depth": 4, "last_seen": int(time.time())},
    {"id": "prt_riverside_1", "name": "IE Rapid Prints", "lat": 33.9806, "lon": -117.3755, "materials": ["PLA", "PETG", "Nylon"], "max_x": 350, "max_y": 350, "max_z": 400, "same_day": True, "is_online": True, "queue_depth": 1, "last_seen": int(time.time())},
    {"id": "prt_orange_1", "name": "OC Fabrication Partner", "lat": 33.7175, "lon": -117.8311, "materials": ["PLA", "PETG", "ABS", "Nylon"], "max_x": 250, "max_y": 250, "max_z": 300, "same_day": False, "is_online": False, "queue_depth": 7, "last_seen": int(time.time())},
]

def ensure_seeded() -> None:
    if not os.path.exists(NODES_PATH):
        with open(NODES_PATH, "w", encoding="utf-8") as f:
            json.dump(SEED_NODES, f, ensure_ascii=False, indent=2)

def _load_nodes() -> List[Dict[str, Any]]:
    ensure_seeded()
    with open(NODES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_nodes(nodes: List[Dict[str, Any]]) -> None:
    with open(NODES_PATH, "w", encoding="utf-8") as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)

def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def find_nearby_printers(lat: float, lon: float, material: str | None = None) -> List[Dict[str, Any]]:
    out = []
    for p in _load_nodes():
        if material and material not in p["materials"]:
            continue
        card = dict(p)
        card["distance_miles"] = round(_haversine_miles(lat, lon, p["lat"], p["lon"]), 1)
        out.append(card)
    out.sort(key=lambda x: (not x.get("is_online", False), x.get("queue_depth", 999), x["distance_miles"]))
    return out[:8]

def submit_print_job(printer_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    printer = next((p for p in _load_nodes() if p["id"] == printer_id), None)
    if not printer:
        raise ValueError("printer not found")
    request_id = f"job_{printer_id}_{int(time.time())}"
    return {"ok": True, "request_id": request_id, "printer_id": printer_id, "printer_name": printer["name"], "status": "submitted", "eta": "same day" if printer.get("same_day") and printer.get("queue_depth", 9) <= 3 else "1-3 days", "note": "Foundation flow only. Real printer network integration comes later.", "payload_summary": {"material": payload.get("material") or "PLA", "family": payload.get("family") or "object"}}

def list_nodes() -> List[Dict[str, Any]]:
    return _load_nodes()

def set_node_status(node_id: str, is_online: bool | None = None, queue_depth: int | None = None, materials: list[str] | None = None) -> Dict[str, Any] | None:
    nodes = _load_nodes()
    for n in nodes:
        if n.get("id") == node_id:
            if is_online is not None: n["is_online"] = bool(is_online)
            if queue_depth is not None: n["queue_depth"] = int(queue_depth)
            if materials is not None: n["materials"] = materials
            n["last_seen"] = int(time.time())
            _save_nodes(nodes)
            return n
    return None
