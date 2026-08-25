# 2026년 약관 원본 교체와 KB 전면 재구축 설계

## 왜 다시 만드는가

사용자가 보험사 공식 발행 경로에서 직접 받은 6개사 약관 PDF 8개를 새로 확보했다. 기존
KB(`backend/data/app.db`)는 2024~2025년에 수집한 다른 판본에서 뽑은 것이라, 새 원본과
같은 문서가 아니다.

측정한 근거:

- `dataset_manifest.json`에 기록된 원본 6개의 SHA-256과 새 파일 8개의 해시가 **하나도
  일치하지 않는다.**
- 쪽수가 전부 다르다(삼성 252→307, 현대 140→162, 메리츠 220→244, KB 169→326,
  DB 126→223, 카카오 198→324/324/331).
- DB에 적재된 조항 363개 중 새 PDF에 **원문 그대로 남아 있는 것은 130개(36%)뿐이다.**

| 보험사 | DB 조항 | 원문 일치 | 부분 일치 | 없음 |
|---|---:|---:|---:|---:|
| SAMSUNG | 68 | 30 | 34 | 3 |
| HYUNDAI | 104 | 55 | 28 | 21 |
| MERITZ | 52 | 5 | 22 | 25 |
| KB | 39 | 13 | 21 | 5 |
| DB | 66 | 14 | 23 | 29 |
| KAKAOPAY | 34 | 13 | 19 | 2 |

이 프로젝트는 `clause_term.raw_text`, `doc_requirement.anchor_phrase`,
`overlap_rule.anchor_phrase`, `clause_standard_map.anchor_phrase_insurer`,
`clause.highlight_spans`가 **전부 `clause.text`의 부분 문자열이어야 한다**는 규칙 위에
서 있다. 원문이 바뀌면 이 파생물이 통째로 무효가 되므로 부분 패치가 성립하지 않는다.
조항을 새 원본에서 다시 뽑는 것 외에 선택지가 없다.

기존 원본 PDF는 `.gitignore`로 커밋되지 않았고 디스크에도 남아 있지 않다. 즉 새 파일이
유일한 원본이며, 되돌아갈 구판본은 없다.

## 새 원본 목록

8개 파일 모두 텍스트 PDF다(스캔 이미지 아님, pdfplumber로 전 페이지 추출 확인). 삼성화재
표지 9쪽만 이미지라 텍스트가 비어 있다.

| 파일 | 쪽 | 표지에 인쇄된 식별자 | SHA-256 |
|---|---:|---|---|
| 삼성화재.pdf | 307 | 없음(표지 이미지), 본문 머리글 "해외여행보험 n / 296" | `95fc1ac0…56406b7` |
| 현대.pdf | 162 | 다이렉트 해외여행보험 (약관분류코드 8403-0000-20260606) | `19fcd296…62ec3c878` |
| 메리츠.pdf | 244 | 다이렉트 해외여행보험 / 메리츠일반-특종/상해/여행B-10-2607A | `f58406b6…1b61dbdd` |
| kb.pdf | 326 | 일반26-15505-1 · KB해외여행보험(다이렉트) · 2026.06 | `49a5ccec…c064e573` |
| db.pdf | 223 | 보험약관 (프로미 해외여행보험Ⅰ) | `151c57ec…cbf3e008` |
| 카카오 1.pdf | 324 | 함께하는 해외여행보험 · 제2026-0199호 (2026.05.04) | `f558fafb…de997d16b` |
| 카카오 2.pdf | 324 | 함께하는 해외여행보험II · 제2026-0199호 (2026.05.04) | `a4b41ae4…38866d19a` |
| 카카오 3.pdf | 331 | 해외여행보험 · 제2026-0199호 (2026.05.04) | `3ed801af…67b4009c` |

카카오 1과 2는 본문이 사실상 동일하다(공백 제거 후 길이 158,692 대 158,682, 앞 6만자
일치율 1.0). 상품명과 실손 특약 구성 표기만 다르다.

## 결정 사항

**1. 카카오페이는 3파일을 한 상품으로 통합한다.** `product`·`policy_version` 각 1행.
`page_ref`에 어느 파일 몇 쪽인지 접두사로 남긴다(`K1 p.198`, `K3 p.201`). 세 파일을 모두
전 페이지 읽되, 본문이 같은 조항은 중복 행으로 넣지 않고 시드 docstring에 "카카오1·2
동일 확인"으로 기록한다.

**2. 8개 PDF를 전 페이지 읽는다.** 이름만 보고 건너뛰지 않는다. 계약행정·세제 특약도
읽고, 사고유형과 무관하다고 판단한 것은 시드 docstring에 "확인함, 무관"으로 남긴다
(기존 `PDF_EXTRACTION_PLAYBOOK.md` 원칙 유지).

