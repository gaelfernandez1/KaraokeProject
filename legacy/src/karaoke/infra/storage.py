from __future__ import annotations

import shutil
from pathlib import Path
from typing import Protocol

from karaoke.config import Settings


class Storage(Protocol):
    def upload(self, local_path: Path, key: str) -> str:
        """Upload file and return the storage key."""
        ...

    def get_signed_url(self, key: str, expires_in: int = 3600) -> str: ...

    def delete(self, key: str) -> None: ...

    def exists(self, key: str) -> bool: ...


class LocalStorage:
    def __init__(self, output_dir: Path = Path("./output")) -> None:
        self._output_dir = output_dir

    def _resolve(self, key: str) -> Path:
        # Use only the basename so keys with path prefixes (e.g. "karaoke/t/f.mp4")
        # still resolve to the flat output directory, matching today's behavior.
        return self._output_dir / Path(key).name

    def upload(self, local_path: Path, key: str) -> str:
        dest = self._resolve(key)
        if dest.resolve() != local_path.resolve():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(local_path), str(dest))
        return key

    def get_signed_url(self, key: str, expires_in: int = 3600) -> str:
        return f"/serve_video/{Path(key).name}"

    def delete(self, key: str) -> None:
        self._resolve(key).unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        return self._resolve(key).exists()


class R2Storage:
    def __init__(
        self,
        account_id: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
    ) -> None:
        # boto3 ships in the core deps, so it's present in every image. The import
        # stays lazy only to avoid paying for it when the local backend is used.
        import boto3

        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )

    def upload(self, local_path: Path, key: str) -> str:
        self._client.upload_file(str(local_path), self._bucket, key)
        return key

    def get_signed_url(self, key: str, expires_in: int = 3600) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError:
            return False


def validate_r2_settings(settings: Settings) -> None:
    """Raise if the R2 backend is selected but any credential is missing."""
    missing = [
        name
        for name in ("r2_account_id", "r2_bucket", "r2_access_key_id", "r2_secret_access_key")
        if not getattr(settings, name)
    ]
    if missing:
        raise RuntimeError(f"storage_backend=r2 requires: {', '.join(missing)}")


def get_storage(settings: Settings) -> Storage:
    if settings.storage_backend == "r2":
        validate_r2_settings(settings)
        return R2Storage(
            account_id=settings.r2_account_id,  # type: ignore[arg-type]
            bucket=settings.r2_bucket,  # type: ignore[arg-type]
            access_key_id=settings.r2_access_key_id,  # type: ignore[arg-type]
            secret_access_key=settings.r2_secret_access_key,  # type: ignore[arg-type]
        )
    return LocalStorage()


def derive_key(base_key: str, filename: str) -> str:
    """Build the storage key for a sibling artifact sharing base_key's task prefix.

    All artifacts of a song live under ``karaoke/{task_id}/``, so given the song's
    stored key we can locate any of its files by swapping the trailing filename.
    """
    prefix, sep, _ = base_key.rpartition("/")
    return f"{prefix}/{filename}" if sep else filename
