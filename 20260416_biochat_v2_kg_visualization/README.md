# BioChat v2 + Knowledge Graph 시각화 (2026-04-16)

## 📋 개요

이 디렉토리는 BioChat v2 프론트엔드와 FastAPI 백엔드를 포함하며, 2026년 4월 16일에 Knowledge Graph 시각화 기능을 추가한 버전입니다.

## 🎯 주요 기능

### 완료된 기능

1. **프론트엔드 개선**
   - 사이드바/메인 창 배경색 구분
   - 모드 토글 버튼 (환자/보호자 😊, 연구자 🧑‍🔬)
   - B2 버튼으로 웰컴 화면 이동
   - 모드별 채팅 분리
   - 반응형 레이아웃

2. **약물 상세 정보**
   - 약물 카드 클릭 시 상세 정보 표시
   - 타겟, 부작용, 임상시험, Pathway 정보
   - Neo4j API 통합
   - 캐싱 시스템

3. **Pathway API 통합**
   - KEGG REST API
   - Reactome ContentService API
   - WikiPathways 검색
   - 약물별 pathway 시각화 (이미지)

4. **Knowledge Graph 시각화** ⭐ NEW
   - Canvas 기반 force-directed graph
   - 노드/엣지 인터랙티브 시각화
   - 드래그, 줌, 패닝 지원
   - 노드 클릭 시 상세 정보
   - 유형별 필터링

## 📁 파일 구조

```
20260416_biochat_v2_kg_visualization/
├── README.md                      # 이 파일
├── biochat_v2.html               # 프론트엔드 (SPA)
├── api_server_v2.py              # FastAPI 백엔드
├── pathway_apis.py               # 외부 Pathway API 통합
├── WORK_SUMMARY_20260416.md      # 작업 요약 문서
├── claude_code_instructions.md   # v1→v2 기능 추가 지시서
├── test_neo4j.py                 # Neo4j 연결 테스트
└── neo4j/                        # Neo4j 관련 스크립트
    └── loaders/
        └── fix_data_issues.py    # 데이터 품질 개선 스크립트
```

## 🚀 실행 방법

### 1. 환경 설정

```bash
# 필요 패키지 설치
pip install fastapi uvicorn python-dotenv neo4j

# .env 파일 생성 (Neo4j 접속 정보)
cat > .env << EOF
NEO4J_URI=bolt+s://xxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j
EOF
```

### 2. 서버 실행

```bash
# FastAPI 서버 실행
uvicorn api_server_v2:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 브라우저 접속

```
http://localhost:8000
```

또는 다른 컴퓨터에서:
```
http://[서버IP]:8000
```

## 📊 Neo4j 데이터베이스

### 통계
- **노드**: 30,558개
- **관계**: 180,000+개
- **Target (gene_symbol)**: 8,880개
- **Drug**: 15개
- **STRING PPI**: 22,938개
- **OpenTargets**: 53개

### 데이터 소스
- DrugBank
- ChEMBL
- GDSC (Genomics of Drug Sensitivity in Cancer)
- STRING (Protein-Protein Interaction)
- OpenTargets
- MSigDB (Molecular Signatures Database)
- DepMap
- KEGG
- Reactome
- WikiPathways

## 🎨 주요 페이지

1. **AI Chat**: 모드별 맞춤 채팅
2. **Dashboard**: 파이프라인 요약 및 차트
3. **약물 탐색**: 15개 후보 약물 상세 정보
4. **ML Pipeline**: 모델 결과 및 앙상블
5. **KG 탐색**: Knowledge Graph 네트워크 시각화 ⭐

## 🔗 API 엔드포인트

### v1 엔드포인트 (Neo4j)
- `GET /api/drug/{name}` - 약물 단건 조회
- `GET /api/drug/{name}/targets` - 약물 타겟
- `GET /api/drug/{name}/side_effects` - 약물 부작용
- `GET /api/drug/{name}/trials` - 약물 임상시험
- `GET /api/drug/{name}/pathways?enrich=true` - 약물 Pathway (외부 API 포함)
- `GET /api/stats` - KG 통계
- `POST /api/chat` - 채팅 (query, user_type)

### v2 엔드포인트 (파이프라인)
- `GET /api/v2/pipeline/meta` - 파이프라인 메타 정보
- `GET /api/v2/pipeline/models?family=ML` - ML/DL 모델 결과
- `GET /api/v2/pipeline/ensemble` - 앙상블 결과
- `GET /api/v2/pipeline/metabric` - METABRIC 검증
- `GET /api/v2/pipeline/admet` - ADMET 요약
- `GET /api/v2/pipeline/candidates` - 후보 약물
- `GET /api/v2/pipeline/summary` - 대시보드용 전체 요약
- `GET /api/v2/kg/graph?limit=500` - KG 시각화 데이터 ⭐

### 외부 API 통합
- `GET /api/pathways/search?query={name}` - Pathway 검색 (KEGG + Reactome + WikiPathways)

## 🧪 테스트 결과

### Pathway API
- ✅ KEGG pathway 이미지 표시
- ✅ Reactome diagram 표시
- ✅ WikiPathways 검색 링크

### KG 시각화
- ✅ Force-directed graph 렌더링
- ✅ 노드 드래그, 화면 패닝, 줌 동작
- ✅ 노드 클릭 상세 정보
- ✅ 유형별 필터링
- ✅ 범례 및 통계 표시

### 프론트엔드
- ✅ 모드별 채팅 분리
- ✅ 약물 카드 상세 정보
- ✅ B2 버튼 웰컴 화면 이동
- ✅ 반응형 레이아웃

## 📝 다음 단계 (지시서에서)

남은 작업 (claude_code_instructions.md 참고):
1. ⏳ 작업 2: 대화 히스토리 관리 (localStorage)
2. ⏳ 작업 3: 다크/라이트 테마 전환
3. ⏳ 작업 4: 채팅 Rich Content 카드
4. ✅ 작업 8: Knowledge Graph 시각화 (완료!)

## 🔧 기술 스택

- **Frontend**: Vanilla JavaScript, Chart.js, HTML5 Canvas
- **Backend**: FastAPI, Python 3.12
- **Database**: Neo4j Aura (cloud)
- **External APIs**: KEGG, Reactome, WikiPathways
- **Visualization**: Force-directed graph (Canvas)

## 📄 라이선스

See repository root for license information.

---

**Last Updated**: 2026-04-16
**Version**: 2.1 (KG Visualization)
