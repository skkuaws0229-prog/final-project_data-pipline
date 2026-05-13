from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import fetch_all, fetch_one
from app.graph_db import close_driver, run_read, verify_connectivity
from app.schemas import (
    Disease,
    DrugCandidate,
    DrugDetail,
    GraphRelationsResponse,
    HealthResponse,
    ImageModalCluster,
    ImageModalEvidence,
    ImageModalReport,
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
        LIMIT $limit
        """,
        {"disease_id": disease_id, "limit": limit},
    )

    for row in candidate_rows:
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
          COUNT(c.candidate_id)::int AS candidate_count
        FROM diseases d
        LEFT JOIN drug_candidates c ON c.disease_id = d.disease_id
        GROUP BY d.disease_id, d.display_name
        ORDER BY d.disease_id
        """
    )


@app.get("/drugs", response_model=list[DrugCandidate])
def list_drugs(
    disease_id: str = Query(..., description="Disease id, e.g. BRCA, RA, STAD"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    disease = fetch_one("SELECT disease_id FROM diseases WHERE disease_id = %(disease_id)s", {"disease_id": disease_id})
    if not disease:
        raise HTTPException(status_code=404, detail=f"Unknown disease_id: {disease_id}")

    return fetch_all(
        """
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
          a.soft_flags
        FROM drug_candidates c
        JOIN drugs d ON d.drug_id = c.drug_id
        LEFT JOIN drug_aliases da ON da.source_drug_id = d.drug_id
        LEFT JOIN admet_results a ON a.candidate_id = c.candidate_id
        WHERE c.disease_id = %(disease_id)s
        ORDER BY c.rank NULLS LAST, d.drug_name
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        {"disease_id": disease_id, "limit": limit, "offset": offset},
    )


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
