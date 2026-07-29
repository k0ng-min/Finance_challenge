# 근거 기반 여행자보험 전 생애주기 AI

2026 금융 AI Challenge 출품작. 여행 전에는 필요한 보장과 상품 후보를 6개 손해보험사(삼성화재·현대해상·메리츠화재·KB손보·DB손보·카카오페이손해보험)의 실제 약관 근거와 함께 비교하고, 사고 발생 후에는 등록한 여러 보험계약을 통합 분석해 청구 검토 담보·필요서류·누락사항을 안내하는 설명가능 AI 웹서비스입니다.

기획 배경과 요구사항은 [`ne.md`](./ne.md), 데이터 모델은 [`new.md`](./new.md)를 참고하세요.

## 구조

```
backend/   FastAPI + SQLAlchemy + SQLite
frontend/  React + TypeScript + Vite
docs/      규정 준수 문서 (출처 등록대장 등)
data/      원본 약관 PDF·추출 텍스트 (gitignore, 로컬 전용 — 아래 "약관 원문" 참고)
```

## 실행 방법

### 1. 백엔드

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate   # Windows
pip install -r requirements.txt

# 약관 원문 PDF를 먼저 확보해 data/raw_pdfs/ 에 두어야 시드가 동작합니다 (아래 "약관 원문" 참고)
python -m app.seed_samsung
python -m app.seed_hyundai
python -m app.seed_meritz
python -m app.seed_kb
python -m app.seed_db
python -m app.seed_kakaopay
python -m app.seed_questions
python -m app.seed_validation_rules

uvicorn app.main:app --port 8000
```

API 문서: `http://localhost:8000/docs`

### 2. 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

`http://localhost:5173` — 백엔드가 8000번 포트에 떠 있어야 합니다.

## 약관 원문

`data/raw_pdfs/`, `data/processed/`는 저장소에 포함하지 않습니다. 각 보험사가 공식 홈페이지에 공개한 약관 PDF 원문을 재배포하지 않기 위함입니다(`docs/compliance/source_register.md`에 각사 공식 출처 URL과 수집 방법을 기록해 두었습니다). 시드 스크립트(`backend/app/seed_*.py`)에는 형광펜 근거로 필요한 조항만 원문 그대로 발췌해 코드에 포함되어 있으므로, PDF 없이도 시드 스크립트 실행 자체는 됩니다 — 다만 재현/검수를 위해 원문을 직접 보려면 `source_register.md`의 URL에서 각자 다시 받아야 합니다.

## 구현 현황

- 가입 전 맞춤 추천 (`POST /trips`) — 6개사 담보·면책조항 비교, 위험활동 감지
- 내 보험 보관함 (`/users/{id}/policies`) — 보험사명·담보명 KB 자동 매칭
- 사고 후 청구 검토 + 능동 질문 (`/incidents`, `/incidents/{id}/answers`)
- 서류 체크 + 누락·모순 검증 (`/incidents/{id}/checklist`, `/evidence`)
- 모든 결과는 실제 약관 조항(clause) 근거가 없으면 자동으로 "확인불가" 처리 (형광펜 근거검증)
- LLM 역할(자유서술 구조화·담보명 표준화)은 `backend/app/services/nlu.py`의 `NLUEngine` 인터페이스로 분리 — 현재는 규칙기반 구현체이며, 외부 AI API 대신 자체 경량 모델로 교체할 자리로 설계함

미구현: React 화면의 실사용자 UX 다듬기, 평가지표(eval_log) 자동 산출, 질병·휴대품·배상책임 등 확장 담보.
