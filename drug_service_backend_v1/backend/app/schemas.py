from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: str


class Disease(BaseModel):
    disease_id: str
    display_name: str
    candidate_count: int


class DrugCandidate(BaseModel):
    candidate_id: str
    disease_id: str
    drug_id: str
    canonical_drug_id: str | None = None
    drug_name: str
    rank: int | None = None
    tier: str | None = None
    score: str | None = None
    target: str | None = None
    target_pathway: str | None = None
    evidence_summary: str | None = None
    canonical_smiles: str | None = None
    safety_score: str | None = None
    verdict: str | None = None
    admet_status: str | None = None
    hard_fail: str | None = None
    hard_fail_reasons: str | None = None
    soft_flags: str | None = None


class DrugDetail(BaseModel):
    drug_id: str
    drug_name: str
    canonical_smiles: str | None = None
    first_seen_disease_id: str | None = None
    candidates: list[dict[str, Any]]


class ImageModalCluster(BaseModel):
    cluster_id: str
    disease_id: str
    cluster_key: str
    cluster_label: str | None = None
    n_observations: int | None = None
    clinical_summary: str | None = None
    pathway_summary: str | None = None
    source_file: str


class ImageModalEvidence(BaseModel):
    evidence_id: str
    disease_id: str
    cluster_id: str | None = None
    cluster_key: str | None = None
    cluster_label: str | None = None
    drug_id: str | None = None
    canonical_drug_id: str | None = None
    match_status: str | None = None
    drug_name: str | None = None
    rank: int | None = None
    tier: str | None = None
    target: str | None = None
    target_pathway: str | None = None
    evidence_text: str | None = None
    source_file: str


class ImageModalReport(BaseModel):
    report_id: str
    disease_id: str
    report_kind: str
    title: str | None = None
    report_text: str
    source_file: str


class GraphNode(BaseModel):
    id: str
    label: str
    name: str
    properties: dict[str, Any] = {}


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    properties: dict[str, Any] = {}


class GraphRelationsResponse(BaseModel):
    disease_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class PathScoreEvidenceSource(BaseModel):
    source_type: str
    source_id: str | None = None
    source_file: str | None = None
    evidence_role: str
    summary: str | None = None
    properties: dict[str, Any] = {}


class PathScoreItem(BaseModel):
    canonical_drug_id: str
    drug_name: str
    rank: int | None = None
    tier: str | None = None
    path_score: float
    positive_score: float
    risk_penalty: float
    components: dict[str, float]
    evidence_sources: list[PathScoreEvidenceSource]
    risk_sources: list[PathScoreEvidenceSource]


class PathScoreResponse(BaseModel):
    disease_id: str
    scoring_version: str
    scores: list[PathScoreItem]


class KgEmbeddingScore(BaseModel):
    disease_id: str
    canonical_drug_id: str
    drug_name: str
    kg_score: float
    distmult_score: float
    transe_score: float
    ensemble_score: float
    is_known_candidate: bool
    candidate_rank: int | None = None
    candidate_tier: str | None = None


class KgEmbeddingResponse(BaseModel):
    disease_id: str
    model: str
    scoring_version: str
    scores: list[KgEmbeddingScore]


class SearchHit(BaseModel):
    id: str
    score: float | None = None
    doc_type: str
    disease_id: str | None = None
    title: str | None = None
    drug_name: str | None = None
    canonical_drug_id: str | None = None
    cluster_id: str | None = None
    match_status: str | None = None
    source_file: str | None = None
    snippet: str | None = None
    highlights: dict[str, list[str]] = {}
    source: dict[str, Any] = {}


class SearchResponse(BaseModel):
    query: str
    total: int
    hits: list[SearchHit]
