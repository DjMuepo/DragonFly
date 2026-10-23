#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tarfile
import tempfile
import time
from pathlib import Path

from app.persistence.settings import load_settings


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> int:
    settings = load_settings()
    parser = argparse.ArgumentParser(description="Create a consistent local DragonFly storage archive.")
    parser.add_argument("--output", type=Path, help="Archive path; defaults to EYE_BACKUP_DIR/timestamp.tar.gz")
    args = parser.parse_args()
    output = args.output
    if output is None:
        if not settings.backup_dir:
            parser.error("set EYE_BACKUP_DIR or pass --output; a local archive is not an external durable backup")
        output = settings.backup_dir / f"dragonfly-{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}.tar.gz"
    output = output.expanduser().resolve()
    if output == settings.database_path or output.is_relative_to(settings.data_dir):
        parser.error("backup archive must be outside EYE_DATA_DIR")
    output.parent.mkdir(parents=True, exist_ok=True)
    if not settings.database_path.is_file():
        parser.error(f"database does not exist: {settings.database_path}")
    with tempfile.TemporaryDirectory(prefix="dragonfly-backup-") as temp:
        staging = Path(temp)
        db_copy = staging / "dragonfly.db"
        source = sqlite3.connect(settings.database_path)
        target = sqlite3.connect(db_copy)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        check = sqlite3.connect(db_copy)
        integrity = check.execute("PRAGMA integrity_check").fetchone()[0]
        check.close()
        if integrity != "ok":
            raise RuntimeError(f"database integrity check failed: {integrity}")
        manifest = {"format": 1, "created_at": time.time(), "files": {}}
        inputs: list[tuple[str, Path]] = [("dragonfly.db", db_copy)]
        migration_marker = settings.data_dir / ".legacy-storage-migration.json"
        if migration_marker.is_file():
            inputs.append((".legacy-storage-migration.json", migration_marker))
        for kind, directory in (("models", settings.models_dir), ("sources", settings.sources_dir)):
            if directory.exists():
                for path in sorted(directory.rglob("*")):
                    if path.is_file() and not path.is_symlink():
                        inputs.append((f"{kind}/{path.relative_to(directory).as_posix()}", path))
        for arcname, path in inputs:
            manifest["files"][arcname] = {"size": path.stat().st_size, "sha256": digest(path)}
        manifest_path = staging / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2), encoding="utf-8")
        with tarfile.open(output, "w:gz") as archive:
            archive.add(manifest_path, arcname="manifest.json")
            for arcname, path in inputs:
                archive.add(path, arcname=arcname, recursive=False)
    print(json.dumps({"archive": str(output), "files": len(manifest["files"]), "sha256": digest(output), "external_destination_attested": settings.backup_external_configured, "restore_tested_attested": settings.backup_restore_tested}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"backup failed: {error}", file=sys.stderr)
        raise SystemExit(1)
