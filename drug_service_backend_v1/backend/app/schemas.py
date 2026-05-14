from typing import Any

from pydantic import BaseModel, Field


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
    is_final_candidate: bool | None = None
    candidate_source: str | None = None


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


class StructureTarget(BaseModel):
    protein_id: str
    gene_symbol: str | None = None
    uniprot_id: str | None = None
    protein_name: str | None = None
    organism: str
    source: str
    target_texts: list[str] = Field(default_factory=list)
    mapping_statuses: list[str] = Field(default_factory=list)
    diseases: list[str] = Field(default_factory=list)
    structure_status: str
    structure_count: int


class StructureTargetsResponse(BaseModel):
    targets: list[StructureTarget]


class StructureListItem(BaseModel):
    structure_id: str
    protein_id: str
    gene_symbol: str | None = None
    uniprot_id: str | None = None
    protein_name: str | None = None
    file_format: str
    structure_status: str
    mean_plddt: float | None = None
    file_size_bytes: int | None = None
    diseases: list[str] = Field(default_factory=list)
    target_texts: list[str] = Field(default_factory=list)
    context_summary: dict[str, Any] = Field(default_factory=dict)
    file_endpoint: str


class StructureListResponse(BaseModel):
    structures: list[StructureListItem]


class StructureTargetLink(BaseModel):
    target_text: str
    mapping_status: str
    confidence: float | None = None
    diseases: str | None = None
    source: str
    raw_json: dict[str, Any] = Field(default_factory=dict)


class StructureContextLink(BaseModel):
    context_id: str
    disease_id: str
    candidate_id: str | None = None
    evidence_id: str | None = None
    canonical_drug_id: str | None = None
    drug_name: str | None = None
    target_source: str
    relation_note: str | None = None


class StructureContextSummary(BaseModel):
    total_links: int = 0
    diseases: list[str] = Field(default_factory=list)
    disease_count: int = 0
    drug_count: int = 0
    evidence_count: int = 0
    candidate_target_count: int = 0
    image_evidence_count: int = 0
    target_source_counts: dict[str, int] = Field(default_factory=dict)


class StructureDetailResponse(BaseModel):
    structure_id: str
    protein_id: str
    gene_symbol: str | None = None
    uniprot_id: str | None = None
    protein_name: str | None = None
    organism: str
    protein_source: str
    provider: str
    provider_accession: str | None = None
    version: str | None = None
    file_format: str
    structure_uri: str
    structure_source_uri: str | None = None
    file_size_bytes: int | None = None
    checksum_sha256: str | None = None
    source_url: str | None = None
    pae_uri: str | None = None
    mean_plddt: float | None = None
    confidence_summary: str | None = None
    license: str | None = None
    status: str
    structure_status: str
    target_texts: list[str] = Field(default_factory=list)
    mapping_statuses: list[str] = Field(default_factory=list)
    diseases: list[str] = Field(default_factory=list)
    target_links: list[StructureTargetLink] = Field(default_factory=list)
    context_links: list[StructureContextLink] = Field(default_factory=list)
    context_summary: StructureContextSummary = Field(default_factory=StructureContextSummary)


class PipelineRunCreateRequest(BaseModel):
    disease_name: str
    mode: str = "full"
    execution_backend: str = "mock"
    requested_by: str | None = None
    random_seed: int = 42
    config_snapshot: dict[str, Any] = Field(default_factory=dict)


class PipelineRunPreflightResponse(BaseModel):
    input_disease_name: str
    disease_name: str
    disease_slug: str
    mode: str
    execution_backend: str
    execution_backend_alias: str | None = None
    is_supported_disease: bool
    backend_enabled: bool
    preflight_status: str
    can_create_run: bool
    will_execute: bool
    reasons: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)


class PipelineRunResponse(BaseModel):
    run_id: str
    disease_name: str
    disease_slug: str
    mode: str
    execution_backend: str
    status: str
    current_step: str | None = None
    requested_by: str | None = None
    s3_output_prefix: str | None = None
    config_snapshot: dict[str, Any] = Field(default_factory=dict)
    random_seed: int | None = None
    verdict: str | None = None
    error_message: str | None = None
    estimated_cost_usd: float | None = None
    estimated_time_minutes: int | None = None
    created_at: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    updated_at: str | None = None


class PipelineRunsResponse(BaseModel):
    runs: list[PipelineRunResponse]


class PipelineRunEvent(BaseModel):
    event_id: str
    run_id: str
    timestamp: str
    level: str
    step: str | None = None
    message: str
    payload_json: dict[str, Any] = Field(default_factory=dict)


class PipelineRunEventsResponse(BaseModel):
    run_id: str
    events: list[PipelineRunEvent]


class PipelineArtifact(BaseModel):
    artifact_id: str
    run_id: str
    artifact_type: str
    step: str | None = None
    name: str
    uri: str
    size_bytes: int | None = None
    checksum: str | None = None
    created_at: str | None = None


class PipelineArtifactsResponse(BaseModel):
    run_id: str
    artifacts: list[PipelineArtifact]


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
    candidate_source: str | None = None
    is_final_candidate: bool | None = None
    provenance_count: int | None = None
    provenance_note: str | None = None
    provenance_source_files: list[str] = Field(default_factory=list)
    provenance_ids: list[str] = Field(default_factory=list)
    provenance_hits: list[dict[str, Any]] = Field(default_factory=list)
    source_file: str | None = None
    snippet: str | None = None
    highlights: dict[str, list[str]] = Field(default_factory=dict)
    source: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    total: int
    raw_total: int | None = None
    hits: list[SearchHit]


class ExplanationContextResponse(BaseModel):
    contract_version: str
    disease_id: str
    drug_name: str | None = None
    canonical_drug_id: str | None = None
    query: dict[str, Any] = Field(default_factory=dict)
    final_candidate: dict[str, Any] | None = None
    candidate_pool: dict[str, Any] | None = None
    admet: dict[str, Any] | None = None
    search_context: dict[str, Any] = Field(default_factory=dict)
    graph_context: dict[str, Any] = Field(default_factory=dict)
    structure_context: dict[str, Any] = Field(default_factory=dict)
    retrieval_sources: list[dict[str, Any]] = Field(default_factory=list)
    prompt_guardrails: list[str] = Field(default_factory=list)
    status: str
