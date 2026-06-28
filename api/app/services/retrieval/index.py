from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

import numpy as np

from ...core.schemas import LicenseInfo, MatchCandidate, RetrievalResponse

DEFAULT_DB_PATH = os.getenv("EYE_LIBRARY_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "library.db"))


# --- Embedding provider ---
# Default provider is deterministic hash embeddings so the system runs without ML deps.
# Swap later with CLIP/VL embeddings by implementing a provider and setting EYE_EMBED_PROVIDER.
from ..embeddings.providers import get_provider, EMBED_DIM  # noqa: E402
from ..vector.faiss_index import search_faiss  # noqa: E402


_provider = get_provider()

# --- model embedding composition weights (text + preview image) ---
W_TEXT = float(os.getenv("EYE_MODEL_EMB_W_TEXT", "0.4"))
W_IMAGE = float(os.getenv("EYE_MODEL_EMB_W_IMAGE", "0.6"))

def _normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    if n > 0:
        return (v / n).astype(np.float32)
    return v.astype(np.float32)

def _static_path_from_url(url: str) -> Optional[str]:
    """Resolve a FastAPI static URL (e.g. /models/<id>/<file>) to a local filesystem path."""
    if not url:
        return None
    if not url.startswith("/models/"):
        return None
    rel = url[len("/models/"):]
    static_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "static", "models"))
    return os.path.join(static_root, rel)

def compute_model_embedding(title: str, tags: str, preview_url: Optional[str]) -> np.ndarray:
    """Compose a stable model embedding using text + preview image (if available)."""
    vt = embed_text(f"{title} {tags}".strip())
    vi = None
    if preview_url:
        p = _static_path_from_url(preview_url)
        if p and os.path.exists(p):
            try:
                vi = embed_image_bytes(open(p, "rb").read())
            except Exception:
                vi = None
    if vi is None or np.allclose(vi, 0):
        return _normalize(vt)
    # Weighted blend
    v = (W_TEXT * vt) + (W_IMAGE * vi)
    return _normalize(v)

def embed_text(text: str) -> np.ndarray:
    return _provider.embed_text(text)

def embed_image_bytes(data: bytes) -> np.ndarray:
    return _provider.embed_image_bytes(data)

def cosine(a: np.ndarray, b: np.ndarray) -> float:

    if a.size == 0 or b.size == 0:
        return 0.0
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)

def db_path() -> str:
    return os.path.abspath(DEFAULT_DB_PATH)

