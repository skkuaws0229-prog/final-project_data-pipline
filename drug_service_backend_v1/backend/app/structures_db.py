from pathlib import Path

from app.config import settings
from app.db import fetch_all, fetch_one


def build_context_summary(context_links: list[dict]) -> dict:
    diseases = sorted({link["disease_id"] for link in context_links if link.get("disease_id")})
    drugs = {link.get("canonical_drug_id") or link.get("drug_name") for link in context_links if link.get("canonical_drug_id") or link.get("drug_name")}
    target_source_counts: dict[str, int] = {}
    for link in context_links:
        source = link.get("target_source") or "unknown"
        target_source_counts[source] = target_source_counts.get(source, 0) + 1
    return {
        "total_links": len(context_links),
        "diseases": diseases,
        "disease_count": len(diseases),
        "drug_count": len(drugs),
        "evidence_count": sum(1 for link in context_links if link.get("evidence_id")),
        "candidate_target_count": target_source_counts.get("candidate_target", 0),
        "image_evidence_count": target_source_counts.get("image_evidence", 0),
        "target_source_counts": target_source_counts,
    }


def list_structure_targets(disease_id: str | None = None, q: str | None = None, limit: int = 100) -> list[dict]:
    filters = []
    params: dict[str, object] = {"limit": limit}
    if disease_id:
        filters.append(
            """
            EXISTS (
              SELECT 1
              FROM regexp_split_to_table(COALESCE(tpl.raw_json->>'diseases', ''), '\\|') AS disease(value)
              WHERE disease.value = %(disease_id)s
            )
            """
        )
        params["disease_id"] = disease_id
    if q:
        filters.append(
            """
            (
              pt.gene_symbol ILIKE %(query)s OR
              pt.uniprot_id ILIKE %(query)s OR
              pt.protein_name ILIKE %(query)s OR
              tpl.target_text ILIKE %(query)s
            )
            """
        )
        params["query"] = f"%{q}%"

    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = fetch_all(
        f"""
        WITH structure_status AS (
          SELECT
            protein_id,
            bool_or(status = 'available') AS has_available_structure,
            count(*) AS structure_count
          FROM alphafold_structures
          GROUP BY protein_id
        ),
        expanded AS (
          SELECT
            pt.protein_id,
            pt.gene_symbol,
            pt.uniprot_id,
            pt.protein_name,
            pt.organism,
            pt.source,
            tpl.target_text,
            tpl.mapping_status,
            tpl.confidence,
            NULLIF(disease.value, '') AS disease_id,
            COALESCE(ss.structure_count, 0) AS structure_count,
            CASE
              WHEN COALESCE(ss.has_available_structure, false) THEN 'available'
              WHEN COALESCE(ss.structure_count, 0) > 0 THEN 'pending'
              ELSE 'not_loaded'
            END AS structure_status
          FROM protein_targets pt
          JOIN target_protein_links tpl ON tpl.protein_id = pt.protein_id
          LEFT JOIN structure_status ss ON ss.protein_id = pt.protein_id
          LEFT JOIN LATERAL regexp_split_to_table(COALESCE(tpl.raw_json->>'diseases', ''), '\\|') AS disease(value) ON true
          {where_sql}
        )
        SELECT
          protein_id,
          gene_symbol,
          uniprot_id,
          protein_name,
          organism,
          source,
          array_remove(array_agg(DISTINCT target_text ORDER BY target_text), NULL) AS target_texts,
          array_remove(array_agg(DISTINCT mapping_status ORDER BY mapping_status), NULL) AS mapping_statuses,
          array_remove(array_agg(DISTINCT disease_id ORDER BY disease_id), NULL) AS diseases,
          max(structure_count) AS structure_count,
          CASE
            WHEN bool_or(structure_status = 'available') THEN 'available'
            WHEN bool_or(structure_status = 'pending') THEN 'pending'
            ELSE 'not_loaded'
          END AS structure_status
        FROM expanded
        GROUP BY protein_id, gene_symbol, uniprot_id, protein_name, organism, source
        ORDER BY gene_symbol NULLS LAST, uniprot_id NULLS LAST
        LIMIT %(limit)s
        """,
        params,
    )
    return [dict(row) for row in rows]


