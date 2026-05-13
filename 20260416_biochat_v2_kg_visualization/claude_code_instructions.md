# BioChat v2 프론트-백엔드 연결 작업 지시서

## 📋 프로젝트 개요

**목표**: 유방암 약물 재창출 KG + ML/DL 파이프라인 통합 챗봇 시스템 구축

**주요 파일**:
- `biochat_v2.html` - 프론트엔드 (Single Page Application)
- `api_server_v2.py` - 백엔드 (FastAPI + Neo4j)
- `.env` - 환경 변수 (Neo4j 연결 정보)

---

## ✅ 완료된 작업

### 작업 1: 연구자/환자 모드 전환 기능 ✅
**상태**: 이미 구현 완료

**구현 내용**:
- 프론트엔드 (`biochat_v2.html`):
  - `toggleMode()` 함수 구현 (line 417-422)
  - localStorage에 사용자 모드 저장 (`biochat_user_mode`)
  - 모드별 UI 변경 (사이드바 메뉴 표시/숨김)
  - 모드별 환영 메시지 및 추천 질문 변경
  - 모드 전환 버튼 UI (line 214-218)

- 백엔드 (`api_server_v2.py`):
  - `ChatRequest` 모델에 `user_type` 파라미터 (line 519)
  - `/api/chat` 엔드포인트에서 사용자 모드 기반 응답 생성 (line 723-726)

**검증**:
```javascript
// localStorage에서 확인
localStorage.getItem('biochat_user_mode') // "patient" 또는 "researcher"
```

---

### 작업 6: 서버 세팅 ✅
**상태**: 이미 실행 중

**실행 방법**:
```bash
# 1. 서버 실행 (개발 모드 - 자동 리로드)
python api_server_v2.py

# 또는
uvicorn api_server_v2:app --host 0.0.0.0 --port 8000 --reload

# 2. 서버 확인
curl http://localhost:8000/api/stats
```

