from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from .accounts import AuthService
from .artifacts import ArtifactStore
from .durable_jobs import DurableJobs
from .persistence.repository import Repository
from .persistence.settings import StorageSettings, load_settings
from .persistence.sqlite_repository import SqliteRepository
from .projects import ProjectService

LOGGER = logging.getLogger("uvicorn.error.dragonfly.storage")


@dataclass
class Runtime:
    settings: StorageSettings
    repo: Repository
    auth: AuthService
    artifacts: ArtifactStore
    jobs: DurableJobs
    projects: ProjectService


def build_runtime() -> Runtime:
    settings = load_settings()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    repo = SqliteRepository(settings.database_path)
    applied = repo.migrate()
    if applied:
        LOGGER.info("applied_migrations %s", applied)
    for warning in settings.warnings:
        LOGGER.warning("storage_warning %s", warning)
    if os.environ.get("EYE_REQUIRE_DURABLE_STORAGE") == "1" and not settings.durable:
        raise RuntimeError("EYE_REQUIRE_DURABLE_STORAGE=1 but EYE_DATA_DIR/EYE_STORAGE_DURABLE=1 are not configured.")
    artifacts = ArtifactStore(settings, repo)
    jobs = DurableJobs(repo)
    projects = ProjectService(repo, artifacts)
    jobs.finalizer = projects.finalize_job
    jobs.source_cleanup = lambda name: artifacts.delete_files([name])
    return Runtime(settings, repo, AuthService(repo, settings.session_ttl_seconds), artifacts, jobs, projects)
