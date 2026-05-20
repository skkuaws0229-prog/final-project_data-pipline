from __future__ import annotations

from pathlib import Path

from pipeline.utils import cloud_storage


def download_s3_uri(s3_uri: str, local_path: str | Path) -> None:
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    cloud_storage.cp(s3_uri, local_path)


def upload_file(local_path: str | Path, s3_uri: str) -> None:
    cloud_storage.cp(local_path, s3_uri)


def download_cloud_uri(uri: str, local_path: str | Path) -> None:
    download_s3_uri(uri, local_path)


def upload_file_to_cloud(local_path: str | Path, uri: str) -> None:
    upload_file(local_path, uri)


def _split_s3(s3_uri: str) -> tuple[str, str]:
    if not s3_uri.startswith("s3://"):
        raise ValueError(f"Not an S3 URI: {s3_uri}")
    rest = s3_uri[5:]
    bucket, _, key = rest.partition("/")
    return bucket, key
