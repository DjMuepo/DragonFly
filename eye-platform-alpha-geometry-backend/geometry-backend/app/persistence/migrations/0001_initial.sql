CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    disabled INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    revoked_at REAL,
    last_used_at REAL
);
CREATE INDEX sessions_user_idx ON sessions(user_id);

CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT 'Object',
    source_artifact_id TEXT,
    cursor_index INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX projects_owner_idx ON projects(owner_id, updated_at);

CREATE TABLE artifacts (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
    owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    filename TEXT NOT NULL UNIQUE,
    size_bytes INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX artifacts_project_idx ON artifacts(project_id);

CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    owner_scope TEXT NOT NULL,
    owner_id TEXT,
    project_id TEXT,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    stage TEXT,
    stage_detail TEXT,
    provider TEXT,
    provider_kind TEXT,
    quality_mode TEXT,
    error TEXT,
    error_code TEXT,
    result_json TEXT,
    preprocessing_json TEXT,
    extra_json TEXT,
    idempotency_key TEXT,
    attempts INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE UNIQUE INDEX jobs_idempotency_idx ON jobs(owner_scope, idempotency_key) WHERE idempotency_key IS NOT NULL;
CREATE INDEX jobs_status_idx ON jobs(status);

CREATE TABLE revisions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    seq INTEGER NOT NULL,
    kind TEXT NOT NULL,
    job_id TEXT UNIQUE,
    model_artifact_id TEXT NOT NULL REFERENCES artifacts(id),
    stl_artifact_id TEXT REFERENCES artifacts(id),
    provider TEXT,
    provider_kind TEXT,
    change_kind TEXT,
    summary TEXT,
    scale_status TEXT NOT NULL DEFAULT 'unknown',
    calibration_json TEXT,
    validation_json TEXT,
    metadata_json TEXT,
    created_at REAL NOT NULL,
    superseded_at REAL,
    UNIQUE (project_id, seq)
);
