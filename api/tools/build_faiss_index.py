from __future__ import annotations
from app.services.vector.faiss_index import build_faiss_index

if __name__ == "__main__":
    res = build_faiss_index()
    print(res)
