from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from pathlib import Path
from typing import Optional

from .persistence.repository import Repository, Row
from .persistence.settings import StorageSettings

PROJECT_SIDECAR_SUFFIXES = (".metadata.json", ".features.json")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ArtifactStore:
    """Tracks files on the configured data disk and signs short-lived download links."""

    def __init__(self, settings: StorageSettings, repo: Repository):
        self.settings = settings
        self.repo = repo
        for directory in (settings.models_dir, settings.sources_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def path_for(self, artifact: Row) -> Path:
        base = self.settings.sources_dir if artifact["kind"] == "source_image" else self.settings.models_dir
        return base / Path(artifact["filename"]).name

    def register(self, owner_id: str, project_id: Optional[str], kind: str, path: Path) -> Row:
        return self.repo.add_artifact(uuid.uuid4().hex, project_id, owner_id, kind, path.name, path.stat().st_size, sha256_file(path), time.time())

    def available(self, artifact: Optional[Row], deep: bool = False) -> tuple[bool, str]:
        if not artifact:
            return False, "artifact is not recorded"
        path = self.path_for(artifact)
        if not path.is_file():
            return False, "file is missing from storage"
        if path.stat().st_size != artifact["size_bytes"]:
            return False, "file size does not match the recorded artifact"
        if deep and sha256_file(path) != artifact["sha256"]:
            return False, "file checksum does not match the recorded artifact"
        return True, "ok"

    def save_source_image(self, content: bytes, original_name: str) -> Path:
        suffix = Path(original_name or "scan.jpg").suffix.lower()
        suffix = suffix if suffix in {".jpg", ".jpeg", ".png", ".webp", ".heic"} else ".jpg"
        path = self.settings.sources_dir / f"{uuid.uuid4().hex}{suffix}"
        path.write_bytes(content)
        return path

    def delete_files(self, filenames: list[str]) -> None:
        for name in filenames:
            safe = Path(name).name
            for base in (self.settings.models_dir, self.settings.sources_dir):
                (base / safe).unlink(missing_ok=True)

    def _signature(self, filename: str, expires: int) -> str:
        return hmac.new(self.settings.signing_secret, f"{filename}|{expires}".encode(), hashlib.sha256).hexdigest()

    def signed_query(self, filename: str, ttl: Optional[int] = None) -> str:
        expires = int(time.time()) + (ttl or self.settings.signed_url_ttl_seconds)
        return f"exp={expires}&sig={self._signature(filename, expires)}"

    def signature_valid(self, filename: str, expires: Optional[str], signature: Optional[str]) -> bool:
        try:
            expiry = int(expires or "")
        except ValueError:
            return False
        if not signature or expiry < time.time():
            return False
        return hmac.compare_digest(signature, self._signature(filename, expiry))
