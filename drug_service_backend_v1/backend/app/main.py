import re
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import settings
from app.db import fetch_all, fetch_one
from app.graph_db import close_driver, run_read, verify_connectivity
from app.kg_embedding_db import get_kg_scores, load_kg_scores
from app.pipeline_db import (
    get_pipeline_run,
    insert_pipeline_config,
    insert_pipeline_event,
    insert_pipeline_run,
    list_pipeline_artifacts,
    list_pipeline_events,
    list_pipeline_runs,
    make_config_yaml,
    normalize_execution_backend,
    normalize_pipeline_request,
    preflight_pipeline_request,
    update_pipeline_run,
    VALID_EXECUTION_BACKENDS,
    VALID_RUN_STATUSES,
)
from app.pipeline_orchestrator import get_orchestrator
from app.search_db import search_text, verify_search_connectivity
from app.structures_db import get_structure_detail, get_structure_file_metadata, list_structure_targets, list_structures, resolve_structure_cache_path
from app.schemas import (
    Disease,
    DrugCandidate,
    DrugDetail,
    ExplanationContextResponse,
    GraphRelationsResponse,
    HealthResponse,
    ImageModalCluster,
    ImageModalEvidence,
    ImageModalReport,
    KgEmbeddingResponse,
    PathScoreResponse,
    PipelineArtifactsResponse,
    PipelineRunCreateRequest,
    PipelineRunEventsResponse,
    PipelineRunPreflightResponse,
    PipelineRunResponse,
    PipelineRunsResponse,
    SearchResponse,
    StructureDetailResponse,
    StructureListResponse,
    StructureTargetsResponse,
)


app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
def shutdown() -> None:
    close_driver()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    row = fetch_one("SELECT 1 AS ok")
    return HealthResponse(status="ok", database="ok" if row and row["ok"] == 1 else "unknown")


@app.get("/health/graph")
def graph_health() -> dict[str, str]:
    try:
        verify_connectivity()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Neo4j unavailable: {exc}") from exc
    return {"status": "ok", "graph": "ok"}


@app.get("/health/search")
def search_health() -> dict[str, str]:
    try:
        verify_search_connectivity()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"OpenSearch unavailable: {exc}") from exc
    return {"status": "ok", "search": "ok"}


@app.get("/health/kg-embedding")
def kg_embedding_health() -> dict[str, str | int]:
    rows = load_kg_scores()
    if not rows:
        raise HTTPException(status_code=503, detail="KG embedding scores unavailable")
    return {"status": "ok", "kg_embedding": "ok", "score_rows": len(rows)}