**환경 설정** (`.env`):
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j
```

**포트**: 8000
**프로세스 확인**: `lsof -ti:8000`

---

### 작업 7: 챗봇 Intent 처리 누락 수정 ✅
**상태**: 2026-04-16 완료

**문제**:
- `prevention`, `lifestyle`, `news`, `disease_stats` intent가 `_classify_intent()`에서 분류되지만
- 실제 처리하는 코드가 없어서 "구체적인 질문 필요" 메시지만 반환됨
- Neo4j 데이터베이스가 비어있어 KG 관련 쿼리 실패

**해결 방법**:
`api_server_v2.py`의 `/api/chat` 엔드포인트에 4개 intent 처리 로직 추가:

1. **`prevention` (예방/검진)**
   - 검진 방법: 유방촬영술, 초음파, MRI
   - 위험 요인: 가족력, 유전자 변이, 호르몬
   - 예방 수칙: 정기 검진, 체중 관리, 운동

2. **`lifestyle` (생활습관/음식)**
   - 추천 식단: 채소, 통곡물, 생선, 콩류
   - 피할 음식: 가공육, 고칼로리, 술
   - 운동: 유산소 150분/주, 근력 운동 2회/주

3. **`news` (최신 정보)**
   - 파이프라인 연구 동향
   - 타겟 치료제 (HDAC, BIRC5, CDK 억제제)
   - 정밀 의료 (METABRIC 기반)

4. **`disease_stats` (질병 통계)**
   - 발생률: 여성암 1위, 연 28,000건
   - 생존율: 5년 93.6%
   - 호발 연령: 40-60대

**코드 위치**: `api_server_v2.py` line 695-770

---

### 작업 8: Neo4j 데이터베이스 구축 ✅
**상태**: 2026-04-16 완료

**실행 내용**:

1. **스키마 적용** (`neo4j/schema/apply_schema.py`):
   - 제약조건 9개 생성 (Drug, Target, Disease, Trial, Hospital, Pathway, SideEffect, Variant, CellLine)
   - 인덱스 14개 생성

2. **S3 큐레이션 데이터 적재** (`neo4j/loaders/load_curated_data.py`):
   - DrugBank: 19,842개 약물
   - ChEMBL: 8,880개 타겟 (Homo sapiens)
   - GDSC: 969개 세포주, 94,372개 테스트 관계
   - STRING: 0개 PPI (매칭 실패)
   - OpenTargets: 0개 association (매칭 실패)
   - MSigDB: 686개 pathway, 729개 관계
   - DepMap: 967개 세포주 메타데이터

3. **파이프라인 결과 적재** (`neo4j/loaders/load_brca_pipeline.py`):
   - BRCA Disease 노드 생성
   - 14개 약물 업데이트 (Docetaxel, Paclitaxel, Romidepsin 등)
   - 14개 TREATS 관계 생성
   - ⚠️ Sepantronium bromide는 DrugBank에 없어서 스킵

**최종 데이터베이스 상태**:
- 노드: 30,558개 (Drug 19,844, Target 8,880, CellLine 969, Pathway 686, Hospital 97, SideEffect 46, Trial 35, Disease 1)
- 관계: 137,479개 (TESTED_IN 89,470, INTERACTS_WITH 46,882, TREATS 14, IN_PATHWAY 729, HAS_SIDE_EFFECT 109, TARGETS 41)

**테스트 검증**:
```bash
python3 test_neo4j.py
# ✅ BRCA 치료 약물 Top 5 조회
# ✅ Docetaxel 부작용 10개 조회 (NEUTROPENIA, NAUSEA, ALOPECIA 등)
# ✅ Docetaxel 타겟 5개 조회 (Tubulin beta-1 chain 등)
# ✅ 임상시험 35개, 병원 97개 확인
```

---

### 작업 9: LLM 모듈 구현 ✅
**상태**: 2026-04-16 완료

**실행 내용**:

1. **llm 디렉토리 생성**:
   - `llm/__init__.py` 생성
   - Python 패키지로 설정

2. **ncis_content.py 구현**:
   - `get_ncis_info(category)` 함수
   - 카테고리: brca, prevention, guide, term
   - 유방암 정보 (정의, 종류, 증상, 위험요인, 통계)
   - 예방 가이드 (검진, 생활습관, 식이요법)
   - 생활 가이드 (치료 중/후 관리, 심리 지원)
   - 용어 사전 (24개 의학 용어)

3. **llm_module.py 구현**:
   - `search_news(query)` - 뉴스 검색 (OpenAI GPT-4 또는 샘플 데이터)
   - `get_lifestyle_guide(topic)` - 생활 가이드 (운동, 식사, 휴식, 정서관리)
   - `search_celebrity_cases(query)` - 유명인 사례 (5명)

4. **서버 재시작 및 테스트**:
   - LLM 모듈 자동 로드 확인
   - `/api/ncis/brca` ✅ 유방암 정보
   - `/api/ncis/prevention` ✅ 예방 가이드
   - `/api/ncis/guide` ✅ 생활 가이드
   - `/api/ncis/term?term=BRCA1` ✅ 용어 검색

**테스트 검증**:
```bash
python3 test_llm_module.py
# ✅ 6개 엔드포인트 모두 정상 작동
# ✅ 국립암센터 정보 제공 (정의, 증상, 통계, 예방, 생활, 용어)
# ✅ LLM 모듈 로드 성공 (HAS_LLM = True)
```

---

### 작업 10: 약물 검색 개선 (퍼지 매칭) ✅
**상태**: 2026-04-16 완료

**실행 내용**:

1. **퍼지 매칭 함수 구현** (`_fuzzy_match_drug()`):
   - Python 표준 라이브러리 `difflib.SequenceMatcher` 사용
   - 유사도 임계값 75% (threshold=0.75)
   - 철자 오류 허용 (예: "Docetacel" → "Docetaxel")

2. **약물 추출 로직 개선** (`_extract_drug_from_query()`):
   - 단계 1: 정확한 매칭 (기존)
   - 단계 2: 파이프라인 약물 퍼지 매칭 (신규)
   - 단계 3: Neo4j CONTAINS 검색 + 퍼지 매칭 (신규)
   - 대소문자 무시 (기존)

3. **테스트 결과**:
   - ✅ 철자 오류: "Docetacel" → "Docetaxel"
   - ✅ 철자 오류: "paclitaxl" → "Paclitaxel"
   - ✅ 철자 오류: "Vinorelbne" → "Vinorelbine"
   - ✅ 대문자: "ROMIDEPSIN" → "Romidepsin"
   - ✅ 소문자: "bortezomib" → "Bortezomib"
   - ✅ 혼합: "DoCeTaXeL" → "Docetaxel"
   - **10/10 테스트 100% 성공**

**테스트 검증**:
```bash
python3 test_drug_search.py
# ✅ 10/10 테스트 성공 (100%)
# ✅ 철자 오류 허용
# ✅ 대소문자 무시
# ✅ Neo4j + 파이프라인 모두 지원
```

---

## 🔧 현재 시스템 상태

### ✅ 정상 작동 기능

1. **파이프라인 데이터 조회**
   - ML/DL 모델 성능 (`/api/v2/pipeline/models`)
   - 앙상블 결과 (`/api/v2/pipeline/ensemble`)
   - METABRIC 검증 (`/api/v2/pipeline/metabric`)
   - ADMET 안전성 (`/api/v2/pipeline/admet`)
   - 최종 후보 15개 (`/api/v2/pipeline/candidates`)

2. **챗봇 AI Chat**
   - 파이프라인 질의: "최종 후보 Top 5", "METABRIC 검증 결과"
   - 예방/생활: "유방암 예방 가이드", "추천 음식"
   - 통계/뉴스: "유방암 발생률", "최신 뉴스"

3. **사용자 모드 전환**
   - 환자/보호자 모드 ↔ 연구자 모드
   - 모드별 메뉴 및 추천 질문

4. **대시보드 시각화**
   - Chart.js 기반 모델 성능 비교
   - 임상 분류 파이차트
   - METABRIC Precision@K 그래프

### ⚠️ 제한 사항

1. **Neo4j 데이터베이스** ✅ → ⚠️ 부분 해결
   - ✅ Drug, Target, Pathway, Hospital 노드 적재 완료
   - ✅ 약물 부작용, 임상시험, 타겟 유전자 조회 가능
   - ✅ 병원 검색 가능
   - ⚠️ 일부 매칭 실패: STRING PPI (0개), OpenTargets association (0개)
   - ⚠️ 1개 약물 누락: Sepantronium bromide (DrugBank에 없음)

2. ~~**LLM 모듈 미구현**~~ ✅ 해결 (2026-04-16)
   - ✅ `llm/ncis_content.py`, `llm/llm_module.py` 구현 완료
   - ✅ 국립암센터 정보 제공 (정의, 증상, 통계, 예방, 생활, 용어 24개)
   - ✅ `/api/ncis/{category}` 엔드포인트 정상 작동
   - ⚠️ 실시간 뉴스 검색은 OpenAI API 필요 (선택적, 샘플 데이터 제공)
   - ⚠️ 챗봇 Intent 분류 개선 필요 (용어 검색 등)

---

## 📝 향후 작업 (TODO)

### ~~우선순위 1: Neo4j 데이터베이스 구축~~ ✅ 완료 (2026-04-16)

**완료 내용**:
- ✅ 스키마 적용: 제약조건 9개, 인덱스 14개
- ✅ S3 데이터 적재: Drug 19,844개, Target 8,880개, CellLine 969개, Pathway 686개
- ✅ 파이프라인 결과: BRCA Disease, 14개 약물, 14개 TREATS 관계
- ✅ 테스트 검증: 약물 조회, 부작용, 타겟, 임상시험, 병원 검색 모두 정상 작동

**재실행 방법** (필요시):
```bash
# 스키마 적용
cd neo4j/schema && python3 apply_schema.py

