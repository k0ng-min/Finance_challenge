# 약관 데이터 출처·버전 등록부

이 문서는 서비스 KB에 적재된 6개 보험사 약관의 출처, 버전, 최신성 상태와 데이터 완전성을 한 곳에서 감사하기 위한 등록부다. 기계 판독 원본은 `backend/data/dataset_manifest.json`이며 아래 표는 사람이 검토하기 위한 동일 정보의 요약이다.

## 검증 상태 정의

| 상태 | 의미 | 추천 순위 사용 |
|---|---|---|
| `VERIFIED_CURRENT` | 공식 출처에서 현재 판매 버전임을 확인 | 허용 |
| `VERIFIED_VERSIONED` | 공식 출처와 특정 버전·시행일을 확인했으나 현재 판매 여부는 별도 판단 | 허용 |
| `NEEDS_CURRENT_VERSION_CHECK` | 공식 출처이나 최신 버전 또는 시행일 재확인 필요 | 제외 |
| `SECONDARY_SOURCE` | 공식 원문이 아닌 판매사·대행사 등 2차 출처 | 제외 |
| `EXTRACTION_INCOMPLETE` | 원문 추출·매핑이 불완전 | 제외 |

## 표준 출처 등록부

SHA-256은 2026-08-08에 등록 URL에서 다시 받은 PDF 바이트의 지문이다. 과거 수집 파일을 보존한 값으로 오해해서는 안 된다.

