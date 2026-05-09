#!/usr/bin/env python3
"""Convert raw STAD pipeline inputs to parquet format."""

import sys
import gzip
import zipfile
import pandas as pd
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest-1/20260421_new_pre_project_biso_STAD")
LOG_FILE = BASE_DIR / "logs" / "convert_log.txt"

def log(msg: str, print_also=True):
    """Log message to file and optionally print."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {msg}"

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_msg + "\n")

    if print_also:
        print(log_msg)

def check_output_file(filepath: Path):
    """Check if output file exists and is not 0-byte."""
    if not filepath.exists():
        log(f"✗ ERROR: Output file not created: {filepath}", True)
        sys.exit(1)

    size = filepath.stat().st_size
    if size == 0:
        log(f"✗ ERROR: 0-byte file detected: {filepath}", True)
        sys.exit(1)

    size_mb = size / (1024 ** 2)
    log(f"  ✓ File size: {size_mb:.2f} MB")

def report_dataframe(df: pd.DataFrame, name: str):
    """Report DataFrame statistics."""
    log(f"  {name}:")
    log(f"    - Rows: {len(df):,}")
    log(f"    - Columns: {len(df.columns):,}")
    log(f"    - Columns: {list(df.columns)[:10]}" + ("..." if len(df.columns) > 10 else ""))

def convert_csv_to_parquet(input_csv: Path, output_parquet: Path):
    """Convert CSV to Parquet."""
    log(f"Converting: {input_csv.name}")

    try:
        df = pd.read_csv(input_csv, low_memory=False)
        report_dataframe(df, input_csv.stem)

        output_parquet.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_parquet, index=False)

        check_output_file(output_parquet)
        log(f"  ✓ Saved: {output_parquet}")

        return df
    except Exception as e:
        log(f"✗ ERROR converting {input_csv.name}: {e}", True)
        sys.exit(1)

def convert_chembl_gz_to_parquet(input_gz: Path, output_parquet: Path):
    """Convert ChEMBL .txt.gz to Parquet."""
    log(f"Converting: {input_gz.name}")

    try:
        with gzip.open(input_gz, 'rt', encoding='utf-8') as f:
            df = pd.read_csv(f, sep='\t', low_memory=False)

        report_dataframe(df, input_gz.stem)

        # Ensure pref_name column exists
        if 'pref_name' not in df.columns and 'molecule_name' in df.columns:
            df['pref_name'] = df['molecule_name']
            log(f"  ℹ Added pref_name from molecule_name")

        output_parquet.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_parquet, index=False)

        check_output_file(output_parquet)
        log(f"  ✓ Saved: {output_parquet}")

        return df
    except Exception as e:
        log(f"✗ ERROR converting {input_gz.name}: {e}", True)
        sys.exit(1)

def parse_drugbank_xml_from_zip(zip_path: Path, output_master: Path, output_synonyms: Path):
    """Parse DrugBank XML from ZIP and create master + synonyms parquet."""
    log(f"Parsing DrugBank XML from: {zip_path.name}")

    try:
        # Extract XML from ZIP
        with zipfile.ZipFile(zip_path, 'r') as z:
            xml_files = [f for f in z.namelist() if f.endswith('.xml')]
            if not xml_files:
                raise ValueError("No XML file found in ZIP")

            xml_file = xml_files[0]
            log(f"  Extracting: {xml_file}")

            with z.open(xml_file) as xml_content:
                tree = ET.parse(xml_content)

        root = tree.getroot()
        ns = {'db': 'http://www.drugbank.ca'}

        drugs = []
        synonyms = []

        log(f"  Parsing drugs...")
        for i, drug in enumerate(root.findall('db:drug', ns), 1):
            if i % 1000 == 0:
                log(f"    Processed {i} drugs...", print_also=False)

            # Get DrugBank ID
            drugbank_id = drug.findtext('db:drugbank-id[@primary="true"]', namespaces=ns)
            if not drugbank_id:
                drugbank_id = drug.findtext('db:drugbank-id', namespaces=ns)

            name = drug.findtext('db:name', namespaces=ns)

            # Get SMILES from calculated properties
            smiles = None
            calc_props = drug.find('db:calculated-properties', ns)
            if calc_props is not None:
                for prop in calc_props.findall('db:property', ns):
                    kind = prop.findtext('db:kind', namespaces=ns)
                    if kind == 'SMILES':
                        smiles = prop.findtext('db:value', namespaces=ns)
                        break

            drugs.append({
                'drugbank_id': drugbank_id,
                'name': name,
                'smiles': smiles
            })

            # Get synonyms
            syn_elem = drug.find('db:synonyms', ns)
            if syn_elem is not None:
                for syn in syn_elem.findall('db:synonym', ns):
                    synonym_text = syn.text
                    if synonym_text:
                        synonyms.append({
                            'drugbank_id': drugbank_id,
                            'synonym': synonym_text
                        })

        # Create DataFrames
        df_drugs = pd.DataFrame(drugs)
        df_synonyms = pd.DataFrame(synonyms)

        report_dataframe(df_drugs, "DrugBank Master")
        report_dataframe(df_synonyms, "DrugBank Synonyms")

        # Save
        output_master.parent.mkdir(parents=True, exist_ok=True)
        output_synonyms.parent.mkdir(parents=True, exist_ok=True)

        df_drugs.to_parquet(output_master, index=False)
        df_synonyms.to_parquet(output_synonyms, index=False)

        check_output_file(output_master)
        check_output_file(output_synonyms)

        log(f"  ✓ Saved: {output_master}")
        log(f"  ✓ Saved: {output_synonyms}")

        return df_drugs, df_synonyms

    except Exception as e:
        log(f"✗ ERROR parsing DrugBank XML: {e}", True)
        sys.exit(1)

def main():
    log("="*80)
    log("Raw Data to Parquet Conversion - STAD (stomach cancer)")
    log("="*80)

    curated = BASE_DIR / "curated_data"
    processed = BASE_DIR / "curated_data" / "processed"

    # ========== 1. GDSC CSV → Parquet ==========
    log("\n[1/4] GDSC CSV → Parquet")

    convert_csv_to_parquet(
        curated / "gdsc" / "GDSC2-dataset.csv",
        processed / "gdsc" / "GDSC2-dataset.parquet"
    )

    convert_csv_to_parquet(
        curated / "gdsc" / "Compounds-annotation.csv",
        processed / "gdsc" / "Compounds-annotation.parquet"
    )

    # ========== 2. DepMap CSV → Parquet ==========
    log("\n[2/4] DepMap CSV → Parquet")

    convert_csv_to_parquet(
        curated / "depmap" / "CRISPRGeneDependency.csv",
        processed / "depmap" / "CRISPRGeneDependency.parquet"
    )

    convert_csv_to_parquet(
        curated / "depmap" / "Model.csv",
        processed / "depmap" / "Model.parquet"
    )

    # ========== 3. ChEMBL .txt.gz → Parquet ==========
    log("\n[3/4] ChEMBL .txt.gz → Parquet")

    chembl_files = list((curated / "chembl").glob("*.txt.gz"))
    log(f"  Found {len(chembl_files)} ChEMBL .txt.gz files")

    for chembl_file in chembl_files:
        output_name = chembl_file.stem + ".parquet"  # Remove .gz, keep .txt → .txt.parquet
        if output_name.endswith('.txt.parquet'):
            output_name = output_name.replace('.txt.parquet', '.parquet')

        convert_chembl_gz_to_parquet(
            chembl_file,
            processed / "chembl" / output_name
        )

    # ========== 4. DrugBank XML → Parquet ==========
    log("\n[4/4] DrugBank XML → Parquet")

    parse_drugbank_xml_from_zip(
        curated / "drugbank" / "drugbank_all_full_database.xml.zip",
        processed / "drugbank" / "drugbank_master.parquet",
        processed / "drugbank" / "drugbank_synonyms.parquet"
    )

    # ========== Summary ==========
    log("\n" + "="*80)
    log("✓ Conversion Complete")
    log("="*80)

    log(f"\nOutput directory: {processed}")
    log("\nGenerated files:")

    for subdir in ['gdsc', 'depmap', 'chembl', 'drugbank']:
        subdir_path = processed / subdir
        if subdir_path.exists():
            log(f"\n  {subdir}/")
            for f in sorted(subdir_path.glob("*.parquet")):
                size_mb = f.stat().st_size / (1024 ** 2)
                log(f"    - {f.name} ({size_mb:.2f} MB)")

    log(f"\n✓ All conversions successful")
    log(f"✓ Log saved to: {LOG_FILE}")

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("\n✗ Conversion interrupted by user", True)
        sys.exit(1)
    except Exception as e:
        log(f"\n✗ Unexpected error: {e}", True)
        sys.exit(1)
