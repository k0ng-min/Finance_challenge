# ClauseTerm(금액·한도 수치화) + CoverageDocMap(필요서류) 채우기 공통 지침

## 배경
6개 보험사 PDF를 이미 100% 읽어서 `Clause`(조항 원문)는 담보 107개/조항 400여건이 DB
(`backend/data/app.db`)에 들어가 있다. 그런데 두 가지가 비어 있다:

1. **`ClauseTerm`(수치 조건: 지급한도/자기부담금/지연기준시간/보상일수 등)이 0건.**
   조항 원문 안에 이미 있는 숫자(예: "US $1,000.00 한도", "20만원 한도", "12시간 이상",
   "180일까지", "70,000원(20일 한도)")를 구조화해서 뽑아내는 작업이 아직 없었다.
2. **`CoverageDocMap`(필요서류)이 원래 4개 담보(상해사망/해외의료비/구조송환/휴대품)에만
   있다.** 새로 추가한 배상책임/항공기납치/여행중단/여권분실/식중독/자택도난 등 100개
   넘는 담보는 필요서류가 하나도 연결 안 돼 있어서, 사고접수 결과 화면에 "필요서류"
   안내가 아예 안 뜬다.

이 작업은 **PDF를 다시 읽을 필요가 없다** — 이미 DB에 저장된 `Clause.text`(원문) 안에서
숫자와 서류 언급을 찾아 구조화하면 된다.

## 담당 범위
보험사 하나(insurer.code = SAMSUNG/HYUNDAI/MERITZ/KB/DB/KAKAOPAY 중 하나)를 맡아서, 그
보험사의 policy_version에 속한 **모든 Clause**를 훑는다.

```python
pv = (db.query(PolicyVersion).join(Product, Product.product_id==PolicyVersion.product_id)
      .filter(Product.insurer_id == insurer.insurer_id).first())
clauses = db.query(Clause).filter(Clause.policy_version_id == pv.policy_version_id).all()
```

## 1) ClauseTerm 추출

`backend/app/models/kb.py`의 `ClauseTerm` 모델 참고. 필드:
- `term_type`: 아래 고정 어휘 중에서만 골라라(다른 보험사와 비교/집계 가능하게 하기 위함).
  절대 자유롭게 새로 짓지 마라:
  - `지급한도` (예: "US$1,000 한도", "5천만원 이내", "20만원 한도")
  - `자기부담금` (예: "10만원 공제 후 10%", "1사고당 3만원")
  - `지연기준시간` (예: "4시간 이상", "12시간 이상" — 항공기/수하물 지연 기준)
  - `보상일수한도` (예: "180일까지", "20일 한도" — 보상 기간 자체의 상한)
  - `면책일수` (예: "2일 이상 입원" — 이 기간을 채워야 지급되는 최소 조건, 보상일수한도와 반대 방향)
  - `1일당지급액` (예: "1일당 70,000원" — 정액 입원일당/지연일당류)
- `value_num`: 숫자만(단위 제외). 통화/퍼센트/일수 등 숫자로 뽑을 수 없는 복합 조건(예:
  "10만원 공제 후 10%"처럼 두 요소가 섞인 경우)은 value_num을 null로 두고 raw_text와
  condition_text에 전체를 그대로 담아라 — 억지로 숫자 하나로 쪼개지 마라.
- `unit`: "원"/"USD"/"%"/"일"/"시간" 등.
- `basis`: "실손"/"정액" 중 하나(해당되면). 애매하면 null.
- `condition_text`: 그 숫자가 적용되는 조건을 사람이 읽을 수 있게(원문에서 그대로 발췌해도
  됨, 짧은 요약이어도 됨 — 단 지어내지 않는다).
- `raw_text`: **반드시 clause.text의 부분 문자열(원문 그대로 복사)**. 이게 이 프로젝트
  전체의 절대 원칙이다 — `app.services.kb_seed_common.raw_text_is_grounded(clause_text,
  raw_text)`로 db.add 전에 검증해라(True가 아니면 절대 추가하지 마라).
- `clause_id`: 그 숫자가 나온 원래 Clause.

**모든 조항에 숫자가 있는 건 아니다.** 계약행정 조항, 순수 지급사유 서술(숫자 없음)은
건너뛰어도 된다. 숫자가 있는데 못 뽑겠으면(표 형식이 깨져서 등) 스크립트 docstring에
"건너뜀 - 이유"로 정직하게 남겨라.

## 2) CoverageDocMap(필요서류) 채우기