def list_structures(disease_id: str | None = None, q: str | None = None, limit: int = 100) -> list[dict]:
    filters = []
    params: dict[str, object] = {"limit": limit}
    if disease_id:
        filters.append(
            """
            EXISTS (
              SELECT 1
              FROM candidate_protein_structure_links cpsl
              WHERE cpsl.structure_id = afs.structure_id
                AND cpsl.disease_id = %(disease_id)s
            )
            """
        )
        params["disease_id"] = disease_id
    if q:
        filters.append(
            """
            (
              pt.gene_symbol ILIKE %(query)s OR
              pt.uniprot_id ILIKE %(query)s OR
              pt.protein_name ILIKE %(query)s
            )
            """
        )
        params["query"] = f"%{q}%"
    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = fetch_all(
        f"""
        WITH target_context AS (
          SELECT
            tpl.protein_id,
            array_remove(array_agg(DISTINCT tpl.target_text ORDER BY tpl.target_text), NULL) AS target_texts,
            array_remove(array_agg(DISTINCT NULLIF(disease.value, '') ORDER BY NULLIF(disease.value, '')), NULL) AS diseases
          FROM target_protein_links tpl
          LEFT JOIN LATERAL regexp_split_to_table(COALESCE(tpl.raw_json->>'diseases', ''), '\\|') AS disease(value) ON true
          GROUP BY tpl.protein_id
        ),
        structure_context AS (
          SELECT
            cpsl.structure_id,
            jsonb_agg(
              jsonb_build_object(
                'disease_id', cpsl.disease_id,
                'candidate_id', cpsl.candidate_id,
                'evidence_id', cpsl.evidence_id,
                'canonical_drug_id', cpsl.canonical_drug_id,
                'drug_name', COALESCE(cd.primary_drug_name, d.drug_name, ime.drug_name),
                'target_source', cpsl.target_source
              )
              ORDER BY cpsl.disease_id, cpsl.target_source, cpsl.context_id
            ) AS context_links
          FROM candidate_protein_structure_links cpsl
          LEFT JOIN canonical_drugs cd ON cd.canonical_drug_id = cpsl.canonical_drug_id
          LEFT JOIN drug_candidates dc ON dc.candidate_id = cpsl.candidate_id
          LEFT JOIN drugs d ON d.drug_id = dc.drug_id
          LEFT JOIN image_modal_drug_evidence ime ON ime.evidence_id = cpsl.evidence_id
          GROUP BY cpsl.structure_id
        )
        SELECT
          afs.structure_id,
          afs.protein_id,
          pt.gene_symbol,
          pt.uniprot_id,
          pt.protein_name,
          afs.file_format,
          CASE
            WHEN afs.status = 'available' THEN 'available'
            WHEN afs.status = 'to_fetch' THEN 'pending'
            WHEN afs.status = 'missing' THEN 'missing'
            ELSE 'failed'
          END AS structure_status,
          afs.mean_plddt,
          afs.file_size_bytes,
          COALESCE(tc.diseases, ARRAY[]::text[]) AS diseases,
          COALESCE(tc.target_texts, ARRAY[]::text[]) AS target_texts,
          COALESCE(sc.context_links, '[]'::jsonb) AS context_links
        FROM alphafold_structures afs
        JOIN protein_targets pt ON pt.protein_id = afs.protein_id
        LEFT JOIN target_context tc ON tc.protein_id = afs.protein_id
        LEFT JOIN structure_context sc ON sc.structure_id = afs.structure_id
        {where_sql}
        ORDER BY pt.gene_symbol NULLS LAST, pt.uniprot_id NULLS LAST
        LIMIT %(limit)s
        """,
        params,
    )
    results = []
    for row in rows:
        item = dict(row)
        context_links = item.pop("context_links") or []
        item["context_summary"] = build_context_summary(context_links)
        item["file_endpoint"] = f"/api/structures/{item['structure_id']}/file"
        results.append(item)
    return results


