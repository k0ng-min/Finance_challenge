# 여행자보험 전 생애주기 AI — ERD 최종본 (v1.0)

> **범위:** 6개 손보사 통합 (삼성화재·현대해상·메리츠화재·KB손보·DB손보·카카오페이손해보험). 2026-07-29 카카오페이손해보험 공시실(kakaopayinscorp.co.kr/disclosure/goods)에서 실제 약관 PDF 확보 확인, 6번째로 편입.
> **표준 담보 사전은 삼성화재 해외여행보험 약관 실물 목차를 기준(reference)으로 확정.** 나머지 4개사는 이 표준에 매핑.
> **기능 전체 반영:** 가입 전 추천 / 사고 후 서류 / 누락·모순 검증 / 형광펜 / 능동 질문 / 평가.

## 영역

- **A. 약관 지식베이스(KB)** — 5개사 상품·담보·조항·서류
- **B. 사용자 도메인** — 여행·가입보험·사고·증빙
- **C. 능동 질문** — 단계별 추가 질문 엔진
- **D. 분석·형광펜·평가**

---

## A. 약관 지식베이스

### insurer
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| insurer_id | INTEGER | PK | |
| name | TEXT | | 보험사명 |
| code | TEXT | UQ | 표준 코드 (SAMSUNG/HYUNDAI/MERITZ/KB/DB) |
| is_underwriter | BOOLEAN | | 약관 발행 주체 여부 |
| official_url | TEXT | | 약관 공개 URL |

### product
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| product_id | INTEGER | PK | |
| insurer_id | INTEGER | FK→insurer | |
| name | TEXT | | 상품명 |
| product_code | TEXT | | |
| channel | TEXT | | 판매채널: 다이렉트/대면/단체 |
| sale_start / sale_end | DATE | | 판매 기간 |
| collected_at | DATE | | 수집일 |
| review_status | TEXT | | raw/verified |

### policy_version
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| policy_version_id | INTEGER | PK | |
| product_id | INTEGER | FK→product | |
| version_label | TEXT | | 약관 버전 (예: 50002_0) |
| effective_date | DATE | | 시행일 |
| approval_no | TEXT | | 준법감시인 심의필/신고번호 |
| source_url | TEXT | | 원문 PDF 출처 |
| file_hash | TEXT | | 무결성 해시 |

### coverage_std (표준 담보 사전) ★삼성 약관 실물 기준
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| coverage_std_id | INTEGER | PK | |
| std_code | TEXT | UQ | 표준 코드 |
| std_name | TEXT | | 표준 담보명 |
| category | TEXT | | 대분류 |
| is_base | BOOLEAN | | 보통약관(기본)/특별약관 구분 |

### coverage (상품별 담보)
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| coverage_id | INTEGER | PK | |
| policy_version_id | INTEGER | FK→policy_version | |
| coverage_std_id | INTEGER | FK→coverage_std | 표준 매핑 |
| raw_name | TEXT | | 약관 원문 담보/특약명 |
| definition | TEXT | | 보장 정의 |
| limit_amount | TEXT | | 보장 한도 |
| deductible | TEXT | | 자기부담금 |
| waiting_condition | TEXT | | 지급조건/대기시간 (예: 지연 2시간 이상) |

### clause (약관 조항) ★형광펜 원천
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| clause_id | INTEGER | PK | |
| policy_version_id | INTEGER | FK→policy_version | |
| coverage_id | INTEGER | FK→coverage (nullable) | 공통조항은 null |
| clause_type | TEXT | | 보장정의/면책/제한/조건/서류/공통 |
| article_no | TEXT | | 조항 번호 |
| text | TEXT | | 조항 원문 |
| page_ref | TEXT | | PDF 위치 |
| embedding_id | TEXT | | 벡터DB 참조 키 (RAG용) |
| default_color | TEXT | | 형광펜 기본색 |

### required_doc_std (표준 청구서류)
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| required_doc_std_id | INTEGER | PK | |
| doc_code | TEXT | UQ | |
| doc_name | TEXT | | 서류명 |
| acquire_location | TEXT | | 현지only/귀국가능/공통 |
| note | TEXT | | 유의사항 (예: 질병분류코드 기재) |

### coverage_doc_map (담보↔서류 N:M)
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| coverage_doc_id | INTEGER | PK | |
| coverage_id | INTEGER | FK→coverage | |
| required_doc_std_id | INTEGER | FK→required_doc_std | |
| is_mandatory | BOOLEAN | | |
| clause_id | INTEGER | FK→clause (nullable) | 근거 조항 |

