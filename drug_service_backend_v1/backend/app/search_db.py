from opensearchpy import OpenSearch

from app.config import settings


_client: OpenSearch | None = None


def get_client() -> OpenSearch:
    global _client
    if _client is None:
        _client = OpenSearch(
            hosts=[settings.opensearch_url],
            use_ssl=settings.opensearch_url.startswith("https://"),
            verify_certs=False,
            timeout=10,
        )
    return _client


def verify_search_connectivity() -> dict:
    return get_client().cluster.health()


def search_text(
    query: str,
    disease_id: str | None = None,
    doc_type: str | None = None,
    limit: int = 20,
) -> dict:
    filters: list[dict] = []
    if disease_id:
        filters.append({"term": {"disease_id": disease_id}})
    if doc_type:
        filters.append({"term": {"doc_type": doc_type}})

    body = {
        "size": limit,
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                "title^3",
                                "drug_name^3",
                                "target^2",
                                "target_pathway^2",
                                "evidence_text^2",
                                "report_text",
                                "clinical_summary",
                                "pathway_summary",
                                "source_file",
                            ],
                            "type": "best_fields",
                            "operator": "and",
                        }
                    }
                ],
                "filter": filters,
            }
        },
        "highlight": {
            "fields": {
                "title": {},
                "drug_name": {},
                "target": {},
                "target_pathway": {},
                "evidence_text": {},
                "report_text": {},
                "clinical_summary": {},
                "pathway_summary": {},
            },
            "fragment_size": 160,
            "number_of_fragments": 2,
        },
    }
    return get_client().search(index=settings.opensearch_index, body=body)
