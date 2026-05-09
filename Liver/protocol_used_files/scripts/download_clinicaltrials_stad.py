#!/usr/bin/env python3
"""
Download ClinicalTrials.gov studies (API v2) for gastric / STAD validation.

Outputs (Lung additional_sources layout compatible):
  clinicaltrials_gastric_cancer_summary.json
  clinicaltrials_gastric_cancer_page_{page:03d}.json   # each: {studies, nextPageToken?}
  clinicaltrials_gastric_cancer_all_studies.json       # {studies: [...]} merged

Input / output shapes:
  - API pages: dict with key ``studies`` (list of study objects), optional ``nextPageToken``.
  - Summary: ``{"query": str, "pages": int, "study_count": int}``.

Reference (Lung): ``20260416_new_pre_project_biso_Lung/step6_3_clinical_trials_validation.py`` (load paths).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

API_BASE = "https://clinicaltrials.gov/api/v2/studies"
DEFAULT_QUERY_COND = "stomach neoplasms"
DEFAULT_PAGE_SIZE = 1000
MAX_RETRIES = 5
RETRY_SLEEP_SEC = 3.0
PAGE_SLEEP_SEC = 0.35


def _setup_logging(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"download_clinicaltrials_stad_{ts}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return log_path


def _fetch_page(
    query_cond: str, page_size: int, page_token: Optional[str]
) -> Dict[str, Any]:
    params: List[Tuple[str, str]] = [
        ("format", "json"),
        ("query.cond", query_cond),
        ("pageSize", str(page_size)),
    ]
    if page_token:
        params.append(("pageToken", page_token))
    url = f"{API_BASE}?{urllib.parse.urlencode(params)}"
    last_err: Optional[BaseException] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "stad-pipeline-clinicaltrials-fetch/1.0"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read()
            return json.loads(raw.decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = e
            logging.warning("fetch attempt %s/%s failed: %s", attempt, MAX_RETRIES, e)
            time.sleep(RETRY_SLEEP_SEC * attempt)
    raise RuntimeError(f"Failed to fetch after {MAX_RETRIES} attempts: {url}") from last_err


def download_all(
    out_dir: Path,
    query_cond: str,
    page_size: int,
    write_combined: bool,
) -> Tuple[int, int]:
    """
    Returns (page_count, study_count).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    token: Optional[str] = None
    page_idx = 0
    all_studies: List[Any] = []

    while True:
        page_idx += 1
        logging.info(
            "I/O read ClinicalTrials.gov page=%s query.cond=%r pageSize=%s",
            page_idx,
            query_cond,
            page_size,
        )
        data = _fetch_page(query_cond, page_size, token)
        studies = data.get("studies") or []
        if not isinstance(studies, list):
            raise TypeError("API response missing list field 'studies'")

        page_path = out_dir / f"clinicaltrials_gastric_cancer_page_{page_idx:03d}.json"
        with page_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        logging.info("I/O write %s (%s studies)", page_path, len(studies))

        all_studies.extend(studies)
        token = data.get("nextPageToken")
        if not token:
            break
        time.sleep(PAGE_SLEEP_SEC)

    summary = {
        "query": query_cond,
        "pages": page_idx,
        "study_count": len(all_studies),
    }
    summary_path = out_dir / "clinicaltrials_gastric_cancer_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    logging.info("I/O write %s -> %s", summary_path, summary)

    if write_combined:
        combined = {"studies": all_studies}
        combined_path = out_dir / "clinicaltrials_gastric_cancer_all_studies.json"
        logging.info("I/O write %s (merged studies=%s)", combined_path, len(all_studies))
        with combined_path.open("w", encoding="utf-8") as f:
            json.dump(combined, f, ensure_ascii=False)

    return page_idx, len(all_studies)


def maybe_sync_s3(local_dir: Path, s3_uri: str) -> None:
    if os.environ.get("SYNC_S3", "").strip() != "1":
        logging.info("SYNC_S3!=1 — skip aws s3 sync")
        return
    dest = s3_uri.rstrip("/") + "/clinicaltrials/"
    logging.info("I/O aws s3 sync %s -> %s", local_dir, dest)
    subprocess.run(
        ["aws", "s3", "sync", str(local_dir), dest, "--only-show-errors"],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch ClinicalTrials.gov for STAD/gastric.")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Project root (parent of scripts/). Default: script parent.",
    )
    parser.add_argument(
        "--query-cond",
        default=DEFAULT_QUERY_COND,
        help="ClinicalTrials.gov query.cond (default: stomach neoplasms / MeSH-aligned).",
    )
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument(
        "--no-combined",
        action="store_true",
        help="Do not write clinicaltrials_gastric_cancer_all_studies.json (saves disk).",
    )
    parser.add_argument(
        "--s3-dest",
        default=os.environ.get("S3_STAD_RAW", "s3://say2-4team/Stad_raw"),
        help="When SYNC_S3=1, sync under <s3>/additional_sources/clinicaltrials/",
    )
    args = parser.parse_args()

    root = args.root or Path(__file__).resolve().parent.parent
    log_path = _setup_logging(root / "logs")
    logging.info("log file: %s", log_path)

    out_dir = root / "curated_data" / "additional_sources" / "clinicaltrials"
    pages, n_studies = download_all(
        out_dir=out_dir,
        query_cond=args.query_cond,
        page_size=args.page_size,
        write_combined=not args.no_combined,
    )
    logging.info("done pages=%s studies=%s out_dir=%s", pages, n_studies, out_dir)

    maybe_sync_s3(out_dir, args.s3_dest.rstrip("/") + "/additional_sources")


if __name__ == "__main__":
    main()