**3. 기존 KB와 개발용 사용자 데이터를 전부 삭제한다.** 계정 730행까지 지운다 — 개발
과정에서 쌓인 테스트 계정이라 남길 이유가 없다. 지우는 것: `policy_version`·`coverage`·
`clause` 및 파생 6종, `app_user`·`user_policy`·`user_coverage`·`trip`·`incident`·
`evidence`·`analysis_run`·`analysis_finding`·`finding_evidence_link`·
`validation_result`·`user_question_log`·`eval_log`.

계정을 지우면 기존 로그인 세션·토큰이 전부 무효가 된다. 배포 환경에서 다시 가입해야
한다는 뜻이라 `reset_kb.py`는 실행 전 대상 행 수를 출력하고 확인을 받는다.

유지하는 것(약관과 무관한 외부 자료·사전): `insurer`, `coverage_std`, `incident_type`,
`required_doc_std`, `standard_clause`, `insurer_premium`, `travel_alert`,
`nonpayment_rate`, `flight_delay_stat`, `country_language`, `onsite_phrase_i18n`,
`question_bank`, `simulation_scenario`, `validation_rule`, `doc_requirement`은 조항을
참조하므로 삭제 후 재생성.

**4. 출처는 "보험사 공식 발행 파일"로만 기록한다.** 방화벽 안쪽 경로에서 사용자가 직접
받았고 공개 URL이 없다. URL을 추적하지 않는다.

- `source_type`: `OFFICIAL_ISSUED_FILE`
- `source_url`: `null`
- `downloaded_at`: `2026-08-18`
- `sha256`: 위 표의 값

**5. 랭킹 게이트에 상태 하나를 추가한다.** 공개 URL이 없어 현재 규칙으로는 6개사 전부
추천 순위에서 빠진다. `VERIFIED_ISSUED_FILE`을 새로 만들어 보험사 공식 발행 파일을 순위
대상으로 허용한다. 고칠 곳은 두 군데뿐이다.

- `backend/scripts/validate_kb.py`의 `VERIFICATION_STATUSES`, `RANKING_ELIGIBLE_STATUSES`
- `backend/app/services/kb_provenance.py`의 `RANKING_ELIGIBLE_STATUSES`

이 변경으로 비교 가능한 보험사가 3개에서 6개로 늘어난다.

**6. 확인되지 않은 시행일은 비워 둔다.** 삼성화재와 DB는 본문 어디에도 약관 버전 코드나
시행일이 인쇄돼 있지 않다(삼성 표지는 이미지, DB 표지는 상품명만). 추정하지 않고
`effective_date: null` + `known_gap`에 사실을 적는다. 메리츠의 `2607A`와 KB의 `2026.06`도
시행일로 단정할 근거가 없어 같게 처리한다.

| insurer | version_label | effective_date |
|---|---|---|
| SAMSUNG | `2026수집본` | null — 표지 이미지, 버전 코드 미인쇄 |
| HYUNDAI | `8403-0000-20260606` | 2026-06-06 |
| MERITZ | `메리츠일반-특종/상해/여행B-10-2607A` | null — 코드 뒷자리를 시행일로 단정 못 함 |
| KB | `일반26-15505-1` | null — 표지 표기는 `2026.06`뿐 |
| DB | `프로미Ⅰ_2026수집본` | null — 버전 코드 미인쇄 |
| KAKAOPAY | `제2026-0199호` | 2026-05-04 |

## 산출물 구조

### 원본 보관

`6개 보험사 약관/`을 없애고 `backend/data/raw_pdfs/`로 옮긴다. 이 경로는 이미
`.gitignore` 대상이라 재배포 금지 정책(`docs/compliance/source_register.md`)을 그대로
지킨다. 저장소 루트에 두면 커밋되어 정책을 위반한다.

```
backend/data/raw_pdfs/samsung_overseas_2026.pdf
                     /hyundai_overseas_8403-0000-20260606.pdf
                     /meritz_overseas_2607A.pdf
                     /kb_overseas_26-15505-1.pdf
                     /db_overseas_promi1_2026.pdf
                     /kakaopay_overseas_2026-0199_together1.pdf
                     /kakaopay_overseas_2026-0199_together2.pdf
                     /kakaopay_overseas_2026-0199_standard.pdf
backend/data/processed/<같은 이름>_full_text.txt   # 페이지 경계 마커 포함, gitignore 대상
```

### 시드 스크립트

기존 `backend/app/seed_<insurer>*.py` 40여 개(보통약관·chunk·inj_deep·terms_docs)를
삭제하고 새로 쓴다. 파일 구조와 idempotent 패턴은 기존 `seed_samsung_full_chunkA.py`와
동일하게 유지한다 — 검증된 형식이고 감사 스크립트가 그 형태를 전제한다.

