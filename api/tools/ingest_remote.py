from __future__ import annotations

import argparse

from app.services.retrieval.index import ensure_schema, upsert_remote_model
from app.services.connectors.policy import allow_in_results
from app.services.connectors.thingiverse import ThingiverseConnector
from app.services.connectors.nih3d import Nih3DConnector
from app.services.connectors.printables import PrintablesConnector
from app.services.connectors.thangs import ThangsConnector
from app.services.connectors.grabcad import GrabCadConnector

CONNECTORS = {
    "thingiverse": ThingiverseConnector,
    "nih3d": Nih3DConnector,
    "printables": PrintablesConnector,
    "thangs": ThangsConnector,
    "grabcad": GrabCadConnector,
}

def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest remote model metadata into the local index (metadata-only).")
    ap.add_argument("--source", required=True, choices=sorted(CONNECTORS.keys()))
    ap.add_argument("--query", required=True)
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--allow-restricted", action="store_true", help="Include restricted licenses in index (still metadata-only).")
    args = ap.parse_args()

    ensure_schema()
    conn = CONNECTORS[args.source]()
    cards = conn.search(args.query, limit=args.limit)
    ing = 0
    for c in cards:
        if not allow_in_results(c.license, args.allow_restricted):
            continue
        upsert_remote_model(
            source=c.source,
            remote_id=c.remote_id,
            title=c.title,
            tags=c.tags,
            license_info=c.license,
            preview_url=c.preview_url,
            external_url=c.external_url,
        )
        ing += 1

    print(f"Ingested {ing} remote model(s) from {args.source}")

if __name__ == "__main__":
    main()