# S3 데이터 적재
cd neo4j/loaders && python3 load_curated_data.py

# 파이프라인 결과 적재
cd neo4j/loaders && python3 load_brca_pipeline.py

# 테스트
python3 test_neo4j.py
```

---

### ~~우선순위 2: LLM 모듈 구현~~ ✅ 완료 (2026-04-16)

**완료 내용**:
- ✅ `llm/ncis_content.py` - 국립암센터 정보 제공 (정의, 증상, 통계, 예방, 생활, 용어)
- ✅ `llm/llm_module.py` - 뉴스 검색, 생활 가이드, 유명인 사례
- ✅ 엔드포인트 정상 작동:
  - `/api/ncis/brca` - 유방암 정보 (5개 섹션)
  - `/api/ncis/prevention` - 예방 가이드 (검진, 생활습관, 식이요법)
  - `/api/ncis/guide` - 생활 가이드 (치료 중/후 관리)
  - `/api/ncis/term?term=유방암` - 용어 검색 (24개 용어)

**테스트 방법**:
```bash
# 엔드포인트 테스트
python3 test_llm_module.py

# 개별 테스트
curl http://localhost:8000/api/ncis/brca
curl http://localhost:8000/api/ncis/prevention
curl "http://localhost:8000/api/ncis/term?term=BRCA1"
```

---

### ~~우선순위 3: 약물 검색 개선~~ ✅ 완료 (2026-04-16)

**완료 내용**:
- ✅ 대소문자 무시 (기존 기능 유지)
- ✅ 철자 오류 허용 (퍼지 매칭, 75% 임계값)
- ✅ difflib.SequenceMatcher 사용 (추가 패키지 불필요)
- ✅ 파이프라인 + Neo4j 약물 모두 지원
- ✅ 10/10 테스트 100% 성공

**구현 방법**:
```python
from difflib import SequenceMatcher

