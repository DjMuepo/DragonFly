from __future__ import annotations

from typing import Dict, Any, List, Tuple
import numpy as np

from app.services.embeddings.providers import get_provider

# Consumer-friendly object families with richer prompt text for better zero-shot matching.
CATEGORY_PROMPTS: Dict[str, List[str]] = {
    "hook": [
        "a 3d printable hook",
        "a wall hook",
        "a hanging hook object",
    ],
    "bracket": [
        "a support bracket",
        "a wall mounting bracket",
        "a structural 3d printed bracket",
    ],
    "container": [
        "a small storage container",
        "a 3d printed box or container",
        "an enclosure container object",
    ],
    "handle": [
        "a handle grip",
        "a tool handle",
        "an ergonomic 3d printed handle",
    ],
    "connector": [
        "a connector part",
        "a joining connector object",
        "a mechanical connector",
    ],
    "adapter": [
        "an adapter part",
        "a pipe or fitting adapter",
        "a 3d printed adapter component",
    ],
    "furniture part": [
        "a furniture part",
        "a chair or desk replacement part",
        "a household furniture component",
    ],
    "toy": [
        "a toy object",
        "a playful plastic toy part",
        "a small toy component",
    ],
    "mechanical part": [
        "a mechanical component",
        "a machine part",
        "a functional 3d printable mechanical part",
    ],
    "clip": [
        "a clip object",
        "a cable clip",
        "a fastening clip part",
    ],
    "phone stand": [
        "a phone stand",
        "a mobile phone holder stand",
        "a 3d printed phone support",
    ],
    "chair": [
        "a chair",
        "a chair component",
        "a seat support part",
    ],
    "desk": [
        "a desk or table",
        "a table support component",
        "a desk furniture part",
    ],
    "pipe adapter": [
        "a pipe adapter",
        "a hose or pipe connector",
        "a threaded plumbing adapter",
    ],
    "grip": [
        "an assistive grip",
        "a grip adapter",
        "an ergonomic grip object",
    ],
    "enclosure": [
        "an electronic enclosure",
        "a housing enclosure box",
        "a protective case enclosure",
    ],
}

_provider = get_provider()

def _avg_text_embedding(prompts: List[str]) -> np.ndarray:
    vecs = []
    for p in prompts:
        v = _provider.embed_text(p)
        n = float(np.linalg.norm(v))
        if n > 0:
            v = v / n
        vecs.append(v.astype(np.float32))
    if not vecs:
        return np.zeros((512,), dtype=np.float32)
    out = np.mean(np.stack(vecs, axis=0), axis=0)
    n = float(np.linalg.norm(out))
    if n > 0:
        out = out / n
    return out.astype(np.float32)

_TEXT_EMBS = {label: _avg_text_embedding(prompts) for label, prompts in CATEGORY_PROMPTS.items()}

def classify_image_bytes(data: bytes) -> Dict[str, Any]:
    img = _provider.embed_image_bytes(data).astype(np.float32)
    n = float(np.linalg.norm(img))
    if n > 0:
        img = img / n

    sims: List[Tuple[float, str]] = []
    for cat, vec in _TEXT_EMBS.items():
        denom = float(np.linalg.norm(img) * np.linalg.norm(vec))
        sim = 0.0 if denom == 0 else float(np.dot(img, vec) / denom)
        sims.append((sim, cat))

    sims.sort(reverse=True, key=lambda x: x[0])
    best_sim, best_cat = sims[0]
    top = [{"label": c, "confidence": max(0.0, min(1.0, s))} for s, c in sims[:5]]

    return {
        "object_family": best_cat,
        "confidence": max(0.0, min(1.0, best_sim)),
        "top": top,
    }
