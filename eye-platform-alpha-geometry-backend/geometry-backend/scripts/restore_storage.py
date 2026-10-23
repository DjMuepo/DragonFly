#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath

from app.persistence.settings import load_settings


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> int:
    settings = load_settings()
    parser = argparse.ArgumentParser(description="Verify and restore a DragonFly storage archive into an EYE_DATA_DIR.")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--target", type=Path, default=settings.data_dir)
    parser.add_argument("--replace", action="store_true", help="Move a non-empty target aside before restoring")
    args = parser.parse_args()
    archive_path = args.archive.expanduser().resolve()
    target = args.target.expanduser().resolve()
    if archive_path.is_relative_to(target):
        parser.error("archive must be outside the restore target")
    with tempfile.TemporaryDirectory(prefix="dragonfly-restore-") as temp:
        staging = Path(temp)
        with tarfile.open(archive_path, "r:gz") as archive:
            for member in archive.getmembers():
                relative = PurePosixPath(member.name)
                if relative.is_absolute() or ".." in relative.parts or member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                    parser.error("archive contains an unsafe path or unsupported file type")
                if member.name not in {"manifest.json", "dragonfly.db", ".legacy-storage-migration.json"} and not member.name.startswith(("models/", "sources/")):
                    parser.error("archive contains an unexpected path")
                if member.isdir():
                    (staging / Path(*relative.parts)).mkdir(parents=True, exist_ok=True)
                    continue
                source = archive.extractfile(member)
                if source is None:
                    parser.error(f"archive member is unreadable: {member.name}")
                destination = staging / Path(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with source, destination.open("wb") as target_stream:
                    shutil.copyfileobj(source, target_stream)
        manifest_path = staging / "manifest.json"
        if not manifest_path.is_file():
            parser.error("archive manifest is missing")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("format") != 1 or "dragonfly.db" not in manifest.get("files", {}):
            parser.error("unsupported or incomplete backup format")
        for name, metadata in manifest["files"].items():
            relative = PurePosixPath(name)
            if relative.is_absolute() or ".." in relative.parts or (name not in {"dragonfly.db", ".legacy-storage-migration.json"} and not name.startswith(("models/", "sources/"))):
                parser.error("manifest contains an unsafe path")
            path = staging / name
            if not path.is_file() or path.stat().st_size != metadata["size"] or digest(path) != metadata["sha256"]:
                parser.error(f"backup integrity failure: {name}")
        db = sqlite3.connect(staging / "dragonfly.db")
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        db.close()
        if integrity != "ok":
            parser.error(f"database integrity check failed: {integrity}")
        if target.exists() and any(target.iterdir()):
            if not args.replace:
                parser.error(f"target is not empty; use --replace to keep it as a rollback copy: {target}")
            rollback = target.with_name(f"{target.name}.pre-restore-{int(time.time())}")
            target.rename(rollback)
            print(f"previous target preserved at {rollback}")
        target.mkdir(parents=True, exist_ok=True)
        for name in manifest["files"]:
            source = staging / name
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    print(json.dumps({"restored_to": str(target), "files": len(manifest["files"]), "archive_sha256": digest(archive_path), "database_integrity": integrity, "external_restore_test_attested": False}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"restore failed: {error}", file=sys.stderr)
        raise SystemExit(1)
