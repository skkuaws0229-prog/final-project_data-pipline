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
