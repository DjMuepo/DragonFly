from __future__ import annotations

import base64
import io
import os
from typing import Optional

import numpy as np

EMBED_DIM = int(os.getenv("EYE_EMBED_DIM", "512"))


class EmbeddingProvider:
    """Embedding provider interface.

    NOTE: if you switch embedding providers/models, you must reindex your library
    embeddings; vectors from different models are not directly comparable.
    """

    name: str = "base"

    def embed_text(self, text: str) -> np.ndarray:
        raise NotImplementedError

    def embed_image_bytes(self, data: bytes) -> np.ndarray:
        # Optional; not all providers support image embeddings.
        return np.zeros((EMBED_DIM,), dtype=np.float32)


class HashEmbeddingProvider(EmbeddingProvider):
    """Deterministic, dependency-free fallback embeddings."""

    name = "hash"

    def embed_text(self, text: str) -> np.ndarray:
        text = (text or "").strip().lower()
        if not text:
            return np.zeros((EMBED_DIM,), dtype=np.float32)
        v = np.zeros((EMBED_DIM,), dtype=np.float32)
        for token in text.split():
            h = abs(hash(token)) % EMBED_DIM
            v[h] += 1.0
        n = float(np.linalg.norm(v))
        if n > 0:
            v /= n
        return v


class ApiEmbeddingProvider(EmbeddingProvider):
    """Calls an external embedding API.

    Expected API contract:
      POST {EYE_EMBED_API_URL}
      JSON {"type": "text"|"image", "text": "..."} or {"type": "image", "image_b64": "..."}
      Response JSON {"embedding": [float, ...]}

    This keeps us provider-agnostic; you can point it at any service.
    """

    name = "api"

    def __init__(self) -> None:
        self.url = os.getenv("EYE_EMBED_API_URL", "http://localhost:8010/embed").rstrip("/")
        self.timeout = float(os.getenv("EYE_EMBED_API_TIMEOUT", "10"))

    def _post(self, payload: dict) -> np.ndarray:
        import requests

        r = requests.post(self.url, json=payload, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        emb = np.array(data.get("embedding", []), dtype=np.float32)
        if emb.size != EMBED_DIM:
            # Allow provider to return any dim; we pad/truncate deterministically.
            out = np.zeros((EMBED_DIM,), dtype=np.float32)
            n = min(EMBED_DIM, emb.size)
            if n > 0:
                out[:n] = emb[:n]
            emb = out
        nrm = float(np.linalg.norm(emb))
        if nrm > 0:
            emb /= nrm
        return emb

    def embed_text(self, text: str) -> np.ndarray:
        return self._post({"type": "text", "text": text or ""})

    def embed_image_bytes(self, data: bytes) -> np.ndarray:
        b64 = base64.b64encode(data).decode("utf-8")
        return self._post({"type": "image", "image_b64": b64})


class LocalClipEmbeddingProvider(EmbeddingProvider):
    """Self-hosted CLIP provider (optional dependency).

    Requires:
      pip install torch open_clip_torch pillow

    Runs on CPU or GPU depending on your torch install.
    """

    name = "clip"

    def __init__(self) -> None:
        self.model_name = os.getenv("EYE_CLIP_MODEL", "ViT-B-32")
        self.pretrained = os.getenv("EYE_CLIP_PRETRAINED", "openai")
        self.device = os.getenv("EYE_CLIP_DEVICE", "cpu")

        try:
            import torch
            import open_clip
            from PIL import Image
        except Exception as e:
            raise RuntimeError(
                "LocalClipEmbeddingProvider requires torch + open_clip_torch + pillow. "
                "Install with: pip install torch open_clip_torch pillow"
            ) from e

        self._torch = torch
        self._open_clip = open_clip
        self._Image = Image

        self._model, _, self._preprocess = open_clip.create_model_and_transforms(
            self.model_name, pretrained=self.pretrained
        )
        self._tokenizer = open_clip.get_tokenizer(self.model_name)
        self._model.to(self.device)
        self._model.eval()

    def embed_text(self, text: str) -> np.ndarray:
        torch = self._torch
        tokens = self._tokenizer([text or ""])  # (1, T)
        with torch.no_grad():
            feats = self._model.encode_text(tokens.to(self.device))
            feats = feats / feats.norm(dim=-1, keepdim=True)
        vec = feats[0].detach().cpu().numpy().astype(np.float32)
        return _fit_dim(vec)

    def embed_image_bytes(self, data: bytes) -> np.ndarray:
        torch = self._torch
        img = self._Image.open(io.BytesIO(data)).convert("RGB")
        x = self._preprocess(img).unsqueeze(0)
        with torch.no_grad():
            feats = self._model.encode_image(x.to(self.device))
            feats = feats / feats.norm(dim=-1, keepdim=True)
        vec = feats[0].detach().cpu().numpy().astype(np.float32)
        return _fit_dim(vec)


def _fit_dim(vec: np.ndarray) -> np.ndarray:
    out = np.zeros((EMBED_DIM,), dtype=np.float32)
    n = min(EMBED_DIM, vec.size)
    if n > 0:
        out[:n] = vec[:n]
    nrm = float(np.linalg.norm(out))
    if nrm > 0:
        out /= nrm
    return out


def get_provider() -> EmbeddingProvider:
    name = os.getenv("EYE_EMBED_PROVIDER", "hash").strip().lower()
    if name in ("hash", "default"):
        return HashEmbeddingProvider()
    if name in ("api", "remote"):
        return ApiEmbeddingProvider()
    if name in ("clip", "local"):
        return LocalClipEmbeddingProvider()
    return HashEmbeddingProvider()
