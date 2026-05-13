#!/usr/bin/env python3
"""
Drug Repurposing KG — FastAPI v2 서버

v1(api_server.py) 기반 + ML/DL 파이프라인 결과 API 추가
포트: 8000
CORS 전체 허용
Neo4j Aura + PubMed + 국립암센터 + Pipeline Results 통합
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ── 프로젝트 루트 ──
PROJECT_ROOT = Path(__file__).resolve().parent  # ← 수정: 현재 폴더
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

# llm 모듈은 선택적 import (없어도 서버 기동 가능)
try:
    from llm.ncis_content import get_ncis_info  # noqa: E402
    from llm.llm_module import search_news, get_lifestyle_guide, search_celebrity_cases  # noqa: E402
    HAS_LLM = True
except ImportError:
    HAS_LLM = False

load_dotenv(PROJECT_ROOT / ".env")
print(f"[ENV] .env loaded from: {PROJECT_ROOT / '.env'}")

# ── Neo4j 설정 ──
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        from neo4j import GraphDatabase
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        _driver.verify_connectivity()
    return _driver


def neo4j_query(cypher: str, **params) -> list[dict]:
    driver = get_driver()
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(cypher, **params)
        return [dict(record) for record in result]


def make_response(data: Any, source: str = "neo4j") -> dict:
    return {
        "status": "success",
        "data": data,
        "source": source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════
#  파이프라인 결과 데이터 (exact slim + strong context + SMILES, random3)
# ══════════════════════════════════════════

PIPELINE_META = {
    "input_set": "exact slim + strong context + SMILES",
    "split": "random sample 3-fold",
    "seed": 42,
    "rows": 6366,
    "ml_feature_dim": 5625,
    "dl_numeric_dim": 5529,
    "strong_context_cols": 5,
    "smiles_vocab": 38,
}

ML_MODELS = [
    {"rank": 1, "name": "CatBoost", "family": "ML", "spearman": 0.8706, "spearman_std": 0.0085, "rmse": 1.1083, "rmse_std": 0.0225, "mae": 0.8263, "pearson": 0.9121, "r2": 0.8322, "ndcg20": 0.9571, "time": "30.1m", "status": "TOP"},
    {"rank": 2, "name": "XGBoost", "family": "ML", "spearman": 0.8647, "spearman_std": 0.0109, "rmse": 1.1347, "rmse_std": 0.0263, "mae": 0.8453, "pearson": 0.9076, "r2": 0.8241, "ndcg20": 0.9535, "time": "15.7m", "status": "TOP"},
    {"rank": 3, "name": "LightGBM", "family": "ML", "spearman": 0.8637, "spearman_std": 0.0073, "rmse": 1.1358, "rmse_std": 0.0209, "mae": 0.8509, "pearson": 0.9066, "r2": 0.8224, "ndcg20": 0.9528, "time": "9.1m", "status": "TOP"},
    {"rank": 4, "name": "LightGBM_DART", "family": "ML", "spearman": 0.8572, "spearman_std": 0.0052, "rmse": 1.1498, "rmse_std": 0.0084, "mae": 0.8606, "pearson": 0.9011, "r2": 0.8115, "ndcg20": 0.9492, "time": "39.3m", "status": "STRONG"},
    {"rank": 5, "name": "ExtraTrees", "family": "ML", "spearman": 0.8441, "spearman_std": None, "rmse": 1.3283, "rmse_std": None, "mae": 1.0181, "pearson": 0.8887, "r2": 0.7590, "ndcg20": 0.9439, "time": "25s", "status": "REFERENCE"},
    {"rank": 6, "name": "RandomForest", "family": "ML", "spearman": 0.8312, "spearman_std": None, "rmse": 1.3954, "rmse_std": None, "mae": 1.0830, "pearson": 0.8795, "r2": 0.7340, "ndcg20": 0.9406, "time": "60s", "status": "REFERENCE"},
]

DL_MODELS = [
    {"rank": 1, "name": "TabNet", "family": "DL", "spearman": 0.8615, "spearman_std": 0.0130, "rmse": 1.1559, "rmse_std": 0.0219, "mae": 0.8768, "pearson": 0.9055, "r2": 0.8175, "ndcg20": 0.9539, "time": "20.2m", "status": "TOP"},
    {"rank": 2, "name": "ResidualMLP", "family": "DL", "spearman": 0.8596, "spearman_std": 0.0290, "rmse": 1.1613, "rmse_std": 0.0502, "mae": 0.8693, "pearson": 0.9034, "r2": 0.8156, "ndcg20": 0.9458, "time": "26.7m", "status": "STRONG"},
    {"rank": 3, "name": "WideDeep", "family": "DL", "spearman": 0.8572, "spearman_std": 0.0119, "rmse": 1.1639, "rmse_std": 0.0177, "mae": 0.8729, "pearson": 0.9029, "r2": 0.8149, "ndcg20": 0.9531, "time": "46.0m", "status": "STRONG"},
    {"rank": 4, "name": "FlatMLP", "family": "DL", "spearman": 0.8558, "spearman_std": 0.0164, "rmse": 1.1695, "rmse_std": 0.0133, "mae": 0.8872, "pearson": 0.9018, "r2": 0.8132, "ndcg20": 0.9582, "time": "36.1m", "status": "STRONG"},
    {"rank": 5, "name": "CrossAttention", "family": "DL", "spearman": 0.8488, "spearman_std": 0.0104, "rmse": 1.2045, "rmse_std": 0.0241, "mae": 0.8996, "pearson": 0.8955, "r2": 0.8018, "ndcg20": 0.9539, "time": "24.0m", "status": "REFERENCE"},
    {"rank": 6, "name": "FTTransformer", "family": "DL", "spearman": 0.8475, "spearman_std": 0.0118, "rmse": 1.2255, "rmse_std": 0.0143, "mae": 0.9187, "pearson": 0.8916, "r2": 0.7948, "ndcg20": 0.9469, "time": "25.8m", "status": "REFERENCE"},
]

ENSEMBLE_RESULT = {
    "weighted_spearman": 0.8720,
    "weighted_rmse": 1.1016,
    "equal_spearman": 0.8720,
    "equal_rmse": 1.1016,
    "total_time": "2.5h",
    "avg_pred_pearson": 0.9817,
    "members": [
        {"name": "CatBoost", "family": "ML", "weight": 0.1682, "spearman": 0.8706, "rmse": 1.1083, "time": "30.1m"},
        {"name": "XGBoost", "family": "ML", "weight": 0.1670, "spearman": 0.8647, "rmse": 1.1347, "time": "15.7m"},
        {"name": "LightGBM", "family": "ML", "weight": 0.1668, "spearman": 0.8637, "rmse": 1.1358, "time": "9.1m"},
        {"name": "TabNet", "family": "DL", "weight": 0.1664, "spearman": 0.8613, "rmse": 1.1560, "time": "20.2m"},
        {"name": "ResidualMLP", "family": "DL", "weight": 0.1661, "spearman": 0.8599, "rmse": 1.1620, "time": "26.7m"},
        {"name": "WideDeep", "family": "DL", "weight": 0.1656, "spearman": 0.8572, "rmse": 1.1639, "time": "46.0m"},
    ],
}

METABRIC_RESULTS = {
    "target_expressed": "29/30",
    "brca_pathway": "23/30",
    "survival_significant": "28/30",
    "p15_precision": "80.0%",
    "rsf_cindex": 0.821,
    "graphsage_p20": 0.94,
    "precision_at_k": [
        {"k": 5, "precision": 80}, {"k": 10, "precision": 90}, {"k": 15, "precision": 80},
        {"k": 20, "precision": 65}, {"k": 25, "precision": 56}, {"k": 30, "precision": 50},
    ],
}

FINAL_CANDIDATES = [
    {"rank": 1, "name": "Romidepsin", "target": "HDAC1, HDAC2, HDAC3, HDAC8", "pathway": "Chromatin histone acetylation", "ic50": -4.741, "validation": 6.90, "safety": 12.00, "combined": 19.00, "category": "expansion", "flags": [], "target_expr": True, "brca_pathway": True, "survival": False, "recommendation": "유방암으로 확장 가능성, 추가 translational 검토 가치"},
    {"rank": 2, "name": "Sepantronium bromide", "target": "BIRC5", "pathway": "Apoptosis regulation", "ic50": -3.855, "validation": 7.35, "safety": 10.00, "combined": 16.50, "category": "unused", "flags": [], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "재창출 관점의 exploratory candidate"},
    {"rank": 3, "name": "Staurosporine", "target": "Broad spectrum kinase inhibitor", "pathway": "RTK signaling", "ic50": -2.476, "validation": 7.55, "safety": 10.00, "combined": 13.50, "category": "unused", "flags": [], "target_expr": True, "brca_pathway": False, "survival": True, "recommendation": "재창출 관점의 exploratory candidate"},
    {"rank": 4, "name": "SN-38", "target": "TOP1", "pathway": "DNA replication", "ic50": -2.462, "validation": 9.00, "safety": 10.00, "combined": 13.00, "category": "expansion", "flags": [], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "유방암으로 확장 가능성, 추가 translational 검토 가치"},
    {"rank": 5, "name": "Docetaxel", "target": "Microtubule stabiliser", "pathway": "Mitosis", "ic50": -3.303, "validation": 9.30, "safety": 6.83, "combined": 12.83, "category": "current", "flags": ["DILI"], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "임상 현실과 일치하는 재발견 후보"},
    {"rank": 6, "name": "Bortezomib", "target": "Proteasome", "pathway": "Protein stability and degradation", "ic50": -4.752, "validation": 9.45, "safety": 5.29, "combined": 12.79, "category": "expansion", "flags": ["DILI"], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "유방암으로 확장 가능성, 추가 translational 검토 가치"},
    {"rank": 7, "name": "Dactinomycin", "target": "RNA polymerase", "pathway": "Other", "ic50": -3.018, "validation": 7.75, "safety": 7.00, "combined": 12.50, "category": "unused", "flags": ["DILI"], "target_expr": True, "brca_pathway": False, "survival": True, "recommendation": "재창출 관점의 exploratory candidate"},
    {"rank": 8, "name": "Vinorelbine", "target": "Microtubule destabiliser", "pathway": "Mitosis", "ic50": -2.830, "validation": 9.15, "safety": 8.00, "combined": 12.50, "category": "current", "flags": [], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "임상 현실과 일치하는 재발견 후보"},
    {"rank": 9, "name": "Dinaciclib", "target": "CDK1, CDK2, CDK5, CDK9", "pathway": "Cell cycle", "ic50": -2.191, "validation": 8.90, "safety": 10.00, "combined": 12.00, "category": "expansion", "flags": [], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "유방암으로 확장 가능성, 추가 translational 검토 가치"},
    {"rank": 10, "name": "Paclitaxel", "target": "Microtubule stabiliser", "pathway": "Mitosis", "ic50": -2.837, "validation": 9.20, "safety": 6.83, "combined": 11.83, "category": "current", "flags": ["DILI"], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "임상 현실과 일치하는 재발견 후보"},
    {"rank": 11, "name": "Vinblastine", "target": "Microtubule destabiliser", "pathway": "Mitosis", "ic50": -2.741, "validation": 9.10, "safety": 7.83, "combined": 11.83, "category": "current", "flags": [], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "임상 현실과 일치하는 재발견 후보"},
    {"rank": 12, "name": "Camptothecin", "target": "TOP1", "pathway": "DNA replication", "ic50": -0.544, "validation": 8.65, "safety": 10.00, "combined": 11.00, "category": "unused", "flags": [], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "재창출 관점의 exploratory candidate"},
    {"rank": 13, "name": "Rapamycin", "target": "MTORC1", "pathway": "PI3K/MTOR signaling", "ic50": -2.395, "validation": 8.95, "safety": 7.71, "combined": 10.21, "category": "expansion", "flags": [], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "유방암으로 확장 가능성, 추가 translational 검토 가치"},
    {"rank": 14, "name": "Luminespib", "target": "HSP90", "pathway": "Protein stability and degradation", "ic50": -1.834, "validation": 8.80, "safety": 5.00, "combined": 6.50, "category": "expansion", "flags": [], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "유방암으로 확장 가능성, 추가 translational 검토 가치"},
    {"rank": 15, "name": "Epirubicin", "target": "Anthracycline", "pathway": "DNA replication", "ic50": 0.093, "validation": 8.30, "safety": 2.83, "combined": 3.33, "category": "current", "flags": ["Ames", "DILI"], "target_expr": True, "brca_pathway": True, "survival": True, "recommendation": "임상 현실과 일치하는 재발견 후보"},
]

ADMET_SUMMARY = {
    "current_use": 5,
    "expansion": 6,
    "unused": 4,
    "assays": 22,
    "total_candidates": 15,
    "raw_approved": 8,
    "raw_candidate": 6,
    "raw_caution": 1,
}

# v1 파이프라인 약물 목록도 유지
PIPELINE_DRUGS = [d["name"] for d in FINAL_CANDIDATES]


# ══════════════════════════════════════════
#  FastAPI 앱
# ══════════════════════════════════════════

app = FastAPI(
    title="Drug Repurposing KG API v2",
    description="유방암 약물 재창출 KG + ML/DL 파이프라인 통합 API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════
#  루트 경로 - HTML 서빙
# ══════════════════════════════════════════

@app.get("/")
def serve_frontend():
    """BioChat v2 프론트엔드 HTML 제공"""
    html_path = Path(__file__).parent / "biochat_v2.html"
    if html_path.exists():
        return FileResponse(html_path)
    return {"message": "BioChat v2 API Server", "docs": "/docs"}


# ══════════════════════════════════════════
#  v1 기존 엔드포인트 (Neo4j 기반)
# ══════════════════════════════════════════

@app.get("/api/drug/{drug_name}")
def get_drug(drug_name: str):
    rows = neo4j_query("MATCH (d:Drug {name: $name}) RETURN d", name=drug_name)
    if not rows:
        raise HTTPException(404, f"Drug '{drug_name}' not found")
    return make_response(dict(rows[0]["d"]))


@app.get("/api/drug/{drug_name}/targets")
def get_drug_targets(drug_name: str):
    rows = neo4j_query(
        "MATCH (d:Drug {name: $name})-[:TARGETS]->(t:Target) "
        "RETURN t.gene_symbol AS gene_symbol, t.protein_name AS protein_name, "
        "t.uniprot_id AS uniprot_id, t.function AS function",
        name=drug_name,
    )
    return make_response(rows)


@app.get("/api/drug/{drug_name}/side_effects")
def get_drug_side_effects(drug_name: str):
    rows = neo4j_query(
        "MATCH (d:Drug {name: $name})-[:HAS_SIDE_EFFECT]->(s:SideEffect) "
        "RETURN s.name AS name, s.meddra_term AS meddra_term",
        name=drug_name,
    )
    return make_response(rows)


@app.get("/api/drug/{drug_name}/trials")
def get_drug_trials(drug_name: str):
    rows = neo4j_query(
        "MATCH (d:Drug {name: $name})-[:IN_TRIAL]->(t:Trial) "
        "RETURN t.nct_id AS nct_id, t.title AS title, t.phase AS phase, "
        "t.status AS status, t.sponsor AS sponsor, "
        "t.start_date AS start_date, t.completion_date AS completion_date",
        name=drug_name,
    )
    return make_response(rows)


def get_kegg_pathway_image(pathway_name: str) -> dict | None:
    """
    KEGG REST API로 pathway 이미지 URL 가져오기

    Returns:
        {"kegg_id": "hsa04151", "image_url": "https://...", "name": "..."}
        또는 None (찾지 못한 경우)
    """
    try:
        # 1. KEGG pathway 검색
        search_query = urllib.parse.quote(pathway_name)
        search_url = f"http://rest.kegg.jp/find/pathway/{search_query}"

        with urllib.request.urlopen(search_url, timeout=5) as resp:
            result = resp.read().decode('utf-8').strip()

        if not result:
            return None

        # 첫 번째 결과 파싱: "path:hsa04151\tPI3K-Akt signaling pathway - Homo sapiens"
        first_line = result.split('\n')[0]
        parts = first_line.split('\t')
        if len(parts) < 2:
            return None

        kegg_id = parts[0].replace('path:', '')  # hsa04151
        kegg_name = parts[1]  # PI3K-Akt signaling pathway - Homo sapiens

        # 2. KEGG 이미지 URL 생성
        image_url = f"https://www.kegg.jp/pathway/{kegg_id}"

        return {
            "kegg_id": kegg_id,
            "kegg_name": kegg_name,
            "image_url": image_url,
            "api_image_url": f"http://rest.kegg.jp/get/{kegg_id}/image"
        }
    except Exception as e:
        print(f"[KEGG API Error] {pathway_name}: {e}")
        return None


@app.get("/api/drug/{drug_name}/pathways")
def get_drug_pathways(drug_name: str, enrich: bool = Query(default=False)):
    """
    약물의 pathway 정보 조회

    Args:
        drug_name: 약물 이름
        enrich: True면 외부 API(KEGG, Reactome, WikiPathways)에서 추가 정보 가져오기
    """
    rows = neo4j_query(
        "MATCH (d:Drug {name: $name})-[:TARGETS]->(t:Target)-[:IN_PATHWAY]->(p:Pathway) "
        "RETURN DISTINCT p.pathway_id AS pathway_id, p.name AS name, p.collection AS collection",
        name=drug_name,
    )

    # KEGG 이미지 URL 추가
    for row in rows:
        pathway_name = row.get('name', '')
        if pathway_name:
            kegg_data = get_kegg_pathway_image(pathway_name)
            if kegg_data:
                row['kegg'] = kegg_data

            # enrich=true면 외부 API에서 추가 정보 가져오기
            if enrich:
                try:
                    from pathway_apis import search_all_pathways
                    external_data = search_all_pathways(pathway_name)
                    row['external'] = external_data
                except Exception as e:
                    print(f"[Pathway Enrich Error] {pathway_name}: {e}")

    return make_response(rows)


@app.get("/api/drugs")
def get_drugs(
    status: str | None = None,
    pipeline: bool = Query(default=False),
    limit: int = Query(default=100, le=20000),
):
    where_clauses = []
    params: dict = {}
    if pipeline:
        where_clauses.append("d.name IN $drug_list")
        params["drug_list"] = PIPELINE_DRUGS
    if status:
        where_clauses.append("d.brca_status = $status")
        params["status"] = status
    where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    rows = neo4j_query(
        f"MATCH (d:Drug) {where} "
        "RETURN d.name AS name, d.brca_status AS brca_status, "
        "d.overall_score AS overall_score, d.safety_score AS safety_score, "
        "d.ic50 AS ic50, d.max_phase AS max_phase, d.target AS target, d.rank AS rank "
        "ORDER BY d.overall_score DESC LIMIT $limit",
        limit=limit, **params,
    )
    return make_response(rows)


@app.get("/api/hospitals")
def get_hospitals(
    region: str | None = None,
    specialty: str | None = Query(default=None),
):
    where_clauses = []
    params: dict = {}
    if region:
        where_clauses.append("h.region = $region")
        params["region"] = region
    if specialty:
        where_clauses.append("h.specialty CONTAINS $specialty")
        params["specialty"] = specialty
    where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    rows = neo4j_query(
        f"MATCH (h:Hospital) {where} "
        "RETURN h.name AS name, h.address AS address, h.phone AS phone, "
        "h.url AS url, h.region AS region, h.specialty AS specialty, "
        "h.category AS category, h.district AS district ORDER BY h.name",
        **params,
    )
    return make_response(rows)


@app.get("/api/stats")
def get_stats():
    node_rows = neo4j_query(
        "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC"
    )
    rel_rows = neo4j_query(
        "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count ORDER BY count DESC"
    )
    return make_response({
        "nodes": {r["label"]: r["count"] for r in node_rows},
        "edges": {r["type"]: r["count"] for r in rel_rows},
        "total_nodes": sum(r["count"] for r in node_rows),
        "total_edges": sum(r["count"] for r in rel_rows),
    })


@app.get("/api/pathways/search")
def search_pathways(query: str):
    """
    외부 pathway 데이터베이스에서 검색 (KEGG, Reactome, WikiPathways)

    Args:
        query: 검색할 pathway 이름 (예: "PI3K", "Apoptosis")

    Returns:
        {
            "kegg": {...},
            "reactome": [{...}, ...],
            "wikipathways": [{...}, ...]
        }
    """
    try:
        from pathway_apis import search_all_pathways
        results = search_all_pathways(query)
        return make_response(results, source="external_apis")
    except Exception as e:
        raise HTTPException(500, f"Pathway search failed: {str(e)}")


@app.get("/api/pubmed")
def search_pubmed(query: str, max_results: int = Query(default=5, le=20)):
    search_url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?"
        + urllib.parse.urlencode({
            "db": "pubmed", "term": query, "retmax": str(max_results),
            "retmode": "json", "sort": "relevance",
        })
    )
    try:
        with urllib.request.urlopen(search_url, timeout=10) as resp:
            search_data = json.loads(resp.read().decode())
    except Exception as e:
        raise HTTPException(502, f"PubMed search failed: {e}")
    id_list = search_data.get("esearchresult", {}).get("idlist", [])
    if not id_list:
        return make_response([], source="pubmed")
    fetch_url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?"
        + urllib.parse.urlencode({
            "db": "pubmed", "id": ",".join(id_list), "retmode": "json",
        })
    )
    try:
        with urllib.request.urlopen(fetch_url, timeout=10) as resp:
            fetch_data = json.loads(resp.read().decode())
    except Exception as e:
        raise HTTPException(502, f"PubMed fetch failed: {e}")
    articles = []
    result = fetch_data.get("result", {})
    for pmid in id_list:
        art = result.get(pmid, {})
        articles.append({
            "pmid": pmid,
            "title": art.get("title", ""),
            "authors": [a.get("name", "") for a in art.get("authors", [])][:5],
            "journal": art.get("fulljournalname", ""),
            "pub_date": art.get("pubdate", ""),
        })
    return make_response(articles, source="pubmed")


@app.get("/api/ncis/{category}")
def get_ncis(category: str, term: str | None = None):
    if not HAS_LLM:
        raise HTTPException(501, "LLM module not available")
    valid = {"brca", "prevention", "guide", "term"}
    if category not in valid:
        raise HTTPException(400, f"Invalid category. Use: {', '.join(valid)}")
    kwargs = {}
    if category == "term":
        kwargs["term"] = term or "유방암"
    data = get_ncis_info(category, **kwargs)
    return make_response(data, source="ncis")


# ══════════════════════════════════════════
#  v2 신규 엔드포인트: ML/DL 파이프라인 결과
# ══════════════════════════════════════════

@app.get("/api/v2/pipeline/meta")
def get_pipeline_meta():
    """파이프라인 메타 정보 (입력셋, 분할, seed 등)."""
    return make_response(PIPELINE_META, source="pipeline")


@app.get("/api/v2/pipeline/models")
def get_pipeline_models(family: str | None = None):
    """ML/DL 모델 결과 조회. family=ML 또는 family=DL로 필터 가능."""
    if family == "ML":
        return make_response(ML_MODELS, source="pipeline")
    elif family == "DL":
        return make_response(DL_MODELS, source="pipeline")
    return make_response({"ml": ML_MODELS, "dl": DL_MODELS}, source="pipeline")


@app.get("/api/v2/pipeline/ensemble")
def get_pipeline_ensemble():
    """앙상블 결과 (weighted + equal)."""
    return make_response(ENSEMBLE_RESULT, source="pipeline")


@app.get("/api/v2/pipeline/metabric")
def get_pipeline_metabric():
    """METABRIC 외부 검증 결과."""
    return make_response(METABRIC_RESULTS, source="pipeline")


@app.get("/api/v2/pipeline/admet")
def get_pipeline_admet():
    """ADMET 안전성 요약."""
    return make_response(ADMET_SUMMARY, source="pipeline")


@app.get("/api/v2/pipeline/candidates")
def get_pipeline_candidates(
    category: str | None = None,
    top: int = Query(default=15, le=30),
):
    """최종 후보 약물 목록. category 필터 가능 (current/expansion/unused)."""
    data = FINAL_CANDIDATES[:top]
    if category:
        data = [d for d in data if d["category"] == category]
    return make_response(data, source="pipeline")


@app.get("/api/v2/pipeline/candidates/{drug_name}")
def get_pipeline_candidate_detail(drug_name: str):
    """특정 후보 약물 상세 조회."""
    for d in FINAL_CANDIDATES:
        if d["name"].lower() == drug_name.lower():
            return make_response(d, source="pipeline")
    raise HTTPException(404, f"Candidate '{drug_name}' not found in pipeline")


@app.get("/api/v2/pipeline/summary")
def get_pipeline_summary():
    """파이프라인 전체 요약 (대시보드용)."""
    return make_response({
        "meta": PIPELINE_META,
        "best_ml": {"name": ML_MODELS[0]["name"], "spearman": ML_MODELS[0]["spearman"]},
        "best_dl": {"name": DL_MODELS[0]["name"], "spearman": DL_MODELS[0]["spearman"]},
        "ensemble": {
            "spearman": ENSEMBLE_RESULT["weighted_spearman"],
            "rmse": ENSEMBLE_RESULT["weighted_rmse"],
        },
        "metabric": {
            "target_expressed": METABRIC_RESULTS["target_expressed"],
            "survival_significant": METABRIC_RESULTS["survival_significant"],
        },
        "admet": ADMET_SUMMARY,
        "top5": [{"name": d["name"], "combined": d["combined"], "category": d["category"]}
                 for d in FINAL_CANDIDATES[:5]],
    }, source="pipeline")


# ══════════════════════════════════════════
#  v2 KG 시각화
# ══════════════════════════════════════════

@app.get("/api/v2/kg/graph")
def get_kg_graph(limit: int = Query(default=500, le=2000)):
    """
    Knowledge Graph 시각화용 노드/엣지 데이터.
    파이프라인 15개 약물을 중심으로 서브그래프 추출.
    """
    # 파이프라인 약물 리스트
    pipeline_drugs = [d["name"] for d in FINAL_CANDIDATES]

    # Neo4j에서 약물 중심 서브그래프 추출
    rows = neo4j_query("""
        MATCH (d:Drug)-[r]->(t)
        WHERE d.name IN $drugs
        WITH d, r, t
        LIMIT $limit
        RETURN
            d.name AS src,
            labels(d)[0] AS src_type,
            type(r) AS rel,
            CASE
                WHEN t.name IS NOT NULL THEN t.name
                WHEN t.gene_symbol IS NOT NULL THEN t.gene_symbol
                WHEN t.term IS NOT NULL THEN t.term
                WHEN t.nct_id IS NOT NULL THEN t.nct_id
                ELSE id(t)
            END AS tgt,
            labels(t)[0] AS tgt_type
    """, drugs=pipeline_drugs, limit=limit)

    # 노드 맵과 엣지 리스트 생성
    nodes_map = {}
    edges_list = []

    for row in rows:
        # 소스 노드 추가
        src_name = row["src"]
        src_type = row["src_type"]
        if src_name and src_name not in nodes_map:
            nodes_map[src_name] = {
                "id": src_name,
                "name": src_name,
                "type": src_type
            }

        # 타겟 노드 추가
        tgt_name = row["tgt"]
        tgt_type = row["tgt_type"]
        if tgt_name and tgt_name not in nodes_map:
            nodes_map[tgt_name] = {
                "id": str(tgt_name),
                "name": str(tgt_name),
                "type": tgt_type
            }

        # 엣지 추가
        if src_name and tgt_name:
            edges_list.append({
                "source": src_name,
                "target": str(tgt_name),
                "relation": row["rel"]
            })

    return make_response({
        "nodes": list(nodes_map.values()),
        "edges": edges_list,
        "stats": {
            "total_nodes": len(nodes_map),
            "total_edges": len(edges_list),
            "drug_nodes": len([n for n in nodes_map.values() if n["type"] == "Drug"])
        }
    }, source="neo4j")


# ══════════════════════════════════════════
#  v2 채팅 (v1 확장 — 파이프라인 질의 추가)
# ══════════════════════════════════════════

class ChatRequest(BaseModel):
    query: str
    user_type: str = "patient"


def _fuzzy_match_drug(query_word: str, drug_list: list[str], threshold: float = 0.8) -> str | None:
    """
    퍼지 매칭으로 약물 이름 찾기 (철자 오류 허용)

    Args:
        query_word: 검색할 단어
        drug_list: 약물 이름 리스트
        threshold: 유사도 임계값 (0.0 ~ 1.0, 기본값 0.8 = 80%)

    Returns:
        매칭된 약물 이름 또는 None
    """
    from difflib import SequenceMatcher

    query_lower = query_word.lower()
    best_match = None
    best_ratio = 0.0

    for drug in drug_list:
        drug_lower = drug.lower()
        # 유사도 계산
        ratio = SequenceMatcher(None, query_lower, drug_lower).ratio()

        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = drug

    return best_match


def _extract_drug_from_query(query: str) -> str | None:
    """
    쿼리에서 약물 이름 추출 (파이프라인 + Neo4j 약물)
    개선: 퍼지 매칭으로 철자 오류 허용
    """
    q_lower = query.lower()

    # 1. 파이프라인 약물 우선 확인 (정확한 매칭)
    for drug in PIPELINE_DRUGS:
        if drug.lower() in q_lower:
            return drug

    # 2. 파이프라인 약물 퍼지 매칭 (철자 오류 허용)
    words = re.split(r'[\s,]+', query)
    for word in words:
        if len(word) < 3:  # 너무 짧은 단어 스킵
            continue
        fuzzy_match = _fuzzy_match_drug(word, PIPELINE_DRUGS, threshold=0.75)
        if fuzzy_match:
            print(f"[Fuzzy match] '{word}' → '{fuzzy_match}' (pipeline)")
            return fuzzy_match

    # 3. Neo4j에서 약물 검색 (대소문자 구분 없음)
    try:
        for word in words:
            if len(word) < 3:
                continue
            # 정확한 매칭 시도
            result = neo4j_query(
                "MATCH (d:Drug) WHERE toLower(d.name) = toLower($word) RETURN d.name AS name LIMIT 1",
                word=word
            )
            if result:
                return result[0]['name']

            # Neo4j에서 유사한 약물 검색 (CONTAINS 사용)
            result = neo4j_query(
                "MATCH (d:Drug) WHERE toLower(d.name) CONTAINS toLower($word) "
                "RETURN d.name AS name LIMIT 5",
                word=word
            )
            if result:
                # 가장 유사한 약물 선택
                drug_names = [r['name'] for r in result]
                fuzzy_match = _fuzzy_match_drug(word, drug_names, threshold=0.75)
                if fuzzy_match:
                    print(f"[Fuzzy match] '{word}' → '{fuzzy_match}' (neo4j)")
                    return fuzzy_match
    except Exception as e:
        print(f"[Drug extraction error] {e}")

    return None


def _classify_intent(query: str) -> str:
    q_lower = query.lower()
    # v2: 파이프라인 관련 intent 추가 (우선순위 높임)
    if any(kw in q_lower for kw in ["파이프라인", "pipeline", "모델 성능", "모델 비교", "모델", "앙상블", "ensemble", "step 4", "step 5", "ml", "dl", "랭킹", "스피어만", "spearman"]):
        return "pipeline_models"
    if any(kw in q_lower for kw in ["metabric", "외부 검증", "검증", "step 6", "메타브릭"]):
        return "pipeline_metabric"
    if any(kw in q_lower for kw in ["admet", "안전성", "안전", "step 7", "독성"]):
        return "pipeline_admet"
    if any(kw in q_lower for kw in ["최종 후보", "후보", "top 5", "top5", "top", "candidate", "step 7+", "추천", "약물 목록", "신약", "재창출"]):
        return "pipeline_candidates"
    # KG 통계
    if any(kw in q_lower for kw in ["knowledge graph", "kg", "그래프 통계", "노드", "엣지", "node", "edge", "kg 통계", "데이터베이스 통계"]):
        return "kg_stats"
    # v1 intents
    if any(kw in q_lower for kw in ["부작용", "side effect", "adverse"]):
        return "side_effects"
    if any(kw in q_lower for kw in ["임상", "trial", "clinical", "kct", "nct"]):
        return "trials"
    if any(kw in q_lower for kw in ["타겟", "target", "표적", "작용기전"]):
        return "targets"
    if any(kw in q_lower for kw in ["pathway", "경로", "신호전달"]):
        return "pathways"
    if any(kw in q_lower for kw in ["병원", "hospital", "의료기관"]):
        return "hospitals"
    if any(kw in q_lower for kw in ["통계", "환자수", "발생률"]):
        return "disease_stats"
    if any(kw in q_lower for kw in ["예방", "검진", "screening"]):
        return "prevention"
    if any(kw in q_lower for kw in ["뉴스", "news", "최신"]):
        return "news"
    if any(kw in q_lower for kw in ["음식", "식단", "운동", "생활"]):
        return "lifestyle"
    return "drug_info"


@app.post("/api/chat")
def chat(req: ChatRequest):
    query = req.query.strip()
    if not query:
        raise HTTPException(400, "query is empty")

    drug_name = _extract_drug_from_query(query)
    intent = _classify_intent(query)
    source = "neo4j"
    data = {}
    answer = ""

    # v2 파이프라인 응답
    if intent == "pipeline_models":
        source = "pipeline"
        best_ml = ML_MODELS[0]
        best_dl = DL_MODELS[0]
        data = {"ml_models": ML_MODELS, "dl_models": DL_MODELS, "ensemble": ENSEMBLE_RESULT}
        answer = (
            f"ML/DL 파이프라인 결과 — "
            f"Best ML: {best_ml['name']} (Spearman {best_ml['spearman']}), "
            f"Best DL: {best_dl['name']} (Spearman {best_dl['spearman']}), "
            f"Ensemble Spearman: {ENSEMBLE_RESULT['weighted_spearman']}"
        )

    elif intent == "pipeline_metabric":
        source = "pipeline"
        data = METABRIC_RESULTS
        answer = (
            f"METABRIC 외부 검증 — 타겟 발현: {METABRIC_RESULTS['target_expressed']}, "
            f"BRCA 경로: {METABRIC_RESULTS['brca_pathway']}, "
            f"생존 유의: {METABRIC_RESULTS['survival_significant']}, "
            f"P@15: {METABRIC_RESULTS['p15_precision']}"
        )

    elif intent == "pipeline_admet":
        source = "pipeline"
        data = ADMET_SUMMARY
        answer = (
            f"ADMET 안전성 요약 — 현재 사용: {ADMET_SUMMARY['current_use']}, "
            f"확장/연구 중: {ADMET_SUMMARY['expansion']}, "
            f"미사용 후보: {ADMET_SUMMARY['unused']}, "
            f"분석 항목: {ADMET_SUMMARY['assays']}개"
        )

    elif intent == "pipeline_candidates":
        source = "pipeline"
        top5 = FINAL_CANDIDATES[:5]
        data = {"candidates": top5}
        names = ", ".join(d["name"] for d in top5)
        answer = f"Top 5 최종 후보: {names}"

    # v1 기존 응답
    elif intent == "side_effects" and drug_name:
        rows = neo4j_query(
            "MATCH (d:Drug {name: $name})-[:HAS_SIDE_EFFECT]->(s:SideEffect) "
            "RETURN s.name AS name, s.meddra_term AS meddra_term",
            name=drug_name,
        )
        data = {"drug": drug_name, "side_effects": rows}
        answer = f"{drug_name}의 주요 부작용: {', '.join(r['name'] for r in rows[:5])}" if rows else f"{drug_name}의 부작용 데이터가 없습니다."

    elif intent == "trials" and drug_name:
        rows = neo4j_query(
            "MATCH (d:Drug {name: $name})-[:IN_TRIAL]->(t:Trial) "
            "RETURN t.nct_id AS nct_id, t.title AS title, t.phase AS phase, t.status AS status, t.sponsor AS sponsor",
            name=drug_name,
        )
        data = {"drug": drug_name, "trials": rows}
        answer = f"{drug_name} 관련 임상시험: {len(rows)}건" if rows else f"{drug_name} 임상시험 데이터 없음."

    elif intent == "targets" and drug_name:
        rows = neo4j_query(
            "MATCH (d:Drug {name: $name})-[:TARGETS]->(t:Target) "
            "RETURN t.gene_symbol AS gene, t.protein_name AS protein",
            name=drug_name,
        )
        data = {"drug": drug_name, "targets": rows}
        answer = f"{drug_name}의 타겟: {', '.join(r['gene'] for r in rows if r['gene'])}" if rows else f"{drug_name} 타겟 데이터 없음."

    elif intent == "pathways" and drug_name:
        # Neo4j에서 pathway 조회
        rows = neo4j_query(
            "MATCH (d:Drug {name: $name})-[:TARGETS]->(t:Target)-[:IN_PATHWAY]->(p:Pathway) "
            "RETURN DISTINCT p.name AS name, p.collection AS collection",
            name=drug_name,
        )

        # 약물 데이터에서 pathway 정보 가져오기 (fallback)
        drug_candidate = next((d for d in FINAL_CANDIDATES if d["name"] == drug_name), None)
        pathway_from_data = drug_candidate.get("pathway") if drug_candidate else None

        # 외부 API에서 pathway 검색 (enrichment)
        external_pathways = None
        if pathway_from_data:
            try:
                from pathway_apis import search_all_pathways
                external_pathways = search_all_pathways(pathway_from_data)
            except Exception as e:
                print(f"[Pathway API Error] {e}")

        # 응답 생성
        if rows:
            pathway_list = [f"• {r['name']} ({r.get('collection', 'MSigDB')})" for r in rows[:5]]
            answer = f"**{drug_name} 관련 Pathways** ({len(rows)}개)\n\n" + "\n".join(pathway_list)
            if len(rows) > 5:
                answer += f"\n\n외 {len(rows)-5}개 더 있습니다."
        elif pathway_from_data:
            answer = f"**{drug_name} 주요 Pathway**: {pathway_from_data}\n\n"
            if external_pathways:
                # KEGG
                if external_pathways.get('kegg'):
                    kegg = external_pathways['kegg']
                    answer += f"🧬 **KEGG**: {kegg['name']}\n→ {kegg['image_url']}\n\n"
                # Reactome
                if external_pathways.get('reactome'):
                    answer += f"🔬 **Reactome**: {len(external_pathways['reactome'])}개 pathway 발견\n"
                    for rp in external_pathways['reactome'][:3]:
                        answer += f"• {rp['displayName']}\n"
                    answer += f"\n💡 상세 정보는 `/api/pathways/search?query={pathway_from_data}` 참조"
        else:
            answer = f"⚠️ {drug_name}의 pathway 정보를 찾을 수 없습니다.\n\n💡 약물 리스트: Docetaxel, Paclitaxel, Romidepsin 등"

        data = {
            "drug": drug_name,
            "pathways_neo4j": rows,
            "pathway_name": pathway_from_data,
            "external": external_pathways
        }

    elif intent == "pathways" and not drug_name:
        # 약물 이름 없이 pathway 질문한 경우 - 일반적인 pathway 검색 안내
        # 쿼리에서 pathway 이름 추출 시도
        common_pathways = ["PI3K", "Apoptosis", "Cell cycle", "MAPK", "mTOR", "Wnt"]
        detected_pathway = None
        for pw in common_pathways:
            if pw.lower() in query.lower():
                detected_pathway = pw
                break

        if detected_pathway:
            # 검색된 pathway로 외부 API 조회
            try:
                from pathway_apis import search_all_pathways
                external_results = search_all_pathways(detected_pathway)

                answer = f"**{detected_pathway} Pathway 정보**\n\n"

                if external_results.get('kegg'):
                    kegg = external_results['kegg']
                    answer += f"🧬 **KEGG**: {kegg['name']}\n→ {kegg['image_url']}\n\n"

                if external_results.get('reactome'):
                    answer += f"🔬 **Reactome**: {len(external_results['reactome'])}개 발견\n"
                    for rp in external_results['reactome'][:3]:
                        answer += f"• {rp['displayName']}\n"

                data = {"pathway": detected_pathway, "results": external_results}
            except Exception as e:
                answer = f"Pathway 검색 중 오류: {str(e)}"
                data = {"error": str(e)}
        else:
            answer = "**Pathway 검색 방법**\n\n특정 pathway를 검색하려면:\n• 'PI3K pathway'\n• 'Apoptosis 경로'\n• 'Cell cycle pathway'\n\n또는 약물과 함께:\n• 'Docetaxel pathway'\n• 'Romidepsin 경로'"
            data = {"hint": "pathway 이름 또는 약물 이름을 포함해주세요"}

    elif intent == "kg_stats":
        # Knowledge Graph 통계
        try:
            node_rows = neo4j_query("MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count")
            rel_rows = neo4j_query("MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count")
            if node_rows or rel_rows:
                total_nodes = sum(r["count"] for r in node_rows)
                total_edges = sum(r["count"] for r in rel_rows)
                data = {"nodes": node_rows, "relationships": rel_rows, "total_nodes": total_nodes, "total_edges": total_edges}
                answer = f"Knowledge Graph 통계 — 전체 노드: {total_nodes}, 전체 엣지: {total_edges}"
            else:
                answer = "⚠️ Neo4j 데이터베이스가 비어있습니다. 파이프라인 데이터를 사용해보세요!\n\n• 최종 후보 Top 5\n• METABRIC 검증 결과\n• ADMET 안전성"
                data = {"hint": "Neo4j 데이터 없음. 파이프라인 기능 사용 권장"}
        except Exception as e:
            answer = f"⚠️ KG 통계 조회 실패: {str(e)}\n파이프라인 데이터는 정상 작동합니다."
            data = {"error": str(e)}

    elif intent == "hospitals":
        rows = neo4j_query(
            "MATCH (h:Hospital) RETURN h.name AS name, h.region AS region, "
            "h.specialty AS specialty, h.phone AS phone ORDER BY h.name LIMIT 20"
        )
        data = {"hospitals": rows}
        if rows:
            answer = f"유방암 치료 병원: {', '.join(r['name'] for r in rows[:5])} 등 {len(rows)}개"
        else:
            answer = "⚠️ 병원 데이터가 Neo4j에 없습니다. 파이프라인 약물 정보는 사용 가능합니다."
            data = {"hint": "Neo4j 병원 데이터 없음"}

    elif intent == "prevention":
        # 예방/검진 정보
        source = "static"
        data = {
            "screening": ["유방촬영술(Mammography) - 40세 이상 1-2년마다", "유방 초음파 - 고위험군", "유방 MRI - BRCA 유전자 변이"],
            "risk_factors": ["가족력", "BRCA1/BRCA2 유전자 변이", "조기 초경/늦은 폐경", "비만", "음주", "호르몬 치료"],
            "prevention": ["정기 검진", "건강한 체중 유지", "운동 (주 150분)", "음주 제한", "금연"]
        }
        answer = (
            "**유방암 예방 가이드**\n\n"
            "**정기 검진:**\n• 40세 이상: 유방촬영술 1-2년마다\n• 고위험군: 유방 초음파, MRI\n\n"
            "**예방 수칙:**\n• 건강한 체중 유지\n• 주 150분 이상 운동\n• 음주 제한, 금연\n• 정기 검진"
        )

    elif intent == "lifestyle":
        # 생활습관/음식 정보
        source = "static"
        data = {
            "recommended_foods": ["채소·과일", "통곡물", "생선", "콩류", "견과류"],
            "avoid_foods": ["가공육", "붉은 고기 과다섭취", "고칼로리 음식", "술"],
            "exercise": ["유산소 운동 주 150분", "근력 운동 주 2회", "일상 활동량 증가"]
        }
        answer = (
            "**유방암 환자 생활 가이드**\n\n"
            "**추천 식단:**\n• 채소·과일, 통곡물\n• 생선, 콩류, 견과류\n\n"
            "**피할 음식:**\n• 가공육, 붉은 고기 과다\n• 고칼로리 음식, 술\n\n"
            "**운동:**\n• 유산소 주 150분\n• 근력 운동 주 2회"
        )

    elif intent == "news":
        # 뉴스/최신 정보
        source = "static"
        data = {"hint": "LLM 모듈 필요"}
        answer = (
            "**최신 유방암 연구 동향**\n\n"
            "• **파이프라인 연구**: ML/DL 기반 약물 재창출\n"
            "• **타겟 치료**: HDAC, BIRC5, CDK 억제제\n"
            "• **정밀 의료**: METABRIC 기반 생존 예측\n\n"
            "*자세한 최신 뉴스는 LLM 모듈이 필요합니다.*"
        )

    elif intent == "disease_stats":
        # 질병 통계
        source = "static"
        data = {
            "incidence": "여성암 1위",
            "annual_cases": "약 28,000건 (2020년 기준)",
            "survival_rate": "5년 생존율 93.6%",
            "age": "40-60대 호발"
        }
        answer = (
            "**유방암 통계**\n\n"
            "• 여성암 발생률 1위\n"
            "• 연간 약 28,000건 (2020년)\n"
            "• 5년 생존율: 93.6%\n"
            "• 호발 연령: 40-60대"
        )

    elif drug_name:
        # 파이프라인 후보에서 먼저 찾기
        cand = next((d for d in FINAL_CANDIDATES if d["name"] == drug_name), None)
        if cand:
            source = "pipeline"
            data = cand
            answer = (
                f"{drug_name} — IC50: {cand['ic50']}, 안전성: {cand['safety']}, "
                f"종합점수: {cand['combined']}, 분류: {cand['category']}"
            )
        else:
            rows = neo4j_query("MATCH (d:Drug {name: $name}) RETURN d", name=drug_name)
            if rows:
                node = dict(rows[0]["d"])
                data = node
                answer = f"{drug_name} — IC50={node.get('ic50', 'N/A')}, 종합={node.get('overall_score', 'N/A')}"
            else:
                answer = f"{drug_name} 정보가 KG에 없습니다."
    else:
        # 인식되지 않은 쿼리 - 사용 가능한 질문 예시 제공
        if req.user_type == "researcher":
            answer = "💡 **연구자 모드** 추천 질문:\n\n• 최종 후보 Top 5\n• 파이프라인 모델 성능\n• METABRIC 검증 결과\n• ADMET 안전성\n• Knowledge Graph 통계\n\n*참고: 현재 Neo4j 데이터는 비어있어 파이프라인 데이터 위주로 답변됩니다.*"
        else:
            answer = "💡 **환자/보호자 모드** 추천 질문:\n\n• 유방암 표준요법 약물\n• Docetaxel 부작용\n• 서울 유방암 병원\n• 유방암 예방 가이드\n• 파이프라인 약물 랭킹\n\n*더 구체적인 질문을 입력해주세요.*"
        data = {"hint": "구체적인 질문 필요", "recognized_intent": intent, "query": query, "user_type": req.user_type}
        print(f"[DEBUG] 인식되지 않은 쿼리: '{query}' → intent: {intent}, drug: {drug_name}, user_type: {req.user_type}")

    return make_response(
        {"answer": answer, "detail": data, "intent": intent, "drug": drug_name},
        source=source,
    )


# ── 서버 실행 ──
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server_v2:app", host="0.0.0.0", port=8000, reload=True)
