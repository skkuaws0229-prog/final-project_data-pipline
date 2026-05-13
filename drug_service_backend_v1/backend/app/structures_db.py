from app.db import fetch_all


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
