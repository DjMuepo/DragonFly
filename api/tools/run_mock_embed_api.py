"""Mock embedding API for local development.

This lets you run EYE_EMBED_PROVIDER=api without any external dependency.

Run:
  python tools/run_mock_embed_api.py

Env:
  EYE_EMBED_DIM=512
  PORT=8010

Then point your backend:
  EYE_EMBED_PROVIDER=api
  EYE_EMBED_API_URL=http://localhost:8010/embed
"""

from __future__ import annotations

import base64
import os

import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

EMBED_DIM = int(os.getenv("EYE_EMBED_DIM", "512"))
PORT = int(os.getenv("PORT", "8010"))

app = FastAPI(title="MockEmbeddingAPI")

class EmbedRequest(BaseModel):
    type: str
    text: str | None = None
    image_b64: str | None = None


def _hash_embed(text: str) -> np.ndarray:
    text = (text or "").strip().lower()
    v = np.zeros((EMBED_DIM,), dtype=np.float32)
    if not text:
        return v
    for token in text.split():
        h = abs(hash(token)) % EMBED_DIM
        v[h] += 1.0
    n = float(np.linalg.norm(v))
    if n > 0:
        v /= n
    return v


@app.post("/embed")
def embed(req: EmbedRequest):
    if req.type == "text":
        vec = _hash_embed(req.text or "")
        return {"embedding": vec.tolist()}
    if req.type == "image":
        # For mock purposes we embed the first few bytes as base64 text.
        if not req.image_b64:
            return {"embedding": np.zeros((EMBED_DIM,), dtype=np.float32).tolist()}
        raw = base64.b64decode(req.image_b64)
        hint = base64.b64encode(raw[:128]).decode("utf-8")
        vec = _hash_embed(hint)
        return {"embedding": vec.tolist()}
    return {"embedding": np.zeros((EMBED_DIM,), dtype=np.float32).tolist()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
