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

## 알려진 최신성 공백

- 메리츠: 공식 도메인의 동일 약관 원문과 시행일을 확인하기 전까지 추천 순위에서 제외한다.
- KB: 보유 PDF는 2020-04 버전이다. 2026-07-28 개정 상품의 최신 약관을 확보하기 전까지 추천 순위에서 제외한다.
- DB: 공식 PDF는 확인했지만 버전·시행일을 특정하지 못해 추천 순위에서 제외한다.
- `VERIFIED_VERSIONED`는 “현재 판매 중”을 보장하지 않는다. 운영 반영 전에는 공식 상품 공시에서 최신성을 다시 확인해야 한다.
# 출처 등록대장 (source_register.md)

## 1. 삼성화재해상보험

| 항목 | 내용 |
|---|---|
| 상품 | 해외여행보험 (다이렉트) |
| 약관 버전 | 50002_0 |
| 시행일 | 2024-04-01 |
| 원문 출처 URL | https://www.samsungfire.com/publication/pdf/50002_0_20240401_file1.pdf |
| 수집 방법 | 삼성화재 공식 홈페이지 공개 약관 PDF 직접 다운로드 (검색 경유, 로그인/유료 접근 없음) |
| 수집일 | 2026-07-28 |
| 로컬 저장 경로 | data/raw_pdfs/samsung_overseas_50002_0_20240401.pdf |
| 페이지 수 | 252 |
| 검수 상태 | raw (KB 적재 시 조항별 원문 대조 검수 필요) |
| 비고 | new.md ERD의 표준 담보 사전(coverage_std)이 참조하는 기준 약관. |

## 2. 현대해상화재보험

| 항목 | 내용 |
|---|---|
| 상품 | 다이렉트 해외여행보험 |
| 약관 코드/시행일 | CM8403, 2025-06-30 |
| 원문 출처 URL | https://direct.hi.co.kr/dhNAS/terms/CM8403_20250630.pdf |
| 수집 방법 | 현대해상 다이렉트 공식 도메인(direct.hi.co.kr) PDF 직접 다운로드 |
| 수집일 | 2026-07-29 |
| 로컬 저장 경로 | data/raw_pdfs/hyundai_overseas_CM8403_20250630.pdf |
| 페이지 수 | 140 |
| 검수 상태 | raw |

## 3. 메리츠화재해상보험

| 항목 | 내용 |
|---|---|
| 상품 | 해외여행보험 |
| 원문 출처 URL | https://ud.udirect.co.kr/travel/meritz/files/overseas.pdf |
| 수집 방법 | **주의**: 메리츠화재 공식 도메인(meritzfire.com)에서 약관 PDF 정적 다운로드 링크를 찾지 못함(페이지 JS 동적 렌더링). 여행보험 판매 파트너사 '유다이렉트(ud.udirect.co.kr)'가 게시한 PDF를 대신 사용. 본문에 "메리츠화재해상보험주식회사" 명의 및 실제 조항 번호·본문이 포함되어 내용은 진본으로 판단되나, 공식 1차 출처가 아니므로 신뢰도가 상대적으로 낮음. |
| 수집일 | 2026-07-29 |
| 로컬 저장 경로 | data/raw_pdfs/meritz_overseas_udirect.pdf |
| 페이지 수 | 220 |
| 검수 상태 | raw — **관문2에서 공식 도메인 원문 재확인 필요** |

## 4. KB손해보험

| 항목 | 내용 |
|---|---|
| 상품 | KB해외여행보험 |
| 약관 코드/배포월 | 15332, 2020-04 |
| 원문 출처 URL | https://direct.kbinsure.co.kr/dwlddoc/lifeshop_1KBoverseasestravel(15332)_policy_202004.pdf |
| 수집 방법 | KB손해보험 다이렉트 공식 도메인(direct.kbinsure.co.kr) PDF 직접 다운로드 |
| 수집일 | 2026-07-29 |
| 로컬 저장 경로 | data/raw_pdfs/kb_overseas_15332_202004.pdf |
| 페이지 수 | 169 |
| 검수 상태 | raw — **주의**: 2026-07-28 KB손해보험이 'KB해외여행보험' 개정 출시(고급형/표준형/실속형) 공지가 확인됨(insight.kbinsure.co.kr). 개정판 약관 PDF 링크는 못 찾음(JS 동적 렌더링). 현재 시드는 2020-04 배포본 기준이므로 **최신 버전 재확인 필요**. |

