from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import requests


def fetch_clinical(study_id: str, out_dir: str | Path, prefix: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    result = {}
    for level in ["PATIENT", "SAMPLE"]:
        cache = out_dir / f"{prefix}_{level.lower()}_clinical_long.json"
        if cache.exists():
            payload = json.loads(cache.read_text(encoding="utf-8"))
        else:
            resp = session.get(
                f"https://www.cbioportal.org/api/studies/{study_id}/clinical-data",
                params={"clinicalDataType": level, "projection": "DETAILED"},
                timeout=180,
            )
            resp.raise_for_status()
            payload = resp.json()
            cache.write_text(json.dumps(payload), encoding="utf-8")
        long_df = pd.DataFrame(payload)
        index = ["patientId"] if level == "PATIENT" else ["patientId", "sampleId"]
        wide = long_df.pivot_table(index=index, columns="clinicalAttributeId", values="value", aggfunc="first").reset_index()
        wide.to_csv(out_dir / f"{prefix}_{level.lower()}_clinical_wide.csv", index=False)
        result[level] = wide
    return result["PATIENT"], result["SAMPLE"]


def fetch_mutations(study_id: str, genes: dict[str, int], out_dir: str | Path, prefix: str) -> pd.DataFrame:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    profile = f"{study_id}_mutations"
    sample_list = f"{study_id}_sequenced"
    cache = out_dir / f"{prefix}_mutations.json"
    if cache.exists():
        payload = json.loads(cache.read_text(encoding="utf-8"))
    else:
        session = requests.Session()
        session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        resp = session.post(
            f"https://www.cbioportal.org/api/molecular-profiles/{profile}/mutations/fetch",
            json={"sampleListId": sample_list, "entrezGeneIds": list(genes.values())},
            timeout=180,
        )
        resp.raise_for_status()
        payload = resp.json()
        cache.write_text(json.dumps(payload), encoding="utf-8")
    df = pd.DataFrame(payload)
    if not df.empty and "entrezGeneId" in df.columns:
        df["hugoGeneSymbol"] = df["entrezGeneId"].map({v: k for k, v in genes.items()})
    df.to_csv(out_dir / f"{prefix}_mutations.csv", index=False)
    return df

