# 근거 기반 여행자보험 전 생애주기 AI

2026 금융 AI Challenge 출품작. 여행 전에는 필요한 보장과 상품 후보를 6개 손해보험사(삼성화재·현대해상·메리츠화재·KB손보·DB손보·카카오페이손해보험)의 실제 약관 근거와 함께 비교하고, 사고 발생 후에는 자유서술 한 문장만으로 사고유형을 분류해 관련 담보·필요서류·주의사항을 실제 약관 조항 원문 근거와 함께 안내하는 설명가능 AI 웹서비스입니다.

이 프로젝트 전체를 관통하는 절대 원칙 하나: **근거 없는 결과를 내지 않는다.** 어떤 안내든 실제 약관 조항(clause)을 원문 그대로 인용해서 붙이고, 근거를 못 찾으면 "확인불가"라고 정직하게 답합니다.

## 기술 스택

| 영역 | 사용 기술 |
|---|---|
| 백엔드 | FastAPI, SQLAlchemy 2.0, SQLite, Pydantic 2 |
| 프론트엔드 | React 19, TypeScript, Vite, React Router, Framer Motion |
| AI/LLM | Google Gemini API(`google-genai`) — 사고 자유서술 구조화, 사고유형(L1→L2) 분류, 조항·서류 상황별 설명, 담보명 표준화 |
| 문서 처리 | pdfplumber (약관 PDF → 텍스트 추출) |
| 인증/보안 | bcrypt(이메일 계정용), 카카오·구글 OAuth, slowapi(요청 빈도 제한), secure(보안 HTTP 헤더) |

Gemini API 키가 없어도 앱은 정상 동작합니다 — LLM이 필요한 자리(자유서술 구조화, 사고유형 분류 등)마다 규칙기반 폴백(`RuleBasedNLU`, 키워드 매칭 등)이 준비되어 있습니다. 다만 사고유형 세부 분류 정확도와 상황별 설명 품질은 Gemini가 있을 때 크게 좋아집니다.

## 데이터: 6개사 약관을 어떻게 정제해서 쓰는가

`data/raw_pdfs/`의 실제 약관 PDF(보험사당 126~252쪽)를 다음 단계로 구조화해 SQLite(`backend/data/app.db`)에 담습니다.

1. **원문 추출** — pdfplumber로 페이지 단위 텍스트 추출. 표 레이아웃 때문에 열 라벨이 문장 중간에 끼어드는 경우만 제거하고, 나머지는 원문을 한 글자도 바꾸지 않습니다.
2. **조항 단위 분해(`Clause`)** — 조(제N조) 단위로 잘라 `clause_type`(보장정의/면책/제한/조건/서류/공통)을 붙입니다.
3. **표준 담보 매핑(`Coverage` ↔ `CoverageStd`)** — 보험사마다 다른 특약명(예: "여행중 배상책임 특별약관" vs "배상책임보장 특별약관")을 표준 담보 코드(`LIABILITY` 등)로 묶어, 같은 성격의 담보를 보험사 간에 비교할 수 있게 합니다.
4. **사고유형 매핑(`ClauseIncidentMap`)** — 이 프로젝트의 핵심 축. "무슨 사고가 났나"(사고유형)와 "무슨 담보로 받나"(coverage)를 분리해서, 조항 하나하나를 사고유형(L1 8개 고정 + L2 39개, 아래 참고)에 `직접`/`조건부`/`면책`으로 매핑합니다. 담보가 늘어나도 사고 판단 로직 자체는 늘어나지 않는 구조입니다.
5. **수치 조건 구조화(`ClauseTerm`)** — 조항 원문 안의 지급한도·자기부담금·지연기준시간·보상일수한도 등 숫자를 뽑아 별도로 저장합니다. 값의 근거가 된 원문 조각(`raw_text`)은 반드시 조항 원문의 부분 문자열이어야 하며, 이를 벗어나면 절대 저장하지 않습니다(`raw_text_is_grounded()` 검증).
6. **필요서류 매핑(`CoverageDocMap`)** — 담보별 청구 필요서류를 표준 서류 코드(`RequiredDocStd`, 14종)에 연결합니다.

**현재 데이터 규모**(2026-07-31 기준): 담보(Coverage) 122건, 조항(Clause) 400여 건, 사고유형 매핑(ClauseIncidentMap) 379건, 수치 조건(ClauseTerm) 101건, 전 담보 필요서류 연결 100%. 원본 재구성 스크립트는 `backend/app/seed_*.py`에 남아 있습니다.

이 정제 파이프라인을 직접 수행한 방법과 원칙은 `backend/PDF_EXTRACTION_PLAYBOOK.md`, `backend/CLAUSE_TERM_DOC_PLAYBOOK.md`에 정리돼 있습니다 — 특히 "원문에 없는 내용은 절대 지어내지 않되, 원문에 실제 있는 내용은 빠뜨리지 않는다"는 두 원칙을 항상 같이 지킵니다.

### 사고유형(incident_type) 체계

8개 대분류(L1, 고정)와 그 아래 소분류(L2)로 구성됩니다.