---

## B. 사용자 도메인

### app_user
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| user_id | INTEGER | PK | |
| nickname | TEXT | | 개인정보 최소수집 |
| created_at | DATETIME | | |

### trip
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| trip_id | INTEGER | PK | |
| user_id | INTEGER | FK→app_user | |
| destination | TEXT | | 목적지 국가 |
| start_date / end_date | DATE | | 여행 기간 |
| purpose | TEXT | | 여행 목적 |
| activities | TEXT(JSON) | | 예정 활동 |
| companion_type | TEXT | | 동반자 유형 |
| rental_car | BOOLEAN | | 렌터카 |
| risk_profile | TEXT(JSON) | | 생성된 위험 프로필 |
| coverage_priority | TEXT(JSON) | | 사용자 보장 우선순위 |

### user_policy (내 보험 보관함)
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| user_policy_id | INTEGER | PK | |
| user_id | INTEGER | FK→app_user | |
| product_id | INTEGER | FK→product (nullable) | KB 매칭 |
| policy_version_id | INTEGER | FK→policy_version (nullable) | 적용 버전 |
| insurer_name_raw / product_name_raw | TEXT | | 증권상 원문명 |
| policy_type | TEXT | | 직접가입/카드부가/단체 |
| period_start / period_end | DATE | | 보험기간 |

### user_coverage (실제 가입 담보) ★미가입 담보 추천 차단
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| user_coverage_id | INTEGER | PK | |
| user_policy_id | INTEGER | FK→user_policy | |
| coverage_id | INTEGER | FK→coverage (nullable) | KB 매칭 |
| coverage_std_id | INTEGER | FK→coverage_std (nullable) | 표준 매핑 (KB 미매칭 시) |
| raw_name | TEXT | | 증권상 담보명 |
| subscribed_amount | TEXT | | 가입금액 |

### incident (사고정보)
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| incident_id | INTEGER | PK | |
| user_id | INTEGER | FK→app_user | |
| trip_id | INTEGER | FK→trip (nullable) | |
| country | TEXT | | 사고 국가 |
| occurred_at | DATETIME | | 사고 일시 |
| cause | TEXT | | 사고 원인 |
| injury_part | TEXT | | 상해 부위 |
| diagnosis | TEXT | | 증상/진단명 |
| hospitalized / surgery | BOOLEAN | | 입원/수술 |
| local_treatment | BOOLEAN | | 현지 병원 치료 |
| medical_cost | TEXT | | 지출 의료비 |
| returned_home | BOOLEAN | | 귀국 여부 |
| structured | TEXT(JSON) | | LLM 구조화 결과 |

### evidence (증빙 보유상태)
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| evidence_id | INTEGER | PK | |
| incident_id | INTEGER | FK→incident | |
| required_doc_std_id | INTEGER | FK→required_doc_std (nullable) | |
| status | TEXT | | 보유/미보유/발급불가 |
| memo | TEXT | | |

> 업로드 원본은 영구저장 안 함. 보유여부·구조화 정보만.

---

## C. 능동 질문 엔진 (문서 7.4)

### question_bank (질문 템플릿)
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| question_id | INTEGER | PK | |
| context_type | TEXT | | 가입전/사고후/누락검증 |
| question_text | TEXT | | 질문 원문 |
| target_field | TEXT | | 이 질문이 채우는 필드 |
| impact_weight | REAL | | 결과 영향도(우선순위 산정) |

### user_question_log (사용자 응답 로그)
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| qlog_id | INTEGER | PK | |
| analysis_run_id | INTEGER | FK→analysis_run | |
| question_id | INTEGER | FK→question_bank | |
| answer_text | TEXT | | 사용자 응답 |
| asked_at | DATETIME | | |

---

## D. 분석 · 형광펜 · 평가

### analysis_run
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| analysis_run_id | INTEGER | PK | |
| user_id | INTEGER | FK→app_user | |
| run_type | TEXT | | 가입전추천/사고후검토/누락검증 |
| trip_id | INTEGER | FK→trip (nullable) | |
| incident_id | INTEGER | FK→incident (nullable) | |
| created_at | DATETIME | | |
| result_summary | TEXT(JSON) | | |

