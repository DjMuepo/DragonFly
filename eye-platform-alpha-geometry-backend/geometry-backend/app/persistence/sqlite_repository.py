from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from .repository import DuplicateError, Repository, Row

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


class SqliteRepository(Repository):
    """SQLite implementation. Durable only when the database file lives on a persistent disk."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = FULL")
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            conn.execute("COMMIT")
        finally:
            conn.close()

    @staticmethod
    def _one(cursor: sqlite3.Cursor) -> Optional[Row]:
        row = cursor.fetchone()
        return dict(row) if row else None

    def migrate(self) -> list[str]:
        applied: list[str] = []
        with self._tx() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, checksum TEXT NOT NULL, applied_at REAL NOT NULL)")
            known = {row["version"]: row["checksum"] for row in conn.execute("SELECT version, checksum FROM schema_migrations")}
            for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
                sql = path.read_text(encoding="utf-8")
                checksum = hashlib.sha256(sql.encode()).hexdigest()
                if path.stem in known:
                    if known[path.stem] != checksum:
                        raise RuntimeError(f"Migration {path.name} was modified after it was applied.")
                    continue
                for statement in [s.strip() for s in sql.split(";\n") if s.strip()]:
                    conn.execute(statement)
                conn.execute("INSERT INTO schema_migrations VALUES (?, ?, strftime('%s','now'))", (path.stem, checksum))
                applied.append(path.stem)
        return applied

    # users and sessions
    def create_user(self, user_id, email, password_hash, display_name, now):
        try:
            with self._tx() as conn:
                conn.execute("INSERT INTO users (id, email, password_hash, display_name, created_at) VALUES (?,?,?,?,?)", (user_id, email, password_hash, display_name, now))
                return self._one(conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)))
        except sqlite3.IntegrityError as error:
            raise DuplicateError("email") from error

    def get_user_by_email(self, email):
        with self._tx() as conn:
            return self._one(conn.execute("SELECT * FROM users WHERE email = ?", (email,)))

    def get_user(self, user_id):
        with self._tx() as conn:
            return self._one(conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)))

    def create_session(self, session_id, user_id, token_hash, now, expires_at):
        with self._tx() as conn:
            conn.execute("INSERT INTO sessions (id, user_id, token_hash, created_at, expires_at, last_used_at) VALUES (?,?,?,?,?,?)", (session_id, user_id, token_hash, now, expires_at, now))

    def get_session_by_token_hash(self, token_hash):
        with self._tx() as conn:
            return self._one(conn.execute("SELECT * FROM sessions WHERE token_hash = ?", (token_hash,)))

    def touch_session(self, session_id, now):
        with self._tx() as conn:
            conn.execute("UPDATE sessions SET last_used_at = ? WHERE id = ?", (now, session_id))

    def revoke_session(self, session_id, now):
        with self._tx() as conn:
            conn.execute("UPDATE sessions SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL", (now, session_id))

    def revoke_user_sessions(self, user_id, now):
        with self._tx() as conn:
            return conn.execute("UPDATE sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL", (now, user_id)).rowcount

    # projects
    def create_project(self, project_id, owner_id, name, label, now):
        with self._tx() as conn:
            conn.execute("INSERT INTO projects (id, owner_id, name, label, created_at, updated_at) VALUES (?,?,?,?,?,?)", (project_id, owner_id, name, label, now, now))
            return self._one(conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)))

    def list_projects(self, owner_id):
        with self._tx() as conn:
            rows = conn.execute(
                "SELECT p.*, (SELECT COUNT(*) FROM revisions r WHERE r.project_id = p.id AND r.superseded_at IS NULL) AS revision_count "
                "FROM projects p WHERE p.owner_id = ? ORDER BY p.updated_at DESC",
                (owner_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_project(self, project_id):
        with self._tx() as conn:
            return self._one(conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)))

    def rename_project(self, project_id, name, now):
        with self._tx() as conn:
            conn.execute("UPDATE projects SET name = ?, updated_at = ? WHERE id = ?", (name, now, project_id))

    def set_project_source(self, project_id, artifact_id):
        with self._tx() as conn:
            conn.execute("UPDATE projects SET source_artifact_id = ? WHERE id = ?", (artifact_id, project_id))

    def set_cursor(self, project_id, index, now):
        with self._tx() as conn:
            conn.execute("UPDATE projects SET cursor_index = ?, updated_at = ? WHERE id = ?", (index, now, project_id))

    def delete_project(self, project_id):
        with self._tx() as conn:
            filenames = [row["filename"] for row in conn.execute("SELECT filename FROM artifacts WHERE project_id = ?", (project_id,))]
            conn.execute("UPDATE jobs SET project_id = NULL WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM revisions WHERE project_id = ?", (project_id,))
            conn.execute("UPDATE projects SET source_artifact_id = NULL WHERE id = ?", (project_id,))
            conn.execute("DELETE FROM artifacts WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            return filenames

    # artifacts
    def add_artifact(self, artifact_id, project_id, owner_id, kind, filename, size_bytes, sha256, now):
        with self._tx() as conn:
            conn.execute("INSERT INTO artifacts (id, project_id, owner_id, kind, filename, size_bytes, sha256, created_at) VALUES (?,?,?,?,?,?,?,?)", (artifact_id, project_id, owner_id, kind, filename, size_bytes, sha256, now))
            return self._one(conn.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)))

    def get_artifact(self, artifact_id):
        with self._tx() as conn:
            return self._one(conn.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)))

    def get_artifact_by_filename(self, filename):
        with self._tx() as conn:
            return self._one(conn.execute("SELECT * FROM artifacts WHERE filename = ?", (filename,)))

    def list_project_artifacts(self, project_id):
        with self._tx() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM artifacts WHERE project_id = ?", (project_id,))]

    # revisions
    def append_revision(self, project_id, revision, base_seq, now):
        try:
            with self._tx() as conn:
                top = conn.execute("SELECT COALESCE(MAX(seq), -1) AS top FROM revisions WHERE project_id = ?", (project_id,)).fetchone()["top"]
                if base_seq is not None:
                    conn.execute("UPDATE revisions SET superseded_at = ? WHERE project_id = ? AND seq > ? AND superseded_at IS NULL", (now, project_id, base_seq))
                seq = top + 1
                conn.execute(
                    "INSERT INTO revisions (id, project_id, seq, kind, job_id, model_artifact_id, stl_artifact_id, provider, provider_kind, change_kind, summary, scale_status, calibration_json, validation_json, metadata_json, created_at) "
                    "VALUES (:id,:project_id,:seq,:kind,:job_id,:model_artifact_id,:stl_artifact_id,:provider,:provider_kind,:change_kind,:summary,:scale_status,:calibration_json,:validation_json,:metadata_json,:created_at)",
                    {**revision, "project_id": project_id, "seq": seq, "created_at": now},
                )
                active = conn.execute("SELECT COUNT(*) AS n FROM revisions WHERE project_id = ? AND superseded_at IS NULL", (project_id,)).fetchone()["n"]
                conn.execute("UPDATE projects SET cursor_index = ?, updated_at = ? WHERE id = ?", (active - 1, now, project_id))
                return self._one(conn.execute("SELECT * FROM revisions WHERE id = ?", (revision["id"],)))
        except sqlite3.IntegrityError as error:
            raise DuplicateError("revision") from error

    def list_revisions(self, project_id, include_superseded=False):
        sql = "SELECT * FROM revisions WHERE project_id = ?" + ("" if include_superseded else " AND superseded_at IS NULL") + " ORDER BY seq"
        with self._tx() as conn:
            return [dict(row) for row in conn.execute(sql, (project_id,))]

    def get_revision(self, revision_id):
        with self._tx() as conn:
            return self._one(conn.execute("SELECT * FROM revisions WHERE id = ?", (revision_id,)))

    def get_revision_by_job(self, job_id):
        with self._tx() as conn:
            return self._one(conn.execute("SELECT * FROM revisions WHERE job_id = ?", (job_id,)))

    # jobs
    def create_job(self, job):
        columns = ", ".join(job)
        placeholders = ", ".join(f":{name}" for name in job)
        try:
            with self._tx() as conn:
                conn.execute(f"INSERT INTO jobs ({columns}) VALUES ({placeholders})", job)
                return self._one(conn.execute("SELECT * FROM jobs WHERE id = ?", (job["id"],)))
        except sqlite3.IntegrityError as error:
            raise DuplicateError("job") from error

    def get_job(self, job_id):
        with self._tx() as conn:
            return self._one(conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)))

    def update_job(self, job_id, fields, now):
        assignments = ", ".join(f"{name} = :{name}" for name in fields)
        with self._tx() as conn:
            conn.execute(f"UPDATE jobs SET {assignments}, updated_at = :_now WHERE id = :_id", {**fields, "_now": now, "_id": job_id})

    def find_job_by_idempotency(self, owner_scope, key):
        with self._tx() as conn:
            return self._one(conn.execute("SELECT * FROM jobs WHERE owner_scope = ? AND idempotency_key = ?", (owner_scope, key)))

    def list_unfinished_jobs(self):
        with self._tx() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM jobs WHERE status IN ('queued','processing')")]

    def claim_job(self, job_id, owner_id, now):
        with self._tx() as conn:
            changed = conn.execute(
                "UPDATE jobs SET owner_id = ?, owner_scope = ?, idempotency_key = NULL, updated_at = ? WHERE id = ? AND owner_id IS NULL AND status = 'done'",
                (owner_id, owner_id, now, job_id),
            ).rowcount
            return changed == 1

    def detach_project_jobs(self, project_id):
        with self._tx() as conn:
            conn.execute("UPDATE jobs SET project_id = NULL WHERE project_id = ?", (project_id,))
