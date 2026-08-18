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

## 2026-08-18 재구축에서 새로 만든 파생 데이터 (2026-08-19 완료)

전면 재구축 직후에는 아래 넷이 비어 있었으나(조항 원문이 통째로 바뀌어 구판본 근거가
전부 무효였다), 새 조항 기준으로 다시 만들었다.

- **`ClauseTerm`(정량 조건, 162건)**: 지급한도·자기부담금·면책일수·보상일수한도·
  지연기준시간·1일당지급액을 정규식으로 추출하고, 앵커 문구가 조항 원문의 부분
  문자열인지 `raw_text_is_grounded()`로 검증했다(`backend/app/seed_clause_terms.py`).
  재현율보다 정밀도를 우선했다 — 놓친 숫자 조건이 있을 수 있으나 잘못 분류하지는
  않는다.
- **`DocRequirement`(서류 세부 요건, 1건)**: 구판본의 `ISSUER_MEDICAL`("의료기관에서
  발급한 것이어야") 앵커는 새 6개사 조항 어디에도 없어(전수 검색 확인) 뺐다.
  `PHOTO_GOV_ID`(신분증 요건)만 남겼다 — 보험사마다 "부착된"/"붙은"으로 표현이 약간
  달라 실제 존재하는 문구("사진이 부착된 정부기관발행 신분증")를 그대로 앵커로 썼다.
- **`OverlapRule`(중복 판정, 7건)**: 기존 실손보험·배상책임과의 중복 판정. 근거를
  전수 검색으로 다시 찾아 `clause_id`를 직접 연결했다(구판본의 "보험사명+조항 제목
  조각" 퍼지 조회는 다른 특약을 잘못 집어온 적이 있어 더 안전한 방식으로 바꿨다).
  실손 의료비(해외)·일상배상책임 2건은 여전히 근거 부족으로 `UNKNOWN`이다.
- **`ClauseStandardMap`(표준약관 대조, 11건)**: 제3조(해외 상해의료비)는 6개사 전부,
  제4조(전쟁·내란 면책)는 삼성·현대·메리츠·KB·DB 5개사에서 근거를 확인했다. 카카오페이는
  제4조 문구를 실손 특약에 반복하지 않아(상해사망 보통약관에서만 규정) 단정하지 않고
  행을 만들지 않았다.

## 2026-08-19 후속 수정

- **현대해상 실손의료비 분리**: `OVS_MED_BASIC`(상해·질병을 하나로 묶은 담보)를 다른
  5개사처럼 `OVS_INJ_MED`/`OVS_ILL_MED`로 분리했다. 이 때문에 사고유형 매핑과 표준약관
  대조에서 현대만 빠지던 문제가 해소됐다.
- **사고유형 매핑 문구 증거 보강**: 담보표준코드만으로 못 잡던 L2 3개(`SPC_NATURAL_
  DISASTER`·`PROP_CASH_SECURITIES`·`LIA_LODGING`)와 `TRV_BAGGAGE_DELAY`를 조항 원문의
  실제 문구(천재지변 지급사유 열거, 유가증권 보험목적 제외, 호텔 객실 배상책임 예외,
  수하물 지연 지급사유)를 증거로 추가 매핑했다.

## 알려진 남은 공백

- 실손 표준약관이 이 KB에 없어, 여행자보험의 해외 의료비 담보가 기존 실손과 정확히
  얼마나 겹치는지는 여전히 확인불가(`UNKNOWN`)로 남아 있다.
- 사고유형 L2 중 4개(`TRV_BAGGAGE_LOSS`·`CHG_CANCELLATION`·`SPC_PET_CARE`·`SPC_OTHER`)는
  6개사 중 어느 곳도 해당 담보를 별도로 팔지 않아(전수 검색으로 확인, 여행취소·반려동물
  돌봄·항공사 귀책 수하물 분실 단독 담보가 원문에 없음) 조항 매핑이 비어 있다 — 근거가
  없어 억지로 채우지 않았다.

## 표준약관(비교 대조용) 출처

6개사 약관과는 별개로, 표준약관 대조 기능(2026-08-12)이 쓰는 금융감독원 표준약관 원문의
출처다. `policy_version` 테이블(6개사 상품 버전)에 속하지 않으므로 위 표와 분리해서
기록한다 — `standard_clause` 테이블 각 행에 아래 값이 직접 저장되어 있다. 이 테이블
자체는 2026-08-18 KB 재구축 때 지우지 않았다(6개사 조항과 무관한 정부 공개 자료).

| standard_name | source_url | source_type | downloaded_at | sha256 | 비고 |
|---|---|---|---|---|---|
| 해외여행 실손의료보험 | [금감원 게시물](https://www.fss.or.kr/fss/bbs/B0000115/view.do?nttId=218364&menuNo=200504) 첨부 [별표 15] 표준약관(제5-13조제1항관련)(보험업감독업무시행세칙).hwp | OFFICIAL_HWP(금감원 자체 게시, 2차 유통 아님) | 2026-08-12 | `c3ee7c4cb6d0f23ccb71821c9669176bf926bbe0add0fe2b9c523714a219ed9e` | 게시일 2026-06-15, 조항 개정이력상 최신 개정 2026-05-06. HWP 원문을 `backend/data/standard_terms/`에 커밋(정부 공개 행정규칙이라 재배포 문제 없음). 제1~9조만 적재(비교 범위는 `docs/superpowers/specs/2026-08-12-standard-terms-comparison-design.md` 참고) |

**매핑 커버리지**: 표준 9개 조문 × 6개사 = 54칸 중 9칸(제3조 5개사, 제4조 4개사)만
근거를 확보해 채웠다(위 "2026-08-18 재구축에서 새로 만든 파생 데이터" 참고). 나머지는
대응 조항을 못 찾았거나 애매해 근거 없이 단정하지 않고 비워 뒀다 —
`backend/app/seed_clause_standard_map.py` 주석 참고.

## 알려진 최신성 공백

- 6개사 전부 보험사 공식 발행 파일(`VERIFIED_ISSUED_FILE`)이지만 공개 URL이 없어 재현
  가능한 재다운로드 검증은 못 한다.
- 삼성화재·메리츠·KB·DB는 본문에 시행일이 인쇄돼 있지 않아 `effective_date`가 비어
  있다(추정하지 않았다).
- `VERIFIED_ISSUED_FILE`은 "현재 판매 중"을 보장하지 않는다. 운영 반영 전에는 공식
  상품 공시에서 최신성을 다시 확인해야 한다.
