#!/usr/bin/env python3
"""Extract ChEMBL compound data from SQLite database."""

import sys
import tarfile
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest-1/20260421_new_pre_project_biso_STAD")
LOG_FILE = BASE_DIR / "logs" / "convert_log.txt"

def log(msg: str):
    """Log message."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {msg}"

    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_msg + "\n")
    print(log_msg)

def extract_and_convert_chembl_sqlite():
    """Extract ChEMBL SQLite and convert to parquet with pref_name."""

    curated = BASE_DIR / "curated_data"
    processed = BASE_DIR / "curated_data" / "processed"
    chembl_tar = curated / "chembl" / "chembl_36_sqlite.tar.gz"
    output_parquet = processed / "chembl" / "chembl_compounds.parquet"

    log("="*60)
    log("Extracting ChEMBL SQLite Database")
    log("="*60)

    # Extract SQLite DB
    log(f"Extracting: {chembl_tar.name}")
    temp_dir = BASE_DIR / "temp_chembl"
    temp_dir.mkdir(exist_ok=True)

    with tarfile.open(chembl_tar, 'r:gz') as tar:
        tar.extractall(temp_dir)

    # Find SQLite DB file
    db_files = list(temp_dir.glob("**/*.db"))
    if not db_files:
        log("✗ ERROR: No SQLite database found in archive")
        sys.exit(1)

    db_file = db_files[0]
    log(f"  Found DB: {db_file.name}")

    # Connect to SQLite
    log("Querying compound data...")
    conn = sqlite3.connect(db_file)

    # Query to get compounds with names and SMILES
    query = """
    SELECT
        m.chembl_id,
        m.pref_name,
        cs.canonical_smiles,
        cs.standard_inchi,
        cs.standard_inchi_key
    FROM molecule_dictionary m
    LEFT JOIN compound_structures cs ON m.molregno = cs.molregno
    WHERE cs.canonical_smiles IS NOT NULL
    """

    log("  Executing query...")
    df = pd.read_sql_query(query, conn)
    conn.close()

    log(f"  Retrieved {len(df):,} compounds")
    log(f"  Columns: {list(df.columns)}")

    # Check pref_name availability
    has_name = df['pref_name'].notna().sum()
    log(f"  Compounds with pref_name: {has_name:,} ({has_name/len(df)*100:.1f}%)")

    # Save to parquet
    output_parquet.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_parquet, index=False)

    size_mb = output_parquet.stat().st_size / (1024**2)
    log(f"  ✓ Saved: {output_parquet}")
    log(f"  ✓ File size: {size_mb:.2f} MB")

    # Cleanup
    log("  Cleaning up temporary files...")
    import shutil
    shutil.rmtree(temp_dir)

    log("="*60)
    log("✓ ChEMBL SQLite extraction complete")
    log("="*60)

    return df

if __name__ == "__main__":
    try:
        extract_and_convert_chembl_sqlite()
    except Exception as e:
        log(f"✗ ERROR: {e}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)
