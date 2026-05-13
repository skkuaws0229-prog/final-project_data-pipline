from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NORMALIZED = ROOT / "03_normalized"
OUT_DIR = ROOT / "10_alphafold"

INPUTS = [
    ("candidate_target", NORMALIZED / "drug_candidates.csv", "target"),
    ("candidate_pathway", NORMALIZED / "drug_candidates.csv", "target_pathway"),
    ("evidence_target", NORMALIZED / "image_modal_drug_evidence.csv", "target"),
    ("evidence_pathway", NORMALIZED / "image_modal_drug_evidence.csv", "target_pathway"),
]

PLACEHOLDERS = {"", "nan", "na", "n/a", "none", "null", "other", "others", "other, kinases", "unknown"}
GENERIC_NON_PROTEIN = {
    "cell cycle",
    "dna replication",
    "mitosis",
    "antimetabolite",
    "anthracycline",
    "dna alkylating agent",
    "dsdna break induction",
    "microtubule stabiliser",
    "microtubule destabiliser",
    "anthracycline",
    "antimetabolite",
}
PATHWAY_KEYWORDS = {
    "pathway",
    "signaling",
    "axis",
    "immune",
    "inflammatory",
    "angiogenesis",
    "remodeling",
    "metabolism",
    "replication",
    "mitosis",
    "cycle",
    "degradation",
    "stability",
}
ALIAS_REVIEW = {
    "PDE5": "PDE5A",
    "ETA": "EDNRA",
    "ETB": "EDNRB",
    "HSP90": "",
    "MTORC1": "",
    "Proteasome": "",
    "PI3Kgamma": "PIK3CG",
    "PI3Kbeta": "PIK3CB",
    "TOP2": "",
    "NAE": "",
}
TOKEN_ALIAS_SUGGESTIONS = {
    "MEK1": "MAP2K1",
    "MEK2": "MAP2K2",
    "BCL-XL": "BCL2L1",
    "IR": "INSR",
    "IKK-1": "CHUK",
    "IKK-2": "IKBKB",
    "MTORC1": "",
    "MTORC2": "",
    "PROTEASOME": "",
    "EPHRINS": "",
    "PDGFR": "",
    "TOP2": "",
}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def is_clean_gene_symbol(text: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][A-Z0-9-]{1,11}", text))


def source_breakdown(items: list[dict[str, str]]) -> str:
    counts = Counter(item["source_type"] for item in items)
    return ";".join(f"{key}:{counts[key]}" for key in sorted(counts))


def classify(text: str) -> tuple[str, str, str, str]:
    norm_lower = text.lower()
    if norm_lower in PLACEHOLDERS:
        return "exclude", "placeholder", "", "placeholder/free value; do not map to AlphaFold"
    if norm_lower in GENERIC_NON_PROTEIN:
        return "exclude", "non_protein_mechanism", "", "drug class, pathway, or biological process, not a single protein"
    if any(keyword in norm_lower for keyword in PATHWAY_KEYWORDS):
        return "exclude", "pathway_or_free_text", "", "pathway/free-text term; requires upstream parsing before protein mapping"
    if any(sep in text for sep in ("|", ";", "+")) or re.search(r",\s*", text):
        return "candidate", "multi_target_parse_review", "", "contains multiple target tokens; parse before UniProt mapping"
    if text in ALIAS_REVIEW:
        return "candidate", "alias_or_family_review", ALIAS_REVIEW[text], "alias/family/complex term; requires manual UniProt mapping"
    if is_clean_gene_symbol(text):
        return "candidate", "exact_gene_symbol_candidate", text, "clean gene-like symbol; still requires UniProt confirmation"
    if re.fullmatch(r"[A-Za-z0-9-]{2,16}", text):
        return "candidate", "alias_or_family_review", "", "gene-like but not canonical uppercase symbol; requires manual review"
    return "exclude", "free_text_or_mechanism", "", "not safe for direct protein structure mapping"