def _fuzzy_match_drug(query_word: str, drug_list: list[str], threshold: float = 0.8):
    query_lower = query_word.lower()
    best_match = None
    best_ratio = 0.0

    for drug in drug_list:
        ratio = SequenceMatcher(None, query_lower, drug.lower()).ratio()
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = drug

    return best_match
```

**테스트 방법**:
```bash
python3 test_drug_search.py
# 10/10 테스트 성공 (철자 오류, 대소문자)
```

---

### 우선순위 4: 프론트엔드 개선

1. **에러 처리**
   - API 호출 실패 시 사용자 친화적 메시지
   - 로딩 인디케이터 추가

2. **모바일 반응형**
   - 사이드바 자동 축소
   - 터치 인터랙션 개선

3. **채팅 기록 저장**
   - localStorage에 대화 내역 저장
   - 세션 복원 기능

---

## 🧪 테스트 시나리오

### 1. 사용자 모드 전환 테스트
```
1. 페이지 로드 → 기본값 "환자/보호자" 확인
2. 모드 전환 버튼 클릭 → "연구자" 모드로 변경
3. 사이드바 메뉴 확인 → Dashboard, 약물 탐색, ML Pipeline 표시
4. 다시 전환 → "환자/보호자" 모드로 복귀, 메뉴 숨김
5. 페이지 새로고침 → 모드 유지 확인
```

### 2. 챗봇 응답 테스트
**환자/보호자 모드**:
- "유방암 예방 가이드" → 검진/예방 정보 제공
- "유방암 환자 추천 음식" → 식단 가이드 제공
- "최종 후보 Top 5" → Romidepsin, Sepantronium bromide 등
- "Docetaxel 부작용" → Neo4j 필요 안내 (현재)

**연구자 모드**:
- "파이프라인 모델 성능" → ML/DL 성능 비교
- "METABRIC 검증 결과" → 타겟 발현, 생존 유의
- "ADMET 안전성" → 현재/확장/미사용 분류
- "Knowledge Graph 통계" → Neo4j 비어있음 안내

### 3. API 엔드포인트 테스트
```bash
# 파이프라인 메타 정보
curl http://localhost:8000/api/v2/pipeline/meta

# ML 모델만 조회
curl http://localhost:8000/api/v2/pipeline/models?family=ML

# 최종 후보 top 10
curl http://localhost:8000/api/v2/pipeline/candidates?top=10

# 챗봇 테스트
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "최종 후보 Top 5", "user_type": "researcher"}'

# Pathway API (신규 - 2026-04-16)
curl "http://localhost:8000/api/pathways/search?query=PI3K"
curl "http://localhost:8000/api/drug/Romidepsin/pathways?enrich=true"

# 약물 상세 정보
curl "http://localhost:8000/api/drug/Sepantronium%20bromide"
curl "http://localhost:8000/api/drug/Docetaxel/targets"
curl "http://localhost:8000/api/drug/Docetaxel/side_effects"
curl "http://localhost:8000/api/drug/Docetaxel/trials"
```

### 4. Pathway API 통합 (2026-04-16 추가)

**외부 API 통합**:
- **KEGG API**: Pathway 이미지 및 기본 정보
- **Reactome API**: 생물학적 pathway 상세 정보 및 다이어그램
- **WikiPathways**: 검색 링크 제공 (API 접근 제한)

**새로운 엔드포인트**:
```bash
# 통합 pathway 검색
GET /api/pathways/search?query={pathway_name}

