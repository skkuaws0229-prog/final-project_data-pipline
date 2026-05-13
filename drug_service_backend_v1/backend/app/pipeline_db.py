from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.config import settings


DISEASE_NAME_TO_SLUG = {
    "난소암": "ov",
    "유방암": "brca",
    "폐암": "luad",
    "간암": "lihc",
    "대장암": "coad",
    "위암": "stad",
    "췌장암": "pdac",
    "두경부암": "hnsc",
    "특발성 폐섬유증": "ipf",
    "폐동맥고혈압": "pah",
    "건선": "psoriasis",
    "류마티스 관절염": "ra",
}

VALID_PIPELINE_MODES = {"basic", "image_modal", "full"}
VALID_EXECUTION_BACKENDS = {"mock", "local_agent", "aws_stepfunctions"}
VALID_RUN_STATUSES = {"queued", "preflight", "running", "waiting_external_job", "validating", "completed", "failed", "cancelled", "blocked"}


PIPELINE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
  run_id TEXT PRIMARY KEY,
  disease_name TEXT NOT NULL,
  disease_slug TEXT NOT NULL,
  mode TEXT NOT NULL CHECK (mode IN ('basic', 'image_modal', 'full')),
  execution_backend TEXT NOT NULL CHECK (execution_backend IN ('local_agent', 'aws_stepfunctions', 'mock')),
  status TEXT NOT NULL CHECK (status IN ('queued', 'preflight', 'running', 'waiting_external_job', 'validating', 'completed', 'failed', 'cancelled', 'blocked')),
  current_step TEXT,
  requested_by TEXT,
  s3_output_prefix TEXT,
  config_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
  random_seed INTEGER,
  verdict TEXT,
  error_message TEXT,
  estimated_cost_usd NUMERIC,
  estimated_time_minutes INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_disease_status ON pipeline_runs(disease_slug, status);
