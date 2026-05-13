from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALPHAFOLD = ROOT / "10_alphafold"
DOCS = ROOT / "docs"
API_BASE_URL = "https://alphafold.ebi.ac.uk/api/prediction"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fetch_prediction(uniprot_id: str, timeout: int) -> tuple[int, list[dict]]:
    url = f"{API_BASE_URL}/{uniprot_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "drug-service-build-alphafold-metadata/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return 404, []
        raise


def structure_id(entry_id: str, uniprot_id: str, latest_version: str) -> str:
    if entry_id:
        base = entry_id.lower().replace("-", "_")
    else:
        base = f"af_{uniprot_id.lower()}_f1"
    version = latest_version or "unknown"
    return f"{base}_v{version}"


def first_value(row: dict, *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and value != "":
            return str(value)
    return ""


def build_metadata_rows(timeout: int, sleep_seconds: float) -> tuple[list[dict[str, str]], list[dict[str, object]]]:
    proteins = read_csv(ALPHAFOLD / "protein_targets_seed_reviewed_v1.csv")
    rows: list[dict[str, str]] = []
    raw_results: list[dict[str, object]] = []

    for protein in proteins:
        uniprot_id = protein["uniprot_id"]
        protein_id = protein["protein_id"]
        try:
            status_code, predictions = fetch_prediction(uniprot_id, timeout=timeout)
            raw_results.append({"uniprot_id": uniprot_id, "status_code": status_code, "response": predictions})
        except Exception as exc:  # noqa: BLE001 - write failures into review CSV
            rows.append(
                {
                    "structure_id": f"af_{uniprot_id.lower()}_lookup_failed",
                    "protein_id": protein_id,
                    "gene_symbol": protein["gene_symbol"],
                    "uniprot_id": uniprot_id,
                    "provider": "alphafold_db",
                    "provider_accession": uniprot_id,
                    "entry_id": "",
                    "version": "",
                    "file_format": "cif",
                    "structure_uri": "",
                    "source_url": f"https://alphafold.ebi.ac.uk/entry/{uniprot_id}",
                    "pae_uri": "",
                    "pdb_url": "",
                    "mean_plddt": "",
                    "confidence_summary": "",
                    "license": "CC-BY-4.0",
                    "status": "failed",
                    "api_status": "query_failed",
                    "model_created_date": "",
                    "notes": str(exc),
                }
            )
            continue

        if not predictions:
            rows.append(
                {
                    "structure_id": f"af_{uniprot_id.lower()}_missing",
                    "protein_id": protein_id,
                    "gene_symbol": protein["gene_symbol"],
                    "uniprot_id": uniprot_id,
                    "provider": "alphafold_db",
                    "provider_accession": uniprot_id,
                    "entry_id": "",
                    "version": "",
                    "file_format": "cif",
                    "structure_uri": "",
                    "source_url": f"https://alphafold.ebi.ac.uk/entry/{uniprot_id}",
                    "pae_uri": "",
                    "pdb_url": "",
                    "mean_plddt": "",
                    "confidence_summary": "",
                    "license": "CC-BY-4.0",
                    "status": "missing",
                    "api_status": f"http_{status_code}",
                    "model_created_date": "",
                    "notes": "No AlphaFold DB prediction returned for UniProt accession",
                }
            )
            time.sleep(sleep_seconds)
            continue

        canonical_entry_id = f"AF-{uniprot_id}-F1"
        selected_predictions = [prediction for prediction in predictions if first_value(prediction, "entryId") == canonical_entry_id]
        if not selected_predictions:
            selected_predictions = predictions[:1]

        for prediction in selected_predictions:
            latest_version = first_value(prediction, "latestVersion")
            entry_id = first_value(prediction, "entryId")
            cif_url = first_value(prediction, "cifUrl")
            pae_url = first_value(prediction, "paeDocUrl")
            excluded_count = max(len(predictions) - len(selected_predictions), 0)
            rows.append(
                {
                    "structure_id": structure_id(entry_id, uniprot_id, latest_version),
                    "protein_id": protein_id,
                    "gene_symbol": protein["gene_symbol"],
                    "uniprot_id": uniprot_id,
                    "provider": "alphafold_db",
                    "provider_accession": uniprot_id,
                    "entry_id": entry_id,
                    "version": f"v{latest_version}" if latest_version else "",
                    "file_format": "cif",
                    "structure_uri": cif_url,
                    "source_url": f"https://alphafold.ebi.ac.uk/entry/{entry_id or uniprot_id}",
                    "pae_uri": pae_url,
                    "pdb_url": first_value(prediction, "pdbUrl"),
                    "mean_plddt": first_value(prediction, "globalMetricValue", "meanPlddt"),
                    "confidence_summary": "metadata_available_download_not_performed",
                    "license": "CC-BY-4.0",
                    "status": "to_fetch",
                    "api_status": f"http_{status_code}",
                    "model_created_date": first_value(prediction, "modelCreatedDate"),
                    "notes": (
                        "AlphaFold DB canonical F1 metadata only; "
                        f"structure file not downloaded; excluded_noncanonical_entries={excluded_count}"
                    ),
                }
            )
        time.sleep(sleep_seconds)

    return rows, raw_results


def validate_rows(rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    ok_rows = [row for row in rows if row["status"] == "to_fetch"]
    structure_dupes = [key for key, count in Counter(row["structure_id"] for row in rows).items() if count > 1]
    protein_dupes = [key for key, count in Counter(row["protein_id"] for row in ok_rows).items() if count > 1]
    missing_uri = [row["uniprot_id"] for row in ok_rows if not row["structure_uri"]]
    bad_provider = [row["uniprot_id"] for row in rows if row["provider"] != "alphafold_db"]
    bad_file_format = [row["uniprot_id"] for row in rows if row["file_format"] not in {"cif", "pdb", "mmcif"}]
    bad_status = [row["uniprot_id"] for row in rows if row["status"] not in {"to_fetch", "missing", "failed"}]

    if structure_dupes:
        errors.append(f"structure_id duplicate: {structure_dupes}")
    if protein_dupes:
        errors.append(f"protein_id has multiple metadata rows: {protein_dupes}")
    if missing_uri:
        errors.append(f"to_fetch rows missing structure_uri: {missing_uri}")
    if bad_provider:
        errors.append(f"invalid provider: {bad_provider}")
    if bad_file_format:
        errors.append(f"invalid file_format: {bad_file_format}")
    if bad_status:
        errors.append(f"invalid status: {bad_status}")
    return errors


def write_summary(rows: list[dict[str, str]], errors: list[str]) -> None:
    status_counts = Counter(row["status"] for row in rows)
    api_counts = Counter(row["api_status"] for row in rows)
    canonical_count = sum(1 for row in rows if row["entry_id"] == f"AF-{row['uniprot_id']}-F1")
    lines = [
        "# AlphaFold DB Metadata 조회 검증 v1",
        "",
        "## 목적",
        "",
        "UniProt ID 27개 기준으로 AlphaFold DB prediction metadata 존재 여부만 확인했다.",
        "구조 파일 다운로드, PAE JSON 다운로드, S3 업로드, PostgreSQL 적재는 실행하지 않았다.",
        "",
        "## 기준 API",
        "",
        "```text",
        "https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}",
        "```",
        "",
        "## 생성 파일",
        "",
        "```text",
        "10_alphafold/alphafold_structures_seed_candidates_v1.csv",
        "10_alphafold/alphafold_metadata_raw_v1.json",
        "10_alphafold/alphafold_metadata_summary_v1.md",
        "```",
        "",
        "## Status Count",
        "",
        "| status | rows |",
        "| --- | ---: |",
        *[f"| {key} | {status_counts[key]} |" for key in sorted(status_counts)],
        "",
        "## Canonical Selection",
        "",
        "| 항목 | rows |",
        "| --- | ---: |",
        f"| canonical AF-{{UniProt}}-F1 selected | {canonical_count} |",
        f"| seed candidate rows | {len(rows)} |",
        "",
        "## API Status Count",
        "",
        "| api_status | rows |",
        "| --- | ---: |",
        *[f"| {key} | {api_counts[key]} |" for key in sorted(api_counts)],
        "",
        "## 무결성 결과",
        "",
    ]
    if errors:
        lines.extend(["```text", *errors, "```", "", "판정: 실패"])
    else:
        lines.extend(
            [
                "```text",
                "structure_id duplicate: 0",
                "to_fetch protein_id duplicate: 0",
                "to_fetch structure_uri missing: 0",
                "provider invalid: 0",
                "file_format invalid: 0",
                "status invalid: 0",
                "```",
                "",
                "판정: 통과",
            ]
        )
    lines.extend(
        [
            "",
            "## 다음 단계",
            "",
            "```text",
            "1. alphafold_structures_seed_candidates_v1.csv 수동 확인",
            "2. PostgreSQL alphafold_structures metadata 적재 dry-run",
            "3. 통과 후 metadata만 DB 적재",
            "4. 실제 .cif/.pdb 파일 다운로드와 S3 저장은 별도 단계에서 실행",
            "```",
        ]
    )
    text = "\n".join(lines) + "\n"
    (ALPHAFOLD / "alphafold_metadata_summary_v1.md").write_text(text, encoding="utf-8")
    (DOCS / "alphafold_metadata_lookup_validation_v1.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check AlphaFold DB metadata availability by UniProt accession.")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--sleep-seconds", type=float, default=0.15)
    args = parser.parse_args()

    rows, raw_results = build_metadata_rows(timeout=args.timeout, sleep_seconds=args.sleep_seconds)
    errors = validate_rows(rows)
    write_csv(
        ALPHAFOLD / "alphafold_structures_seed_candidates_v1.csv",
        [
            "structure_id",
            "protein_id",
            "gene_symbol",
            "uniprot_id",
            "provider",
            "provider_accession",
            "entry_id",
            "version",
            "file_format",
            "structure_uri",
            "source_url",
            "pae_uri",
            "pdb_url",
            "mean_plddt",
            "confidence_summary",
            "license",
            "status",
            "api_status",
            "model_created_date",
            "notes",
        ],
        rows,
    )
    (ALPHAFOLD / "alphafold_metadata_raw_v1.json").write_text(
        json.dumps(raw_results, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_summary(rows, errors)
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"metadata lookup ok: rows={len(rows)} status={dict(Counter(row['status'] for row in rows))}")


if __name__ == "__main__":
    main()
