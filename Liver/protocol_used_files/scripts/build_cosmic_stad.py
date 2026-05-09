#!/usr/bin/env python3
"""
Build STAD-scoped COSMIC tables (mirrors Lung ``cosmic_lung/*`` layout).

Reads COSMIC release tarballs under ``additional_sources/cosmic/`` (local or S3-synced),
applies tissue filters aligned with Lung methodology:
  - **Actionability (GRCh37):** ``DISEASE`` contains ``stomach`` (case-insensitive).
  - **Cancer Gene Census (GRCh38):** ``TUMOUR_TYPES_SOMATIC`` matches stomach|gastric.
  - **Classification (GRCh38):** ``PRIMARY_SITE`` == ``stomach`` (case-insensitive).
  - **Mutant Census (GRCh38):** ``COSMIC_PHENOTYPE_ID`` in classification-derived id set.

Input / output shapes:
  - Input tars: COSMIC standard exports (same basenames as ``Stad_raw/additional_sources/cosmic/``).
  - Output dir: ``.../cosmic_stad/<run_date>/`` with 4× (parquet + tsv.gz) + ``build_manifest.json``.

Reference (Lung): ``s3://say2-4team/Lung_raw/additional_sources/cosmic_lung/20260417/``.
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import logging
import os
import subprocess
import tarfile
import time
from pathlib import Path
from typing import BinaryIO, Dict, Iterable, List, Optional, Set

import pandas as pd

LOG = logging.getLogger(__name__)


def _setup_logging(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"build_cosmic_stad_{ts}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return log_path


def _find_tar_member(tf: tarfile.TarFile, suffix: str) -> tarfile.TarInfo:
    for m in tf.getmembers():
        if m.isfile() and m.name.endswith(suffix):
            return m
    raise FileNotFoundError(f"No member ending with {suffix!r} in tar {tf.name}")


def _open_tar_member_text(tf: tarfile.TarFile, suffix: str) -> Tuple[BinaryIO, str]:
    member = _find_tar_member(tf, suffix)
    bio = tf.extractfile(member)
    if bio is None:
        raise OSError(f"Cannot extract member {member.name}")
    LOG.info("I/O read tar member %s from %s", member.name, getattr(tf, "name", "?"))
    return bio, member.name


def _read_actionability(tar_path: Path) -> pd.DataFrame:
    with tarfile.open(tar_path, "r") as tf:
        bio, _ = _open_tar_member_text(tf, "Actionability_AllData_v19_GRCh37.tsv")
        return pd.read_csv(bio, sep="\t", low_memory=False)


def _read_cgc(tar_path: Path) -> pd.DataFrame:
    with tarfile.open(tar_path, "r") as tf:
        bio, _ = _open_tar_member_text(tf, "Cosmic_CancerGeneCensus_v103_GRCh38.tsv.gz")
        # tar member is .gz bytes
        raw = bio.read()
    return pd.read_csv(io.BytesIO(raw), sep="\t", compression="gzip", low_memory=False)


def _read_classification(tar_path: Path) -> pd.DataFrame:
    with tarfile.open(tar_path, "r") as tf:
        bio, _ = _open_tar_member_text(tf, "Cosmic_Classification_v103_GRCh38.tsv.gz")
        raw = bio.read()
    return pd.read_csv(io.BytesIO(raw), sep="\t", compression="gzip", low_memory=False)


def _stomach_phenotype_ids(
    classification: pd.DataFrame, include_gej_pattern: bool
) -> Set[str]:
    ps = classification["PRIMARY_SITE"].fillna("").str.lower()
    mask = ps == "stomach"
    if include_gej_pattern:
        text = (
            classification["PRIMARY_SITE"].fillna("")
            + " "
            + classification["PRIMARY_HISTOLOGY"].fillna("")
            + " "
            + classification["HISTOLOGY_SUBTYPE_1"].fillna("")
            + " "
            + classification["HISTOLOGY_SUBTYPE_2"].fillna("")
            + " "
            + classification["HISTOLOGY_SUBTYPE_3"].fillna("")
        ).str.lower()
        mask = mask | text.str.contains(
            r"gastric|stomach|gastro-oesophageal|gastroesophageal|oesophagogastric|esophagogastric",
            regex=True,
            na=False,
        )
    ids = set(classification.loc[mask, "COSMIC_PHENOTYPE_ID"].astype(str))
    return ids


def _iter_mutant_census_chunks(
    tar_path: Path, chunksize: int
) -> Iterable[pd.DataFrame]:
    with tarfile.open(tar_path, "r") as tf:
        member = _find_tar_member(tf, "Cosmic_MutantCensus_v103_GRCh38.tsv.gz")
        bio = tf.extractfile(member)
        if bio is None:
            raise OSError(f"Cannot extract {member.name}")
        LOG.info("I/O stream mutant census %s chunksize=%s", member.name, chunksize)
        gz = gzip.GzipFile(fileobj=bio)
        for chunk in pd.read_csv(gz, sep="\t", chunksize=chunksize, low_memory=False):
            yield chunk


def _write_tsv_gz(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as gz:
        df.to_csv(gz, sep="\t", index=False)
    LOG.info("I/O write %s rows=%s cols=%s", path, len(df), df.shape[1])


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    LOG.info("I/O write %s rows=%s cols=%s", path, len(df), df.shape[1])


def maybe_sync_s3(local_run_dir: Path, s3_additional_sources: str) -> None:
    if os.environ.get("SYNC_S3", "").strip() != "1":
        LOG.info("SYNC_S3!=1 — skip aws s3 sync")
        return
    # Versioned layout (Lung ``cosmic_lung/<date>/`` 동형): cosmic_stad/<run_date>/
    dest = f"{s3_additional_sources.rstrip('/')}/cosmic_stad/{local_run_dir.name}/"
    LOG.info("I/O aws s3 sync %s -> %s", local_run_dir, dest)
    subprocess.run(
        ["aws", "s3", "sync", str(local_run_dir), dest, "--only-show-errors"],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build cosmic_stad curated tables from COSMIC tars.")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Project root (parent of scripts/). Default: script parent.",
    )
    parser.add_argument(
        "--cosmic-dir",
        type=Path,
        default=None,
        help="Directory containing COSMIC *.tar (default: <root>/curated_data/additional_sources/cosmic).",
    )
    parser.add_argument(
        "--run-date",
        default=time.strftime("%Y%m%d"),
        help="Output subfolder under cosmic_stad/ (default: today UTC+local).",
    )
    parser.add_argument(
        "--include-gej-pattern",
        action="store_true",
        help="Broaden classification/mutant filter using gastric/GEJ-related histology text.",
    )
    parser.add_argument(
        "--mutant-chunksize",
        type=int,
        default=300_000,
        help="Rows per read when scanning Mutant Census.",
    )
    parser.add_argument(
        "--s3-dest-additional-sources",
        default=os.environ.get("S3_STAD_RAW", "s3://say2-4team/Stad_raw") + "/additional_sources",
        help="When SYNC_S3=1, sync under .../cosmic_stad/",
    )
    args = parser.parse_args()

    root = args.root or Path(__file__).resolve().parent.parent
    _setup_logging(root / "logs")

    cosmic_dir = args.cosmic_dir or (root / "curated_data" / "additional_sources" / "cosmic")
    paths = {
        "actionability": cosmic_dir / "Actionability_AllData_Tsv_v19_GRCh37.tar",
        "cgc": cosmic_dir / "Cosmic_CancerGeneCensus_Tsv_v103_GRCh38.tar",
        "classification": cosmic_dir / "Cosmic_Classification_Tsv_v103_GRCh38.tar",
        "mutant": cosmic_dir / "Cosmic_MutantCensus_Tsv_v103_GRCh38.tar",
    }
    for k, p in paths.items():
        if not p.is_file():
            raise FileNotFoundError(f"Missing COSMIC tar for {k}: {p}")

    out_root = root / "curated_data" / "additional_sources" / "cosmic_stad" / args.run_date
    out_root.mkdir(parents=True, exist_ok=True)

    LOG.info("Building cosmic_stad -> %s", out_root)

    act = _read_actionability(paths["actionability"])
    act_f = act[act["DISEASE"].fillna("").str.contains("stomach", case=False, na=False)].copy()
    _write_parquet(act_f, out_root / "cosmic_stad_actionability_v19_grch37.parquet")
    _write_tsv_gz(act_f, out_root / "cosmic_stad_actionability_v19_grch37.tsv.gz")

    cgc = _read_cgc(paths["cgc"])
    tum = cgc["TUMOUR_TYPES_SOMATIC"].fillna("")
    cgc_f = cgc[tum.str.contains(r"stomach|gastric", case=False, na=False, regex=True)].copy()
    _write_parquet(cgc_f, out_root / "cosmic_stad_cancer_gene_census_v103_grch38.parquet")
    _write_tsv_gz(cgc_f, out_root / "cosmic_stad_cancer_gene_census_v103_grch38.tsv.gz")

    cl = _read_classification(paths["classification"])
    pheno_ids = _stomach_phenotype_ids(cl, args.include_gej_pattern)
    cl_f = cl[cl["COSMIC_PHENOTYPE_ID"].astype(str).isin(pheno_ids)].copy()
    _write_parquet(cl_f, out_root / "cosmic_stad_classification_v103_grch38.parquet")
    _write_tsv_gz(cl_f, out_root / "cosmic_stad_classification_v103_grch38.tsv.gz")

    mutant_parts: List[pd.DataFrame] = []
    n_seen = 0
    for chunk in _iter_mutant_census_chunks(paths["mutant"], args.mutant_chunksize):
        n_seen += len(chunk)
        sub = chunk[chunk["COSMIC_PHENOTYPE_ID"].astype(str).isin(pheno_ids)]
        if len(sub):
            mutant_parts.append(sub)
    mutant_df = pd.concat(mutant_parts, axis=0, ignore_index=True) if mutant_parts else pd.DataFrame()
    LOG.info("Mutant census scanned rows=%s kept=%s", n_seen, len(mutant_df))
    _write_parquet(mutant_df, out_root / "cosmic_stad_mutant_census_v103_grch38.parquet")
    _write_tsv_gz(mutant_df, out_root / "cosmic_stad_mutant_census_v103_grch38.tsv.gz")

    manifest: Dict[str, object] = {
        "run_date": args.run_date,
        "cosmic_dir": str(cosmic_dir),
        "rows": {
            "actionability_stomach_disease": int(len(act_f)),
            "cancer_gene_census_tumour_somatic_stomach_gastric": int(len(cgc_f)),
            "classification_stomach_phenotypes": int(len(cl_f)),
            "mutant_census": int(len(mutant_df)),
        },
        "include_gej_pattern": bool(args.include_gej_pattern),
        "phenotype_id_count": len(pheno_ids),
    }
    man_path = out_root / "build_manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    LOG.info("I/O write %s", man_path)

    maybe_sync_s3(out_root, args.s3_dest_additional_sources)
    LOG.info("Done cosmic_stad build.")


if __name__ == "__main__":
    main()
