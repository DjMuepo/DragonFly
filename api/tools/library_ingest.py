#!/usr/bin/env python3
"""Ingest a JSON catalog into the local license-aware model index.

Usage:
  python tools/library_ingest.py --input sample_library/models.json

This script is intentionally lightweight:
- Uses a deterministic placeholder embedding (no ML deps).
- Stores metadata + embedding into SQLite (api/data/library.db by default).

Later, replace the embedding function in app/services/retrieval/index.py with a real
vision-language embedding pipeline, and re-run ingestion.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.schemas import LicenseInfo
from app.services.retrieval.index import db_path, ensure_schema, upsert_model

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Path to models.json catalog")
    args = p.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        raise SystemExit(f"Input not found: {in_path}")

    ensure_schema()
    items = json.loads(in_path.read_text(encoding="utf-8"))

    n = 0
    for it in items:
        lic = LicenseInfo(**(it.get("license") or {}))
        upsert_model(
            id=it["id"],
            source=it["source"],
            title=it["title"],
            tags=it.get("tags",""),
            license_info=lic,
            preview_url=it.get("preview_url"),
            file_url=it.get("file_url"),
        )
        n += 1

    print(f"Ingested {n} models into {db_path()}")

if __name__ == "__main__":
    main()
