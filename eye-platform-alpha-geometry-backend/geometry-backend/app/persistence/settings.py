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
    require_durable: bool
    max_active_jobs_per_user: int
    max_active_guest_jobs: int
    daily_reconstructions_per_user: int
    daily_reconstructions_per_guest: int
    upload_max_bytes: int
    job_timeout_seconds: int
    provider_request_timeout_seconds: int
    backup_dir: Path | None
    backup_external_configured: bool
    backup_restore_tested: bool
    trust_proxy_headers: bool

    @property
    def warnings(self) -> list[str]:
        items = []
        if not self.durable:
            items.append("Storage is not marked durable. Set EYE_DATA_DIR to a persistent disk and EYE_STORAGE_DURABLE=1.")
        if not self.signing_secret_configured:
            items.append("EYE_SIGNING_SECRET is not set; signed file links will not survive a restart.")
        if not self.backup_external_configured:
            items.append("No external backup destination is configured.")
        if self.backup_external_configured and not self.backup_restore_tested:
            items.append("An external backup destination is configured, but restore testing is not attested.")
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
    backup_dir = os.environ.get("EYE_BACKUP_DIR", "").strip()
    settings = StorageSettings(
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
        require_durable=os.environ.get("EYE_REQUIRE_DURABLE_STORAGE") == "1",
        max_active_jobs_per_user=int(os.environ.get("EYE_MAX_ACTIVE_RECONSTRUCTION_JOBS_PER_USER", "1")),
        max_active_guest_jobs=int(os.environ.get("EYE_MAX_ACTIVE_GUEST_JOBS", "1")),
        daily_reconstructions_per_user=int(os.environ.get("EYE_DAILY_RECONSTRUCTION_QUOTA_PER_USER", "1")),
        daily_reconstructions_per_guest=int(os.environ.get("EYE_DAILY_RECONSTRUCTION_QUOTA_PER_GUEST", "1")),
        upload_max_bytes=int(os.environ.get("EYE_UPLOAD_MAX_BYTES", str(15 * 1024 * 1024))),
        job_timeout_seconds=int(os.environ.get("EYE_REPLICATE_TIMEOUT_SECONDS", "600")),
        provider_request_timeout_seconds=int(os.environ.get("EYE_REPLICATE_REQUEST_TIMEOUT_SECONDS", "60")),
        backup_dir=Path(backup_dir).expanduser().resolve() if backup_dir else None,
        backup_external_configured=os.environ.get("EYE_BACKUP_EXTERNAL") == "1" and bool(backup_dir),
        backup_restore_tested=os.environ.get("EYE_BACKUP_RESTORE_TESTED") == "1",
        trust_proxy_headers=os.environ.get("EYE_TRUST_PROXY_HEADERS") == "1",
    )
    if settings.max_active_jobs_per_user < 0 or settings.max_active_guest_jobs < 0 or settings.daily_reconstructions_per_user < 0 or settings.daily_reconstructions_per_guest < 0:
        raise RuntimeError("Reconstruction quotas and concurrency caps must be zero or positive.")
    if settings.upload_max_bytes < 1024 or settings.upload_max_bytes > 100 * 1024 * 1024:
        raise RuntimeError("EYE_UPLOAD_MAX_BYTES must be between 1 KiB and 100 MiB.")
    if not 30 <= settings.job_timeout_seconds <= 3600:
        raise RuntimeError("EYE_REPLICATE_TIMEOUT_SECONDS must be between 30 and 3600 seconds.")
    if not 5 <= settings.provider_request_timeout_seconds <= 300:
        raise RuntimeError("EYE_REPLICATE_REQUEST_TIMEOUT_SECONDS must be between 5 and 300 seconds.")
    if not 300 <= settings.session_ttl_seconds <= 180 * 24 * 3600:
        raise RuntimeError("EYE_SESSION_TTL_SECONDS must be between 5 minutes and 180 days.")
    if not 60 <= settings.signed_url_ttl_seconds <= 24 * 3600:
        raise RuntimeError("EYE_SIGNED_URL_TTL_SECONDS must be between 1 minute and 24 hours.")
    if settings.backup_external_configured and settings.backup_dir and settings.backup_dir.is_relative_to(data_dir):
        raise RuntimeError("EYE_BACKUP_DIR must be outside EYE_DATA_DIR when marked external.")
    if configured and not settings.database_path.is_relative_to(data_dir):
        raise RuntimeError("EYE_DATABASE_PATH must be inside EYE_DATA_DIR so it shares the persistent disk.")
    return settings
