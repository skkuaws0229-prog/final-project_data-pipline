#!/usr/bin/env python3
"""
Fetch PDC file manifests for CPTAC-STAD (and optional related gastric proteome studies).

Uses public ``https://pdc.cancer.gov/graphql`` (POST JSON). For each ``pdc_study_id`` from
``studyCatalog``, resolves ``study { disease_type program_name study_submitter_id }`` and
keeps studies matching filters, then calls ``filesPerStudy(pdc_study_id: ...)``.

Output (default):
  ``curated_data/cptac_stad/pdc_manifests/<run_date>/index.json``
  ``curated_data/cptac_stad/pdc_manifests/<run_date>/files_<PDC_ID>.json``

Input / output shapes:
  - GraphQL ``filesPerStudy`` returns a list of dicts (file metadata) or null on error.
  - ``index.json`` lists studies with ``n_files`` and total_bytes (sum of parsed file_size).

Reference: https://pdc.cancer.gov/API_documentation/pdc-jupyter-python-examples.html
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

GRAPHQL_URL = "https://pdc.cancer.gov/graphql"
DEFAULT_SLEEP_SEC = 0.08


def _setup_logging(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"fetch_pdc_cptac_stad_manifest_{ts}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return log_path


def _post(query: str, timeout: int = 120) -> Dict[str, Any]:
    body = json.dumps({"query": query}).encode("utf-8")
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "stad-pipeline-pdc-manifest/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _study_catalog_ids() -> List[str]:
    data = _post("{ studyCatalog { pdc_study_id } }")
    if data.get("errors"):
        raise RuntimeError(f"PDC studyCatalog error: {data['errors'][:2]}")
    rows = data["data"]["studyCatalog"]
    return [r["pdc_study_id"] for r in rows]


def _study_detail(pdc_study_id: str) -> List[Dict[str, Any]]:
    q = (
        '{ study(pdc_study_id: "%s") { pdc_study_id disease_type program_name '
        "study_submitter_id } }" % pdc_study_id.replace('"', "")
    )
    data = _post(q)
    if data.get("errors"):
        logging.warning("study(%s) errors: %s", pdc_study_id, data["errors"][:1])
        return []
    return list(data.get("data", {}).get("study") or [])


def _files_per_study(pdc_study_id: str) -> Optional[List[Dict[str, Any]]]:
    q = (
        '{ filesPerStudy(pdc_study_id: "%s") { file_name file_type file_size md5sum '
        "file_location data_category file_format } }" % pdc_study_id.replace('"', "")
    )
    data = _post(q, timeout=180)
    if data.get("errors"):
        logging.warning("filesPerStudy(%s) errors: %s", pdc_study_id, str(data["errors"])[:500])
        return None
    files = data.get("data", {}).get("filesPerStudy")
    return files if isinstance(files, list) else None


def _keep_study(
    row: Dict[str, Any],
    cptac_only: bool,
    require_submitter_stad: bool,
) -> bool:
    prog = (row.get("program_name") or "").lower()
    dis = (row.get("disease_type") or "").lower()
    sub = (row.get("study_submitter_id") or "").lower()
    if cptac_only and "clinical proteomic tumor analysis consortium" not in prog:
        return False
    if require_submitter_stad:
        return "stad" in sub
    if "stomach" in dis or "gastric" in dis:
        return True
    if "stad" in sub:
        return True
    return False


def _parse_size(v: Any) -> int:
    try:
        if v is None or v == "":
            return 0
        return int(str(v).strip())
    except ValueError:
        return 0


def maybe_sync_s3(local_dir: Path, s3_cptac_prefix: str) -> None:
    if os.environ.get("SYNC_S3", "").strip() != "1":
        logging.info("SYNC_S3!=1 — skip aws s3 sync")
        return
    dest = s3_cptac_prefix.rstrip("/") + "/pdc_manifests/"
    logging.info("I/O aws s3 sync %s -> %s", local_dir, dest)
    subprocess.run(
        ["aws", "s3", "sync", str(local_dir), dest, "--only-show-errors"],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="PDC CPTAC-STAD file manifests.")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--run-date", default=time.strftime("%Y%m%d"))
    parser.add_argument(
        "--all-gastric-programs",
        action="store_true",
        help="Include non-CPTAC gastric programs (default: CPTAC program only).",
    )
    parser.add_argument(
        "--require-submitter-stad",
        action="store_true",
        help="Only studies whose submitter id contains 'STAD' (narrowest CPTAC-STAD slice).",
    )
    parser.add_argument(
        "--s3-cptac-prefix",
        default=os.environ.get("S3_STAD_RAW", "s3://say2-4team/Stad_raw") + "/cptac_stad",
    )
    args = parser.parse_args()

    root = args.root or Path(__file__).resolve().parent.parent
    _setup_logging(root / "logs")

    out_dir = root / "curated_data" / "cptac_stad" / "pdc_manifests" / args.run_date
    out_dir.mkdir(parents=True, exist_ok=True)

    cptac_only = not args.all_gastric_programs

    logging.info("I/O PDC studyCatalog (cptac_only=%s)", cptac_only)
    ids = _study_catalog_ids()
    logging.info("Catalog study count=%s", len(ids))

    selected: List[Dict[str, Any]] = []
    for i, pid in enumerate(ids):
        rows = _study_detail(pid)
        time.sleep(DEFAULT_SLEEP_SEC)
        for row in rows:
            if _keep_study(row, cptac_only=cptac_only, require_submitter_stad=args.require_submitter_stad):
                selected.append(row)
        if (i + 1) % 50 == 0:
            logging.info("Catalog scan progress %s/%s", i + 1, len(ids))

    logging.info("Selected studies n=%s", len(selected))
    index_studies: List[Dict[str, Any]] = []

    for row in selected:
        pid = row["pdc_study_id"]
        logging.info("I/O filesPerStudy %s (%s)", pid, row.get("study_submitter_id"))
        files = _files_per_study(pid)
        time.sleep(DEFAULT_SLEEP_SEC)
        if files is None:
            n_files, total_b = 0, 0
            payload: Any = None
        else:
            n_files = len(files)
            total_b = sum(_parse_size(f.get("file_size")) for f in files)
            payload = files
            (out_dir / f"files_{pid}.json").write_text(
                json.dumps({"study": row, "files": files}, indent=2),
                encoding="utf-8",
            )
        index_studies.append(
            {
                "pdc_study_id": pid,
                "study_submitter_id": row.get("study_submitter_id"),
                "disease_type": row.get("disease_type"),
                "program_name": row.get("program_name"),
                "n_files": n_files,
                "total_file_size_bytes": total_b,
            }
        )

    index = {
        "run_date": args.run_date,
        "graphql": GRAPHQL_URL,
        "filters": {
            "cptac_only": cptac_only,
            "require_submitter_stad": bool(args.require_submitter_stad),
        },
        "studies": index_studies,
    }
    (out_dir / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    logging.info("I/O write %s", out_dir / "index.json")

    maybe_sync_s3(out_dir.parent, args.s3_cptac_prefix)
    logging.info("Done PDC manifests -> %s", out_dir)


if __name__ == "__main__":
    main()