| insurer | product_name | policy_version | effective_date | source_url | source_type | downloaded_at | sha256 | verification_status | coverage_count | clause_count | incident_map_count | term_count | doc_map_count | known_gap |
|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|
| SAMSUNG | 해외여행보험(다이렉트) | 50002_0 | 2024-04-01 | [공식 PDF](https://www.samsungfire.com/publication/pdf/50002_0_20240401_file1.pdf) | OFFICIAL_PDF | 2026-07-28 | `0ca4c127c566bc3a61d41ddb459d7134e8d5b931b06a99bceff6b48f92db7bb0` | VERIFIED_VERSIONED | 21 | 68 | 84 | 10 | 73 | 원문 전체 수작업 대조 전 |
| HYUNDAI | 다이렉트 해외여행보험 | CM8403_20250630 | 2025-06-30 | [공식 PDF](https://direct.hi.co.kr/dhNAS/terms/CM8403_20250630.pdf) | OFFICIAL_PDF | 2026-07-29 | `294b8f4e9afd724c6eac94b6c25a0bd948e064b40d3817f6c40b6976035c72ed` | VERIFIED_VERSIONED | 21 | 104 | 48 | 20 | 90 | 원문 전체 수작업 대조 전 |
| MERITZ | 해외여행보험 | udirect_수집본 | 미확정 | [2차 출처 PDF](https://ud.udirect.co.kr/travel/meritz/files/overseas.pdf) | SECONDARY_DISTRIBUTOR_PDF | 2026-07-29 | `6dbd0749379312a7400354b05c501ddb221aded066dca6155217c72b5b5a22a0` | SECONDARY_SOURCE | 26 | 52 | 66 | 11 | 89 | 공식 메리츠 원문과 시행일 미확정 |
| KB | KB해외여행보험 | 15332_202004 | 2020-04-01 | [공식 PDF](https://direct.kbinsure.co.kr/dwlddoc/lifeshop_1KBoverseasestravel(15332)_policy_202004.pdf) | OFFICIAL_PDF | 2026-07-29 | `05be224f1faa8835a18dc4e7546baf80c84ce83089db7038e7ab75ac86e29a40` | NEEDS_CURRENT_VERSION_CHECK | 15 | 39 | 54 | 13 | 56 | 2026-07-28 개정 상품의 최신 약관 PDF 미확정 |
| DB | 해외여행보험 | idbins_수집본 | 미확정 | [공식 PDF](https://www.idbins.com/pcweb/bizxpress/pdc/tl/__etc/%ED%95%B4%EC%99%B8%EC%97%AC%ED%96%89.pdf) | OFFICIAL_PDF | 2026-07-29 | `2050e5ce0ae6ec928cd94d9e51165657b52b6e2b71a0ee16b1f93b0698cf175a` | NEEDS_CURRENT_VERSION_CHECK | 21 | 66 | 65 | 30 | 87 | 버전·시행일 미확정 |
| KAKAOPAY | 해외여행보험 | 20241101 | 2024-11-01 | [공식 CDN PDF](https://static.kakaoinsure.com/notilus/files/20241101_%ED%95%B4%EC%99%B8%EC%97%AC%ED%96%89%EB%B3%B4%ED%97%98%20%EC%95%BD%EA%B4%80.pdf) | OFFICIAL_CDN_PDF | 2026-07-29 | `d9e33fa75a75ec284cb35f4880ae6735693fcf0081bb601867ddc21001742cfb` | VERIFIED_VERSIONED | 12 | 34 | 35 | 12 | 51 | 원문 전체 수작업 대조 전 |

## 무결성 감사 규칙

`cd backend && python -m scripts.validate_kb`를 실행하면 다음을 검사한다.

1. `Clause → Coverage → PolicyVersion → Product → Insurer` 추적과 정책 버전 일치
2. 약관 버전·시행일·출처 URL·PDF SHA-256 및 매니페스트/DB 일치
3. 추천 근거인 `ClauseTerm`, `CoverageDocMap`, `ClauseIncidentMap`, `OverlapRule`의 참조 무결성
4. 사고 유형 매핑의 유효한 관계값과 추천 대상 관계값 게이트
5. `ClauseTerm.raw_text`와 `OverlapRule.anchor_phrase`가 실제 `Clause.text`에 존재하는지 여부
6. 보험사별 Coverage/Clause/Incident Map/Term/Docs 완전성 집계
7. 사용자·분석 실행 데이터와 분리한 KB 전용 동결 지문

현재 DB에는 `직접/조건부/면책` 외에 과거 시드에서 만든 `제한` 매핑 15건이 있다. `제한`은 알려진 레거시 값으로 무결성 오류는 아니지만 추천 근거에서는 제외되므로 감사 결과에 경고로 표시된다.

## 표준약관(비교 대조용) 출처

6개사 약관과는 별개로, 표준약관 대조 기능(2026-08-12)이 쓰는 금융감독원 표준약관 원문의
출처다. `policy_version` 테이블(6개사 상품 버전)에 속하지 않으므로 위 표와 분리해서
기록한다 — `standard_clause` 테이블 각 행에 아래 값이 직접 저장되어 있다.

| standard_name | source_url | source_type | downloaded_at | sha256 | 비고 |
|---|---|---|---|---|---|
| 해외여행 실손의료보험 | [금감원 게시물](https://www.fss.or.kr/fss/bbs/B0000115/view.do?nttId=218364&menuNo=200504) 첨부 [별표 15] 표준약관(제5-13조제1항관련)(보험업감독업무시행세칙).hwp | OFFICIAL_HWP(금감원 자체 게시, 2차 유통 아님) | 2026-08-12 | `c3ee7c4cb6d0f23ccb71821c9669176bf926bbe0add0fe2b9c523714a219ed9e` | 게시일 2026-06-15, 조항 개정이력상 최신 개정 2026-05-06. HWP 원문을 `backend/data/standard_terms/`에 커밋(정부 공개 행정규칙이라 재배포 문제 없음). 제1~9조만 적재(비교 범위는 `docs/superpowers/specs/2026-08-12-standard-terms-comparison-design.md` 참고) |

**매핑 커버리지**: 표준 9개 조문 × 6개사 = 54칸 중 9칸(제3조 6개사 전부, 제4조 3개사)만
근거를 확보해 채웠다. 나머지는 대응 조항을 못 찾았거나 애매해 근거 없이 단정하지 않고
비워 뒀다 — `clause_standard_map` 시드 스크립트(`backend/app/seed_clause_standard_map.py`)
주석 참고.

## 알려진 최신성 공백

- 메리츠: 공식 도메인의 동일 약관 원문과 시행일을 확인하기 전까지 추천 순위에서 제외한다.
- KB: 보유 PDF는 2020-04 버전이다. 2026-07-28 개정 상품의 최신 약관을 확보하기 전까지 추천 순위에서 제외한다.
- DB: 공식 PDF는 확인했지만 버전·시행일을 특정하지 못해 추천 순위에서 제외한다.
- `VERIFIED_VERSIONED`는 “현재 판매 중”을 보장하지 않는다. 운영 반영 전에는 공식 상품 공시에서 최신성을 다시 확인해야 한다.