def get_structure_detail(structure_id: str) -> dict | None:
    row = fetch_one(
        """
        WITH target_context AS (
          SELECT
            tpl.protein_id,
            array_remove(array_agg(DISTINCT tpl.target_text ORDER BY tpl.target_text), NULL) AS target_texts,
            array_remove(array_agg(DISTINCT tpl.mapping_status ORDER BY tpl.mapping_status), NULL) AS mapping_statuses,
            array_remove(array_agg(DISTINCT NULLIF(disease.value, '') ORDER BY NULLIF(disease.value, '')), NULL) AS diseases,
            jsonb_agg(
              DISTINCT jsonb_build_object(
                'target_text', tpl.target_text,
                'mapping_status', tpl.mapping_status,
                'confidence', tpl.confidence,
                'diseases', COALESCE(tpl.raw_json->>'diseases', ''),
                'source', tpl.source,
                'raw_json', tpl.raw_json
              )
            ) AS target_links
          FROM target_protein_links tpl
          LEFT JOIN LATERAL regexp_split_to_table(COALESCE(tpl.raw_json->>'diseases', ''), '\\|') AS disease(value) ON true
          GROUP BY tpl.protein_id
        ),
        structure_context AS (
          SELECT
            cpsl.structure_id,
            jsonb_agg(
              jsonb_build_object(
                'context_id', cpsl.context_id,
                'disease_id', cpsl.disease_id,
                'candidate_id', cpsl.candidate_id,
                'evidence_id', cpsl.evidence_id,
                'canonical_drug_id', cpsl.canonical_drug_id,
                'drug_name', COALESCE(cd.primary_drug_name, d.drug_name, ime.drug_name),
                'target_source', cpsl.target_source,
                'relation_note', cpsl.relation_note
              )
              ORDER BY cpsl.disease_id, cpsl.target_source, cpsl.context_id
            ) AS context_links
          FROM candidate_protein_structure_links cpsl
          LEFT JOIN canonical_drugs cd ON cd.canonical_drug_id = cpsl.canonical_drug_id
          LEFT JOIN drug_candidates dc ON dc.candidate_id = cpsl.candidate_id
          LEFT JOIN drugs d ON d.drug_id = dc.drug_id
          LEFT JOIN image_modal_drug_evidence ime ON ime.evidence_id = cpsl.evidence_id
          GROUP BY cpsl.structure_id
        )
        SELECT
          afs.structure_id,
          afs.protein_id,
          pt.gene_symbol,
          pt.uniprot_id,
          pt.protein_name,
          pt.organism,
          pt.source AS protein_source,
          afs.provider,
          afs.provider_accession,
          afs.version,
          afs.file_format,
          afs.structure_uri,
          afs.structure_source_uri,
          afs.file_size_bytes,
          afs.checksum_sha256,
          afs.source_url,
          afs.pae_uri,
          afs.mean_plddt,
          afs.confidence_summary,
          afs.license,
          afs.status,
          CASE
            WHEN afs.status = 'available' THEN 'available'
            WHEN afs.status = 'to_fetch' THEN 'pending'
            WHEN afs.status = 'missing' THEN 'missing'
            ELSE 'failed'
          END AS structure_status,
          COALESCE(tc.target_texts, ARRAY[]::text[]) AS target_texts,
          COALESCE(tc.mapping_statuses, ARRAY[]::text[]) AS mapping_statuses,
          COALESCE(tc.diseases, ARRAY[]::text[]) AS diseases,
          COALESCE(tc.target_links, '[]'::jsonb) AS target_links,
          COALESCE(sc.context_links, '[]'::jsonb) AS context_links
        FROM alphafold_structures afs
        JOIN protein_targets pt ON pt.protein_id = afs.protein_id
        LEFT JOIN target_context tc ON tc.protein_id = afs.protein_id
        LEFT JOIN structure_context sc ON sc.structure_id = afs.structure_id
        WHERE afs.structure_id = %(structure_id)s
        """,
        {"structure_id": structure_id},
    )
    if not row:
        return None
    result = dict(row)
    context_links = result.get("context_links") or []
    result["context_summary"] = build_context_summary(context_links)
    return result


def get_structure_file_metadata(structure_id: str) -> dict | None:
    row = fetch_one(
        """
        SELECT
          afs.structure_id,
          afs.protein_id,
          pt.uniprot_id,
          pt.gene_symbol,
          afs.file_format,
          afs.structure_uri,
          afs.structure_source_uri,
          afs.file_size_bytes,
          afs.checksum_sha256,
          afs.status
        FROM alphafold_structures afs
        JOIN protein_targets pt ON pt.protein_id = afs.protein_id
        WHERE afs.structure_id = %(structure_id)s
        """,
        {"structure_id": structure_id},
    )
    return dict(row) if row else None


def resolve_structure_cache_path(structure_row: dict) -> Path:
    uri = structure_row.get("structure_uri") or ""
    cache_root = Path(settings.alphafold_structure_cache_dir)
    marker = "/drug_service_build/11_structures/"
    if uri.startswith("s3://") and marker in uri:
        return cache_root / uri.split(marker, 1)[1]

    uniprot_id = str(structure_row.get("uniprot_id") or "").upper()
    filename = Path(uri).name if uri else f"{structure_row['structure_id']}.{structure_row.get('file_format', 'cif')}"
    return cache_root / "alphafold" / uniprot_id / filename