- **INJ 상해**: 상해사망·후유장해 / 해외상해치료 / 귀국후 국내치료
- **ILL 질병**: 질병사망·고도후유장해 / 해외·국내 질병치료 / 감염병·격리
- **PROP 휴대품·재물**: 도난 / 파손 / 분실 / 현금·유가증권 / 여권분실
- **LIA 배상책임**: 대인 / 대물 / 임차물·호텔객실
- **TRV 운송**: 항공지연·결항 / 수하물지연·분실 / 항공기납치
- **CHG 여행변경**: 여행취소 / 여행중단·조기귀국
- **EMG 긴급지원**: 수색구조 / 의료이송 / 유해송환 / 가족방문비용
- **SPC 특수·기타**: 전쟁·테러(면책) / 천재지변 / 반려동물돌봄 / 그 외 미분류

8개 L1은 절대 늘리지 않고, 새로운 사고유형은 L2로만 확장합니다. 기존 L2 어디에도 맞지 않는 조항·사고가 나오면 조용히 버리지 않고 `needs_review=True`로 새 L2를 만들어 사람이 나중에 검수하도록 표시합니다(현재 "식중독보상금(입원)", "자택 도난손해(가재)" 2건이 이렇게 생성돼 있습니다).

## 작동 방식 (런타임 흐름)

1. **사고 자유서술 입력** — 사용자가 사고 상황을 문장으로 입력합니다.
2. **1단계 분류(L1)** — Gemini가 자유서술만으로 8개 대분류 중 하나를 즉시 판정합니다(`incident_classify_gemini.classify_l1`).
3. **2단계 확인 질문(L2)** — 판정된 L1에 태그된 질문(`question_bank.applies_to_l1`)만 골라 던집니다. 예: INJ면 진단명/입원여부, TRV면 지연시간처럼 대분류마다 다른 질문 세트가 미리 정의돼 있습니다.
4. **2단계 분류(L2)** — 답변이 쌓일 때마다 Gemini가 그 L1 안의 L2 후보 중 하나로 재분류합니다. 이미 충분히 확신 있게 분류됐으면(신뢰도 임계치 이상) 매번 다시 묻지 않고 재사용해 API 호출을 아낍니다.
5. **담보 매칭** — 확정된 사고유형(type_id)에 `직접`/`조건부`/`면책`으로 매핑된 조항을 가진, 사용자가 등록한 실제 담보만 추려냅니다. 사고 상황의 수식자(활동 등, 예: "스쿠버다이빙")가 면책 조항 원문에 실제로 언급돼 있으면 "직접" 조항이 같이 걸려 있어도 면책을 우선 표시합니다(과도하게 낙관적인 안내 방지).
6. **결과 생성** — 관련 조항(형광펜 근거), 수치 조건(ClauseTerm), 필요서류(CoverageDocMap)를 담보별로 묶어 보여줍니다. 각 카드 설명에는 Gemini가 이번 사고 내용에 맞춰 조항·서류를 풀어 설명한 문장이 자동으로 덧붙습니다(`explain_clause_plain`, `explain_docs_for_incident`) — 실패해도 예외를 삼키고 기본 설명으로 대체되므로 흐름이 끊기지 않습니다.
7. **약관 형광펜** — 사고 상황과 직접 관련된 조항 구간만 노란색으로 표시(`/clauses/{id}/relevance`). 인용은 항상 조항 원문의 부분 문자열인지 대조 검증을 거칩니다.
8. **누락·모순 검증** — LLM을 쓰지 않는 결정적 규칙(`services/validation.py`)으로 보험기간 불일치, 정보 누락, 입력값 모순(예: 수술은 받았는데 입원은 아니오) 등을 별도로 확인합니다.

담보를 찾지 못하면 "청구검토후보"라고 억지로 말하지 않고 "확인불가"로 정직하게 답합니다(근거 없는 결과 금지).

## 실행 방법

이 저장소를 클론하면 **정제된 데이터가 들어있는 SQLite DB(`backend/data/app.db`)가 그대로 포함**되어 있으므로, 시드 스크립트를 처음부터 다시 돌릴 필요 없이 바로 서버를 띄울 수 있습니다.

### 1. 백엔드

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate   # Windows, macOS/Linux는 source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env     # Windows: copy .env.example .env
# .env를 열어 GEMINI_API_KEY 등을 채웁니다(비워둬도 규칙기반 폴백으로 동작).

uvicorn app.main:app --port 8000
```

API 문서: `http://localhost:8000/docs`

앱을 처음 띄우면 `main.py`가 스키마 마이그레이션(누락된 컬럼 추가)을 자동으로 실행합니다. DB를 완전히 새로 만들고 싶다면(`backend/data/app.db` 삭제 후) `backend/app/seed_*.py`를 아래 순서로 실행하세요 — 단, 이 경우 조항 원문 확보를 위해 `data/raw_pdfs/`에 각사 약관 PDF가 있어야 합니다(아래 "약관 원문" 참고).