def connect() -> sqlite3.Connection:
    con = sqlite3.connect(db_path())
    con.row_factory = sqlite3.Row
    return con

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS models (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    tags TEXT,
    license_json TEXT,
    preview_url TEXT,
    file_url TEXT,
    embedding BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_models_source ON models(source);

CREATE TABLE IF NOT EXISTS remote_models (
    key TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    remote_id TEXT NOT NULL,
    title TEXT NOT NULL,
    tags TEXT,
    license_json TEXT,
    preview_url TEXT,
    external_url TEXT,
    embedding BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_remote_source ON remote_models(source);

"""

def ensure_schema() -> None:
    with connect() as con:
        con.executescript(SCHEMA_SQL)
        con.commit()

def _pack(vec: np.ndarray) -> bytes:
    return vec.astype(np.float32).tobytes()

def _unpack(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)

@dataclass
class ModelRow:
    id: str
    source: str
    title: str
    tags: str
    license: LicenseInfo
    preview_url: Optional[str]
    file_url: Optional[str]
    embedding: np.ndarray


def upsert_remote_model(
    *,
    source: str,
    remote_id: str,
    title: str,
    tags: str = "",
    license_info: Optional[LicenseInfo] = None,
    preview_url: Optional[str] = None,
    external_url: Optional[str] = None,
    embedding: Optional[np.ndarray] = None,
) -> None:
    ensure_schema()
    lic = license_info or LicenseInfo(status="UNKNOWN")
    emb = embedding if embedding is not None else compute_model_embedding(title, tags, preview_url)
    key = f"{source}:{remote_id}"
    with connect() as con:
        con.execute(
            """INSERT INTO remote_models(key, source, remote_id, title, tags, license_json, preview_url, external_url, embedding)
            VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(key) DO UPDATE SET
              title=excluded.title,
              tags=excluded.tags,
              license_json=excluded.license_json,
              preview_url=excluded.preview_url,
              external_url=excluded.external_url,
              embedding=excluded.embedding
            """,
            (key, source, remote_id, title, tags, lic.model_dump_json(), preview_url, external_url, _pack(emb)),
        )
        con.commit()

def upsert_model(
    *,
    id: str,
    source: str,
    title: str,
    tags: str = "",
    license_info: Optional[LicenseInfo] = None,
    preview_url: Optional[str] = None,
    file_url: Optional[str] = None,
    embedding: Optional[np.ndarray] = None,
) -> None:
    ensure_schema()
    lic = license_info or LicenseInfo(status="UNKNOWN")
    emb = embedding if embedding is not None else compute_model_embedding(title, tags, preview_url)
    with connect() as con:
        con.execute(
            """INSERT INTO models(id, source, title, tags, license_json, preview_url, file_url, embedding)
            VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
              source=excluded.source,
              title=excluded.title,
              tags=excluded.tags,
              license_json=excluded.license_json,
              preview_url=excluded.preview_url,
              file_url=excluded.file_url,
              embedding=excluded.embedding
            """,
            (id, source, title, tags, lic.model_dump_json(), preview_url, file_url, _pack(emb)),
        )
        con.commit()

def search(
    *,
    query_hint: Optional[str],
    allow_restricted: bool,
    limit: int,
    image_bytes: Optional[bytes] = None,
    query_vector: Optional[np.ndarray] = None,
) -> RetrievalResponse:
    ensure_schema()
    q = (query_vector if query_vector is not None else (embed_image_bytes(image_bytes) if image_bytes else embed_text(query_hint or "")))
    rows: List[ModelRow] = []
    with connect() as con:
        cur = con.execute("SELECT * FROM models")
        remote_cur = con.execute("SELECT * FROM remote_models")
        for r in cur.fetchall():
            lic = LicenseInfo.model_validate_json(r["license_json"]) if r["license_json"] else LicenseInfo(status="UNKNOWN")
            if (lic.status == "RESTRICTED") and (not allow_restricted):
                continue
            rows.append(
                ModelRow(
                    id=r["id"],
                    source=r["source"],
                    title=r["title"],
                    tags=r["tags"] or "",
                    license=lic,
                    preview_url=r["preview_url"],
                    file_url=r["file_url"],
                    external_url=None,
                    embedding=_unpack(r["embedding"]),
                )
            )

    # Remote (metadata-only) rows
    with connect() as con:
        remote_cur = con.execute("SELECT * FROM remote_models")
        for r in remote_cur.fetchall():
            lic = LicenseInfo.model_validate_json(r["license_json"]) if r["license_json"] else LicenseInfo(status="UNKNOWN")
            if (lic.status == "RESTRICTED") and (not allow_restricted):
                continue
            rows.append(
                ModelRow(
                    id=f'{r["source"]}:{r["remote_id"]}',
                    source=r["source"],
                    title=r["title"],
                    tags=r["tags"] or "",
                    license=lic,
                    preview_url=r["preview_url"],
                    file_url=None,
                    external_url=r["external_url"],
                    embedding=_unpack(r["embedding"]),
                )
            )


    # Score
    # FAISS path (preferred when available)
    try:
        faiss_hits = search_faiss(q, k=max(1, limit * 3))
        matches: List[MatchCandidate] = []
        for hit in faiss_hits:
            lic = LicenseInfo.model_validate_json(hit["license_json"]) if hit.get("license_json") else LicenseInfo(status="UNKNOWN")
            if (lic.status == "RESTRICTED") and (not allow_restricted):
                continue
            matches.append(
                MatchCandidate(
                    id=hit["id"],
                    source=hit["source"],
                    title=hit["title"],
                    similarity=float(hit["similarity"]),
                    license=lic,
                    preview_url=hit.get("preview_url"),
                    external_url=None,
                    hosted=bool(hit.get("file_url")),
                )
            )
            if len(matches) >= limit:
                break
        max_sim = float(matches[0].similarity) if matches else 0.0
        novelty = "COMMON" if max_sim >= 0.85 else ("SOMEWHAT_UNIQUE" if max_sim >= 0.65 else "UNIQUE")
        best = matches[0] if matches else None
        return RetrievalResponse(matches=matches[:limit], novelty=novelty, best_match=best, max_similarity=max_sim)
    except Exception:
        pass

    # Score
    scored: List[Tuple[float, ModelRow]] = []
    for row in rows:
        sim = cosine(q, row.embedding)
        # clamp into 0..1 for UI (cosine with these embeddings already 0..1)
        sim = max(0.0, min(1.0, sim))
        scored.append((sim, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[: max(1, limit)]
    matches: List[MatchCandidate] = [
        MatchCandidate(
            id=row.id,
            external_url=(row.external_url if not row.file_url else None),
            hosted=bool(row.file_url),
            source=row.source,
            title=row.title,
            similarity=float(sim),
            license=row.license,
            preview_url=row.preview_url,
        )
        for sim, row in top
    ]
    max_sim = float(top[0][0]) if top else 0.0
    novelty = "COMMON" if max_sim >= 0.85 else ("SOMEWHAT_UNIQUE" if max_sim >= 0.65 else "UNIQUE")
    best = matches[0] if matches else None
    return RetrievalResponse(matches=matches[:limit], novelty=novelty, best_match=best, max_similarity=max_sim)
