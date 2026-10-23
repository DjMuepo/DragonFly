from __future__ import annotations

import logging
import os
import shutil
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .accounts import AuthService
from .artifacts import ArtifactStore
from .durable_jobs import DurableJobs
from .persistence.repository import Repository
from .persistence.settings import StorageSettings, load_settings
from .persistence.sqlite_repository import SqliteRepository
from .projects import ProjectService
from .environment import validate_mock_provider_settings

LOGGER = logging.getLogger("uvicorn.error.dragonfly.storage")


@dataclass
class Runtime:
    settings: StorageSettings
    repo: Repository
    auth: AuthService
    artifacts: ArtifactStore
    jobs: DurableJobs
    projects: ProjectService
    legacy_migration: dict


def migrate_legacy_storage(settings: StorageSettings, legacy_root: Path | None = None) -> dict:
    if not os.environ.get("EYE_DATA_DIR", "").strip() and legacy_root is None:
        return {"copied_files": 0, "conflicts": 0, "database_copied": False}
    backend_dir = legacy_root or Path(__file__).resolve().parents[1]
    legacy_database = backend_dir / "data" / "dragonfly.db"
    marker = settings.data_dir / ".legacy-storage-migration.json"
    prior_migration = json.loads(marker.read_text(encoding="utf-8")) if marker.is_file() else None
    copied = 0
    conflicts = 0
    database_copied = False
    if legacy_database.is_file() and not settings.database_path.exists() and legacy_database != settings.database_path:
        source_digest = _file_digest(legacy_database)
        settings.database_path.parent.mkdir(parents=True, exist_ok=True)
        import sqlite3
        source = sqlite3.connect(legacy_database)
        target = sqlite3.connect(settings.database_path)
        try:
            source.backup(target)
            database_copied = True
        finally:
            target.close()
            source.close()
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({"legacy_database_sha256": source_digest}, sort_keys=True), encoding="utf-8")
    elif legacy_database.is_file() and settings.database_path.is_file() and legacy_database != settings.database_path:
        legacy_digest = _file_digest(legacy_database)
        if prior_migration and legacy_digest == prior_migration.get("legacy_database_sha256"):
            pass
        elif legacy_digest != _file_digest(settings.database_path):
            raise RuntimeError("Both legacy and persistent databases exist with different contents. Resolve the migration manually; neither database was overwritten.")
    legacy_dirs = (
        (backend_dir / "static" / "models", settings.models_dir),
        (backend_dir / "static" / "uploads", settings.uploads_dir),
        (backend_dir / "data" / "sources", settings.sources_dir),
    )
    for source_dir, destination_dir in legacy_dirs:
        if source_dir.resolve() == destination_dir.resolve() or not source_dir.is_dir():
            continue
        for source in source_dir.rglob("*"):
            if not source.is_file() or source.is_symlink():
                continue
            destination = destination_dir / source.relative_to(source_dir)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                if destination.stat().st_size != source.stat().st_size or _file_digest(destination) != _file_digest(source):
                    conflicts += 1
                    raise RuntimeError(f"Legacy artifact conflicts with persistent storage at {destination}; neither file was overwritten.")
                continue
            shutil.copy2(source, destination)
            copied += 1
    result = {"copied_files": copied, "conflicts": conflicts, "database_copied": database_copied}
    if conflicts:
        LOGGER.error("legacy_storage_migration_conflicts count=%s", conflicts)
    if copied or database_copied:
        LOGGER.info("legacy_storage_migration %s", result)
    return result


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_runtime() -> Runtime:
    validate_mock_provider_settings()
    settings = load_settings()
    if settings.require_durable and not settings.durable:
        raise RuntimeError("EYE_REQUIRE_DURABLE_STORAGE=1 but EYE_DATA_DIR/EYE_STORAGE_DURABLE=1 are not configured.")
    if settings.require_durable and not settings.signing_secret_configured:
        raise RuntimeError("EYE_REQUIRE_DURABLE_STORAGE=1 requires a stable EYE_SIGNING_SECRET.")
    if os.environ.get("EYE_REQUIRE_BACKUP") == "1" and not (settings.backup_external_configured and settings.backup_restore_tested):
        raise RuntimeError("EYE_REQUIRE_BACKUP=1 requires an external EYE_BACKUP_DIR, EYE_BACKUP_EXTERNAL=1, and EYE_BACKUP_RESTORE_TESTED=1.")
    legacy_migration = migrate_legacy_storage(settings)
    for directory in (settings.data_dir, settings.models_dir, settings.uploads_dir, settings.sources_dir, settings.database_path.parent):
        directory.mkdir(parents=True, exist_ok=True)
        if not os.access(directory, os.W_OK | os.X_OK):
            raise RuntimeError(f"Storage directory is not writable: {directory}")
        probe = directory / f".dragonfly-write-check-{os.getpid()}"
        try:
            probe.write_bytes(b"ok")
            probe.unlink()
        except OSError as error:
            raise RuntimeError(f"Storage directory is not writable: {directory}") from error
    repo = SqliteRepository(settings.database_path)
    integrity = repo.integrity_check()
    if integrity != "ok":
        raise RuntimeError(f"Storage database integrity check failed: {integrity}")
    applied = repo.migrate()
    if applied:
        LOGGER.info("applied_migrations %s", applied)
    for warning in settings.warnings:
        LOGGER.warning("storage_warning %s", warning)
    artifacts = ArtifactStore(settings, repo)
    jobs = DurableJobs(repo, settings)
    projects = ProjectService(repo, artifacts)
    jobs.finalizer = projects.finalize_job
    jobs.source_cleanup = lambda name: artifacts.delete_files([name])
    return Runtime(settings, repo, AuthService(repo, settings.session_ttl_seconds), artifacts, jobs, projects, legacy_migration)
