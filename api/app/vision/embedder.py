from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional
import numpy as np

from app.services.embeddings.providers import get_provider

_provider = get_provider()

def embed_image_bytes(data: bytes) -> np.ndarray:
    return _provider.embed_image_bytes(data)

def embed_image_file(path: str | Path) -> np.ndarray:
    return embed_image_bytes(Path(path).read_bytes())
