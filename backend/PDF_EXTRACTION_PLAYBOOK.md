# PDF 조항 추출 공통 지침 (임시 작업 문서 — 6개사 전체 딥다이브용)

여행자보험 청구 도우미 서비스. 6개 보험사 약관을 DB(backend/data/app.db, SQLite)에 시딩하고
incident_type(사고유형, backend/app/seed_incident_types.py의 L1 8개+L2)으로 조항을 매핑한다.
삼성화재는 이미 252쪽 전체를 다 읽고 분류 완료(21개 담보, 68개 조항). 이제 같은 방식으로
나머지 보험사도 전체를 다 읽는다.

## 먼저 읽을 파일
- `backend/app/seed_samsung_inj_deep.py`, `backend/app/seed_samsung_full_chunkA.py`,
  `backend/app/seed_samsung_full_chunkD.py` — 실제 작업 예시(Clause/CoverageStd/Coverage/
  ClauseIncidentMap 생성 패턴, idempotent 처리 방식).
- `backend/app/models/kb.py` — 스키마.
- `backend/app/services/kb_seed_common.py` — get_or_create_coverage_std.
- `backend/app/seed_incident_types.py` — incident_type L1/L2 TAXONOMY 전체.
- `backend/app/services/incident_classify_gemini.py`의 `create_reviewable_type` — 8개 L1
  어디에도 정말 안 맞을 때 needs_review=True로 새 L2를 만드는 방법.

## 기존에 이미 있는 CoverageStd 코드 (반드시 재사용 — 새로 만들지 마라)
같은 종류의 담보를 다른 보험사에서 발견하면 **이 코드를 그대로 재사용**해라(예: 어느
보험사든 "질병사망" 특약을 찾으면 ILL_DEATH를 쓴다, 새 코드 만들지 마라):

```
DEATH_INJURY      상해사망·후유장해
OVS_INJ_MED       해외발생 상해의료비 (상해 해외/국내 실손의료비)
RESCUE            중대사고 구조송환비용
PERSONAL_EFFECTS  휴대품 손해(분실제외)
ILL_DEATH         질병사망·고도후유장해
LIABILITY         배상책임
HIJACK            항공기납치
OVS_ILL_MED       해외발생 질병의료비 (질병 해외/국내 실손의료비)
FLIGHT_DELAY      항공기 지연·결항
PET_CARE          반려동물 돌봄서비스
FOOD_POISONING    식중독보상금
INFECTIOUS_DISEASE 특정감염병보상금
TRIP_INTERRUPTION 여행중단 추가비용
PASSPORT_LOSS     여권분실 재발급비용
HOME_THEFT        자택 도난손해(가재)
GOOD_SAMARITAN    의사상자 상해위험
WAR_RISK          전쟁위험
NON_COVERED_MED   비급여 실손의료비
```

작업 시작 전에 `db.query(CoverageStd).all()`로 최신 목록을 다시 한번 조회해서 확인해라
(다른 보험사 작업이 병행되면서 새 코드가 늘어났을 수 있다). 정말 위 목록에 없는 새로운
종류의 담보(예: "상해입원일당" 정액보장, "스포츠활동상해보장제외"처럼 지급구조 자체가
다른 것)를 발견했을 때만 새 CoverageStd를 만들어라 — std_code는 영문 대문자 스네이크
케이스로 짧고 명확하게(예: `INJ_HOSPITAL_ALLOWANCE`), std_name은 실제 특약명 요약,
category는 상해/질병/휴대품/배상책임/운송/여행변경/구조/특수 중 적절한 것, is_base=False.

## grounding + 완전성 원칙 (절대 원칙, 어기면 전체 작업이 무효)
1. **임의로 지어내지 마라.** 모든 Clause.text는 pdfplumber extract_text()로 뽑은 PDF 원문
   그대로(의역/재구성/다른 보험사 문구 재사용 절대 금지). 표 레이아웃 때문에 열 라벨이
   문장 중간에 끼어드는 경우만 그 라벨을 제거하고 나머지는 원문 그대로 이어붙여라.
2. **실제 있는 내용은 빠짐없이 분류해서 넣어라.** 담당 페이지 범위에 있는 특약은 전부
   pdfplumber로 실제로 펼쳐서 확인해라 — 이름만 보고 "아마 무관하겠지"라고 짐작하지
   마라. 사고유형과 진짜 무관한(순수 계약행정/세제) 특약이면 넣지 않아도 되지만, 실제로
   읽어서 확인한 뒤에 그렇게 판단해야 하고 스크립트 docstring에 "확인함, 무관"이라고
   정직하게 남겨라.
3. 지급사유(보장정의)뿐 아니라 면책·제한·조건 조항도 실제 있는 대로 전부 Clause로
   넣고 clause_type을 정확히 붙여라(보장정의/면책/제한/조건/서류/공통).
4. 추출이 지저분해서(표/스캔) 정확히 못 뽑는 부분은 절대 추측하지 말고 스크립트
   docstring에 "건너뜀 — 이유"로 정직하게 남겨라.
5. 청구서류(clause_type='서류') 조항은 ClauseIncidentMap에 매핑하지 않는다(이미
   CoverageDocMap 경로로 따로 소비됨).
6. 8개 L1(INJ/ILL/PROP/LIA/TRV/CHG/EMG/SPC) 어디에도 정말 안 맞으면 억지로 끼워맞추지
   말고 needs_review=True인 새 L2를 만들어서 매핑해라(조용히 빠뜨리지 않는다).

## 산출물 규칙
- 파일명: `backend/app/seed_<insurer>_full_chunk<N>.py` (insurer는 hyundai/meritz/kb/db/
  kakaopay, N은 담당 번호).
- 구조는 seed_samsung_full_chunkA.py와 동일: 모듈 docstring(뭘 발견했고 어디에 매핑했는지
  요약, 페이지 번호 포함) + idempotent한 run() 함수(SessionLocal 열고, 이미 있으면
  건너뛰는 exact-text-match 체크, db.commit(), db.close()).
- **이 스크립트를 실행하지 마라.** 다른 보험사/청크 작업과 동시에 DB에 쓰면 SQLite 충돌이
  날 수 있다. 스크립트 작성만 하고 끝내라. 읽기 전용 DB 조회(기존 CoverageStd 확인 등)는
  자유롭게 해도 된다.
- 다른 파일은 건드리지 마라. git 커밋/푸시 금지.
- Windows 콘솔 인코딩 문제를 피하려면 print() 문에 em-dash(—) 같은 특수문자 대신
  일반 괄호나 하이픈(-)을 써라.

## 보고 형식
최종 보고(400단어 이내): 담당 페이지 범위에서 실제로 발견한 특약들 각각 핵심 내용
스니펫+페이지+매핑한 incident_type, 만든 행 개수 요약, 건너뛴 부분과 이유, 무관하다고
확인만 하고 넘어간 특약 목록.
