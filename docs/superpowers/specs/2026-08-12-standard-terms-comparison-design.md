# 표준약관 대조(해외여행 실손의료보험) — 설계

작성 2026-08-12.

## 무엇을 하려는가

6개사 약관 조항을 금융감독원의 **법정 표준약관**과 조문 단위로 대조해서, 각 회사가
표준보다 넓게/좁게 쓴 지점과 표준에는 있는데 이 회사 약관엔 아예 없는 지점을 원문과
함께 보여준다. 시중 어떤 보험 비교 서비스도 보험료·가입금액 비교만 하지, 조항 문장을
규제 기준선과 대조하지는 않는다.

## 왜 이 축인가

`README.md`의 "기존보험 연결" 절에 이미 적어둔 한계가 있다: 실손 표준약관이 없어서
"기존 실손이 해외 의료기관을 보상하는가"를 확인불가로 남긴 판정이 3건. 이번 기능으로
그 표준약관을 실제로 확보하면, 확인불가로 남겨뒀던 판정 중 최소 1건(국내/해외 의료기관
보상범위 관련)을 데이터로 좁힐 수 있다 — 새 기능이 기존에 정직하게 적어둔 공백을
실제로 메우는 구조다.

## 데이터 원천

**금융감독원 자체 게시물**(2차 유통사 아님 — 6개사 중 메리츠·DB가 겪은 출처 신뢰도
문제가 여기엔 없다):

```
https://www.fss.or.kr/fss/bbs/B0000115/view.do?nttId=218364&menuNo=200504
첨부: [별표 15] 표준약관(제5-13조제1항관련)(보험업감독업무시행세칙).hwp
게시일 2026-06-15, 조항 개정이력상 최신 개정 2026-05-06
다운로드: https://www.fss.or.kr/fss/cmmn/file/fileDown.do?menuNo=200504&atchFileId=29447dbe2fa84d85881c10281c6b9d38&fileSn=1&bbsId=
```

HWP(구버전 바이너리, OLE2 컴파운드 포맷)라 `pdfplumber`를 못 쓴다. `pyhwp`(`hwp5txt`
CLI)로 텍스트 추출 — 이미 로컬에서 실행해 확인했고, "해외여행 실손의료보험" 섹션이
제1조~제43조까지 조문 구조 그대로(`제N조(제목)` 패턴) 깨끗하게 나온다.

**출처 등록**: 6개사 PDF와 동일한 방식으로 `docs/compliance/source_register.md`와
`backend/data/dataset_manifest.json`에 행을 추가한다 — source_url, downloaded_at,
sha256(원본 hwp 바이트), verification_status. 정부 공개 행정규칙이라 재배포 문제가
없으므로 원문을 저장소에 커밋한다(6개사 PDF는 재배포 금지라 커밋 안 하는 것과 다름).

## 비교 범위(MVP)

43개 조문 중 **제1~9조**만 비교 대상으로 삼는다 — 보장종목/용어정의/보상내용/면책/
가입금액한도/청구·지급절차. 제10조 이후(계약 해지·부활·소멸시효·분쟁조정 등 계약관리
조항)는 사실상 전 보험사가 표준을 그대로 준용하는 보일러플레이트라 대조 실익이 낮아
이번 범위에서 제외한다. 필요해지면 나중에 조문 범위만 넓히면 되는 구조로 만든다
(하드코딩된 제1~9조 리스트가 아니라 `standard_clause` 테이블 행 자체가 범위를 결정).

## 데이터 모델

```python
class StandardClause(Base):
    standard_clause_id: int  # PK
    standard_name: str       # "해외여행 실손의료보험"
    article_no: str          # "제4조"
    title: str                # "보상하지 않는 사항"
    text: str                 # 원문 그대로(개정 각주 포함, 한 글자도 안 바꿈)
    amended_at: str | None    # "2026-05-06"
    source_url: str
    downloaded_at: date
    sha256: str

class ClauseStandardMap(Base):
    id: int  # PK
    standard_clause_id: int  # FK -> StandardClause
    insurer_id: int           # FK -> Insurer (대응 조항이 없어도 이 행은 반드시 존재)
    clause_id: int | None     # FK -> Clause, 대응 조항이 있을 때만
    relation: str              # SAME | BROADER | NARROWER | MISSING_IN_INSURER
    anchor_phrase_standard: str        # StandardClause.text의 부분 문자열 (필수)
    anchor_phrase_insurer: str | None  # Clause.text의 부분 문자열 (clause_id 있을 때만)
    note: str | None                    # 판정 근거를 사람이 읽을 한 문장
```

`overlap_rule`과 완전히 같은 철학: **판정을 코드가 아니라 데이터로 둔다.** 시드
스크립트가 각 행의 `anchor_phrase_standard`/`anchor_phrase_insurer`가 실제 원문의
부분 문자열인지 검증하고, 못 찾으면 예외를 던지고 롤백한다(`raw_text_is_grounded()`와
같은 함수 재사용). `clause_id`는 상수로 박지 않고 (보험사, 표준담보/조항 종류)로
조회한다 — 약관을 재시드해도 어긋나지 않도록.

