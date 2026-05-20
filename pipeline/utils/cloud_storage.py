from __future__ import annotations

import subprocess
from pathlib import Path


CLOUD_URI_SCHEMES = ("s3://", "gs://")


def is_cloud_uri(uri: str) -> bool:
    return uri.startswith(CLOUD_URI_SCHEMES)


def is_s3_uri(uri: str) -> bool:
    return uri.startswith("s3://")


def is_gcs_uri(uri: str) -> bool:
    return uri.startswith("gs://")


def require_cloud_uri(uri: str) -> None:
    if not is_cloud_uri(uri):
        raise ValueError(f"Expected s3:// or gs:// URI, got {uri}")


def cp(source: str | Path, destination: str | Path) -> None:
    src = str(source)
    dst = str(destination)
    cmd = _cp_command(src, dst)
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def sync(source: str | Path, destination: str | Path) -> None:
    src = _with_trailing_slash(str(source))
    dst = str(destination)
    cmd = _sync_command(src, dst)
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def object_exists(uri: str) -> bool:
    require_cloud_uri(uri)
    cmd = ["aws", "s3", "ls", uri] if is_s3_uri(uri) else ["gcloud", "storage", "ls", uri]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.returncode == 0 and bool(result.stdout.strip())


def list_objects(uri: str, suffixes: tuple[str, ...] | None = None, limit: int | None = None) -> list[str]:
    require_cloud_uri(uri)
    cmd = _recursive_ls_command(uri)
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        return []

    objects: list[str] = []
    for line in result.stdout.splitlines():
        key = _parse_ls_key(line, uri)
        if not key or (suffixes and not key.endswith(suffixes)):
            continue
        objects.append(key)
        if limit and len(objects) >= limit:
            break
    return objects


def object_count(uri: str, suffixes: tuple[str, ...] | None = None, limit: int | None = None) -> int:
    return len(list_objects(uri, suffixes=suffixes, limit=limit))


def _cp_command(source: str, destination: str) -> list[str]:
    if is_s3_uri(source) or is_s3_uri(destination):
        return ["aws", "s3", "cp", source, destination]
    if is_gcs_uri(source) or is_gcs_uri(destination):
        return ["gcloud", "storage", "cp", source, destination]
    raise ValueError(f"At least one cp endpoint must be cloud storage: {source} -> {destination}")


def _sync_command(source: str, destination: str) -> list[str]:
    if is_s3_uri(source) or is_s3_uri(destination):
        return ["aws", "s3", "sync", source, destination]
    if is_gcs_uri(source) or is_gcs_uri(destination):
        return ["gcloud", "storage", "rsync", "-r", source, destination]
    raise ValueError(f"At least one sync endpoint must be cloud storage: {source} -> {destination}")


def _recursive_ls_command(uri: str) -> list[str]:
    root = _with_trailing_slash(uri)
    if is_s3_uri(uri):
        return ["aws", "s3", "ls", root, "--recursive"]
    return ["gcloud", "storage", "ls", "-r", root]


def _parse_ls_key(line: str, root_uri: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""
    if is_s3_uri(root_uri):
        parts = stripped.split()
        return parts[-1] if parts else ""
    if stripped.startswith("gs://"):
        if stripped.endswith("/"):
            return ""
        root = _with_trailing_slash(root_uri)
        return stripped[len(root):] if stripped.startswith(root) else stripped
    return ""


def _with_trailing_slash(uri: str) -> str:
    return uri if uri.endswith("/") else uri + "/"
