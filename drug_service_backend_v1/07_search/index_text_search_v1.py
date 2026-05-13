#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable


NORMALIZED_DIR = Path(os.environ.get("NORMALIZED_DIR", "/normalized"))
OPENSEARCH_URL = os.environ.get("OPENSEARCH_URL", "http://opensearch:9200").rstrip("/")
INDEX_NAME = os.environ.get("OPENSEARCH_INDEX", "drug_service_text_v1")


def request(method: str, path: str, body: dict | str | None = None, content_type: str = "application/json") -> dict:
    data = None
    if body is not None:
        data = body.encode("utf-8") if isinstance(body, str) else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{OPENSEARCH_URL}{path}",
        data=data,
        method=method,
        headers={"Content-Type": content_type},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def wait_for_opensearch() -> None:
    for _ in range(60):
        try:
            request("GET", "/_cluster/health")
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("OpenSearch did not become ready")


def read_csv(name: str) -> list[dict[str, str]]:
    with (NORMALIZED_DIR / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def build_documents() -> Iterable[tuple[str, dict]]:
    drugs = {row["drug_id"]: row for row in read_csv("drugs.csv")}
    aliases = {row["source_drug_id"]: row for row in read_csv("drug_aliases.csv")}
    admet = {row["candidate_id"]: row for row in read_csv("admet_results.csv")}
    clusters = {row["cluster_id"]: row for row in read_csv("image_modal_clusters.csv")}
    evidence_matches = {row["evidence_id"]: row for row in read_csv("image_modal_evidence_drug_matches.csv")}

    for row in read_csv("drug_candidates.csv"):
        drug = drugs.get(row["drug_id"], {})
        alias = aliases.get(row["drug_id"], {})
        admet_row = admet.get(row["candidate_id"], {})
        drug_name = drug.get("drug_name") or row["drug_id"]
        doc = {
            "doc_type": "drug_candidate",
            "document_id": row["candidate_id"],
            "disease_id": row["disease_id"],
            "drug_id": row["drug_id"],
            "canonical_drug_id": clean(alias.get("canonical_drug_id")),
            "drug_name": drug_name,
            "title": f"{row['disease_id']} candidate drug: {drug_name}",
            "rank": clean(row.get("rank")),
            "tier": clean(row.get("tier")),
            "score": clean(row.get("score")),
            "target": clean(row.get("target")),
            "target_pathway": clean(row.get("target_pathway")),
            "evidence_text": clean(row.get("evidence_summary")),
            "canonical_smiles": clean(drug.get("canonical_smiles")),
            "safety_score": clean(admet_row.get("safety_score")),
            "verdict": clean(admet_row.get("verdict")),
            "admet_status": clean(admet_row.get("admet_status")),
            "hard_fail": clean(admet_row.get("hard_fail")),
            "hard_fail_reasons": clean(admet_row.get("hard_fail_reasons")),
            "soft_flags": clean(admet_row.get("soft_flags")),
            "source_file": clean(row.get("source_file")),
        }
        yield row["candidate_id"], doc

    for row in read_csv("image_modal_drug_evidence.csv"):
        cluster = clusters.get(row["cluster_id"], {})
        match = evidence_matches.get(row["evidence_id"], {})
        doc = {
            "doc_type": "image_evidence",
            "document_id": row["evidence_id"],
            "disease_id": row["disease_id"],
            "cluster_id": clean(row.get("cluster_id")),
            "cluster_key": clean(cluster.get("cluster_key")),
            "cluster_label": clean(cluster.get("cluster_label")),
            "drug_id": clean(row.get("drug_id")),
            "canonical_drug_id": clean(match.get("canonical_drug_id")),
            "match_status": clean(match.get("match_status")),
            "drug_name": clean(row.get("drug_name")),
            "title": f"{row['disease_id']} image evidence: {row.get('drug_name') or row['evidence_id']}",
            "rank": clean(row.get("rank")),
            "tier": clean(row.get("tier")),
            "target": clean(row.get("target")),
            "target_pathway": clean(row.get("target_pathway")),
            "evidence_text": clean(row.get("evidence_text")),
            "clinical_summary": clean(cluster.get("clinical_summary")),
            "pathway_summary": clean(cluster.get("pathway_summary")),
            "source_file": clean(row.get("source_file")),
        }
        yield row["evidence_id"], doc

    for row in read_csv("image_modal_reports.csv"):
        doc = {
            "doc_type": "image_report",
            "document_id": row["report_id"],
            "disease_id": row["disease_id"],
            "title": clean(row.get("title")) or f"{row['disease_id']} {row['report_kind']} report",
            "report_kind": clean(row.get("report_kind")),
            "report_text": clean(row.get("report_text")),
            "source_file": clean(row.get("source_file")),
        }
        yield row["report_id"], doc


def create_index() -> None:
    try:
        request("DELETE", f"/{INDEX_NAME}")
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise

    mapping = {
        "settings": {
            "index": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
            },
            "analysis": {
                "analyzer": {
                    "drug_text_analyzer": {
                        "type": "standard",
                        "stopwords": "_english_",
                    }
                }
            },
        },
        "mappings": {
            "dynamic": True,
            "properties": {
                "doc_type": {"type": "keyword"},
                "document_id": {"type": "keyword"},
                "disease_id": {"type": "keyword"},
                "drug_id": {"type": "keyword"},
                "canonical_drug_id": {"type": "keyword"},
                "cluster_id": {"type": "keyword"},
                "match_status": {"type": "keyword"},
                "source_file": {"type": "keyword"},
                "title": {"type": "text", "analyzer": "drug_text_analyzer"},
                "drug_name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "target": {"type": "text", "analyzer": "drug_text_analyzer"},
                "target_pathway": {"type": "text", "analyzer": "drug_text_analyzer"},
                "evidence_text": {"type": "text", "analyzer": "drug_text_analyzer"},
                "report_text": {"type": "text", "analyzer": "drug_text_analyzer"},
                "clinical_summary": {"type": "text", "analyzer": "drug_text_analyzer"},
                "pathway_summary": {"type": "text", "analyzer": "drug_text_analyzer"},
            },
        },
    }
    request("PUT", f"/{INDEX_NAME}", mapping)


def bulk_index(documents: list[tuple[str, dict]]) -> None:
    lines = []
    for doc_id, doc in documents:
        lines.append(json.dumps({"index": {"_index": INDEX_NAME, "_id": doc_id}}, ensure_ascii=False))
        lines.append(json.dumps({k: v for k, v in doc.items() if v is not None}, ensure_ascii=False))
    payload = "\n".join(lines) + "\n"
    response = request("POST", "/_bulk", payload, content_type="application/x-ndjson")
    if response.get("errors"):
        raise RuntimeError(json.dumps(response, ensure_ascii=False)[:4000])


def main() -> None:
    wait_for_opensearch()
    create_index()
    documents = list(build_documents())
    bulk_index(documents)
    request("POST", f"/{INDEX_NAME}/_refresh")
    counts: dict[str, int] = {}
    for _, doc in documents:
        counts[doc["doc_type"]] = counts.get(doc["doc_type"], 0) + 1
    print(f"Indexed {len(documents)} documents into {INDEX_NAME}: {counts}")


if __name__ == "__main__":
    main()
