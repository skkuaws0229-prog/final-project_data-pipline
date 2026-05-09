#!/usr/bin/env python3
"""
LINCS drug-level parquet의 Entrez ID 컬럼을
Gene Symbol + 'crispr__' prefix로 변환.

입력 : data/lincs_{cancer}_drug_level.parquet (컬럼: canonical_drug_id, '5720', '466', ...)
매핑 : scripts/gene_symbol_to_entrez.json   ({symbol: entrez} 형식)
출력 : data/lincs_{cancer}_drug_level_with_crispr_prefix.parquet
       (컬럼: canonical_drug_id, crispr__PSME1, crispr__ATF1, ...)
"""
import argparse
import json
from pathlib import Path
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="1차 집계 LINCS parquet")
    ap.add_argument("--mapping", required=True, help="gene_symbol_to_entrez.json")
    ap.add_argument("--output", required=True, help="출력 parquet 경로")
    ap.add_argument("--id-col", default="canonical_drug_id", help="drug ID 컬럼명")
    args = ap.parse_args()

    print(f"[1] Load input: {args.input}")
    df = pd.read_parquet(args.input)
    print(f"    Shape: {df.shape}")

    print(f"[2] Load mapping: {args.mapping}")
    with open(args.mapping) as f:
        symbol_to_entrez = json.load(f)
    entrez_to_symbol = {str(v): k for k, v in symbol_to_entrez.items()}
    print(f"    Mapping entries: {len(entrez_to_symbol)}")

    print("[3] Rename Entrez columns to Gene Symbols")
    id_col = args.id_col
    gene_cols = [c for c in df.columns if c != id_col]

    rename = {}
    unmatched = []
    for c in gene_cols:
        sym = entrez_to_symbol.get(str(c))
        if sym is None:
            unmatched.append(c)
        else:
            rename[c] = f"crispr__{sym}"
    print(f"    Matched: {len(rename)} / {len(gene_cols)}")
    print(f"    Unmatched (dropped): {len(unmatched)}")

    keep_cols = [id_col] + [c for c in gene_cols if c in rename]
    out = df[keep_cols].rename(columns=rename)
    print(f"    Output shape: {out.shape}")

    print(f"[4] Save: {args.output}")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(args.output, index=False)

    print("[DONE] First 10 columns:", list(out.columns[:10]))


if __name__ == "__main__":
    main()
