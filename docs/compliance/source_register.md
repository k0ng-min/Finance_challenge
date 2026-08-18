# 약관 데이터 출처·버전 등록부

이 문서는 서비스 KB에 적재된 6개 보험사 약관의 출처, 버전, 최신성 상태와 데이터 완전성을 한 곳에서 감사하기 위한 등록부다. 기계 판독 원본은 `backend/data/dataset_manifest.json`이며 아래 표는 사람이 검토하기 위한 동일 정보의 요약이다.

## 2026-08-18 전면 재구축

사용자가 보험사 공식 발행 경로에서 직접 받은 2026년판 약관 PDF 8개(카카오페이는 3파일을
1개 상품으로 통합)로 KB를 전면 재구축했다. 이전 판본(2024~2025년 수집분)은 SHA-256이
전혀 일치하지 않는 다른 문서였고, 조항 363개 중 새 판본에 원문 그대로 남은 것이 130개
(36%)뿐이었다 — 설계 문서
[`docs/superpowers/specs/2026-08-18-terms-rebuild-2026-design.md`](../superpowers/specs/2026-08-18-terms-rebuild-2026-design.md)
참고.

원본 PDF는 방화벽 안쪽 사내 경로에서 사용자가 직접 받았고 공개 URL이 없다. 문서 자체는
보험사 공식 발행본이므로 이 사실을 반영해 검증 상태에 `VERIFIED_ISSUED_FILE`을 추가했다.

## 검증 상태 정의

| 상태 | 의미 | 추천 순위 사용 |
|---|---|---|
| `VERIFIED_CURRENT` | 공식 출처에서 현재 판매 버전임을 확인 | 허용 |
| `VERIFIED_VERSIONED` | 공식 출처와 특정 버전·시행일을 확인했으나 현재 판매 여부는 별도 판단 | 허용 |
| `VERIFIED_ISSUED_FILE` | 보험사가 공식 발행한 약관 파일(공개 URL 없음) | 허용 |
| `NEEDS_CURRENT_VERSION_CHECK` | 공식 출처이나 최신 버전 또는 시행일 재확인 필요 | 제외 |
| `SECONDARY_SOURCE` | 공식 원문이 아닌 판매사·대행사 등 2차 출처 | 제외 |
| `EXTRACTION_INCOMPLETE` | 원문 추출·매핑이 불완전 | 제외 |

## 표준 출처 등록부

SHA-256은 2026-08-18에 사용자가 제공한 PDF 파일 바이트의 지문이다. 원본은
`backend/data/raw_pdfs/`(gitignore 대상, 재배포하지 않음)에 있다.

| insurer | product_name | policy_version | effective_date | source_url | source_type | downloaded_at | sha256 | verification_status | coverage_count | clause_count | incident_map_count | term_count | doc_map_count | known_gap |
|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|
| SAMSUNG | 해외여행보험 | 2026수집본 | 미확정 | (공개 URL 없음) | OFFICIAL_ISSUED_FILE | 2026-08-18 | `95fc1ac011933d8b329eeee3698cfd8adffa0540bf353b0e90dca446156406b7` | VERIFIED_ISSUED_FILE | 17 | 48 | 71 | 0 | 67 | 표지가 이미지라 버전 코드·시행일 미인쇄. clause_term/doc_requirement 미구축 |
| HYUNDAI | 다이렉트 해외여행보험 | 8403-0000-20260606 | 2026-06-06 | (공개 URL 없음) | OFFICIAL_ISSUED_FILE | 2026-08-18 | `19fcd2966b4d17fdca41bd8edfdfff028a4de3ba38ed3574e83406262ec3c878` | VERIFIED_ISSUED_FILE | 12 | 42 | 33 | 0 | 37 | clause_term/doc_requirement 미구축 |
| MERITZ | 다이렉트 해외여행보험 | 메리츠일반-특종/상해/여행B-10-2607A | 미확정 | (공개 URL 없음) | OFFICIAL_ISSUED_FILE | 2026-08-18 | `f58406b6496f1031da5f5c870e73c65b7b85ef06d16e2b04448b53d21b61dbdd` | VERIFIED_ISSUED_FILE | 42 | 143 | 145 | 0 | 162 | 약관번호 뒷자리(2607A)를 시행일로 단정할 근거 없음. clause_term/doc_requirement 미구축 |
| KB | KB해외여행보험(다이렉트) | 일반26-15505-1 | 미확정 | (공개 URL 없음) | OFFICIAL_ISSUED_FILE | 2026-08-18 | `49a5ccecdb5cffe5bcf730efedf13322e0719cff8261aebcf47b724cc064e573` | VERIFIED_ISSUED_FILE | 25 | 56 | 66 | 0 | 92 | 표지 표기는 "2026.06"뿐. 실손의료비 특약(p.170-286)은 핵심 보장정의·면책만 반영. clause_term/doc_requirement 미구축 |
| DB | 프로미 해외여행보험Ⅰ | 프로미Ⅰ_2026수집본 | 미확정 | (공개 URL 없음) | OFFICIAL_ISSUED_FILE | 2026-08-18 | `151c57ec603cad5b5d5dcc4128468e2ac9102d45d842554f1d98fbbecbf3e008` | VERIFIED_ISSUED_FILE | 17 | 94 | 165 | 0 | 68 | 버전 코드·시행일 미인쇄. clause_term/doc_requirement 미구축 |
| KAKAOPAY | 해외여행보험 | 제2026-0199호 | 2026-05-04 | (공개 URL 없음) | OFFICIAL_ISSUED_FILE | 2026-08-18 | `3ed801afa9c8e930b01aed97f4ba8d67823d9ee7d5e4d2d533a3a80f67b4009c` | VERIFIED_ISSUED_FILE | 18 | 29 | 24 | 0 | 71 | 「함께하는 해외여행보험」·「함께하는 해외여행보험II」 두 파일과 본문 동일 확인 후 통합(각 sha256은 `dataset_manifest.json` 참고). clause_term/doc_requirement 미구축 |