```bash
python -m app.seed_samsung && python -m app.seed_hyundai && python -m app.seed_meritz \
  && python -m app.seed_kb && python -m app.seed_db && python -m app.seed_kakaopay \
  && python -m app.seed_personal_effects && python -m app.seed_questions && python -m app.seed_validation_rules \
  && python -m app.seed_incident_types && python -m app.seed_clause_incident_map
# 이후 backend/app/seed_*_inj_deep.py, seed_*_full_chunk*.py, seed_*_terms_docs.py를
# 보험사별로 순서대로 실행하면 이번에 확장한 딥다이브 데이터까지 재구성됩니다.
```

### 2. 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

`http://localhost:5173` — 백엔드가 8000번 포트에 떠 있어야 정상 동작합니다.

## 프로젝트 구조

```
backend/
  app/
    main.py              FastAPI 앱, 스키마 마이그레이션
    models/               SQLAlchemy 모델(kb.py=약관 KB, user.py=사용자, question.py, analysis.py)
    routers/               API 엔드포인트
    services/               핵심 로직
      claim_review.py            사고유형 기반 담보 매칭 규칙 엔진
      incident_classify_gemini.py 사고유형 L1/L2 분류(Gemini)
      nlu.py / nlu_gemini.py       자유서술 구조화
      clause_spans_gemini.py       약관 형광펜 관련도 계산
      validation.py                결정적 누락·모순 검증
    seed_*.py               6개사 약관 데이터 시딩 스크립트
  data/app.db              SQLite DB(정제된 데이터 포함, 저장소에 커밋됨)
  PDF_EXTRACTION_PLAYBOOK.md      조항 추출 원칙 문서
  CLAUSE_TERM_DOC_PLAYBOOK.md     수치·서류 구조화 원칙 문서
frontend/   React + TypeScript + Vite
docs/       규정 준수 문서(약관 원문 출처 등록대장 등)
data/raw_pdfs/  원본 약관 PDF (gitignore, 로컬 전용 — 아래 "약관 원문" 참고)
```

## 약관 원문

`data/raw_pdfs/`, `data/processed/`는 저장소에 포함하지 않습니다. 각 보험사가 공식 홈페이지에 공개한 약관 PDF 원문을 재배포하지 않기 위함입니다(`docs/compliance/source_register.md`에 각사 공식 출처 URL과 수집 방법을 기록해 두었습니다). 조항 원문 발췌 자체는 `backend/app/seed_*.py`와 `backend/data/app.db`에 이미 포함돼 있으므로, PDF 없이도 서버 실행과 조회는 됩니다 — 원문을 처음부터 다시 추출하거나 검수하려면 `source_register.md`의 URL에서 각자 PDF를 받아야 합니다.

## 구현 현황

- 가입 전 맞춤 추천(`POST /trips`) — 6개사 담보·면책조항 비교, 위험활동 감지
- 내 보험 보관함(`/users/{id}/policies`) — 보험사명·담보명 KB 자동 매칭
- **사고유형(L1/L2) 기반 청구 검토** + 단계별 확인 질문(`/incidents`, `/incidents/{id}/answers`) — 예전 키워드 휴리스틱 방식은 폐기됨
- 서류 체크 + 누락·모순 검증(`/incidents/{id}/checklist`, `/evidence`)
- 약관 형광펜 — 사고 상황과 직접 관련된 조항 구간만 노란색으로 표시, 검색 지원
- 조항 수치 조건(ClauseTerm) 별도 표시 — 지급한도·자기부담금 등을 배지로 분리 노출
- 활동 기반 면책 우선 판단 — 사고 상황의 수식자(예: 스쿠버다이빙)가 면책 조항과 실제로 일치하면 과도하게 낙관적인 안내를 하지 않음
- 사고 내용과 조항·필요서류를 연결한 Gemini 상황별 설명 자동 표시
- 모든 결과는 실제 약관 조항 근거가 없으면 자동으로 "확인불가" 처리
- 인증/보안 — 카카오·구글 로그인, 회원가입 동의, 로그인 계정 간 데이터 접근 차단(IDOR 방지), 요청 빈도 제한, 보안 HTTP 헤더, CORS 제한

미구현/알려진 한계:
- 실제 가입금액(상품요약서·보험다모아 기준 숫자)은 아직 반영되지 않음 — 약관에 명시된 조건·한도까지만 반영됨
- 카카오페이손해보험의 배상책임/휴대물품손해/항공기납치/구조송환/여행중단/여권분실 6개 담보는 검수 중 원문이 아닌 요약본으로 확인되어 제거함 — 재추출 필요
- L1 분류가 애매할 때 후보 2~3개를 직접 골라 확인하는 UX는 아직 없음(추가 질문으로만 좁힘)
- 벡터 임베딩 기반 RAG는 구현되어 있지 않음(SQL 기반 후보 필터링만 사용)
- 평가지표(eval_log) 자동 산출, 실제 PASS/FDS 등 금융권 수준 본인인증·이상거래탐지(외부 유료 연동 필요)는 이번 프로젝트 범위에서 제외
