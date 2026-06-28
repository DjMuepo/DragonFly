from __future__ import annotations

from typing import Optional

import numpy as np

from ...core.schemas import RetrievalResponse
from .index import search as _search


def search_models(
    *,
    query_hint: Optional[str] = None,
    allow_restricted: bool = False,
    limit: int = 6,
    image_bytes: Optional[bytes] = None,
    query_vector: Optional[np.ndarray] = None,
) -> RetrievalResponse:
    """License-aware retrieval over the local SQLite index.

    The query can be:
      - text (query_hint)
      - image bytes (image_bytes)
      - precomputed vector (query_vector)

    Provider selection is controlled by EYE_EMBED_PROVIDER.
    """

    return _search(
        query_hint=query_hint,
        allow_restricted=allow_restricted,
        limit=limit,
        image_bytes=image_bytes,
        query_vector=query_vector,
    )
