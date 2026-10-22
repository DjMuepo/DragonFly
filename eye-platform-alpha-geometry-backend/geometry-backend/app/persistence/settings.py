from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class StorageSettings:
    data_dir: Path
    models_dir: Path
    uploads_dir: Path
    sources_dir: Path
    database_path: Path
    durable: bool
    session_ttl_seconds: int
    signed_url_ttl_seconds: int
    signing_secret: bytes
    signing_secret_configured: bool

    @property
    def warnings(self) -> list[str]:
        items = []
        if not self.durable:
            items.append("Storage is not marked durable. Set EYE_DATA_DIR to a persistent disk and EYE_STORAGE_DURABLE=1.")
        if not self.signing_secret_configured:
            items.append("EYE_SIGNING_SECRET is not set; signed file links will not survive a restart.")
        return items


def load_settings() -> StorageSettings:
    configured = os.environ.get("EYE_DATA_DIR", "").strip()
    if configured:
        data_dir = Path(configured).expanduser().resolve()
        models_dir = data_dir / "models"
        uploads_dir = data_dir / "uploads"
    else:
        data_dir = BASE_DIR / "data"
        models_dir = BASE_DIR / "static" / "models"
        uploads_dir = BASE_DIR / "static" / "uploads"
    secret = os.environ.get("EYE_SIGNING_SECRET", "")
    return StorageSettings(
        data_dir=data_dir,
        models_dir=models_dir,
        uploads_dir=uploads_dir,
        sources_dir=data_dir / "sources",
        database_path=Path(os.environ.get("EYE_DATABASE_PATH") or data_dir / "dragonfly.db"),
        durable=bool(configured) and os.environ.get("EYE_STORAGE_DURABLE") == "1",
        session_ttl_seconds=int(os.environ.get("EYE_SESSION_TTL_SECONDS", str(30 * 24 * 3600))),
        signed_url_ttl_seconds=int(os.environ.get("EYE_SIGNED_URL_TTL_SECONDS", "900")),
        signing_secret=secret.encode() if secret else os.urandom(32),
        signing_secret_configured=bool(secret),
    )
