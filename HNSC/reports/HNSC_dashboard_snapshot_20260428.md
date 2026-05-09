# HNSC Dashboard Snapshot (2026-04-28)

대시보드 엔트리:
- `hnsc_dashboard/app.py`

실행:
```bash
cd 20260427_HNSC
streamlit run hnsc_dashboard/app.py
```

표시 지표:
- Step6 Any-match (Top30): 28 / 30
- Unmatched: 2
- Step7 Provisional Top15: 15
- Step7 REVIEW: 3

주요 테이블:
- Step6 외부검증 스냅샷 (`external_validation/<RESULT_TAG>/top30_external_validation_independent.csv`)
- Step7 Top15 provisional (`results/<RESULT_TAG>/step7_top15_hnsc_provisional.csv`)
- Top30 Tier1/2/3/4 (`results/<RESULT_TAG>/top30_tier1234_fixed_hnsc.csv`)
- Step7 Top15 fixed tier (`results/<RESULT_TAG>/step7_top15_hnsc_provisional_with_fixed_tier.csv`)

연결 리포트(업데이트):
- `reports/HNSC_pipeline_full_summary_20260428.md`

