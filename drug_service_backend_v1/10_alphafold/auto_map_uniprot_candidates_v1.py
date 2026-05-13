from __future__ import annotations

import csv
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALPHAFOLD = ROOT / "10_alphafold"
UNIPROT_SEARCH_URL = "https://rest.uniprot.org/uniprotkb/search"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def query_uniprot(gene_symbol: str, reviewed: bool = True, size: int = 5) -> dict:
    reviewed_clause = " AND reviewed:true" if reviewed else ""
    query = f"(gene_exact:{gene_symbol}) AND (organism_id:9606){reviewed_clause}"
    params = {
        "query": query,
        "fields": "accession,id,gene_names,protein_name,organism_name,reviewed,length",
        "format": "json",
        "size": str(size),
    }
    url = f"{UNIPROT_SEARCH_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "drug-service-build-target-mapper/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def result_summary(result: dict) -> tuple[str, str, str, str, str, str]:
    rows = result.get("results", [])
    if not rows:
        return "", "", "", "", "0", "no_reviewed_human_gene_exact_hit"
    first = rows[0]
    accession = first.get("primaryAccession", "")
    entry_name = first.get("uniProtkbId", "")
    genes = first.get("genes", [])
    primary_gene = ""
    all_gene_names: list[str] = []
    for gene in genes:
        gene_name = gene.get("geneName", {}).get("value")
        if gene_name and not primary_gene:
            primary_gene = gene_name
        if gene_name:
            all_gene_names.append(gene_name)
        for syn in gene.get("synonyms", []):
            value = syn.get("value")
            if value:
                all_gene_names.append(value)
    protein_name = (
        first.get("proteinDescription", {})
        .get("recommendedName", {})
        .get("fullName", {})
        .get("value", "")
    )
    return accession, entry_name, primary_gene, protein_name, str(len(rows)), "|".join(dict.fromkeys(all_gene_names))


def collect_mapping_targets() -> list[dict[str, str]]:
    priority_rows = read_csv(ALPHAFOLD / "target_priority_for_structure_v1.csv")
    alias_rows = read_csv(ALPHAFOLD / "alias_resolution_review_v1.csv")

    targets: dict[str, dict[str, str]] = {}
    for row in priority_rows:
        if row["priority"] not in {"P1", "P2"}:
            continue
        gene = row["suggested_gene_symbol"].strip()
        if not gene:
            continue
        key = gene.upper()
        targets[key] = {
            "source": "priority",
            "priority": row["priority"],
            "raw_text": row["target_text"],
            "suggested_gene_symbol": gene,
            "mentions": row["mentions"],
            "diseases": row["diseases"],
            "candidate_class": row["candidate_class"],
        }

    for row in alias_rows:
        gene = row["suggested_gene_symbol"].strip()
        if not gene:
            continue
        key = gene.upper()
        existing = targets.get(key)
        if existing:
            existing["source"] = f"{existing['source']}|alias_review"
            existing["raw_text"] = f"{existing['raw_text']}|{row['raw_text']}"
            continue
        targets[key] = {
            "source": "alias_review",
            "priority": "P2_alias",
            "raw_text": row["raw_text"],
            "suggested_gene_symbol": gene,
            "mentions": row["mentions"],
            "diseases": row["diseases"],
            "candidate_class": row["candidate_class"],
        }

    return sorted(targets.values(), key=lambda r: (r["priority"], r["suggested_gene_symbol"]))


def main() -> None:
    targets = collect_mapping_targets()
    rows: list[dict[str, str]] = []
    failures: list[str] = []
    for target in targets:
        gene = target["suggested_gene_symbol"]
        try:
            result = query_uniprot(gene, reviewed=True)
            accession, entry_name, primary_gene, protein_name, hit_count, gene_names = result_summary(result)
            status = "auto_suggested" if accession and primary_gene.upper() == gene.upper() and hit_count == "1" else "needs_review"
            if accession and primary_gene.upper() == gene.upper() and hit_count != "1":
                status = "needs_review_multi_hit"
            if not accession:
                status = "unresolved"
            rows.append(
                {
                    **target,
                    "auto_uniprot_id": accession,
                    "uniprot_entry_name": entry_name,
                    "uniprot_primary_gene": primary_gene,
                    "uniprot_gene_names": gene_names,
                    "protein_name": protein_name,
                    "hit_count": hit_count,
                    "auto_mapping_status": status,
                    "mapping_notes": "reviewed human gene_exact query",
                }
            )
        except Exception as exc:  # noqa: BLE001 - write failures to review CSV
            failures.append(f"{gene}: {exc}")
            rows.append(
                {
                    **target,
                    "auto_uniprot_id": "",
                    "uniprot_entry_name": "",
                    "uniprot_primary_gene": "",
                    "uniprot_gene_names": "",
                    "protein_name": "",
                    "hit_count": "0",
                    "auto_mapping_status": "query_failed",
                    "mapping_notes": str(exc),
                }
            )
        time.sleep(0.15)

    write_csv(
        ALPHAFOLD / "uniprot_auto_mapping_candidates_v1.csv",
        [
            "source",
            "priority",
            "raw_text",
            "suggested_gene_symbol",
            "mentions",
            "diseases",
            "candidate_class",
            "auto_uniprot_id",
            "uniprot_entry_name",
            "uniprot_primary_gene",
            "uniprot_gene_names",
            "protein_name",
            "hit_count",
            "auto_mapping_status",
            "mapping_notes",
        ],
        rows,
    )

    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row["auto_mapping_status"]] = status_counts.get(row["auto_mapping_status"], 0) + 1
    summary = [
        "# UniProt 자동 매핑 후보 v1",
        "",
        "```text",
        f"input targets: {len(targets)}",
        *[f"{key}: {status_counts[key]}" for key in sorted(status_counts)],
        f"query failures: {len(failures)}",
        "```",
        "",
        "주의:",
        "",
        "```text",
        "UniProt 자동 조회 결과는 production 확정값이 아니다.",
        "AlphaFold DB API와 구조 다운로드는 실행하지 않았다.",
        "auto_mapping_status=auto_suggested row도 검토 후 reviewed seed로 승격한다.",
        "```",
    ]
    if failures:
        summary.extend(["", "## Query failures", "", "```text", *failures, "```"])
    (ALPHAFOLD / "uniprot_auto_mapping_summary_v1.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