## 5. DB손해보험

| 항목 | 내용 |
|---|---|
| 상품 | 해외여행보험 |
| 원문 출처 URL | https://www.idbins.com/pcweb/bizxpress/pdc/tl/__etc/해외여행.pdf |
| 수집 방법 | DB손해보험 공식 도메인(idbins.com) PDF 직접 다운로드 |
| 수집일 | 2026-07-29 |
| 로컬 저장 경로 | data/raw_pdfs/db_overseas.pdf |
| 페이지 수 | 126 |
| 검수 상태 | raw — 약관 버전 라벨/시행일이 파일명에 명시되지 않아 원문 내 명시적 표기 재확인 필요 |

## 6. 카카오페이손해보험

| 항목 | 내용 |
|---|---|
| 상품 | 해외여행보험 |
| 약관 시행일 | 2024-11-01 |
| 원문 출처 URL | https://static.kakaoinsure.com/notilus/files/20241101_해외여행보험 약관.pdf |
| 수집 방법 | 공식 홈페이지 상품공시(kakaopayinscorp.co.kr/disclosure/goods)는 SPA(JS 동적 렌더링)라 정적 크롤링이 불가하여, 해당 페이지가 내부적으로 호출하는 공식 공개 API(papi.kakaoinsure.com/notilus/v1/notices, categoryId=15 "판매중 상품")를 통해 게시물 목록(제목·시행일·PDF 경로)을 조회한 뒤 '해외여행보험' 최신 보험약관(INSURANCE_POLICY 타입) 항목을 다운로드함. 인증·로그인 불필요, 사이트가 사용자에게 실제로 내려주는 것과 동일한 원본 PDF(static.kakaoinsure.com CDN 직배포)이므로 다른 5개사와 신뢰도 차이 없음. |
| 수집일 | 2026-07-29 |
| 로컬 저장 경로 | data/raw_pdfs/kakaopay_overseas_20241101.pdf |
| 페이지 수 | 198 |
| 검수 상태 | raw |
| 비고 | ne.md 최초 버전은 "카카오페이는 약관 원문 미공개로 제외"라고 명시했으나, 사용자 확인 결과 공시실에 실제 공개되어 있어 6번째 보험사로 편입함(ne.md 갱신 필요 — 관리자 확인 요망). |

## 데이터 사용조건 확인

- 금융소비자보호법에 따라 보험사 공식 홈페이지에 일반 공개된 약관 PDF임 (로그인·회원가입 불필요, 별도 이용약관/유료화 없음).
- 본 프로젝트는 비영리 공모전(2026 금융 AI Challenge) MVP 목적으로 원문을 인용·구조화하며, 원문 자체를 재배포하지 않고 조항 단위로 근거 표시(형광펜) 용도로만 사용한다.
- 상품 커버리지/금액/조건은 시행일(2024-04-01) 기준이며, 실사용 시 최신 약관 재확인이 필요하다는 점을 서비스 화면에 고지한다.

## 확보 현황 요약

6개사(삼성화재·현대해상·메리츠화재·KB손보·DB손보·카카오페이손해보험) 모두 원문 PDF 확보 및
KB 적재(표준담보 3종: 상해사망·후유장해/해외발생 상해의료비/중대사고 구조송환비용) 완료.

**재검수 필요 항목(관문2 진행 시 우선순위):**
1. 메리츠화재 — 공식 도메인 원문으로 교체 확인
2. KB손보 — 2026-07-28 개정판(고급형/표준형/실속형) 최신 약관으로 교체 확인
3. 전체 — 질병의료비/휴대품/배상책임 등 MVP 외 담보로 확대 시 각사 원문 재수집 필요