# 약물 pathway 정보 (외부 API enrichment)
GET /api/drug/{drug_name}/pathways?enrich=true
```

**응답 예시**:
```json
{
  "kegg": {
    "kegg_id": "map04151",
    "name": "PI3K-Akt signaling pathway",
    "image_url": "https://www.kegg.jp/pathway/map04151"
  },
  "reactome": [
    {
      "stId": "R-HSA-109704",
      "displayName": "PI3K Cascade",
      "diagram_url": "https://reactome.org/.../R-HSA-109704.png"
    }
  ]
}
```

---

## 📊 시스템 아키텍처

```
┌─────────────────┐
│  biochat_v2.html│  ← 프론트엔드 (SPA)
│  (포트: 8000)   │
└────────┬────────┘
         │ HTTP/JSON
         ↓
┌─────────────────┐
│ api_server_v2.py│  ← 백엔드 (FastAPI)
│  (포트: 8000)   │
└────┬──────┬─────┘
     │      │
     │      └──────→ 파이프라인 데이터 (내장)
     │               - ML_MODELS
     │               - DL_MODELS
     │               - FINAL_CANDIDATES
     │
     └────→ Neo4j Aura (비어있음)
              - Drug, Target, Pathway
              - SideEffect, Trial, Hospital
```

---

## 🔐 보안 및 배포

### 개발 환경
- CORS: 전체 허용 (`allow_origins=["*"]`)
- 디버그 모드: 활성화 (`reload=True`)

### 프로덕션 배포 시 주의사항
1. CORS 제한: 특정 도메인만 허용
2. `.env` 파일 보안: 환경 변수로 관리
3. Neo4j 비밀번호 강화
4. HTTPS 적용
5. Rate limiting 추가

---

## 📚 참고 자료

**사용 기술 스택**:
- **프론트엔드**: HTML5, Vanilla JavaScript, Chart.js
- **백엔드**: Python 3.11+, FastAPI, Neo4j Driver
- **데이터베이스**: Neo4j Aura (그래프 DB)
- **스타일**: CSS3 (커스텀, 다크 테마)

**API 문서**:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**프로젝트 구조**:
```
20260416_프론트-백앤드 연결/
├── api_server_v2.py        # FastAPI 백엔드
├── biochat_v2.html         # 프론트엔드
├── .env                    # 환경 변수
├── neo4j/
│   ├── schema/
│   │   └── apply_schema.py
│   └── loaders/
│       ├── load_curated_data.py
│       └── load_pipeline_results.py
└── llm/  (미구현)
    ├── ncis_content.py
    └── llm_module.py
```

---

## 🐛 알려진 이슈

1. ~~**Neo4j 데이터 없음**~~ ✅ 완전 해결 (2026-04-16)
   - ~~증상: 약물 부작용, 임상시험 조회 불가~~
   - ✅ 해결: 데이터 로딩 완료 (30,558개 노드, 180,000+개 관계)
   - ✅ 모든 하위 이슈 해결:
     - ✅ STRING PPI 매칭 성공 (22,938개 INTERACTS_WITH 엣지)
     - ✅ OpenTargets association 매칭 성공 (53개 ASSOCIATED_WITH 엣지)
     - ✅ Sepantronium bromide 추가 완료 (ChEMBL 데이터 포함)
   - 📝 상세 내역:
     - Target gene_symbol 속성 추가: 8,880개
     - gene_symbol 기반 매칭으로 외부 데이터 통합 가능

2. ~~**LLM 모듈 없음**~~ ✅ 해결 (2026-04-16)
   - ~~증상: `/api/ncis/*` 엔드포인트 501 에러~~
   - ✅ 해결: llm 모듈 구현 완료
   - ⚠️ 남은 이슈:
     - Intent 분류 개선 필요 (BRCA1 질문이 drug_info로 분류됨)
     - 실시간 뉴스는 OpenAI API 필요 (현재 샘플 데이터)

3. ~~**약물 검색 정확도**~~ ✅ 해결 (2026-04-16)
   - ~~증상: 철자 오류 시 검색 실패~~
   - ✅ 해결: 퍼지 매칭 구현 완료 (75% 임계값)
   - ✅ 테스트: 10/10 성공 (100%)

---

## 📞 문의

- 프로젝트: 유방암 약물 재창출 Knowledge Graph
- 버전: v2.0.0
- 날짜: 2026-04-16