@app.get("/graph/kg-embedding", response_model=KgEmbeddingResponse)
def graph_kg_embedding(
    disease_id: str = Query(..., description="Disease id, e.g. BRCA, RA, STAD"),
    model: str = Query("ensemble", pattern="^(distmult|transe|ensemble)$"),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    disease = fetch_one("SELECT disease_id FROM diseases WHERE disease_id = %(disease_id)s", {"disease_id": disease_id})
    if not disease:
        raise HTTPException(status_code=404, detail=f"Unknown disease_id: {disease_id}")
    scores = get_kg_scores(disease_id=disease_id, model=model, limit=limit)
    if not scores:
        raise HTTPException(status_code=503, detail="KG embedding scores unavailable")
    return {"disease_id": disease_id, "model": model, "scoring_version": "kg_embedding_v1", "scores": scores}


@app.get("/api/structures/targets", response_model=StructureTargetsResponse)
def get_structure_targets(
    disease_id: str | None = Query(None, description="Optional disease id, e.g. RA, PAH, HNSC"),
    q: str | None = Query(None, min_length=1, description="Optional gene, UniProt, protein, or target text search"),
    limit: int = Query(100, ge=1, le=200),
) -> dict:
    if disease_id:
        disease = fetch_one("SELECT disease_id FROM diseases WHERE disease_id = %(disease_id)s", {"disease_id": disease_id})
        if not disease:
            raise HTTPException(status_code=404, detail=f"Unknown disease_id: {disease_id}")
    return {"targets": list_structure_targets(disease_id=disease_id, q=q, limit=limit)}


@app.get("/api/structures", response_model=StructureListResponse)
def get_structures(
    disease_id: str | None = Query(None, description="Optional disease id, e.g. RA, PAH, HNSC"),
    q: str | None = Query(None, min_length=1, description="Optional gene, UniProt, or protein search"),
    limit: int = Query(100, ge=1, le=200),
) -> dict:
    if disease_id:
        disease = fetch_one("SELECT disease_id FROM diseases WHERE disease_id = %(disease_id)s", {"disease_id": disease_id})
        if not disease:
            raise HTTPException(status_code=404, detail=f"Unknown disease_id: {disease_id}")
    return {"structures": list_structures(disease_id=disease_id, q=q, limit=limit)}


@app.get("/api/structures/{structure_id}", response_model=StructureDetailResponse)
def get_structure(structure_id: str) -> dict:
    detail = get_structure_detail(structure_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Unknown structure_id: {structure_id}")
    return detail


@app.get("/api/structures/{structure_id}/file")
def get_structure_file(structure_id: str) -> FileResponse:
    structure = get_structure_file_metadata(structure_id)
    if not structure:
        raise HTTPException(status_code=404, detail=f"Unknown structure_id: {structure_id}")
    if structure["status"] != "available":
        raise HTTPException(status_code=409, detail=f"Structure file is not available: {structure_id}")

    local_path = resolve_structure_cache_path(structure)
    if not local_path.exists():
        raise HTTPException(status_code=404, detail=f"Structure file is not present in API cache: {structure_id}")

    media_type = "chemical/x-cif" if structure["file_format"] in {"cif", "mmcif"} else "chemical/x-pdb"
    return FileResponse(local_path, media_type=media_type, filename=local_path.name)


def _serialize_pipeline_row(row: dict) -> dict:
    serialized = dict(row)
    for key in ("created_at", "started_at", "ended_at", "updated_at", "timestamp"):
        if serialized.get(key) is not None:
            serialized[key] = serialized[key].isoformat()
    if serialized.get("config_snapshot") is None:
        serialized["config_snapshot"] = {}
    return serialized


@app.post("/api/pipeline-runs", response_model=PipelineRunResponse)
def create_pipeline_run(request: PipelineRunCreateRequest) -> dict:
    try:
        preflight = preflight_pipeline_request(
            request.disease_name,
            request.mode,
            request.execution_backend,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    disease_name = preflight["disease_name"]
    disease_slug = preflight["disease_slug"]
    mode = preflight["mode"]
    execution_backend = preflight["execution_backend"]
    config_snapshot = {
        "disease_name": disease_name,
        "disease_slug": disease_slug,
        "mode": mode,
        "execution_backend": execution_backend,
        "execution_backend_input": preflight["execution_backend_alias"] or request.execution_backend,
        "input_disease_name": request.disease_name,
        "preflight": preflight,
        "random_seed": request.random_seed,
        "user_config": request.config_snapshot,
        "secret_policy": "store_secret_ids_only",
    }
    run = insert_pipeline_run(
        disease_name=disease_name,
        disease_slug=disease_slug,
        mode=mode,
        execution_backend=execution_backend,
        requested_by=request.requested_by,
        config_snapshot=config_snapshot,
        random_seed=request.random_seed,
    )
    config_yaml = make_config_yaml(disease_name, disease_slug, mode, execution_backend, request.random_seed)
    insert_pipeline_config(run["run_id"], disease_name, disease_slug, config_yaml)
    if preflight["preflight_status"] == "needs_registration":
        insert_pipeline_event(
            run["run_id"],
            "warning",
            "preflight",
            "신규 질환은 등록과 입력 데이터 검증이 필요합니다",
            preflight,
        )
        blocked = update_pipeline_run(
            run["run_id"],
            status="blocked",
            current_step="preflight",
            verdict="needs_registration",
            error_message="disease registration and input data verification required",
        )
        return _serialize_pipeline_row(blocked or run)
    run = get_orchestrator(execution_backend).submit_run(run)
    return _serialize_pipeline_row(run)


@app.post("/api/pipeline-runs/preflight", response_model=PipelineRunPreflightResponse)
def preflight_pipeline_run(request: PipelineRunCreateRequest) -> dict:
    try:
        return preflight_pipeline_request(request.disease_name, request.mode, request.execution_backend)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/pipeline-runs", response_model=PipelineRunsResponse)
def list_pipeline_run_statuses(
    disease_slug: str | None = Query(None, description="Optional disease slug, e.g. ra, ov, pah"),
    status: str | None = Query(None, description="Optional run status filter"),
    execution_backend: str | None = Query(None, description="Optional backend: mock, local_agent, aws_stepfunctions"),
    requested_by: str | None = Query(None, description="Optional requester filter, e.g. frontend, chatbot"),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    if status and status not in VALID_RUN_STATUSES:
        raise HTTPException(status_code=400, detail=f"Unsupported status: {status}")
    if execution_backend:
        execution_backend = normalize_execution_backend(execution_backend)
        if execution_backend not in VALID_EXECUTION_BACKENDS:
            raise HTTPException(status_code=400, detail=f"Unsupported execution_backend: {execution_backend}")
    runs = [
        _serialize_pipeline_row(row)
        for row in list_pipeline_runs(
            disease_slug=disease_slug,
            status=status,
            execution_backend=execution_backend,
            requested_by=requested_by,
            limit=limit,
        )
    ]
    return {"runs": runs}


@app.get("/api/pipeline-runs/{run_id}", response_model=PipelineRunResponse)
def get_pipeline_run_status(run_id: str) -> dict:
    run = get_pipeline_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Unknown run_id: {run_id}")
    return _serialize_pipeline_row(run)


@app.get("/api/pipeline-runs/{run_id}/events", response_model=PipelineRunEventsResponse)
def get_pipeline_run_events(run_id: str) -> dict:
    if not get_pipeline_run(run_id):
        raise HTTPException(status_code=404, detail=f"Unknown run_id: {run_id}")
    events = [_serialize_pipeline_row(row) for row in list_pipeline_events(run_id)]
    return {"run_id": run_id, "events": events}


@app.get("/api/pipeline-runs/{run_id}/artifacts", response_model=PipelineArtifactsResponse)
def get_pipeline_run_artifacts(run_id: str) -> dict:
    if not get_pipeline_run(run_id):
        raise HTTPException(status_code=404, detail=f"Unknown run_id: {run_id}")
    artifacts = [_serialize_pipeline_row(row) for row in list_pipeline_artifacts(run_id)]
    return {"run_id": run_id, "artifacts": artifacts}


@app.post("/api/pipeline-runs/{run_id}/cancel", response_model=PipelineRunResponse)
def cancel_pipeline_run(run_id: str) -> dict:
    run = get_pipeline_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Unknown run_id: {run_id}")
    updated = get_orchestrator(run["execution_backend"]).cancel_run(run_id)
    return _serialize_pipeline_row(updated)


@app.post("/api/pipeline-runs/{run_id}/complete", response_model=PipelineRunResponse)
def complete_pipeline_run(run_id: str) -> dict:
    run = get_pipeline_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Unknown run_id: {run_id}")
    if run["execution_backend"] != "mock":
        raise HTTPException(status_code=400, detail="Only mock backend can be manually completed in this phase")
    if run["status"] not in {"running", "validating", "waiting_external_job"}:
        raise HTTPException(status_code=409, detail=f"Run cannot be completed from status: {run['status']}")
    updated = get_orchestrator(run["execution_backend"]).complete_run(run_id)
    return _serialize_pipeline_row(updated)


def _format_search_hits(result: dict) -> list[dict]:
    hits = []
    for hit in result.get("hits", {}).get("hits", []):
        source = hit.get("_source", {})
        highlights = hit.get("highlight", {})
        snippet = None
        for fragments in highlights.values():
            if fragments:
                snippet = fragments[0]
                break
        if snippet is None:
            snippet = source.get("evidence_text") or source.get("report_text") or source.get("clinical_summary") or source.get("title")
        hits.append(
            {
                "id": hit.get("_id"),
                "score": hit.get("_score"),
                "doc_type": source.get("doc_type"),
                "disease_id": source.get("disease_id"),
                "title": source.get("title"),
                "drug_name": source.get("drug_name"),
                "canonical_drug_id": source.get("canonical_drug_id"),
                "cluster_id": source.get("cluster_id"),
                "match_status": source.get("match_status"),
                "candidate_source": source.get("candidate_source"),
                "is_final_candidate": source.get("is_final_candidate"),
                "source_file": source.get("source_file"),
                "snippet": snippet,
                "highlights": highlights,
                "source": source,
            }
        )
    return hits


def _search_context_hits(query: str, disease_id: str, doc_type: str, limit: int) -> dict:
    result = search_text(query, disease_id=disease_id, doc_type=doc_type, limit=limit, fetch_size=min(limit * 10, 100))
    total = result.get("hits", {}).get("total", {})
    raw_total = total.get("value", 0) if isinstance(total, dict) else total
    hits = _format_search_hits(result)
    if doc_type == "candidate_pool":
        hits = _collapse_candidate_pool_search_hits(hits, limit, include_provenance=False)
    return {"total": len(hits) if doc_type == "candidate_pool" else raw_total, "raw_total": raw_total, "hits": hits[:limit]}


def _find_final_candidate_context(disease_id: str, drug_name: str | None, canonical_drug_id: str | None) -> dict | None:
    filters = ["c.disease_id = %(disease_id)s"]
    params: dict[str, Any] = {"disease_id": disease_id}
    if canonical_drug_id:
        filters.append("COALESCE(da.canonical_drug_id, c.drug_id) = %(canonical_drug_id)s")
        params["canonical_drug_id"] = canonical_drug_id
    if drug_name:
        filters.append("LOWER(d.drug_name) = LOWER(%(drug_name)s)")
        params["drug_name"] = drug_name
    if len(filters) == 1:
        return None
    return fetch_one(
        f"""
        SELECT
          c.candidate_id,
          c.disease_id,
          c.drug_id,
          COALESCE(da.canonical_drug_id, c.drug_id) AS canonical_drug_id,
          d.drug_name,
          c.rank,
          c.tier,
          c.score,
          c.target,
          c.target_pathway,
          c.evidence_summary,
          d.canonical_smiles,
          a.safety_score,
          a.verdict,
          a.admet_status,
          a.hard_fail,
          a.hard_fail_reasons,
          a.soft_flags,
          c.source_file,
          true AS is_final_candidate,
          'final_candidate' AS candidate_source
        FROM drug_candidates c
        JOIN drugs d ON d.drug_id = c.drug_id
        LEFT JOIN drug_aliases da ON da.source_drug_id = d.drug_id
        LEFT JOIN admet_results a ON a.candidate_id = c.candidate_id
        WHERE {' AND '.join(filters)}
        ORDER BY c.rank NULLS LAST, c.candidate_id
        LIMIT 1
        """,
        params,
    )


def _find_candidate_pool_context(disease_id: str, drug_name: str | None, canonical_drug_id: str | None) -> dict | None:
    filters = ["disease_id = %(disease_id)s"]
    params: dict[str, Any] = {"disease_id": disease_id}
    lookup_filters = []
    if canonical_drug_id:
        lookup_filters.append("canonical_drug_id = %(canonical_drug_id)s")
        params["canonical_drug_id"] = canonical_drug_id
    if drug_name:
        lookup_filters.append("LOWER(drug_name) = LOWER(%(drug_name)s)")
        params["drug_name"] = drug_name
    if not lookup_filters:
        return None
    filters.append(f"({' OR '.join(lookup_filters)})")
    rows = fetch_all(
        f"""
        SELECT
          candidate_id,
          disease_id,
          drug_id,
          canonical_drug_id,
          drug_name,
          rank,
          tier,
          score,
          target,
          target_pathway,
          evidence_summary,
          canonical_smiles,
          source_file,
          source_row_number,
          is_final_candidate
        FROM candidate_pool
        WHERE {' AND '.join(filters)}
        ORDER BY rank NULLS LAST, candidate_id
        """,
        params,
    )
    if not rows:
        return None
    representative = dict(rows[0])
    source_files = sorted({row["source_file"] for row in rows if row.get("source_file")})
    return {
        **representative,
        "provenance_count": len(rows),
        "provenance_note": f"원천 candidate_pool row {len(rows)}개에서 집계됨",
        "source_files": source_files,
        "provenance_ids": [row["candidate_id"] for row in rows],
        "provenance_rows": [dict(row) for row in rows[:20]],
    }


def _find_image_evidence_context(disease_id: str, drug_name: str | None, canonical_drug_id: str | None, limit: int = 10) -> list[dict]:
    filters = ["e.disease_id = %(disease_id)s"]
    params: dict[str, Any] = {"disease_id": disease_id, "limit": limit}
    lookup_filters = []
    if canonical_drug_id:
        lookup_filters.append("m.canonical_drug_id = %(canonical_drug_id)s")
        params["canonical_drug_id"] = canonical_drug_id
    if drug_name:
        lookup_filters.append("LOWER(e.drug_name) = LOWER(%(drug_name)s)")
        params["drug_name"] = drug_name
    if not lookup_filters:
        return []
    filters.append(f"({' OR '.join(lookup_filters)})")
    return fetch_all(
        f"""
        SELECT
          e.evidence_id,
          e.disease_id,
          e.cluster_id,
          c.cluster_key,
          c.cluster_label,
          e.drug_id,
          m.canonical_drug_id,
          COALESCE(m.match_status, 'unmatched') AS match_status,
          e.drug_name,
          e.rank,
          e.tier,
          e.target,
          e.target_pathway,
          e.evidence_text,
          e.source_file
        FROM image_modal_drug_evidence e
        LEFT JOIN image_modal_clusters c ON c.cluster_id = e.cluster_id
        LEFT JOIN image_modal_evidence_drug_matches m ON m.evidence_id = e.evidence_id
        WHERE {' AND '.join(filters)}
        ORDER BY e.rank NULLS LAST, e.drug_name, c.cluster_key
        LIMIT %(limit)s
        """,
        params,
    )


def _find_structure_context(disease_id: str, drug_name: str | None, canonical_drug_id: str | None, limit: int = 10) -> dict:
    filters = ["cpsl.disease_id = %(disease_id)s"]
    params: dict[str, Any] = {"disease_id": disease_id, "limit": limit}
    lookup_filters = []
    if canonical_drug_id:
        lookup_filters.append("cpsl.canonical_drug_id = %(canonical_drug_id)s")
        params["canonical_drug_id"] = canonical_drug_id
    if drug_name:
        lookup_filters.extend(
            [
                "LOWER(cd.primary_drug_name) = LOWER(%(drug_name)s)",
                "LOWER(d.drug_name) = LOWER(%(drug_name)s)",
                "LOWER(ime.drug_name) = LOWER(%(drug_name)s)",
            ]
        )
        params["drug_name"] = drug_name
    if not lookup_filters:
        return {
            "available_structures": [],
            "target_genes": [],
            "context_links": [],
            "resolution_method": "candidate_protein_structure_links",
            "context_summary": {"total_links": 0, "structure_count": 0, "available_structure_count": 0, "target_gene_count": 0},
        }
    filters.append(f"({' OR '.join(lookup_filters)})")
    rows = fetch_all(
        f"""
        SELECT
          cpsl.context_id,
          cpsl.disease_id,
          cpsl.candidate_id,
          cpsl.evidence_id,
          cpsl.canonical_drug_id,
          COALESCE(cd.primary_drug_name, d.drug_name, ime.drug_name) AS drug_name,
          cpsl.target_source,
          cpsl.relation_note,
          pt.protein_id,
          pt.gene_symbol,
          pt.uniprot_id,
          pt.protein_name,
          afs.structure_id,
          CASE
            WHEN afs.status = 'available' THEN 'available'
            WHEN afs.status = 'to_fetch' THEN 'pending'
            WHEN afs.status = 'missing' THEN 'missing'
            ELSE 'failed'
          END AS structure_status,
          afs.file_format,
          afs.file_size_bytes,
          afs.mean_plddt
        FROM candidate_protein_structure_links cpsl
        JOIN protein_targets pt ON pt.protein_id = cpsl.protein_id
        LEFT JOIN alphafold_structures afs ON afs.structure_id = cpsl.structure_id
        LEFT JOIN canonical_drugs cd ON cd.canonical_drug_id = cpsl.canonical_drug_id
        LEFT JOIN drug_candidates dc ON dc.candidate_id = cpsl.candidate_id
        LEFT JOIN drugs d ON d.drug_id = dc.drug_id
        LEFT JOIN image_modal_drug_evidence ime ON ime.evidence_id = cpsl.evidence_id
        WHERE {' AND '.join(filters)}
        ORDER BY pt.gene_symbol NULLS LAST, cpsl.target_source, cpsl.context_id
        LIMIT %(limit)s
        """,
        params,
    )
    target_genes = sorted({row["gene_symbol"] for row in rows if row.get("gene_symbol")})
    structures = {}
    for row in rows:
        if not row.get("structure_id"):
            continue
        structures[row["structure_id"]] = {
            "structure_id": row["structure_id"],
            "protein_id": row["protein_id"],
            "gene_symbol": row["gene_symbol"],
            "uniprot_id": row["uniprot_id"],
            "protein_name": row["protein_name"],
            "structure_status": row["structure_status"],
            "file_format": row["file_format"],
            "file_size_bytes": row["file_size_bytes"],
            "mean_plddt": float(row["mean_plddt"]) if row.get("mean_plddt") is not None else None,
            "file_endpoint": f"/api/structures/{row['structure_id']}/file",
        }
    return {
        "available_structures": list(structures.values()),
        "target_genes": target_genes,
        "context_links": [dict(row) for row in rows],
        "resolution_method": "candidate_protein_structure_links",
        "context_summary": {
            "total_links": len(rows),
            "structure_count": len(structures),
            "available_structure_count": sum(1 for item in structures.values() if item["structure_status"] == "available"),
            "target_gene_count": len(target_genes),
        },
    }


def _extract_target_tokens(*texts: str | None) -> list[str]:
    tokens: list[str] = []
    seen = set()
    stopwords = {"AND", "AXIS", "PATHWAY", "SIGNALING", "INFLAMMATORY", "TARGET", "MECHANISM"}
    for text in texts:
        if not text:
            continue
        for token in re.findall(r"[A-Za-z][A-Za-z0-9-]{1,12}", text):
            normalized = token.upper().strip("-")
            if len(normalized) < 3 or normalized in stopwords or normalized in seen:
                continue
            seen.add(normalized)
            tokens.append(normalized)
    return tokens


def _structure_context_from_target_texts(target_texts: list[str], limit: int = 10) -> dict:
    structures: dict[str, dict] = {}
    target_genes = set()
    matched_tokens = []
    for token in target_texts:
        for item in list_structures(q=token, limit=limit):
            matched_tokens.append(token)
            if item.get("gene_symbol"):
                target_genes.add(item["gene_symbol"])
            structures[item["structure_id"]] = item
        if len(structures) >= limit:
            break
    available_structures = list(structures.values())[:limit]
    return {
        "available_structures": available_structures,
        "target_genes": sorted(target_genes),
        "context_links": [],
        "resolution_method": "target_text_fallback",
        "matched_target_tokens": sorted(set(matched_tokens)),
        "context_summary": {
            "total_links": 0,
            "structure_count": len(available_structures),
            "available_structure_count": sum(1 for item in available_structures if item.get("structure_status") == "available"),
            "target_gene_count": len(target_genes),
        },
    }


def _build_retrieval_sources(
    final_candidate: dict | None,
    candidate_pool: dict | None,
    image_evidence: list[dict],
    graph_context: dict,
    structure_context: dict,
) -> list[dict]:
    sources = []
    if final_candidate:
        sources.append(
            {
                "source_type": "final_candidate",
                "source_id": final_candidate.get("candidate_id"),
                "source_file": final_candidate.get("source_file"),
                "evidence_role": "support",
                "summary": f"Final candidate rank {final_candidate.get('rank')}, tier {final_candidate.get('tier')}",
                "provenance_count": 1,
            }
        )
    if candidate_pool:
        sources.append(
            {
                "source_type": "candidate_pool",
                "source_id": candidate_pool.get("candidate_id"),
                "source_file": ", ".join(candidate_pool.get("source_files") or []),
                "evidence_role": "support",
                "summary": candidate_pool.get("provenance_note"),
                "provenance_count": candidate_pool.get("provenance_count"),
            }
        )
    for evidence in image_evidence:
        sources.append(
            {
                "source_type": "image_evidence",
                "source_id": evidence.get("evidence_id"),
                "source_file": evidence.get("source_file"),
                "evidence_role": "support" if evidence.get("match_status") != "evidence_only" else "supporting_evidence_only",
                "summary": evidence.get("evidence_text"),
                "provenance_count": 1,
            }
        )
    for source in graph_context.get("evidence_sources", [])[:10]:
        sources.append(source)
    for source in graph_context.get("risk_sources", [])[:10]:
        sources.append(source)
    for structure in structure_context.get("available_structures", []):
        sources.append(
            {
                "source_type": "structure",
                "source_id": structure.get("structure_id"),
                "source_file": structure.get("file_endpoint"),
                "evidence_role": "structure_reference",
                "summary": f"{structure.get('gene_symbol') or structure.get('uniprot_id')} AlphaFold structure reference",
                "provenance_count": 1,
            }
        )
    return sources


@app.get("/api/explanation-context", response_model=ExplanationContextResponse)
def get_explanation_context(
    disease_id: str = Query(..., description="Disease id, e.g. RA, BRCA"),
    drug_name: str | None = Query(None, min_length=1, description="Optional drug name"),
    canonical_drug_id: str | None = Query(None, min_length=1, description="Optional canonical drug id"),
    include_search: bool = Query(True),
    include_graph: bool = Query(True),
    include_structure: bool = Query(True),
    search_limit: int = Query(10, ge=1, le=50),
) -> dict:
    disease = fetch_one("SELECT disease_id FROM diseases WHERE disease_id = %(disease_id)s", {"disease_id": disease_id})
    if not disease:
        raise HTTPException(status_code=404, detail=f"Unknown disease_id: {disease_id}")
    if not drug_name and not canonical_drug_id:
        raise HTTPException(status_code=400, detail="Either drug_name or canonical_drug_id is required")

    final_candidate = _find_final_candidate_context(disease_id, drug_name, canonical_drug_id)
    resolved_drug_name = drug_name or (final_candidate or {}).get("drug_name")
    resolved_canonical_id = canonical_drug_id or (final_candidate or {}).get("canonical_drug_id")
    candidate_pool = _find_candidate_pool_context(disease_id, resolved_drug_name, resolved_canonical_id)
    if not resolved_drug_name and candidate_pool:
        resolved_drug_name = candidate_pool.get("drug_name")
    if not resolved_canonical_id and candidate_pool:
        resolved_canonical_id = candidate_pool.get("canonical_drug_id")

    image_evidence = _find_image_evidence_context(disease_id, resolved_drug_name, resolved_canonical_id, limit=20)
    admet = None
    if final_candidate:
        admet = {
            "safety_score": final_candidate.get("safety_score"),
            "verdict": final_candidate.get("verdict"),
            "admet_status": final_candidate.get("admet_status"),
            "hard_fail": final_candidate.get("hard_fail"),
            "hard_fail_reasons": final_candidate.get("hard_fail_reasons"),
            "soft_flags": final_candidate.get("soft_flags"),
        }

    search_context = {"candidate_pool_hits": [], "final_candidate_hits": [], "image_evidence_hits": [], "image_report_hits": []}
    if include_search and resolved_drug_name:
        try:
            search_context = {
                "candidate_pool_hits": _search_context_hits(resolved_drug_name, disease_id, "candidate_pool", search_limit),
                "final_candidate_hits": _search_context_hits(resolved_drug_name, disease_id, "drug_candidate", search_limit),
                "image_evidence_hits": _search_context_hits(resolved_drug_name, disease_id, "image_evidence", search_limit),
                "image_report_hits": _search_context_hits(resolved_drug_name, disease_id, "image_report", search_limit),
            }
        except Exception as exc:
            search_context["error"] = f"OpenSearch query failed: {exc}"

    graph_context = {"path_score": None, "positive_score": None, "risk_penalty": None, "components": {}, "evidence_sources": [], "risk_sources": []}
    if include_graph:
        try:
            path_scores = graph_path_score(disease_id=disease_id, limit=200)["scores"]
            for item in path_scores:
                if (resolved_canonical_id and item.get("canonical_drug_id") == resolved_canonical_id) or (
                    resolved_drug_name and (item.get("drug_name") or "").lower() == resolved_drug_name.lower()
                ):
                    graph_context = item
                    break
        except Exception as exc:
            graph_context["error"] = f"Path score query failed: {exc}"

    structure_context = {"available_structures": [], "target_genes": [], "context_summary": {"total_links": 0}}
    if include_structure:
        structure_context = _find_structure_context(disease_id, resolved_drug_name, resolved_canonical_id, limit=50)
        if not structure_context.get("available_structures"):
            target_tokens = _extract_target_tokens(
                (final_candidate or {}).get("target"),
                (final_candidate or {}).get("target_pathway"),
                *[evidence.get("target") for evidence in image_evidence],
                *[evidence.get("target_pathway") for evidence in image_evidence],
            )
            if target_tokens:
                fallback_context = _structure_context_from_target_texts(target_tokens, limit=10)
                if fallback_context.get("available_structures"):
                    structure_context = fallback_context

    retrieval_sources = _build_retrieval_sources(final_candidate, candidate_pool, image_evidence, graph_context, structure_context)
    status = "ready" if retrieval_sources else "no_evidence"
    if search_context.get("error") or graph_context.get("error"):
        status = "partial"
    return {
        "contract_version": "retrieval_context_v1",
        "disease_id": disease_id,
        "drug_name": resolved_drug_name,
        "canonical_drug_id": resolved_canonical_id,
        "query": {
            "disease_id": disease_id,
            "drug_name": drug_name,
            "canonical_drug_id": canonical_drug_id,
            "include_search": include_search,
            "include_graph": include_graph,
            "include_structure": include_structure,
            "search_limit": search_limit,
        },
        "final_candidate": dict(final_candidate) if final_candidate else None,
        "candidate_pool": candidate_pool,
        "admet": admet,
        "search_context": search_context,
        "graph_context": graph_context,
        "structure_context": structure_context,
        "retrieval_sources": retrieval_sources,
        "prompt_guardrails": [
            "Use only the evidence in retrieval_context.",
            "Do not claim clinical efficacy beyond the provided evidence.",
            "Mention risk_sources or ADMET risk when present.",
            "Cite source_file or source_type for key claims.",
            "AlphaFold structure is a target/protein reference, not proof of drug efficacy.",
            "Path score and KG score are internal explanatory scores, not clinical scores.",
        ],
        "status": status,
    }


@app.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1, description="Text query"),
    disease_id: str | None = Query(None, description="Optional disease id filter, e.g. RA"),
    doc_type: str | None = Query(None, description="Optional doc type: candidate_pool, drug_candidate, image_evidence, image_report"),
    limit: int = Query(20, ge=1, le=50),
    include_provenance: bool = Query(False, description="Include collapsed candidate_pool provenance rows"),
) -> dict:
    if disease_id:
        disease = fetch_one("SELECT disease_id FROM diseases WHERE disease_id = %(disease_id)s", {"disease_id": disease_id})
        if not disease:
            raise HTTPException(status_code=404, detail=f"Unknown disease_id: {disease_id}")

    allowed_doc_types = {"candidate_pool", "drug_candidate", "image_evidence", "image_report"}
    if doc_type and doc_type not in allowed_doc_types:
        raise HTTPException(status_code=400, detail=f"Unknown doc_type: {doc_type}")

    should_collapse_candidate_pool = doc_type == "candidate_pool" and not include_provenance
    fetch_size = min(limit * 10, 500) if should_collapse_candidate_pool else limit
    try:
        result = search_text(q, disease_id=disease_id, doc_type=doc_type, limit=limit, fetch_size=fetch_size)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"OpenSearch query failed: {exc}") from exc

    raw_hits = []
    for hit in result.get("hits", {}).get("hits", []):
        source = hit.get("_source", {})
        highlights = hit.get("highlight", {})
        snippet = None
        for fragments in highlights.values():
            if fragments:
                snippet = fragments[0]
                break
        if snippet is None:
            snippet = source.get("evidence_text") or source.get("report_text") or source.get("clinical_summary") or source.get("title")
        raw_hits.append(
            {
                "id": hit.get("_id"),
                "score": hit.get("_score"),
                "doc_type": source.get("doc_type"),
                "disease_id": source.get("disease_id"),
                "title": source.get("title"),
                "drug_name": source.get("drug_name"),
                "canonical_drug_id": source.get("canonical_drug_id"),
                "cluster_id": source.get("cluster_id"),
                "match_status": source.get("match_status"),
                "candidate_source": source.get("candidate_source"),
                "is_final_candidate": source.get("is_final_candidate"),
                "source_file": source.get("source_file"),
                "snippet": snippet,
                "highlights": highlights,
                "source": source,
            }
        )

    hits = _collapse_candidate_pool_search_hits(raw_hits, limit, include_provenance) if should_collapse_candidate_pool else raw_hits
    total = result.get("hits", {}).get("total", {})
    raw_total = total.get("value", 0) if isinstance(total, dict) else total
    total_value = len(hits) if should_collapse_candidate_pool else raw_total
    return {"query": q, "total": total_value, "raw_total": raw_total, "hits": hits}


def _collapse_candidate_pool_search_hits(raw_hits: list[dict], limit: int, include_provenance: bool = False) -> list[dict]:
    grouped: dict[tuple[str, str], dict] = {}
    for hit in raw_hits:
        disease = (hit.get("disease_id") or "").strip()
        drug_name = (hit.get("drug_name") or "").strip()
        key = (disease.lower(), drug_name.lower())
        if key not in grouped:
            grouped[key] = {**hit, "_provenance_hits": []}
        group = grouped[key]
        group["_provenance_hits"].append(hit)
        if (hit.get("score") or 0) > (group.get("score") or 0):
            for field in ["id", "score", "title", "canonical_drug_id", "source_file", "snippet", "highlights", "source"]:
                group[field] = hit.get(field)
        if hit.get("is_final_candidate"):
            group["is_final_candidate"] = True

    collapsed = []
    for group in grouped.values():
        provenance_hits = group.pop("_provenance_hits")
        provenance_ids = [hit["id"] for hit in provenance_hits if hit.get("id")]
        source_files = sorted({hit["source_file"] for hit in provenance_hits if hit.get("source_file")})
        group["provenance_count"] = len(provenance_hits)
        group["provenance_ids"] = provenance_ids
        group["provenance_source_files"] = source_files
        group["provenance_note"] = (
            f"원천 candidate_pool row {len(provenance_hits)}개에서 집계됨"
            if len(provenance_hits) > 1
            else "원천 candidate_pool row 1개에서 집계됨"
        )
        group["provenance_hits"] = provenance_hits if include_provenance else []
        collapsed.append(group)

    collapsed.sort(key=lambda item: (-(item.get("score") or 0), item.get("drug_name") or ""))
    return collapsed[:limit]


def _put_node(nodes: dict[str, dict], node_id: str | None, label: str, name: str | None, properties: dict | None = None) -> None:
    if not node_id:
        return
    if node_id not in nodes:
        nodes[node_id] = {"id": node_id, "label": label, "name": name or node_id, "properties": properties or {}}
        return
    nodes[node_id]["properties"].update(properties or {})


def _put_edge(edges: dict[str, dict], edge_id: str, source: str | None, target: str | None, edge_type: str, properties: dict | None = None) -> None:
    if not source or not target:
        return
    edges[edge_id] = {
        "id": edge_id,
        "source": source,
        "target": target,
        "type": edge_type,
        "properties": properties or {},
    }


def _to_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _truthy(value) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _is_pass_text(value) -> bool:
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"pass", "pass_admet_gate", "ok"} or text.startswith("pass")