def read_targets() -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for source_type, path, column in INPUTS:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                text = normalize_text(row.get(column, ""))
                if not text:
                    continue
                grouped[text].append(
                    {
                        "source_type": source_type,
                        "disease_id": row.get("disease_id", ""),
                        "source_file": row.get("source_file", ""),
                    }
                )
    return grouped


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def split_target_tokens(text: str) -> list[str]:
    raw_tokens = re.split(r"[;,|+]", text)
    tokens: list[str] = []
    for raw in raw_tokens:
        token = normalize_text(raw)
        if not token:
            continue
        if token.lower() in PLACEHOLDERS or token.lower() in GENERIC_NON_PROTEIN:
            continue
        words = re.findall(r"[A-Za-z][A-Za-z0-9-]{1,15}", token)
        if len(words) == 1 and words[0].lower() not in PLACEHOLDERS:
            if words[0].lower() in GENERIC_NON_PROTEIN:
                continue
            tokens.append(words[0])
            continue
        for word in words:
            if word.lower() in PLACEHOLDERS:
                continue
            if word.lower() in GENERIC_NON_PROTEIN:
                continue
            if len(word) < 2:
                continue
            if re.fullmatch(r"[A-Z][A-Z0-9-]{1,11}", word) or word in TOKEN_ALIAS_SUGGESTIONS:
                tokens.append(word)
    deduped: list[str] = []
    seen = set()
    for token in tokens:
        key = token.upper()
        if key not in seen:
            seen.add(key)
            deduped.append(token)
    return deduped


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    grouped = read_targets()
    candidates: list[dict[str, str]] = []
    exclusions: list[dict[str, str]] = []
    seed_rows: list[dict[str, str]] = []
    parsed_rows: list[dict[str, str]] = []

    for text, items in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0].lower())):
        decision, reason_or_class, suggested_gene, notes = classify(text)
        diseases = sorted({item["disease_id"] for item in items if item["disease_id"]})
        files = sorted({item["source_file"] for item in items if item["source_file"]})
        common = {
            "target_text": text,
            "normalized_target_text": text.lower(),
            "mentions": str(len(items)),
            "source_breakdown": source_breakdown(items),
            "diseases": "|".join(diseases),
            "example_source_files": "|".join(files[:5]),
            "notes": notes,
        }
        if decision == "candidate":
            row = {
                **common,
                "candidate_class": reason_or_class,
                "suggested_gene_symbol": suggested_gene,
                "mapping_status": "needs_uniprot_mapping",
                "uniprot_id": "",
                "review_owner": "",
            }
            candidates.append(row)
            seed_rows.append(
                {
                    "protein_id": "",
                    "gene_symbol": suggested_gene or text,
                    "uniprot_id": "",
                    "protein_name": "",
                    "organism": "Homo sapiens",
                    "source_target_text": text,
                    "mapping_status": "needs_uniprot_mapping",
                    "notes": notes,
                }
            )
            if reason_or_class == "multi_target_parse_review":
                for token in split_target_tokens(text):
                    token_upper = token.upper()
                    suggested = TOKEN_ALIAS_SUGGESTIONS.get(token, TOKEN_ALIAS_SUGGESTIONS.get(token_upper, token_upper))
                    parsed_rows.append(
                        {
                            "source_target_text": text,
                            "parsed_token": token,
                            "suggested_gene_symbol": suggested,
                            "parse_status": "needs_review",
                            "uniprot_id": "",
                            "mentions": str(len(items)),
                            "diseases": "|".join(diseases),
                            "notes": "parsed from multi-target raw text; verify before seed insertion",
                        }
                    )
        else:
            exclusions.append({**common, "exclusion_reason": reason_or_class})

    write_csv(
        OUT_DIR / "target_mapping_candidates_v1.csv",
        [
            "target_text",
            "normalized_target_text",
            "candidate_class",
            "suggested_gene_symbol",
            "mapping_status",
            "uniprot_id",
            "mentions",
            "source_breakdown",
            "diseases",
            "example_source_files",
            "review_owner",
            "notes",
        ],
        candidates,
    )
    write_csv(
        OUT_DIR / "target_mapping_exclusions_v1.csv",
        [
            "target_text",
            "normalized_target_text",
            "exclusion_reason",
            "mentions",
            "source_breakdown",
            "diseases",
            "example_source_files",
            "notes",
        ],
        exclusions,
    )
    write_csv(
        OUT_DIR / "protein_targets_seed_v1.csv",
        [
            "protein_id",
            "gene_symbol",
            "uniprot_id",
            "protein_name",
            "organism",
            "source_target_text",
            "mapping_status",
            "notes",
        ],
        seed_rows,
    )
    write_csv(
        OUT_DIR / "target_mapping_parsed_tokens_v1.csv",
        [
            "source_target_text",
            "parsed_token",
            "suggested_gene_symbol",
            "parse_status",
            "uniprot_id",
            "mentions",
            "diseases",
            "notes",
        ],
        parsed_rows,
    )

    summary = [
        "# AlphaFold Target Mapping 후보 생성 v1",
        "",
        "## 생성 결과",
        "",
        "```text",
        f"unique raw target/pathway texts: {len(grouped)}",
        f"mapping candidates: {len(candidates)}",
        f"exclusions: {len(exclusions)}",
        f"protein seed rows: {len(seed_rows)}",
        f"parsed multi-target token rows: {len(parsed_rows)}",
        "```",
        "",
        "## 산출물",
        "",
        "```text",
        "10_alphafold/target_mapping_candidates_v1.csv",
        "10_alphafold/target_mapping_exclusions_v1.csv",
        "10_alphafold/target_mapping_parsed_tokens_v1.csv",
        "10_alphafold/protein_targets_seed_v1.csv",
        "```",
        "",
        "## 주의",
        "",
        "```text",
        "UniProt ID는 아직 자동 확정하지 않았다.",
        "AlphaFold DB API, AlphaFold Server, 구조 다운로드는 실행하지 않았다.",
        "candidate row는 사람이 검토한 뒤 protein_targets / target_protein_links seed로 적재한다.",
        "```",
    ]
    (OUT_DIR / "target_mapping_summary_v1.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