```
backend/app/reset_kb.py                       # 3번 삭제 범위를 수행, 단독 실행
backend/app/seed_<insurer>_2026_<chunk>.py    # 보험사별 청크
backend/app/seed_2026_incident_map.py         # 파생: 조항↔사고유형
backend/app/seed_2026_clause_terms.py         # 파생: 정량 조건
backend/app/seed_2026_coverage_docs.py        # 파생: 담보↔서류, doc_requirement
backend/app/seed_2026_overlap_rules.py        # 파생: 중복 판정
backend/app/seed_2026_clause_standard_map.py  # 파생: 표준약관 대조
```

`highlight_spans`와 `plain_text`는 Gemini 런타임 캐시이므로 NULL로 두고 화면에서 다시
채워진다.

### CoverageStd

기존 28개 코드를 재사용한다. 새 약관에서 실제로 확인된, 지급 구조가 다른 담보만 추가한다.
현재까지 헤딩 스캔으로 확인한 후보:

- 상해·질병 입원일당(정액, 일수 구간별로 특약이 나뉜다)
- 골절진단비 / 치아파절 제외형
- 기후성질환(온열·한랭)진단비 — KB에만 있다
- 지수형 항공기 지연보장(실손이 아니라 지수 기준 정액)
- 중증·비중증 비급여 해외여행 실손의료비 — 2024년 실손 개편 반영, 구판본에 없던 구성
- 스포츠활동상해 보장제외 / 사망·후유장해 보장제외(담보를 빼는 특약)

정독 중 추가로 나오면 같은 기준(영문 대문자 스네이크, `is_base=False`)으로 만든다.

## 작업 순서

**Phase 0 — 원본 정리.** 파일 이동·이름 정규화, SHA-256 기록, 전체 텍스트 캐시 생성,
`6개 보험사 약관/` 삭제.

**Phase 1 — 판 갈기.** `reset_kb.py` 작성·실행, 랭킹 게이트에 `VERIFIED_ISSUED_FILE`
추가, 보험사별 특별약관 헤딩·페이지 범위를 실측해 청크 경계 확정(DB손보는 목차가 3~5쪽에
뭉쳐 있어 본문 스캔으로 잡아야 한다).

**Phase 2 — 정독과 조항 추출.** 보험사별 순차 진행: 삼성 → 현대 → 메리츠 → KB → DB →
카카오. 청크당 담당 페이지 범위 전체를 pdfplumber로 펼쳐 읽고 `Coverage`·`Clause`를
만든다. 예상 청크 수는 24개 내외.

| 보험사 | 쪽 | 청크 경계(초안) |
|---|---:|---|
| 삼성화재 | 307 | 1-55 / 56-76 / 77-174 / 175-203 / 204-230 / 231-307 |
| 현대 | 162 | 1-39 / 40-97 / 98-118 / 119-162 |
| 메리츠 | 244 | 1-42 / 43-86 / 87-176 / 177-244 |
| KB | 326 | 1-88 / 89-145 / 146-169 / 170-286 / 287-326 |
| DB | 223 | Phase 1에서 확정 |
| 카카오3 | 331 | 1-49 / 50-195 / 196-260 / 261-331 |
| 카카오1·2 | 648 | 전 페이지 읽고 카카오3과의 차이만 추출 |

**Phase 3 — 파생 재생성.** 사고유형 매핑, 정량 조건, 서류 매핑, 중복 규칙, 표준약관 대조.

**Phase 4 — 문서 갱신.** `dataset_manifest.json`, `docs/compliance/source_register.md`,
`README.md`의 데이터 현황, `PDF_EXTRACTION_PLAYBOOK.md`의 파일 경로.

**Phase 5 — 검증.**

## 검증

**기존 감사** — `cd backend && python -m scripts.validate_kb`. 추적 무결성, 매니페스트↔DB
일치, 앵커 문구 grounding, 보험사별 집계를 검사한다. 통과 후 `--freeze`로 지문을 다시
동결한다.

**신규 자동 대조** — `backend/scripts/verify_clause_grounding.py`를 만든다. 모든
`clause.text`를 공백 정규화한 뒤 해당 PDF 추출 텍스트의 부분 문자열인지 검사하고, 어긋난
조항을 파일·쪽과 함께 보고한다. 이번 드리프트를 사람이 눈치채기까지 오래 걸렸다는 것이
이 스크립트가 필요한 이유다. 통과 기준은 **일치율 100%** — 한 건이라도 어긋나면 그 조항은
근거가 될 수 없다.

**회귀** — `cd backend && python -m pytest`. 조항 개수·특정 문구를 하드코딩한 테스트가
있으면 새 원본 기준으로 고친다(테스트가 검증하려던 성질은 유지한다).

## 범위에서 빼는 것

- 프론트엔드 화면 변경. 조항 인용·형광펜은 DB만 갈리면 그대로 동작한다.
- 보험료·여행경보·부지급률·지연통계 등 외부 자료 재수집.
- 구판본 보존이나 버전 이력 기능. 되돌아갈 구판본 파일이 없어서 성립하지 않는다.
- 병렬 서브에이전트 분담. 요청이 있으면 Phase 2를 병렬로 돌린다.
