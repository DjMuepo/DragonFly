from __future__ import annotations
import argparse
from app.services.connectors.nih3d import Nih3DConnector
from app.services.retrieval.index import ensure_schema, upsert_remote_model
from app.services.connectors.policy import allow_in_results

def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest NIH 3D entries by IDs (metadata + deep link).")
    ap.add_argument("--ids", nargs="+", required=True, help="NIH entry IDs like 3DPX-021858")
    ap.add_argument("--allow-restricted", action="store_true")
    args = ap.parse_args()

    ensure_schema()
    conn = Nih3DConnector()
    ing = 0
    for rid in args.ids:
        card = conn.fetch(rid)
        if not card:
            print(f"skip {rid} (fetch failed)")
            continue
        if not allow_in_results(card.license, args.allow_restricted):
            print(f"skip {rid} (restricted)")
            continue
        upsert_remote_model(
            source=card.source,
            remote_id=card.remote_id,
            title=card.title,
            tags=card.tags,
            license_info=card.license,
            preview_url=card.preview_url,
            external_url=card.external_url,
        )
        ing += 1
        print(f"ingested {rid}: {card.title}")
    print(f"Done. Ingested {ing} NIH entries.")

if __name__ == "__main__":
    main()