`backend/app/models/kb.py`의 `RequiredDocStd`/`CoverageDocMap` 참고.
`app.services.kb_seed_common.get_or_create_doc_std(db, doc_code, doc_name, acquire_location, note)` 사용.

### 이미 있는 RequiredDocStd 코드 (의료 관련 — 재사용)
```
CLAIM_FORM            보험금 청구서(회사 양식)
MEDICAL_EXPENSE_CERT  진료비계산서·영수증
MEDICAL_DETAIL_CERT   진료비세부내역서
TREATMENT_CERT        입원치료확인서/통원확인서
PRESCRIPTION          의사처방전(처방조제비 포함)
DISABILITY_CERT       장해진단서
DEATH_CERT            사망진단서
ID_CARD               신분증(청구인)
```

### 새로 만들 코드 (비의료 담보용 — 이 이름만 써라, 충돌 방지)
```
POLICE_REPORT           현지 경찰 신고확인서(도난·분실·배상책임 사고)
FLIGHT_DELAY_CERT       항공기 지연·결항 확인서(항공사 발급)
BAGGAGE_IRREGULARITY    수하물 지연·분실 확인서(항공사 발급, PIR)
PASSPORT_REISSUE_RECEIPT 여권(여행증명서) 재발급 영수증·확인서
LIABILITY_EVIDENCE      배상책임 관련 서류(합의서·손해배상 청구서·상대방 피해 확인서류)
```
(acquire_location은 "현지only"/"귀국가능"/"공통" 중 하나 — get_or_create_coverage_std와
같은 패턴.)

### 매핑 규칙 (건너뛰지 말고 전부 다뤄라)
각 새 담보(Coverage)에 대해:
1. **필수 서류**: `CLAIM_FORM`(청구서)과 `ID_CARD`(신분증)는 거의 모든 담보에 공통으로
   필요하다 — 이 둘은 기본으로 넣어도 된다(약관에 "청구는 보통약관 제7조를 준용한다"처럼
   써있는 경우가 많은데, 그게 바로 이 공통 서류를 가리키는 것이다).
2. **담보 성격별 추가 서류**:
   - 의료비 관련(상해/질병 치료): MEDICAL_EXPENSE_CERT, MEDICAL_DETAIL_CERT, TREATMENT_CERT
   - 사망: DEATH_CERT / 후유장해: DISABILITY_CERT
   - 휴대품 도난·자택도난·배상책임: POLICE_REPORT
   - 항공기 지연·결항: FLIGHT_DELAY_CERT
   - 수하물 지연·분실: BAGGAGE_IRREGULARITY
   - 여권분실: PASSPORT_REISSUE_RECEIPT (+ POLICE_REPORT, 분실 신고했다면)
   - 배상책임: LIABILITY_EVIDENCE
   - 구체적으로 조항 원문(특히 clause_type='서류'로 이미 저장된 조항이 있으면 그것부터
     확인)에 서류명이 실제로 언급돼 있으면 그걸 우선 근거로 써라(clause 연결도 가능하면
     CoverageDocMap.clause_id에 넣어라 — 없으면 null로 둬도 된다).
3. `is_mandatory`: 원문에 "제출하여야 합니다"처럼 필수로 명시된 건 True, "필요시"/"경우에
   따라" 뉘앙스면 False.

## 완전성 원칙
새로 추가된 담보 전부(원래 4개 제외) 하나도 빠짐없이 최소 CLAIM_FORM+ID_CARD는 연결해라
— "필요서류 하나도 없음"으로 남겨두지 마라(사용자에게 서류 안내가 아예 안 뜨는 것보다
기본 서류라도 안내하는 게 낫다).

## 산출물
`backend/app/seed_<insurer>_terms_docs.py` (insurer는 samsung/hyundai/meritz/kb/db/
kakaopay). idempotent한 run() 함수.

**이 스크립트를 실행하지 마라.** 다른 5개 보험사도 동시에 같은 작업 중이라, 전부 같은
SQLite 파일(backend/data/app.db)에 동시에 쓰면 충돌(database is locked)이 날 수 있다.
스크립트 작성만 하고 끝내라 — 실행은 전부 모이면 순서대로 한다. 읽기 전용 DB 조회
(기존 Clause 원문 확인, 기존 RequiredDocStd 목록 확인 등)는 자유롭게 해도 된다.

## 보고
최종 보고(400단어 이내): 뽑아낸 ClauseTerm 개수와 term_type별 분포, 새로 채운
CoverageDocMap 담보 개수, 새로 만든 RequiredDocStd 코드, 건너뛴 부분과 이유.