CREATE TABLE IF NOT EXISTS pipeline_run_events (
  event_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
  level TEXT NOT NULL CHECK (level IN ('info', 'warning', 'error', 'debug')),
  step TEXT,
  message TEXT NOT NULL,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_pipeline_run_events_run_time ON pipeline_run_events(run_id, timestamp);
CREATE TABLE IF NOT EXISTS pipeline_artifacts (
  artifact_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
  artifact_type TEXT NOT NULL CHECK (artifact_type IN ('report', 'csv', 'json', 'plot', 'model_summary', 's3_prefix', 'log', 'validation')),
  step TEXT,
  name TEXT NOT NULL,
  uri TEXT NOT NULL,
  size_bytes BIGINT,
  checksum TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_pipeline_artifacts_run ON pipeline_artifacts(run_id);
CREATE TABLE IF NOT EXISTS pipeline_configs (
  config_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
  disease_name TEXT NOT NULL,
  disease_slug TEXT NOT NULL,
  config_yaml TEXT NOT NULL,
  config_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_pipeline_configs_run ON pipeline_configs(run_id);
"""


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def ensure_pipeline_schema() -> None:
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(PIPELINE_SCHEMA_SQL)
        conn.commit()


def normalize_pipeline_request(disease_name: str, mode: str, execution_backend: str) -> tuple[str, str, str]:
    disease_name = disease_name.strip()
    disease_slug = DISEASE_NAME_TO_SLUG.get(disease_name)
    if not disease_slug:
        raise ValueError(f"Unsupported disease_name: {disease_name}")
    if mode not in VALID_PIPELINE_MODES:
        raise ValueError(f"Unsupported mode: {mode}")
    if execution_backend not in VALID_EXECUTION_BACKENDS:
        raise ValueError(f"Unsupported execution_backend: {execution_backend}")
    return disease_name, disease_slug, mode


def make_config_yaml(disease_name: str, disease_slug: str, mode: str, execution_backend: str, random_seed: int) -> str:
    return "\n".join(
        [
            f"disease_name: {disease_name}",
            f"disease_slug: {disease_slug}",
            f"mode: {mode}",
            f"execution_backend: {execution_backend}",
            f"random_seed: {random_seed}",
            "secret_policy: store_secret_ids_only",
            "",
        ]
    )


def row_to_dict(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def insert_pipeline_run(
    disease_name: str,
    disease_slug: str,
    mode: str,
    execution_backend: str,
    requested_by: str | None,
    config_snapshot: dict[str, Any],
    random_seed: int,
) -> dict[str, Any]:
    ensure_pipeline_schema()
    run_id = new_id("run")
    now = utc_now()
    s3_output_prefix = f"{settings.pipeline_default_s3_prefix.rstrip('/')}/{disease_slug}/"
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pipeline_runs (
                  run_id, disease_name, disease_slug, mode, execution_backend, status,
                  current_step, requested_by, s3_output_prefix, config_snapshot, random_seed,
                  created_at, updated_at
                )
                VALUES (
                  %(run_id)s, %(disease_name)s, %(disease_slug)s, %(mode)s, %(execution_backend)s, 'queued',
                  'queued', %(requested_by)s, %(s3_output_prefix)s, %(config_snapshot)s, %(random_seed)s,
                  %(now)s, %(now)s
                )
                RETURNING *
                """,
                {
                    "run_id": run_id,
                    "disease_name": disease_name,
                    "disease_slug": disease_slug,
                    "mode": mode,
                    "execution_backend": execution_backend,
                    "requested_by": requested_by,
                    "s3_output_prefix": s3_output_prefix,
                    "config_snapshot": json.dumps(config_snapshot),
                    "random_seed": random_seed,
                    "now": now,
                },
            )
            run = cur.fetchone()
        conn.commit()
    return row_to_dict(run) or {}


def insert_pipeline_event(run_id: str, level: str, step: str, message: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    ensure_pipeline_schema()
    event_id = new_id("event")
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pipeline_run_events (event_id, run_id, level, step, message, payload_json)
                VALUES (%(event_id)s, %(run_id)s, %(level)s, %(step)s, %(message)s, %(payload_json)s)
                RETURNING *
                """,
                {
                    "event_id": event_id,
                    "run_id": run_id,
                    "level": level,
                    "step": step,
                    "message": message,
                    "payload_json": json.dumps(payload or {}),
                },
            )
            event = cur.fetchone()
        conn.commit()
    return row_to_dict(event) or {}


def insert_pipeline_artifact(run_id: str, artifact_type: str, step: str, name: str, uri: str) -> dict[str, Any]:
    ensure_pipeline_schema()
    artifact_id = new_id("artifact")
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pipeline_artifacts (artifact_id, run_id, artifact_type, step, name, uri)
                VALUES (%(artifact_id)s, %(run_id)s, %(artifact_type)s, %(step)s, %(name)s, %(uri)s)
                RETURNING *
                """,
                {"artifact_id": artifact_id, "run_id": run_id, "artifact_type": artifact_type, "step": step, "name": name, "uri": uri},
            )
            artifact = cur.fetchone()
        conn.commit()
    return row_to_dict(artifact) or {}


def insert_pipeline_config(run_id: str, disease_name: str, disease_slug: str, config_yaml: str) -> dict[str, Any]:
    ensure_pipeline_schema()
    config_id = new_id("config")
    config_hash = hashlib.sha256(config_yaml.encode("utf-8")).hexdigest()
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pipeline_configs (config_id, run_id, disease_name, disease_slug, config_yaml, config_hash)
                VALUES (%(config_id)s, %(run_id)s, %(disease_name)s, %(disease_slug)s, %(config_yaml)s, %(config_hash)s)
                RETURNING *
                """,
                {
                    "config_id": config_id,
                    "run_id": run_id,
                    "disease_name": disease_name,
                    "disease_slug": disease_slug,
                    "config_yaml": config_yaml,
                    "config_hash": config_hash,
                },
            )
            config = cur.fetchone()
        conn.commit()
    return row_to_dict(config) or {}


def update_pipeline_run(run_id: str, **fields: Any) -> dict[str, Any] | None:
    ensure_pipeline_schema()
    if not fields:
        return get_pipeline_run(run_id)
    fields["updated_at"] = utc_now()
    assignments = ", ".join(f"{key} = %({key})s" for key in fields)
    params = {"run_id": run_id, **fields}
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE pipeline_runs SET {assignments} WHERE run_id = %(run_id)s RETURNING *", params)
            row = cur.fetchone()
        conn.commit()
    return row_to_dict(row)


def get_pipeline_run(run_id: str) -> dict[str, Any] | None:
    ensure_pipeline_schema()
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM pipeline_runs WHERE run_id = %(run_id)s", {"run_id": run_id})
            return row_to_dict(cur.fetchone())


def list_pipeline_runs(
    disease_slug: str | None = None,
    status: str | None = None,
    execution_backend: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    ensure_pipeline_schema()
    filters = []
    params: dict[str, Any] = {"limit": limit}
    if disease_slug:
        filters.append("disease_slug = %(disease_slug)s")
        params["disease_slug"] = disease_slug
    if status:
        filters.append("status = %(status)s")
        params["status"] = status
    if execution_backend:
        filters.append("execution_backend = %(execution_backend)s")
        params["execution_backend"] = execution_backend

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    query = f"""
        SELECT *
        FROM pipeline_runs
        {where_clause}
        ORDER BY created_at DESC, run_id DESC
        LIMIT %(limit)s
    """
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]


def list_pipeline_events(run_id: str) -> list[dict[str, Any]]:
    ensure_pipeline_schema()
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM pipeline_run_events WHERE run_id = %(run_id)s ORDER BY timestamp, event_id", {"run_id": run_id})
            return [dict(row) for row in cur.fetchall()]


def list_pipeline_artifacts(run_id: str) -> list[dict[str, Any]]:
    ensure_pipeline_schema()
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM pipeline_artifacts WHERE run_id = %(run_id)s ORDER BY created_at, artifact_id", {"run_id": run_id})
            return [dict(row) for row in cur.fetchall()]
