from __future__ import annotations

import json
import os
import sqlite3
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

try:
    import faiss  # type: ignore
except Exception:
    faiss = None

DEFAULT_DB_PATH = os.getenv("EYE_LIBRARY_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "library.db"))
INDEX_DIR = os.getenv("EYE_FAISS_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "faiss"))
INDEX_PATH = os.path.join(INDEX_DIR, "models.index")
META_PATH = os.path.join(INDEX_DIR, "models_meta.json")

def connect() -> sqlite3.Connection:
    con = sqlite3.connect(os.path.abspath(DEFAULT_DB_PATH))
    con.row_factory = sqlite3.Row
    return con

def _unpack(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)

def build_faiss_index() -> Dict[str, Any]:
    if faiss is None:
        raise RuntimeError("faiss-cpu not installed")
    os.makedirs(INDEX_DIR, exist_ok=True)

    rows = []
    with connect() as con:
        cur = con.execute("SELECT id, source, title, tags, license_json, preview_url, file_url, embedding FROM models")
        rows.extend([dict(r) for r in cur.fetchall()])
        # remote models are metadata-only but still searchable
        try:
            cur2 = con.execute("SELECT key as id, source, title, tags, license_json, preview_url, NULL as file_url, embedding FROM remote_models")
            rows.extend([dict(r) for r in cur2.fetchall()])
        except Exception:
            pass

    if not rows:
        raise RuntimeError("No model rows found to index")

    vecs: List[np.ndarray] = []
    meta: List[Dict[str, Any]] = []
    for r in rows:
        emb = _unpack(r["embedding"]).astype(np.float32)
        # normalize
        n = float(np.linalg.norm(emb))
        if n > 0:
            emb = emb / n
        vecs.append(emb)
        meta.append({
            "id": r["id"],
            "source": r["source"],
            "title": r["title"],
            "tags": r.get("tags") or "",
            "license_json": r.get("license_json"),
            "preview_url": r.get("preview_url"),
            "file_url": r.get("file_url"),
        })

    mat = np.stack(vecs, axis=0).astype(np.float32)
    dim = mat.shape[1]
    index = faiss.IndexFlatIP(dim)  # cosine w/ normalized vectors
    index.add(mat)
    faiss.write_index(index, INDEX_PATH)
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    return {"ok": True, "count": len(meta), "dim": dim, "index_path": INDEX_PATH}

def load_faiss() -> Tuple[Any, List[Dict[str, Any]]]:
    if faiss is None:
        raise RuntimeError("faiss-cpu not installed")
    if not os.path.exists(INDEX_PATH) or not os.path.exists(META_PATH):
        raise RuntimeError("FAISS index not built yet")
    index = faiss.read_index(INDEX_PATH)
    with open(META_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)
    return index, meta

def search_faiss(query_vec: np.ndarray, k: int = 10) -> List[Dict[str, Any]]:
    index, meta = load_faiss()
    q = query_vec.astype(np.float32)
    n = float(np.linalg.norm(q))
    if n > 0:
        q = q / n
    q = np.expand_dims(q, axis=0)
    scores, ids = index.search(q, k)
    out: List[Dict[str, Any]] = []
    for score, idx in zip(scores[0].tolist(), ids[0].tolist()):
        if idx < 0 or idx >= len(meta):
            continue
        item = dict(meta[idx])
        item["similarity"] = float(max(0.0, min(1.0, score)))
        out.append(item)
    return out
