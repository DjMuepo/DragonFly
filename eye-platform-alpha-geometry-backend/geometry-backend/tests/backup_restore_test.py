from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="dragonfly-backup-test-") as temp:
    base = Path(temp)
    source = base / "source"
    source.mkdir()
    env = {**os.environ, "EYE_DATA_DIR": str(source), "EYE_STORAGE_DURABLE": "1", "EYE_SIGNING_SECRET": "test"}
    subprocess.run([sys.executable, "-m", "app.persistence.migrate"], cwd=ROOT, env={**env, "PYTHONPATH": str(ROOT)}, check=True, capture_output=True)
    (source / "models").mkdir(parents=True)
    (source / "sources").mkdir()
    model = source / "models" / "model.glb"
    photo = source / "sources" / "scan.jpg"
    marker = source / ".legacy-storage-migration.json"
    model.write_bytes(b"glb bytes")
    photo.write_bytes(b"jpeg bytes")
    marker.write_text('{"legacy_database_sha256":"test"}', encoding="utf-8")
    with sqlite3.connect(source / "dragonfly.db") as connection:
        connection.execute("INSERT INTO users(id,email,password_hash,display_name,created_at) VALUES('u','u@example.com','hash','U',1)")
        connection.execute("INSERT INTO projects(id,owner_id,name,label,created_at,updated_at) VALUES('p','u','P','Object',1,1)")
        connection.commit()
    archive_path = base / "backup.tar.gz"
    subprocess.run([sys.executable, "scripts/backup_storage.py", "--output", str(archive_path)], cwd=ROOT, env={**env, "PYTHONPATH": str(ROOT)}, check=True, capture_output=True)
    restored = base / "restored"
    subprocess.run([sys.executable, "scripts/restore_storage.py", str(archive_path), "--target", str(restored)], cwd=ROOT, env={**env, "PYTHONPATH": str(ROOT)}, check=True, capture_output=True)
    assert (restored / "models/model.glb").read_bytes() == model.read_bytes()
    assert (restored / "sources/scan.jpg").read_bytes() == photo.read_bytes()
    assert (restored / ".legacy-storage-migration.json").read_bytes() == marker.read_bytes()
    with sqlite3.connect(restored / "dragonfly.db") as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("SELECT name FROM projects WHERE id='p'").fetchone()[0] == "P"
    refusal = subprocess.run([sys.executable, "scripts/restore_storage.py", str(archive_path), "--target", str(source)], cwd=ROOT, env={**env, "PYTHONPATH": str(ROOT)}, capture_output=True)
    assert refusal.returncode != 0 and b"target is not empty" in refusal.stderr

    corrupted = base / "corrupt.tar.gz"
    with tarfile.open(archive_path, "r:gz") as original, tarfile.open(corrupted, "w:gz") as output:
        for member in original.getmembers():
            stream = original.extractfile(member) if member.isfile() else None
            if member.name == "models/model.glb":
                import io
                stream = io.BytesIO(b"changed bytes")
            output.addfile(member, stream)
    reject_target = base / "reject"
    failure = subprocess.run([sys.executable, "scripts/restore_storage.py", str(corrupted), "--target", str(reject_target)], cwd=ROOT, env={**env, "PYTHONPATH": str(ROOT)}, capture_output=True)
    assert failure.returncode != 0 and b"backup integrity failure" in failure.stderr
print("backup restore PASS")
