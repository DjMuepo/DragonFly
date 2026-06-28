"""Reindex all model embeddings in the local SQLite library.

Usage:
  # Example: API-based embeddings
  EYE_EMBED_PROVIDER=api EYE_EMBED_API_URL=http://localhost:8010/embed \
    python tools/reindex_embeddings.py

  # Example: self-hosted CLIP (requires torch+open_clip_torch)
  EYE_EMBED_PROVIDER=clip EYE_CLIP_DEVICE=cuda python tools/reindex_embeddings.py

Notes:
  - This recalculates the embedding blob stored in the `models` table.
  - If you change embedding model/provider, you MUST run this so all vectors live
    in the same vector space.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass

import numpy as np

from app.services.embeddings.providers import get_provider, EMBED_DIM
from app.services.retrieval.index import compute_model_embedding


DB_PATH = os.getenv(
    "EYE_LIBRARY_DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "data", "library.db"),
)


def _pack(vec: np.ndarray) -> bytes:
    return vec.astype(np.float32).tobytes()


def main() -> None:
    provider = get_provider()
    print(f"Reindexing embeddings with provider: {provider.name} (dim={EMBED_DIM})")

    con = sqlite3.connect(os.path.abspath(DB_PATH))
    con.row_factory = sqlite3.Row

    rows = con.execute("SELECT id, title, tags, preview_url FROM models").fetchall()
    print(f"Found {len(rows)} models")

    updated = 0
    for r in rows:
        model_id = r["id"]
        title = r["title"] or ""
        tags = r["tags"] or ""
        preview_url = r["preview_url"]
        vec = compute_model_embedding(title, tags, preview_url)
        con.execute("UPDATE models SET embedding=? WHERE id=?", (_pack(vec), model_id))
        updated += 1
        if updated % 50 == 0:
            con.commit()
            print(f"  updated {updated}...")

    con.commit()
    con.close()
    print(f"Done. Updated {updated} embeddings.")


if __name__ == "__main__":
    # allow running from api/ with PYTHONPATH=.
    main()
