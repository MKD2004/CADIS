"""Original uploads, stored by content hash: ``<data_dir>/files/<sha256>``.

Keeping the original lets ingestion be re-run (retries, re-ingest after a
parser change) and makes duplicate uploads cheap: the same bytes are stored
once, however many documents point at them.
"""

import hashlib
import os
import tempfile
from pathlib import Path

from cadis.config import get_settings


def sha256_of(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class FileStore:
    def __init__(self, base_dir: str | Path | None = None):
        self.base = Path(base_dir) if base_dir else get_settings().files_dir
        self.base.mkdir(parents=True, exist_ok=True)

    def path(self, sha: str) -> Path:
        if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
            raise ValueError(f"not a sha256 hex digest: {sha!r}")
        return self.base / sha

    def save(self, content: bytes) -> str:
        """Store the bytes (atomically) and return their sha256."""
        sha = sha256_of(content)
        target = self.path(sha)
        if target.exists():
            return sha
        fd, tmp = tempfile.mkstemp(dir=self.base, prefix=".upload-")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(content)
            os.replace(tmp, target)
        except BaseException:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise
        return sha

    def read(self, sha: str) -> bytes:
        return self.path(sha).read_bytes()

    def exists(self, sha: str) -> bool:
        return self.path(sha).exists()

    def delete(self, sha: str) -> None:
        try:
            self.path(sha).unlink()
        except FileNotFoundError:
            pass