## 무결성 감사 규칙

`cd backend && python -m scripts.validate_kb`를 실행하면 다음을 검사한다.

1. `Clause → Coverage → PolicyVersion → Product → Insurer` 추적과 정책 버전 일치
2. 약관 버전·시행일·출처 URL·PDF SHA-256 및 매니페스트/DB 일치
3. 추천 근거인 `ClauseTerm`, `CoverageDocMap`, `ClauseIncidentMap`, `OverlapRule`의 참조 무결성
4. 사고 유형 매핑의 유효한 관계값과 추천 대상 관계값 게이트
5. `ClauseTerm.raw_text`와 `OverlapRule.anchor_phrase`가 실제 `Clause.text`에 존재하는지 여부
6. 보험사별 Coverage/Clause/Incident Map/Term/Docs 완전성 집계
7. 사용자·분석 실행 데이터와 분리한 KB 전용 동결 지문

별도로 `cd backend && python -m scripts.verify_clause_grounding`을 실행하면 모든
`Clause.text`가 원본 PDF 추출본(`backend/data/processed/*_full_text.txt`)의 부분
문자열인지 대조한다. 표 레이아웃 때문에 열 라벨이 문장 중간에 낀 것을 지운 경우는
공백만 제거하는 이 스크립트의 정규화 기준으로는 여전히 "불일치"로 잡힐 수 있다 —
사람이 직접 대조해 정당함을 확인한 사례들이다.

## 2026-08-18 재구축에서 아직 만들지 않은 것

- **`ClauseTerm`(정량 조건)**: 지급한도·자기부담금·면책일수 등을 조항에서 뽑아 구조화하는
  작업. 조항 원문 재추출이 끝난 지금부터 다시 시작해야 한다.
- **`DocRequirement`(서류 세부 요건)**: `backend/app/seed_doc_requirements.py`가 앱
  기동 시 자동 실행을 시도하지만, 찾던 앵커 문구("의료기관에서 발급한 것이어야" 등)가
  새 조항 원문에 그대로 없어 조용히 건너뛴다(앱은 죽지 않는다). 새 조항 문구에 맞는
  앵커를 다시 찾아야 한다.
- **`OverlapRule`**: 기존 실손보험과의 중복 판정 규칙. 재구축 전 규칙도 실손 표준약관
  근거 부족으로 대부분 `UNKNOWN`이었다.
- **`ClauseStandardMap`**: 표준약관(아래 절) 대 6개사 조항 대조. 구 조항 기준 9칸만
  채워져 있었고, 그 대응 관계는 새 조항에서 다시 확인해야 한다.

이 넷은 `dataset_manifest.json`의 각 보험사 `known_gap`에도 동일하게 기록돼 있다.

## 표준약관(비교 대조용) 출처

6개사 약관과는 별개로, 표준약관 대조 기능(2026-08-12)이 쓰는 금융감독원 표준약관 원문의
출처다. `policy_version` 테이블(6개사 상품 버전)에 속하지 않으므로 위 표와 분리해서
기록한다 — `standard_clause` 테이블 각 행에 아래 값이 직접 저장되어 있다. 이 테이블
자체는 2026-08-18 KB 재구축 때 지우지 않았다(6개사 조항과 무관한 정부 공개 자료).

| standard_name | source_url | source_type | downloaded_at | sha256 | 비고 |
|---|---|---|---|---|---|
| 해외여행 실손의료보험 | [금감원 게시물](https://www.fss.or.kr/fss/bbs/B0000115/view.do?nttId=218364&menuNo=200504) 첨부 [별표 15] 표준약관(제5-13조제1항관련)(보험업감독업무시행세칙).hwp | OFFICIAL_HWP(금감원 자체 게시, 2차 유통 아님) | 2026-08-12 | `c3ee7c4cb6d0f23ccb71821c9669176bf926bbe0add0fe2b9c523714a219ed9e` | 게시일 2026-06-15, 조항 개정이력상 최신 개정 2026-05-06. HWP 원문을 `backend/data/standard_terms/`에 커밋(정부 공개 행정규칙이라 재배포 문제 없음). 제1~9조만 적재(비교 범위는 `docs/superpowers/specs/2026-08-12-standard-terms-comparison-design.md` 참고) |

**매핑 커버리지**: `clause_standard_map`은 2026-08-18 재구축으로 비어 있다(위 "아직
만들지 않은 것" 참고) — 구 조항 기준 대응 관계(9/54칸)는 새 조항에서 다시 확인해야 하며,
지금 화면의 표준약관 대조 기능은 대응 근거가 없는 상태다.

## 알려진 최신성 공백

- 6개사 전부 보험사 공식 발행 파일(`VERIFIED_ISSUED_FILE`)이지만 공개 URL이 없어 재현
  가능한 재다운로드 검증은 못 한다.
- 삼성화재·메리츠·KB·DB는 본문에 시행일이 인쇄돼 있지 않아 `effective_date`가 비어
  있다(추정하지 않았다).
- `VERIFIED_ISSUED_FILE`은 "현재 판매 중"을 보장하지 않는다. 운영 반영 전에는 공식
  상품 공시에서 최신성을 다시 확인해야 한다.
