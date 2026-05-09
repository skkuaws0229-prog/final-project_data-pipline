from __future__ import annotations

from pathlib import Path


def download_s3_uri(s3_uri: str, local_path: str | Path) -> None:
    import boto3

    bucket, key = _split_s3(s3_uri)
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    boto3.client("s3").download_file(bucket, key, str(local_path))


def upload_file(local_path: str | Path, s3_uri: str) -> None:
    import boto3

    bucket, key = _split_s3(s3_uri)
    boto3.client("s3").upload_file(str(local_path), bucket, key)


def _split_s3(s3_uri: str) -> tuple[str, str]:
    if not s3_uri.startswith("s3://"):
        raise ValueError(f"Not an S3 URI: {s3_uri}")
    rest = s3_uri[5:]
    bucket, _, key = rest.partition("/")
    return bucket, key