### analysis_finding (분석 결과)
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| finding_id | INTEGER | PK | |
| analysis_run_id | INTEGER | FK→analysis_run | |
| finding_type | TEXT | | 추천담보/보장공백/필요서류/누락/모순/제한조건 |
| status | TEXT | | 청구검토후보/추가정보필요/서류확보필요/계약확인필요/관련성낮음/확인불가 |
| target_ref | TEXT | | 대상 참조 |
| description | TEXT | | 확정적 지급표현 금지 |
| confidence | TEXT | | 근거강도 |

### finding_evidence_link (결과↔근거조항, 형광펜)
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| link_id | INTEGER | PK | |
| finding_id | INTEGER | FK→analysis_finding | |
| clause_id | INTEGER | FK→clause | 근거 약관 |
| highlight_color | TEXT | | 파랑/초록/노랑/빨강/회색 |

> 모든 finding은 최소 1개 clause 연결 필수. 없으면 status='확인불가'.

### validation_rule (규칙 엔진 정의, 문서 11.2)
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| rule_id | INTEGER | PK | |
| rule_code | TEXT | UQ | 예: PERIOD_MISMATCH |
| rule_name | TEXT | | 예: 보험기간-사고일 불일치 |
| severity | TEXT | | 오류/경고/확인 |
| description | TEXT | | |

### validation_result (규칙 실행 결과)
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| vresult_id | INTEGER | PK | |
| analysis_run_id | INTEGER | FK→analysis_run | |
| rule_id | INTEGER | FK→validation_rule | |
| passed | BOOLEAN | | |
| detail | TEXT | | 위반 상세 |

### eval_log (평가 로그, 문서 13)
| 컬럼 | 타입 | 키 | 설명 |
|---|---|---|---|
| eval_id | INTEGER | PK | |
| analysis_run_id | INTEGER | FK→analysis_run (nullable) | |
| baseline_type | TEXT | | 규칙/일반LLM/단순RAG/필터+RAG/통합 |
| metric_name | TEXT | | Recall/Precision/무근거생성률 등 |
| metric_value | REAL | | |
| dataset_tag | TEXT | | 평가셋 식별자 |
| recorded_at | DATETIME | | |

---

## 표준 담보 사전 시드 (삼성 약관 실물 기준)

| std_code | std_name | category | is_base |
|---|---|---|---|
| DEATH_INJURY | 상해사망·후유장해 | 상해 | 보통약관 |
| DEATH_ILLNESS | 질병사망·고도후유장해 | 질병 | 특약 |
| OVS_INJ_MED | 해외발생 상해의료비 | 의료 | 특약 |
| OVS_ILL_MED | 해외발생 질병의료비 | 의료 | 특약 |
| OVS_ACTUAL_MED | 해외여행 실손의료비(기본형) | 의료 | 특약 |
| OVS_NONPAY_MED | 해외여행 비급여 실손의료비 | 의료 | 특약 |
| LIABILITY | 여행중 배상책임 | 배상 | 특약 |
| BAGGAGE | 여행중 휴대품손해(분실제외) | 휴대품 | 특약 |
| RESCUE | 중대사고 구조송환비용 | 구조 | 특약 |
| HIJACK | 항공기납치 | 특수 | 특약 |
| FLIGHT_DELAY | 항공기 지연·결항(실손형) | 지연 | 특약 |
| BAG_DELAY | 수하물 지연·손실 추가비용 | 지연 | 특약 |
| PET_CARE | 항공기 지연 시 반려견 돌봄 추가비용 | 지연 | 특약 |

> 나머지 4개사(현대·메리츠·KB·DB)는 각 사 원문 담보명을 raw_name에 넣고 위 std_code로 매핑.
> 매핑이 애매한 담보(회사 고유 특약)는 관문2에서 std 사전에 추가 논의.

---

## 관계 요약 (ERDCloud 연결선)

```
insurer 1─N product 1─N policy_version 1─N coverage
policy_version 1─N clause;  coverage 1─N clause(nullable)
coverage_std 1─N coverage;  coverage_std 1─N user_coverage(nullable)
coverage N─M required_doc_std (via coverage_doc_map)

app_user 1─N trip / user_policy / incident / analysis_run
user_policy 1─N user_coverage
incident 1─N evidence;  required_doc_std 1─N evidence(nullable)
product 1─N user_policy(nullable);  coverage 1─N user_coverage(nullable)

analysis_run 1─N analysis_finding / validation_result / user_question_log / eval_log
analysis_finding N─M clause (via finding_evidence_link)
question_bank 1─N user_question_log
validation_rule 1─N validation_result
```