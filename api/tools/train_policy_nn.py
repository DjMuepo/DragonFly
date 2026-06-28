from __future__ import annotations
import argparse, os, json
from app.services.structural.policy_nn import (
    load_events_jsonl, build_training_rows, train_policy,
    save_model, latest_model_path, versioned_model_path, encode_features
)

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default="events.jsonl")
    ap.add_argument("--outdir", default=os.getenv("EYE_MODELS_DIR", "app/models"))
    ap.add_argument("--epochs", type=int, default=15)
    args = ap.parse_args()

    events = load_events_jsonl(args.events)
    rows = build_training_rows(events)
    if len(rows) < 10:
        print("Not enough training rows (need >=10).")
        return

    model = train_policy(rows, epochs=args.epochs, lr=1e-3, hidden=64)
    vpath = versioned_model_path(args.outdir)
    lpath = latest_model_path(args.outdir)
    save_model(model, vpath, meta={"rows": len(rows), "epochs": args.epochs})
    save_model(model, lpath, meta={"rows": len(rows), "epochs": args.epochs, "latest": True})
    print(f"Saved model: {lpath} (+ versioned)")

if __name__ == "__main__":
    main()