`relation` 정의:
- `SAME` — 표준과 실질적으로 같은 내용
- `BROADER` — 이 회사가 표준보다 넓게 보상(가입금액 상향, 면책 항목 삭제 등)
- `NARROWER` — 이 회사가 표준보다 좁게 보상(표준에 없는 면책 추가, 조건 부가 등)
- `MISSING_IN_INSURER` — 표준엔 있는데 이 회사 약관에 대응 조항 자체가 없음
  (`clause_id`는 NULL, `anchor_phrase_insurer`도 NULL)

대응 조항을 못 찾았는데 성격상 `MISSING_IN_INSURER`도 아닌 애매한 경우(예: 표현이
너무 달라 사람이 봐도 판단이 안 서는 경우)는 행을 만들지 않는다 — 근거 없이 추측해서
넣지 않는다는 원칙을 여기서도 지킨다. 화면에서는 "대조 안 됨"으로 조용히 빠지는 게
아니라 매핑 커버리지 자체를 등록부에 기록해 정직하게 드러낸다(아래 "한계" 참고).

## 시드 파이프라인

새 의존성: `pyhwp`(`requirements.txt`에 추가) — HWP 추출은 시드 스크립트 실행 시점에만
필요하고 런타임 서버는 이미 시드된 DB만 읽으므로, 배포 환경에 hwp 파서가 없어도 앱은
정상 동작한다(6개사 PDF의 `pdfplumber`와 같은 위치 — 시드 전용 의존성).

```
backend/app/seed_standard_clauses.py
  hwp5txt로 추출한 텍스트를 "제N조(제목)" 정규식으로 조 단위 분해 → StandardClause 시드
  6개사 seed_*.py와 동일한 관례(누락 컬럼 자동 추가, 재실행 가능)

backend/app/seed_clause_standard_map.py
  StandardClause 제1~9조 × 6개사에 대해 대응 조항 판정 행을 시드
  Gemini로 정렬 후보 제안 → 사람이 anchor_phrase 확정 → 스크립트가 grounding 검증
  (Gemini 키 없으면 이 시드는 수작업으로만 채움 — 근거 조항 조회 자체는 LLM 없이도 됨)
```

## API

```
GET /standard-clauses?standard_name=해외여행실손의료보험
    표준 조항 목록(제1~9조), 원문 포함

GET /insurers/{insurer_code}/standard-comparison?standard_name=해외여행실손의료보험
    이 보험사의 조문별 대조 결과 — 표준 조항 원문, 대응 조항 원문(있으면),
    relation, anchor 하이라이트 좌표
```

기존 `insurers.py` 라우터 관례(`/insurers/{insurer_code}/...`)를 그대로 따른다.

## 화면

기존 보험사 상세 화면(`InsurerIncidentClauses.tsx`, 여행 준비 흐름 안)에 탭을 하나
추가: **"표준약관과 비교"**. 조문별로 표준 원문 / 이 회사 대응 조항 원문을 나란히
배치하고, 판정 배지(동일 · 표준보다 넓음 · 표준보다 좁음 · 대응 조항 없음)를 붙인다.
앵커 문구는 기존 형광펜 방식대로 강조 표시.

## 한계 · 정직하게 드러낼 것

- 조문 정렬(alignment)은 사람 검수를 거친 데이터이지 실시간 AI 판단이 아니다 — 약관이
  재시드되면 매핑도 다시 검수해야 정확성이 유지된다.
- 제10조 이후 계약관리 조항은 이번 범위에 없다는 것을 화면에 명시한다("보장 내용만
  비교, 계약 일반조항은 포함 안 됨").
- 매핑 커버리지(표준 9개 조문 × 6개사 = 54칸 중 실제 채워진 칸 수)를 등록부에 남겨,
  못 채운 칸을 "표준과 같음"으로 오인하지 않게 한다.
- 이 대조는 **보상 여부를 판정하는 근거가 아니라 참고 정보**다. 표준약관은 그 자체로
  법적 최소 기준이 아니라 감독당국이 마련한 모델 약관이므로("보상되지 않는다"가 아니라
  "표준과 다르게 쓰여 있으니 확인하라"까지만), 여행경보-면책 연동 기능 때 세운 경계선과
  같은 문구 원칙을 적용한다.

## 테스트

- `StandardClause.text`에서 잘라낸 조 단위 텍스트가 hwp 추출 원문의 연속 부분 문자열인지
- `ClauseStandardMap`의 두 anchor_phrase가 각각 대응 원문의 부분 문자열인지
  (`raw_text_is_grounded()` 재사용)
- `MISSING_IN_INSURER`인데 `clause_id`가 채워진 행, 또는 그 반대의 모순 행이 없는지
- `scripts/validate_kb.py`에 이 두 테이블의 참조 무결성 검사 추가
