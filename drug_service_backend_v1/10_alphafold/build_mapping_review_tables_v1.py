from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALPHAFOLD = ROOT / "10_alphafold"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def priority_band(mentions: int, candidate_class: str, source_breakdown: str) -> tuple[str, str]:
    if candidate_class == "exact_gene_symbol_candidate" and mentions >= 10:
        return "P1", "frequent exact gene-like target"
    if candidate_class == "exact_gene_symbol_candidate":
        return "P2", "exact gene-like target"
    if candidate_class == "alias_or_family_review" and mentions >= 5:
        return "P2", "frequent alias/family target; review before mapping"
    if candidate_class == "multi_target_parse_review" and mentions >= 3:
        return "P3", "multi-target raw text; use parsed token review first"
    if "candidate_target" in source_breakdown:
        return "P3", "candidate target source present"
    return "P4", "lower frequency or evidence-only target"


def main() -> None:
    candidates = read_csv(ALPHAFOLD / "target_mapping_candidates_v1.csv")
    parsed_tokens = read_csv(ALPHAFOLD / "target_mapping_parsed_tokens_v1.csv")

    alias_rows: list[dict[str, str]] = []
    for row in candidates:
        if row["candidate_class"] == "alias_or_family_review":
            alias_rows.append(
                {
                    "review_item_type": "raw_alias_or_family",
                    "raw_text": row["target_text"],
                    "suggested_gene_symbol": row["suggested_gene_symbol"],
                    "candidate_class": row["candidate_class"],
                    "mentions": row["mentions"],
                    "diseases": row["diseases"],
                    "source_breakdown": row["source_breakdown"],
                    "review_decision": "needs_review",
                    "final_gene_symbol": "",
                    "uniprot_id": "",
                    "mapping_status": "unresolved",
                    "confidence": "",
                    "review_notes": row["notes"],
                }
            )

    for row in parsed_tokens:
        if row["suggested_gene_symbol"] != row["parsed_token"].upper() or not row["suggested_gene_symbol"]:
            alias_rows.append(
                {
                    "review_item_type": "parsed_token_alias",
                    "raw_text": row["parsed_token"],
                    "suggested_gene_symbol": row["suggested_gene_symbol"],
                    "candidate_class": "parsed_token_review",
                    "mentions": row["mentions"],
                    "diseases": row["diseases"],
                    "source_breakdown": "parsed_from_multi_target",
                    "review_decision": "needs_review",
                    "final_gene_symbol": "",
                    "uniprot_id": "",
                    "mapping_status": "unresolved",
                    "confidence": "",
                    "review_notes": f"source_target_text={row['source_target_text']}",
                }
            )

    priority_rows: list[dict[str, str]] = []
    for row in candidates:
        mentions = int(row["mentions"])
        band, reason = priority_band(mentions, row["candidate_class"], row["source_breakdown"])
        priority_rows.append(
            {
                "priority": band,
                "target_text": row["target_text"],
                "suggested_gene_symbol": row["suggested_gene_symbol"],
                "candidate_class": row["candidate_class"],
                "mentions": row["mentions"],
                "diseases": row["diseases"],
                "source_breakdown": row["source_breakdown"],
                "review_status": "not_started",
                "uniprot_id": "",
                "structure_priority_reason": reason,
                "recommended_next_action": "map_uniprot" if band in {"P1", "P2"} else "review_or_defer",
            }
        )

    priority_order = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}
    priority_rows.sort(key=lambda r: (priority_order[r["priority"]], -int(r["mentions"]), r["target_text"].lower()))
    alias_rows.sort(key=lambda r: (-int(r["mentions"]), r["raw_text"].lower(), r["review_item_type"]))

    write_csv(
        ALPHAFOLD / "alias_resolution_review_v1.csv",
        [
            "review_item_type",
            "raw_text",
            "suggested_gene_symbol",
            "candidate_class",
            "mentions",
            "diseases",
            "source_breakdown",
            "review_decision",
            "final_gene_symbol",
            "uniprot_id",
            "mapping_status",
            "confidence",
            "review_notes",
        ],
        alias_rows,
    )
    write_csv(
        ALPHAFOLD / "target_priority_for_structure_v1.csv",
        [
            "priority",
            "target_text",
            "suggested_gene_symbol",
            "candidate_class",
            "mentions",
            "diseases",
            "source_breakdown",
            "review_status",
            "uniprot_id",
            "structure_priority_reason",
            "recommended_next_action",
        ],
        priority_rows,
    )

    summary = [
        "# Target Mapping Review Tables v1",
        "",
        "```text",
        f"alias review rows: {len(alias_rows)}",
        f"priority rows: {len(priority_rows)}",
        "```",
        "",
        "Generated files:",
        "",
        "```text",
        "10_alphafold/alias_resolution_review_v1.csv",
        "10_alphafold/target_priority_for_structure_v1.csv",
        "```",
    ]
    (ALPHAFOLD / "mapping_review_tables_summary_v1.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
