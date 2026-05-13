#!/usr/bin/env python3
import csv
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "05_validation"
API_BASE = "http://127.0.0.1:8010"
PSQL = ["docker", "exec", "-i", "drug-service-postgres", "psql", "-U", "drug_service", "-d", "drug_service"]


def run(cmd, check=True):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{proc.stderr}")
    return proc


def psql_csv(query):
    proc = run(PSQL + ["-A", "-F", ",", "-c", query])
    lines = [line for line in proc.stdout.splitlines() if line and not line.startswith("(")]
    if not lines:
        return []
    reader = csv.DictReader(lines)
    return list(reader)


def api_json(path, retries=12):
    url = f"{API_BASE}{path}"
    last_error = None
    for _ in range(retries):
        try:
            with urlopen(url, timeout=5) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"API request failed: {url}: {last_error}")


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    checks = []

    health = api_json("/health")
    checks.append({"check": "api_health", "status": "pass" if health == {"status": "ok", "database": "ok"} else "fail", "detail": json.dumps(health)})

    db_counts = psql_csv(
        """
        SELECT 'diseases' AS table_name, COUNT(*)::text AS count FROM diseases
        UNION ALL SELECT 'drugs', COUNT(*)::text FROM drugs
        UNION ALL SELECT 'canonical_drugs', COUNT(*)::text FROM canonical_drugs
        UNION ALL SELECT 'drug_candidates', COUNT(*)::text FROM drug_candidates
        UNION ALL SELECT 'admet_results', COUNT(*)::text FROM admet_results
        UNION ALL SELECT 'image_modal_sources', COUNT(*)::text FROM image_modal_sources
        UNION ALL SELECT 'image_modal_clusters', COUNT(*)::text FROM image_modal_clusters
        UNION ALL SELECT 'image_modal_cluster_members', COUNT(*)::text FROM image_modal_cluster_members
        UNION ALL SELECT 'image_modal_drug_evidence', COUNT(*)::text FROM image_modal_drug_evidence
        UNION ALL SELECT 'image_modal_reports', COUNT(*)::text FROM image_modal_reports
        UNION ALL SELECT 'drug_aliases', COUNT(*)::text FROM drug_aliases
        UNION ALL SELECT 'disease_aliases', COUNT(*)::text FROM disease_aliases
        ORDER BY table_name;
        """
    )
    write_csv(OUT_DIR / "validation_counts_v1.csv", db_counts, ["table_name", "count"])

    diseases = api_json("/diseases")
    api_count_rows = []
    for disease in diseases:
        disease_id = disease["disease_id"]
        drugs = api_json(f"/drugs?disease_id={disease_id}&limit=500")
        clusters = api_json(f"/image-modal/clusters?disease_id={disease_id}")
        evidence = api_json(f"/image-modal/evidence?disease_id={disease_id}&limit=500")
        reports = api_json(f"/image-modal/reports?disease_id={disease_id}")
        api_count_rows.append({
            "disease_id": disease_id,
            "candidate_count_from_diseases": disease["candidate_count"],
            "drugs_api_count": len(drugs),
            "clusters_api_count": len(clusters),
            "evidence_api_count": len(evidence),
            "reports_api_count": len(reports),
            "drugs_missing_canonical": sum(1 for row in drugs if not row.get("canonical_drug_id")),
            "evidence_unmatched": sum(1 for row in evidence if row.get("match_status") != "matched"),
        })
    write_csv(
        OUT_DIR / "api_disease_counts_v1.csv",
        api_count_rows,
        ["disease_id", "candidate_count_from_diseases", "drugs_api_count", "clusters_api_count", "evidence_api_count", "reports_api_count", "drugs_missing_canonical", "evidence_unmatched"],
    )

    for row in api_count_rows:
        status = "pass" if int(row["candidate_count_from_diseases"]) == int(row["drugs_api_count"]) else "fail"
        checks.append({"check": f"api_count_match_{row['disease_id']}", "status": status, "detail": json.dumps(row)})
        checks.append({"check": f"drug_canonical_present_{row['disease_id']}", "status": "pass" if int(row["drugs_missing_canonical"]) == 0 else "fail", "detail": json.dumps(row)})

    unmatched = psql_csv(
        """
        SELECT disease_id, drug_name, normalized_drug_name, COUNT(*)::text AS rows
        FROM image_modal_evidence_drug_matches
        WHERE match_status = 'unmatched'
        GROUP BY disease_id, drug_name, normalized_drug_name
        ORDER BY disease_id, rows DESC, drug_name;
        """
    )
    write_csv(OUT_DIR / "unresolved_aliases_v1.csv", unmatched, ["disease_id", "drug_name", "normalized_drug_name", "rows"])

    cross_disease = psql_csv(
        """
        SELECT da.canonical_drug_id, cd.primary_drug_name, COUNT(DISTINCT c.disease_id)::text AS disease_count,
               STRING_AGG(DISTINCT c.disease_id, ';' ORDER BY c.disease_id) AS diseases
        FROM drug_candidates c
        JOIN drug_aliases da ON da.source_drug_id = c.drug_id
        JOIN canonical_drugs cd ON cd.canonical_drug_id = da.canonical_drug_id
        GROUP BY da.canonical_drug_id, cd.primary_drug_name
        HAVING COUNT(DISTINCT c.disease_id) > 1
        ORDER BY COUNT(DISTINCT c.disease_id) DESC, cd.primary_drug_name;
        """
    )
    write_csv(OUT_DIR / "cross_disease_canonical_drugs_v1.csv", cross_disease, ["canonical_drug_id", "primary_drug_name", "disease_count", "diseases"])

    target_profile = psql_csv(
        """
        SELECT 'drug_candidates' AS source, COUNT(*)::text AS total_rows,
               COUNT(*) FILTER (WHERE target IS NULL OR target = '')::text AS missing_target_rows,
               COUNT(*) FILTER (WHERE LENGTH(COALESCE(target, '')) > 120)::text AS long_target_rows
        FROM drug_candidates
        UNION ALL
        SELECT 'image_modal_drug_evidence', COUNT(*)::text,
               COUNT(*) FILTER (WHERE target IS NULL OR target = '')::text,
               COUNT(*) FILTER (WHERE LENGTH(COALESCE(target, '')) > 120)::text
        FROM image_modal_drug_evidence;
        """
    )
    write_csv(OUT_DIR / "target_profile_v1.csv", target_profile, ["source", "total_rows", "missing_target_rows", "long_target_rows"])

    cluster_profile = psql_csv(
        """
        SELECT disease_id,
               COUNT(*)::text AS clusters,
               COUNT(*) FILTER (WHERE cluster_label IS NULL OR cluster_label = '')::text AS missing_cluster_label,
               COUNT(*) FILTER (WHERE n_observations IS NULL)::text AS missing_n_observations
        FROM image_modal_clusters
        GROUP BY disease_id
        ORDER BY disease_id;
        """
    )
    write_csv(OUT_DIR / "cluster_profile_v1.csv", cluster_profile, ["disease_id", "clusters", "missing_cluster_label", "missing_n_observations"])

    checks.append({"check": "image_modal_evidence_match_rate", "status": "warn" if unmatched else "pass", "detail": f"unmatched_unique={len(unmatched)}"})
    checks.append({"check": "cross_disease_canonical_drugs", "status": "pass", "detail": f"multi_disease_canonical_drugs={len(cross_disease)}"})
    checks.append({"check": "target_profile", "status": "warn" if any(int(r["long_target_rows"]) > 0 for r in target_profile) else "pass", "detail": json.dumps(target_profile)})
    checks.append({"check": "cluster_profile", "status": "warn" if any(int(r["missing_cluster_label"]) > 0 for r in cluster_profile) else "pass", "detail": json.dumps(cluster_profile)})

    write_csv(OUT_DIR / "validation_checks_v1.csv", checks, ["check", "status", "detail"])

    smoke = {
        "generated_at": now,
        "health": health,
        "diseases_count": len(diseases),
        "sample_brca_drugs": api_json("/drugs?disease_id=BRCA&limit=2"),
        "sample_brca_image_modal_evidence": api_json("/image-modal/evidence?disease_id=BRCA&limit=2"),
        "sample_pah_reports": api_json("/image-modal/reports?disease_id=PAH"),
    }
    (OUT_DIR / "api_smoke_test_v1.json").write_text(json.dumps(smoke, indent=2, ensure_ascii=False))

    status_counts = defaultdict_int(checks)
    report = [
        "# Drug Service Validation Report v1",
        "",
        f"Generated at: {now}",
        "",
        "## Summary",
        "",
        f"- Checks: {len(checks)}",
        f"- Pass: {status_counts.get('pass', 0)}",
        f"- Warn: {status_counts.get('warn', 0)}",
        f"- Fail: {status_counts.get('fail', 0)}",
        "",
        "## Key Counts",
        "",
    ]
    for row in db_counts:
        report.append(f"- {row['table_name']}: {row['count']}")
    report.extend([
        "",
        "## Known Warnings",
        "",
        "- Colon, IPF, and PAH have image-modal drug linkage mainly embedded in Markdown reports, so structured evidence rows are not yet fully extracted.",
        f"- Unmatched image-modal drug evidence unique names: {len(unmatched)}",
        "- Target terms mix genes, pathways, mechanisms, and free-text target axes; keep original target text plus canonical tokens in the next graph/search phase.",
        "- Some image-modal cluster labels are missing and require fallback display using cluster_key.",
        "",
        "## Artifacts",
        "",
        "- validation_counts_v1.csv",
        "- api_disease_counts_v1.csv",
        "- unresolved_aliases_v1.csv",
        "- cross_disease_canonical_drugs_v1.csv",
        "- target_profile_v1.csv",
        "- cluster_profile_v1.csv",
        "- validation_checks_v1.csv",
        "- api_smoke_test_v1.json",
    ])
    (OUT_DIR / "validation_summary_v1.md").write_text("\n".join(report) + "\n")
    print(OUT_DIR / "validation_summary_v1.md")


def defaultdict_int(rows):
    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return counts


if __name__ == "__main__":
    main()