def _round_score(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


@app.get("/graph/path-score", response_model=PathScoreResponse)
def graph_path_score(
    disease_id: str = Query(..., description="Disease id, e.g. BRCA, RA, STAD"),
    limit: int = Query(100, ge=1, le=200),
) -> dict:
    disease_rows = run_read(
        """
        MATCH (d:Disease {disease_id: $disease_id})
        RETURN d.disease_id AS disease_id
        """,
        {"disease_id": disease_id},
    )
    if not disease_rows:
        raise HTTPException(status_code=404, detail=f"Unknown disease_id: {disease_id}")

    rows = run_read(
        """
        MATCH (drug:Drug)-[candidate:CANDIDATE_FOR]->(disease:Disease {disease_id: $disease_id})
        OPTIONAL MATCH (drug)-[candidate_target_rel:HAS_TARGET {disease_id: $disease_id}]->(candidate_target:TargetConcept)
        WITH drug, candidate, collect(DISTINCT {
          target_id: candidate_target.target_id,
          concept_text: candidate_target.concept_text,
          concept_type: candidate_target.concept_type,
          relation_kind: candidate_target_rel.relation_kind,
          source_id: candidate_target_rel.source_id
        }) AS candidate_targets
        OPTIONAL MATCH (disease:Disease {disease_id: $disease_id})-[:HAS_IMAGE_CLUSTER]->(cluster:ImageCluster)-[:HAS_IMAGE_EVIDENCE]->(evidence:ImageEvidence)-[support:SUPPORTS_DRUG]->(drug)
        OPTIONAL MATCH (evidence)-[evidence_target_rel:MENTIONS_TARGET {disease_id: $disease_id}]->(evidence_target:TargetConcept)
        RETURN
          drug.canonical_drug_id AS canonical_drug_id,
          drug.primary_drug_name AS drug_name,
          candidate.candidate_id AS candidate_id,
          candidate.rank AS rank,
          candidate.tier AS tier,
          candidate.score AS candidate_score,
          candidate.evidence_summary AS candidate_evidence_summary,
          candidate.safety_score AS safety_score,
          candidate.verdict AS verdict,
          candidate.admet_status AS admet_status,
          candidate.hard_fail AS hard_fail,
          candidate.hard_fail_reasons AS hard_fail_reasons,
          candidate.soft_flags AS soft_flags,
          candidate.source_file AS candidate_source_file,
          candidate_targets AS candidate_targets,
          collect(DISTINCT {
            evidence_id: evidence.evidence_id,
            cluster_id: cluster.cluster_id,
            cluster_key: cluster.cluster_key,
            cluster_label: cluster.cluster_label,
            evidence_text: evidence.evidence_text,
            rank: evidence.rank,
            tier: evidence.tier,
            match_status: support.match_status,
            source_file: evidence.source_file
          }) AS image_evidence,
          collect(DISTINCT {
            evidence_id: evidence.evidence_id,
            target_id: evidence_target.target_id,
            concept_text: evidence_target.concept_text,
            concept_type: evidence_target.concept_type,
            relation_kind: evidence_target_rel.relation_kind,
            source_id: evidence_target_rel.source_id
        }) AS evidence_targets
        ORDER BY candidate.rank IS NULL, candidate.rank, drug.primary_drug_name
        """,
        {"disease_id": disease_id},
    )

    max_rank_rows = run_read(
        """
        MATCH (:Drug)-[candidate:CANDIDATE_FOR]->(:Disease {disease_id: $disease_id})
        WHERE candidate.rank IS NOT NULL
        RETURN max(toInteger(candidate.rank)) AS max_rank
        """,
        {"disease_id": disease_id},
    )
    max_rank = _to_int(max_rank_rows[0]["max_rank"]) if max_rank_rows else None
    if max_rank is None or max_rank < 1:
        max_rank = 1
    score_items = []

    for row in rows:
        rank = _to_int(row["rank"])
        candidate_targets = [target for target in row["candidate_targets"] if target.get("target_id")]
        image_evidence = [evidence for evidence in row["image_evidence"] if evidence.get("evidence_id")]
        evidence_targets = [target for target in row["evidence_targets"] if target.get("target_id")]

        rank_component = 0.0
        if rank is not None:
            rank_component = 1.0 if max_rank <= 1 else max(0.0, 1.0 - ((rank - 1) / max(max_rank - 1, 1)))

        hard_fail = _truthy(row["hard_fail"])
        verdict_pass = _is_pass_text(row["verdict"]) or _is_pass_text(row["admet_status"])
        safety_score = _to_float(row["safety_score"])
        safety_component = 0.0
        if verdict_pass and not hard_fail:
            safety_component = 1.0
        elif safety_score is not None and not hard_fail:
            safety_component = min(max(safety_score / 10.0, 0.0), 1.0)

        evidence_component = min(len(image_evidence) / 3.0, 1.0)

        candidate_target_ids = {target["target_id"] for target in candidate_targets}
        evidence_target_ids = {target["target_id"] for target in evidence_targets}
        target_overlap_count = len(candidate_target_ids & evidence_target_ids)
        target_overlap_component = 0.0
        if candidate_target_ids:
            target_overlap_component = target_overlap_count / len(candidate_target_ids)

        components = {
            "candidate_rank": round(rank_component * 0.30, 4),
            "admet": round(safety_component * 0.20, 4),
            "image_evidence": round(evidence_component * 0.25, 4),
            "target_overlap": round(target_overlap_component * 0.15, 4),
        }
        positive_score = sum(components.values())

        risk_penalty = 0.0
        risk_sources = []
        if hard_fail:
            risk_penalty += 0.25
            risk_sources.append(
                {
                    "source_type": "admet",
                    "source_id": row["candidate_id"],
                    "source_file": row["candidate_source_file"],
                    "evidence_role": "risk",
                    "summary": row["hard_fail_reasons"] or "ADMET hard_fail is set",
                    "properties": {"hard_fail": row["hard_fail"], "hard_fail_reasons": row["hard_fail_reasons"]},
                }
            )
        if not verdict_pass:
            risk_penalty += 0.10
            risk_sources.append(
                {
                    "source_type": "admet",
                    "source_id": row["candidate_id"],
                    "source_file": row["candidate_source_file"],
                    "evidence_role": "risk",
                    "summary": f"ADMET verdict/status is not pass: {row['verdict'] or row['admet_status']}",
                    "properties": {"verdict": row["verdict"], "admet_status": row["admet_status"]},
                }
            )
        if row["soft_flags"]:
            risk_penalty += 0.05
            risk_sources.append(
                {
                    "source_type": "admet",
                    "source_id": row["candidate_id"],
                    "source_file": row["candidate_source_file"],
                    "evidence_role": "risk",
                    "summary": row["soft_flags"],
                    "properties": {"soft_flags": row["soft_flags"]},
                }
            )

        evidence_sources = [
            {
                "source_type": "drug_candidate",
                "source_id": row["candidate_id"],
                "source_file": row["candidate_source_file"],
                "evidence_role": "support",
                "summary": row["candidate_evidence_summary"] or f"Candidate rank {rank}, tier {row['tier']}",
                "properties": {
                    "rank": rank,
                    "tier": row["tier"],
                    "score": row["candidate_score"],
                    "verdict": row["verdict"],
                    "admet_status": row["admet_status"],
                },
            }
        ]
        for evidence in image_evidence[:10]:
            evidence_sources.append(
                {
                    "source_type": "image_modal_evidence",
                    "source_id": evidence["evidence_id"],
                    "source_file": evidence["source_file"],
                    "evidence_role": "support",
                    "summary": evidence["evidence_text"],
                    "properties": {
                        "cluster_id": evidence["cluster_id"],
                        "cluster_key": evidence["cluster_key"],
                        "cluster_label": evidence["cluster_label"],
                        "rank": evidence["rank"],
                        "tier": evidence["tier"],
                        "match_status": evidence["match_status"],
                    },
                }
            )
        if target_overlap_count:
            evidence_sources.append(
                {
                    "source_type": "target_overlap",
                    "source_id": row["candidate_id"],
                    "source_file": row["candidate_source_file"],
                    "evidence_role": "support",
                    "summary": f"{target_overlap_count} candidate target/pathway concept(s) overlap with image-modal evidence targets.",
                    "properties": {
                        "overlap_target_ids": sorted(candidate_target_ids & evidence_target_ids),
                        "candidate_target_count": len(candidate_target_ids),
                        "evidence_target_count": len(evidence_target_ids),
                    },
                }
            )

        path_score = _round_score(positive_score - risk_penalty)
        score_items.append(
            {
                "canonical_drug_id": row["canonical_drug_id"],
                "drug_name": row["drug_name"],
                "rank": rank,
                "tier": row["tier"],
                "path_score": path_score,
                "positive_score": _round_score(positive_score),
                "risk_penalty": _round_score(risk_penalty),
                "components": components,
                "evidence_sources": evidence_sources,
                "risk_sources": risk_sources,
            }
        )

    score_items.sort(key=lambda item: (-item["path_score"], item["rank"] if item["rank"] is not None else 9999, item["drug_name"]))
    deduped_score_items = []
    seen_drug_ids = set()
    for item in score_items:
        if item["canonical_drug_id"] in seen_drug_ids:
            continue
        seen_drug_ids.add(item["canonical_drug_id"])
        deduped_score_items.append(item)
    return {"disease_id": disease_id, "scoring_version": "path_scoring_v1", "scores": deduped_score_items[:limit]}


@app.get("/graph/relations", response_model=GraphRelationsResponse)
def graph_relations(
    disease_id: str = Query(..., description="Disease id, e.g. BRCA, RA, STAD"),
    limit: int = Query(50, ge=1, le=200, description="Maximum candidate drugs to include"),
    include_evidence: bool = Query(True),
    include_targets: bool = Query(True),
) -> dict:
    disease_rows = run_read(
        """
        MATCH (d:Disease {disease_id: $disease_id})
        RETURN d.disease_id AS disease_id, d.display_name AS display_name
        """,
        {"disease_id": disease_id},
    )
    if not disease_rows:
        raise HTTPException(status_code=404, detail=f"Unknown disease_id: {disease_id}")

    nodes: dict[str, dict] = {}
    edges: dict[str, dict] = {}
    disease = disease_rows[0]
    _put_node(nodes, disease["disease_id"], "Disease", disease["display_name"], {"disease_id": disease["disease_id"]})

    candidate_rows = run_read(
        """
        MATCH (drug:Drug)-[r:CANDIDATE_FOR]->(disease:Disease {disease_id: $disease_id})
        RETURN
          drug.canonical_drug_id AS drug_id,
          drug.primary_drug_name AS drug_name,
          drug.drug_source_status AS drug_source_status,
          r.candidate_id AS candidate_id,
          r.rank AS rank,
          r.tier AS tier,
          r.score AS score,
          r.safety_score AS safety_score,
          r.verdict AS verdict,
          r.admet_status AS admet_status,
          r.hard_fail AS hard_fail
        ORDER BY r.rank IS NULL, r.rank, drug.primary_drug_name
        """,
        {"disease_id": disease_id},
    )

    seen_candidate_drug_ids = set()
    for row in candidate_rows:
        if row["drug_id"] in seen_candidate_drug_ids:
            continue
        seen_candidate_drug_ids.add(row["drug_id"])
        _put_node(
            nodes,
            row["drug_id"],
            "Drug",
            row["drug_name"],
            {
                "canonical_drug_id": row["drug_id"],
                "drug_source_status": row["drug_source_status"],
                "rank": row["rank"],
                "tier": row["tier"],
                "verdict": row["verdict"],
            },
        )
        _put_edge(
            edges,
            f"CANDIDATE_FOR:{row['candidate_id']}",
            row["drug_id"],
            disease_id,
            "CANDIDATE_FOR",
            {
                "candidate_id": row["candidate_id"],
                "rank": row["rank"],
                "tier": row["tier"],
                "score": row["score"],
                "safety_score": row["safety_score"],
                "verdict": row["verdict"],
                "admet_status": row["admet_status"],
                "hard_fail": row["hard_fail"],
            },
        )
        if len(seen_candidate_drug_ids) >= limit:
            break

    if include_evidence:
        cluster_rows = run_read(
            """
            MATCH (disease:Disease {disease_id: $disease_id})-[:HAS_IMAGE_CLUSTER]->(cluster:ImageCluster)
            RETURN
              cluster.cluster_id AS cluster_id,
              coalesce(cluster.cluster_label, cluster.cluster_key) AS cluster_name,
              cluster.cluster_key AS cluster_key
            ORDER BY cluster.cluster_key
            """,
            {"disease_id": disease_id},
        )

        for row in cluster_rows:
            _put_node(
                nodes,
                row["cluster_id"],
                "ImageCluster",
                row["cluster_name"],
                {"cluster_key": row["cluster_key"], "disease_id": disease_id},
            )
            _put_edge(
                edges,
                f"HAS_IMAGE_CLUSTER:{disease_id}:{row['cluster_id']}",
                disease_id,
                row["cluster_id"],
                "HAS_IMAGE_CLUSTER",
                {"disease_id": disease_id},
            )

        evidence_rows = run_read(
            """
            MATCH (disease:Disease {disease_id: $disease_id})-[:HAS_IMAGE_CLUSTER]->(cluster:ImageCluster)
            MATCH (cluster)-[:HAS_IMAGE_EVIDENCE]->(evidence:ImageEvidence)-[r:SUPPORTS_DRUG]->(drug:Drug)
            RETURN
              cluster.cluster_id AS cluster_id,
              coalesce(cluster.cluster_label, cluster.cluster_key) AS cluster_name,
              cluster.cluster_key AS cluster_key,
              evidence.evidence_id AS evidence_id,
              evidence.evidence_text AS evidence_text,
              evidence.rank AS evidence_rank,
              evidence.tier AS evidence_tier,
              evidence.match_status AS match_status,
              evidence.drug_name AS evidence_drug_name,
              drug.canonical_drug_id AS drug_id,
              drug.primary_drug_name AS drug_name,
              drug.drug_source_status AS drug_source_status
            ORDER BY evidence.rank IS NULL, evidence.rank, evidence.drug_name, cluster.cluster_key
            """,
            {"disease_id": disease_id},
        )

        for row in evidence_rows:
            _put_node(
                nodes,
                row["drug_id"],
                "Drug",
                row["drug_name"],
                {
                    "canonical_drug_id": row["drug_id"],
                    "drug_source_status": row["drug_source_status"],
                    "match_status": row["match_status"],
                },
            )
            _put_node(
                nodes,
                row["cluster_id"],
                "ImageCluster",
                row["cluster_name"],
                {"cluster_key": row["cluster_key"], "disease_id": disease_id},
            )
            _put_node(
                nodes,
                row["evidence_id"],
                "ImageEvidence",
                row["evidence_drug_name"] or row["evidence_id"],
                {
                    "evidence_text": row["evidence_text"],
                    "rank": row["evidence_rank"],
                    "tier": row["evidence_tier"],
                    "match_status": row["match_status"],
                    "disease_id": disease_id,
                },
            )
            _put_edge(
                edges,
                f"HAS_IMAGE_CLUSTER:{disease_id}:{row['cluster_id']}",
                disease_id,
                row["cluster_id"],
                "HAS_IMAGE_CLUSTER",
                {"disease_id": disease_id},
            )
            _put_edge(
                edges,
                f"HAS_IMAGE_EVIDENCE:{row['cluster_id']}:{row['evidence_id']}",
                row["cluster_id"],
                row["evidence_id"],
                "HAS_IMAGE_EVIDENCE",
                {"disease_id": disease_id},
            )
            _put_edge(
                edges,
                f"SUPPORTS_DRUG:{row['evidence_id']}:{row['drug_id']}",
                row["evidence_id"],
                row["drug_id"],
                "SUPPORTS_DRUG",
                {"match_status": row["match_status"], "rank": row["evidence_rank"], "tier": row["evidence_tier"]},
            )

    if include_targets:
        target_rows = run_read(
            """
            MATCH (drug:Drug)-[r:HAS_TARGET]->(target:TargetConcept)
            WHERE drug.canonical_drug_id IN $drug_ids AND r.disease_id = $disease_id
            RETURN
              drug.canonical_drug_id AS drug_id,
              target.target_id AS target_id,
              target.concept_text AS concept_text,
              target.concept_type AS concept_type,
              r.relation_kind AS relation_kind,
              r.source_id AS source_id
            ORDER BY target.concept_type, target.concept_text
            """,
            {"disease_id": disease_id, "drug_ids": [row["drug_id"] for row in candidate_rows]},
        )

        for row in target_rows:
            _put_node(
                nodes,
                row["target_id"],
                "TargetConcept",
                row["concept_text"],
                {"concept_type": row["concept_type"]},
            )
            _put_edge(
                edges,
                f"HAS_TARGET:{row['source_id']}:{row['relation_kind']}:{row['target_id']}",
                row["drug_id"],
                row["target_id"],
                "HAS_TARGET",
                {"relation_kind": row["relation_kind"], "source_id": row["source_id"], "disease_id": disease_id},
            )

        evidence_target_rows = run_read(
            """
            MATCH (evidence:ImageEvidence {disease_id: $disease_id})-[r:MENTIONS_TARGET]->(target:TargetConcept)
            RETURN
              evidence.evidence_id AS evidence_id,
              target.target_id AS target_id,
              target.concept_text AS concept_text,
              target.concept_type AS concept_type,
              r.relation_kind AS relation_kind,
              r.source_id AS source_id
            ORDER BY target.concept_type, target.concept_text
            """,
            {"disease_id": disease_id},
        )

        for row in evidence_target_rows:
            if row["evidence_id"] not in nodes:
                continue
            _put_node(
                nodes,
                row["target_id"],
                "TargetConcept",
                row["concept_text"],
                {"concept_type": row["concept_type"]},
            )
            _put_edge(
                edges,
                f"MENTIONS_TARGET:{row['source_id']}:{row['relation_kind']}:{row['target_id']}",
                row["evidence_id"],
                row["target_id"],
                "MENTIONS_TARGET",
                {"relation_kind": row["relation_kind"], "source_id": row["source_id"], "disease_id": disease_id},
            )

    return {"disease_id": disease_id, "nodes": list(nodes.values()), "edges": list(edges.values())}


@app.get("/diseases", response_model=list[Disease])
def list_diseases() -> list[dict]:
    return fetch_all(
        """
        SELECT
          d.disease_id,
          d.display_name,
          COUNT(DISTINCT COALESCE(da.canonical_drug_id, c.drug_id))::int AS candidate_count
        FROM diseases d
        LEFT JOIN drug_candidates c ON c.disease_id = d.disease_id
        LEFT JOIN drugs drug ON drug.drug_id = c.drug_id
        LEFT JOIN drug_aliases da ON da.source_drug_id = drug.drug_id
        GROUP BY d.disease_id, d.display_name
        ORDER BY d.disease_id
        """
    )


def _resolve_disease_id(disease_code: str) -> str:
    disease = fetch_one(
        """
        SELECT disease_id
        FROM diseases
        WHERE disease_id = %(disease_code)s
           OR lower(disease_id) = lower(%(disease_code)s)
        LIMIT 1
        """,
        {"disease_code": disease_code},
    )
    if not disease:
        raise HTTPException(status_code=404, detail=f"Unknown disease_id: {disease_code}")
    return disease["disease_id"]


def _list_final_drug_candidates(disease_code: str, limit: int, offset: int) -> list[dict]:
    disease_id = _resolve_disease_id(disease_code)
    return fetch_all(
        """
        WITH ranked AS (
          SELECT
            c.candidate_id,
            c.disease_id,
            c.drug_id,
            da.canonical_drug_id,
            d.drug_name,
            c.rank,
            c.tier,
            c.score,
            c.target,
            c.target_pathway,
            c.evidence_summary,
            d.canonical_smiles,
            a.safety_score,
            a.verdict,
            a.admet_status,
            a.hard_fail,
            a.hard_fail_reasons,
            a.soft_flags,
            ROW_NUMBER() OVER (
              PARTITION BY c.disease_id, COALESCE(da.canonical_drug_id, c.drug_id)
              ORDER BY c.rank NULLS LAST, c.candidate_id
            ) AS row_number
          FROM drug_candidates c
          JOIN drugs d ON d.drug_id = c.drug_id
          LEFT JOIN drug_aliases da ON da.source_drug_id = d.drug_id
          LEFT JOIN admet_results a ON a.candidate_id = c.candidate_id
          WHERE c.disease_id = %(disease_id)s
        )
        SELECT
          candidate_id,
          disease_id,
          drug_id,
          canonical_drug_id,
          drug_name,
          rank,
          tier,
          score,
          target,
          target_pathway,
          evidence_summary,
          canonical_smiles,
          safety_score,
          verdict,
          admet_status,
          hard_fail,
          hard_fail_reasons,
          soft_flags,
          true AS is_final_candidate,
          'final_candidate' AS candidate_source
        FROM ranked
        WHERE row_number = 1
        ORDER BY rank NULLS LAST, drug_name
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        {"disease_id": disease_id, "limit": limit, "offset": offset},
    )


def _list_candidate_pool(disease_code: str, limit: int, offset: int) -> list[dict]:
    disease_id = _resolve_disease_id(disease_code)
    return fetch_all(
        """
        WITH ranked AS (
          SELECT
            candidate_id,
            disease_id,
            drug_id,
            canonical_drug_id,
            drug_name,
            rank,
            tier,
            score,
            target,
            target_pathway,
            evidence_summary,
            canonical_smiles,
            is_final_candidate,
            ROW_NUMBER() OVER (
              PARTITION BY disease_id, lower(drug_name)
              ORDER BY rank NULLS LAST, candidate_id
            ) AS row_number
          FROM candidate_pool
          WHERE disease_id = %(disease_id)s
        )
        SELECT
          candidate_id,
          disease_id,
          drug_id,
          canonical_drug_id,
          drug_name,
          rank,
          tier,
          score,
          target,
          target_pathway,
          evidence_summary,
          canonical_smiles,
          NULL::text AS safety_score,
          NULL::text AS verdict,
          NULL::text AS admet_status,
          NULL::text AS hard_fail,
          NULL::text AS hard_fail_reasons,
          NULL::text AS soft_flags,
          is_final_candidate,
          'candidate_pool' AS candidate_source
        FROM ranked
        WHERE row_number = 1
        ORDER BY rank NULLS LAST, drug_name
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        {"disease_id": disease_id, "limit": limit, "offset": offset},
    )


@app.get("/drugs", response_model=list[DrugCandidate])
def list_drugs(
    disease_id: str = Query(..., description="Disease id, e.g. BRCA, RA, STAD"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    return _list_final_drug_candidates(disease_id, limit, offset)


@app.get("/api/diseases/{disease_code}/candidates", response_model=list[DrugCandidate])
@app.get("/v1/diseases/{disease_code}/candidates", response_model=list[DrugCandidate])
def list_disease_candidates(
    disease_code: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    return _list_candidate_pool(disease_code, limit, offset)


@app.get("/v1/diseases/{disease_code}/final-candidates", response_model=list[DrugCandidate])
def list_disease_final_candidates(
    disease_code: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    return _list_final_drug_candidates(disease_code, limit, offset)


@app.get("/drugs/{drug_id}", response_model=DrugDetail)
def get_drug(drug_id: str) -> dict:
    drug = fetch_one(
        """
        SELECT drug_id, drug_name, canonical_smiles, first_seen_disease_id
        FROM drugs
        WHERE drug_id = %(drug_id)s
        """,
        {"drug_id": drug_id},
    )
    if not drug:
        raise HTTPException(status_code=404, detail=f"Unknown drug_id: {drug_id}")

    candidates = fetch_all(
        """
        SELECT
          c.candidate_id,
          c.disease_id,
          c.rank,
          c.tier,
          c.score,
          c.target,
          c.target_pathway,
          c.evidence_summary,
          a.safety_score,
          a.verdict,
          a.admet_status,
          a.hard_fail,
          a.hard_fail_reasons,
          a.soft_flags
        FROM drug_candidates c
        LEFT JOIN admet_results a ON a.candidate_id = c.candidate_id
        WHERE c.drug_id = %(drug_id)s
        ORDER BY c.disease_id, c.rank NULLS LAST
        """,
        {"drug_id": drug_id},
    )
    return {**drug, "candidates": candidates}


@app.get("/image-modal/clusters", response_model=list[ImageModalCluster])
def list_image_modal_clusters(
    disease_id: str = Query(..., description="Disease id, e.g. BRCA, RA, STAD"),
) -> list[dict]:
    disease = fetch_one("SELECT disease_id FROM diseases WHERE disease_id = %(disease_id)s", {"disease_id": disease_id})
    if not disease:
        raise HTTPException(status_code=404, detail=f"Unknown disease_id: {disease_id}")

    return fetch_all(
        """
        SELECT
          cluster_id,
          disease_id,
          cluster_key,
          cluster_label,
          n_observations,
          clinical_summary,
          pathway_summary,
          source_file
        FROM image_modal_clusters
        WHERE disease_id = %(disease_id)s
        ORDER BY cluster_key
        """,
        {"disease_id": disease_id},
    )


@app.get("/image-modal/evidence", response_model=list[ImageModalEvidence])
def list_image_modal_evidence(
    disease_id: str = Query(..., description="Disease id, e.g. BRCA, RA, STAD"),
    cluster_id: str | None = Query(None),
    drug_name: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> list[dict]:
    disease = fetch_one("SELECT disease_id FROM diseases WHERE disease_id = %(disease_id)s", {"disease_id": disease_id})
    if not disease:
        raise HTTPException(status_code=404, detail=f"Unknown disease_id: {disease_id}")

    filters = ["e.disease_id = %(disease_id)s"]
    params: dict = {"disease_id": disease_id, "limit": limit}
    if cluster_id:
        filters.append("e.cluster_id = %(cluster_id)s")
        params["cluster_id"] = cluster_id
    if drug_name:
        filters.append("LOWER(e.drug_name) = LOWER(%(drug_name)s)")
        params["drug_name"] = drug_name

    return fetch_all(
        f"""
        SELECT
          e.evidence_id,
          e.disease_id,
          e.cluster_id,
          c.cluster_key,
          c.cluster_label,
          e.drug_id,
          m.canonical_drug_id,
          COALESCE(m.match_status, 'unmatched') AS match_status,
          e.drug_name,
          e.rank,
          e.tier,
          e.target,
          e.target_pathway,
          e.evidence_text,
          e.source_file
        FROM image_modal_drug_evidence e
        LEFT JOIN image_modal_clusters c ON c.cluster_id = e.cluster_id
        LEFT JOIN image_modal_evidence_drug_matches m ON m.evidence_id = e.evidence_id
        WHERE {' AND '.join(filters)}
        ORDER BY e.rank NULLS LAST, e.drug_name, c.cluster_key
        LIMIT %(limit)s
        """,
        params,
    )


@app.get("/image-modal/reports", response_model=list[ImageModalReport])
def list_image_modal_reports(
    disease_id: str = Query(..., description="Disease id, e.g. BRCA, RA, STAD"),
) -> list[dict]:
    disease = fetch_one("SELECT disease_id FROM diseases WHERE disease_id = %(disease_id)s", {"disease_id": disease_id})
    if not disease:
        raise HTTPException(status_code=404, detail=f"Unknown disease_id: {disease_id}")

    return fetch_all(
        """
        SELECT
          report_id,
          disease_id,
          report_kind,
          title,
          report_text,
          source_file
        FROM image_modal_reports
        WHERE disease_id = %(disease_id)s
        ORDER BY report_kind, source_file
        """,
        {"disease_id": disease_id},
    )
