# 현지 대응 팩(「현지에서」)과 사고 시뮬레이션 — 설계

작성 2026-08-16.

## 무엇을 하려는가

이 서비스의 생애주기는 `여행 전 → 사고 접수 → 청구 준비 → 부지급 후`까지 채워져 있는데,
정작 청구 결과가 결정되는 구간인 **여행 중·사고 직후 현지**가 비어 있다. 비교 서비스
(보험다모아·보맵·굿리치·시그널플래너)는 전부 "가입 전" 한 구간에만 산다.

두 화면을 추가한다.

- **「현지에서」(`/onsite`)** — 해외 현지에 서 있는 사람이 쓰는 도구. 귀국하면 못 받는
  서류 알림 + 병원·경찰서에 그대로 보여주는 현지어 서류 요청 카드 + 비행기모드에서도
  열리는 오프라인 캐시.
- **「사고 시뮬레이션」(`/simulate`)** — 가입 전에 "이 여행에서 이런 일이 나면 보험사별로
  어떻게 갈리는지"를 기존 청구 판정 엔진에 그대로 태워서 미리 보여준다.

## 왜 이 축인가

### 현지 서류

해외에서 부지급이 나는 흔한 이유는 담보가 없어서가 아니라 **영수증만 받아와서**다.
약관은 "사고증명서는 국외의 의료관련법에서 정한 의료기관에서 발급한 것이어야 합니다"
(삼성 제7조 ②항)처럼 발급 주체·기재 항목을 요구하는데, 여행자는 그걸 모르고 카운터에서
receipt만 받는다. 귀국하면 그 서류는 영영 못 받는다.

이 판단에 필요한 데이터는 **이미 DB에 있고 안 쓰이고 있다**: `required_doc_std`
14종 중 9종이 `acquire_location = '현지only'`인데, 지금은 `DocumentCheck.tsx:169`의
배지로만 노출된다 — 즉 이미 귀국한 사람이 보는 사후 체크리스트에서만 보인다.

### 시뮬레이션

지금 보험사 비교는 전부 표의 숫자(보험료·지급한도)다. 사용자는 숫자 차이를 체감하지
못한다. 반면 이 프로젝트에는 **활동 수식자 기반 면책 우선 판정**
(`claim_review._activity_matches_waiver`)이 이미 있다 — 사고 상황에 "스쿠버다이빙"이
들어가면, 그 문구가 실제로 면책 조항 원문에 있는 보험사만 면책으로 뒤집힌다.
이걸 가입 전에 돌리면 같은 사고에 대해 보험사별 결론이 조항 원문과 함께 갈린다.
비교표로는 절대 안 보이는 차이이고, 새 판단 로직 없이 기존 엔진 재사용으로 나온다.

## 원칙 (기존과 동일)

- 근거 없는 결과를 내지 않는다. 조항 원문 인용은 항상 `clause.text`의 부분 문자열.
- **조항 원문은 번역하지 않는다.** 근거 자체이므로 한국어 원문 그대로 인용한다.
  번역 대상은 서류명(`required_doc_std.doc_name`)과 요건 표시문구
  (`doc_requirement.label`)뿐이고, 화면에는 **항상 한국어와 병기**한다 — 현지어만
  단독으로 노출되는 화면은 만들지 않는다.
- 판정 규칙은 코드가 아니라 데이터(테이블 행)로 둔다(`overlap_rule`,
  `clause_standard_map`과 같은 원칙).
- 근거가 없으면 "보장됩니다/안 됩니다" 대신 **확인불가**.

---

# A. 「현지에서」 (`/onsite`)

## 화면 구성 — 한 페이지 3단

### 1단 · 이 여행 / 현지only 서류

- 연결된 여행의 `trip.end_date` 기준 D-day 표시.
- `required_doc_std.acquire_location == '현지only'` 인 서류만 "귀국하면 못 받는 것"으로
  분리해서 맨 위에 둔다. `귀국가능`·`공통`은 아래 접힌 영역.
- 이 여행에 연결된 사고(`incident.trip_id`)가 있으면 → 그 사고의 `evidence.status`를
  읽어 진행률(예: 5건 중 3건 확보). 사고가 없으면 → **예방 모드**: 진행률 없이
  "이 여행에서 사고가 나면 현지에서만 받을 수 있는 서류" 목록만.
- 여행이 없는 사용자(게스트 포함)는 국가만 직접 골라도 2단이 동작한다
  (기존 `IncidentReport`가 "연결된 여행이 없으면 국가만이라도 직접 입력"을 허용하는
  것과 같은 방식).

### 2단 · 현지어 서류 요청 카드

- 사고유형 L1 8개 중 하나를 고르면 → 그 유형에 매핑된 담보 → `coverage_doc_map` →
  서류 목록.
- 서류마다 카드 한 장:
  - 서류명 — 한국어 / 현지어 병기
  - 그 서류의 약관 요건(`doc_requirement.label`) — 한국어 / 현지어 병기
  - 근거 조항 인용(`doc_requirement.anchor_phrase`가 포함된 `clause.text` 구간) —
    **한국어 원문 그대로**
- 카드 상단에 현지어 한 줄 안내문(예: "보험 청구용으로 아래 항목이 포함된 서류가
  필요합니다") — 이 문장도 `onsite_phrase_i18n`에 `kind='intro'`로 둔다.

### 3단 · 오프라인

- "이 화면을 미리 열어두면 비행기모드에서도 열립니다" + 마지막 동기화 시각.
- 오프라인으로 뜬 경우 상단에 "오프라인 — {시각} 기준" 배지.

## 데이터 모델

```python
class CountryLanguage(Base):
    """한국어 국가명 → 그 나라에서 서류 요청에 통하는 언어.

    country_name 표기는 travel_alert.country_name과 맞춘다(둘 다 외교부 국가명 기준).
    매핑이 없는 국가는 추측하지 않고 영어(en)로 떨어뜨린다 — 병원·경찰서 문서 창구에서
    가장 통할 가능성이 높은 기본값이고, 화면에는 한국어가 항상 병기되므로 정보가
    사라지지 않는다.
    """
    __tablename__ = "country_language"
    __table_args__ = (UniqueConstraint("country_name", "lang_code"),)

    id = Column(Integer, primary_key=True)
    country_name = Column(String, nullable=False, index=True)
    lang_code = Column(String, nullable=False)     # ISO 639-1: en/ja/zh/th/vi/es/fr/de/id/...
    lang_name_ko = Column(String, nullable=False)  # "영어"
    is_primary = Column(Boolean, default=True)     # 다국어 국가는 대표 하나만 True


class OnsitePhraseI18n(Base):
    """현지어 문구 캐시.

    조항 원문은 여기 들어오지 않는다(근거는 번역하지 않는다). 서류명·요건 표시문구·
    안내문만 담는다.

    source가 'seed'면 사람이 검수해 커밋한 번역, 'gemini'면 런타임에 만들어 캐시한
    번역이다. 같은 (kind, ref_id, lang_code)로 두 번 부르지 않으므로 두 번째 사용자부터는
    API 호출이 없고, 오프라인 캐시에도 그대로 들어간다.
    """
    __tablename__ = "onsite_phrase_i18n"
    __table_args__ = (UniqueConstraint("kind", "ref_id", "lang_code"),)

    id = Column(Integer, primary_key=True)
    kind = Column(String, nullable=False)      # doc_name | requirement | intro
    ref_id = Column(Integer, nullable=False)   # required_doc_std_id | requirement_id | 0(intro)
    lang_code = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    source = Column(String, nullable=False)    # seed | gemini
    created_at = Column(DateTime)
```

## 번역 흐름

1. `onsite_phrase_i18n`에 `(kind, ref_id, lang_code)` 행이 있으면 그대로 쓴다.
2. 없으면 Gemini로 번역하고 `source='gemini'`로 저장한 뒤 쓴다.
3. Gemini 키가 없거나 호출이 실패하면 **한국어만 표시한다.** 기능 자체를 막지 않는다
   — 서류 목록·약관 요건·근거 조항은 번역 없이도 그대로 유효하기 때문이다.
   (`doc_verify_gemini`처럼 기능을 통째로 막는 경우와 다르다. 거긴 LLM 없이는 결과
   자체가 존재할 수 없지만, 여기선 번역이 전달 수단일 뿐이다.)

시드 대상 언어: 한국인 해외여행 상위 국가 기준 `en / ja / zh / th / vi / es / fr / de`
8개. 나머지는 Gemini 경로로 채워진다.

## 백엔드 API

```
GET  /trips/{trip_id}/onsite                    현지 대응 팩(여행 연결 O) — routers/trips.py
GET  /onsite?country={한국어국가명}              현지 대응 팩(여행 연결 X, 게스트 가능) — routers/onsite.py
```

두 엔드포인트는 같은 응답 스키마(`OnsitePackOut`)를 쓰고, 실제 조립은 양쪽 다
`services/onsite.py`의 같은 함수 하나가 한다(라우터는 입력만 다르게 넘긴다).
한 번의 요청으로 사고유형 8개분의 서류·요건·근거 인용·현지어를 전부 내려보낸다 —
오프라인 캐시에 담을 단위가 요청 하나여야 비행기모드에서 화면이 온전히 뜬다.
서류는 14종·요건은 7건뿐이라 8개 유형을 다 담아도 응답이 작다.

### 어느 보험사의 서류인가

`coverage_doc_map`은 보험사별 담보에 달려 있으므로, 대상 보험사를 정해야 한다.

| 상황 | 대상 |
|---|---|
| `trip.user_policy_id`가 있음 | 그 보험사 하나 |
| 여행은 있는데 보험 미등록 / 여행 없이 국가만 선택 | 6개사 **합집합**을 `required_doc_std` 단위로 묶어서 표시 |

합집합일 때는 요건(`requirements`)마다 어느 보험사 조항인지 `insurer_name`을 붙여
구분한다 — 근거의 출처를 뭉뚱그리지 않는다. 서류 자체는 표준 코드(`required_doc_std`)
단위라 보험사가 달라도 같은 줄로 합쳐진다.

응답 개요:

```
OnsitePackOut
  country: str
  lang_code: str
  lang_name_ko: str
  trip: { trip_id, start_date, end_date } | null
  progress: { total, secured } | null      # 연결된 사고가 있을 때만
  incident_types: [ { type_id, l1_code, name } ]
  docs_by_type: {
    type_id: [
      {
        required_doc_std_id
        doc_name_ko, doc_name_local
        acquire_location                    # 현지only | 귀국가능 | 공통
        status: 보유|미보유|발급불가|null    # 연결된 사고가 있을 때만
        requirements: [
          { label_ko, label_local, clause_quote, clause_article_no, insurer_name }
        ]
      }
    ]
  }
  intro_local: str | null
  generated_at: datetime
```

`clause_quote`는 `anchor_phrase`를 포함하는 `clause.text` 구간을 잘라 쓴다 — 자를 때
말줄임표를 붙이지 않으므로 **항상 원문의 연속 부분 문자열**이다(기존
`coverage_overlap`의 인용 규칙과 동일).

## PWA / 오프라인

- `vite-plugin-pwa`를 devDependency로 추가(런타임 의존성 없음).
- **precache**: 앱 셸(JS/CSS/index.html) + 3D 아이콘 자산.
- **runtime cache**: `/trips/*/onsite`, `/onsite*` 는 NetworkFirst —
  온라인이면 최신, 오프라인이면 마지막 응답. 응답에 `generated_at`이 있으므로
  화면에 "언제 기준"인지 정직하게 표시할 수 있다.
- `render.yaml`의 정적 사이트에 헤더 규칙 추가:
  `sw.js`(및 워크박스 산출물)에 `Cache-Control: no-cache` — 없으면 재배포해도
  브라우저가 옛 서비스워커를 계속 쓴다.
- SPA rewrite(`/* → /index.html`)가 이미 있으므로 오프라인 내비게이션은 그대로 동작.
- **범위 한정**: PWA는 오프라인 열람만 담당한다. 오프라인 중 데이터 쓰기(서류 상태
  변경 등)는 이번 범위에서 제외한다 — 동기화 충돌 처리가 별개 문제다. 오프라인일 때
  쓰기 UI는 비활성화하고 이유를 표시한다.

---

# B. 「사고 시뮬레이션」 (`/simulate`)

## 새로 필요한 것 둘

**(1) 조회 범위.** 기존 `claim_review.relevant_coverages_for_type()`는 **사용자가
등록한 담보**(`user_coverage` 조인) 기준이라 가입 전에는 아무것도 안 나온다. 자매
함수를 추가한다.

```python
def simulate_coverages_for_type(
    db, type_ids: list[int], policy_version_id: int, modifiers: dict | None = None,
): ...
```

`user_coverage`/`user_policy` 조인 대신 `coverage.policy_version_id`로 필터할 뿐,
**판정 로직(`rank_maps`, `_activity_matches_waiver`)은 손대지 않고 그대로 호출한다.**
기존 사고 접수 흐름의 코드 경로는 한 줄도 바뀌지 않는다(`_rank_maps` → `rank_maps`
이름만 공개로 바꿨다).

**(2) L1 → L2 확장(`expand_type_ids`).** 구현 중에 발견한 것: `clause_incident_map`은
**L2에만** 걸려 있다. L1 시나리오의 `type_id`를 그대로 조회하면 6개사 전부 "확인불가"가
나온다 — 근거가 없어서가 아니라 조회 축이 어긋나서다. L1이면 그 아래 L2 전체로 넓히고,
사용자가 L2를 고르면 그 하나만 본다.

**인용문 잘라내기.** 면책 조항은 열거 항목이 길어서(제5조 "보험금을 지급하지 않는 사유")
앞에서부터 200자를 자르면 정작 근거가 된 "스쿠버다이빙"이 통째로 잘려나간다. 활동
수식자 때문에 올라온 면책 판정이면 그 문구를 `anchor_phrase`로 넘겨 창을 잡는다 —
중복보장 진단이 쓰던 것과 같은 장치다(`services/clause_quote.py`로 공용화).

## 시나리오는 L1, 세분화는 사용자가

시나리오 행은 **L1(8개 대분류) 단위로만** 둔다. 사고 접수 흐름이 "L1 먼저 판정 →
L2로 좁힘"인 것과 같은 구조다. 화면에서 사용자가 그 L1 안의 L2를 직접 고르면 결과가
다시 계산된다 — 시뮬레이션은 자유서술이 없어서 Gemini가 L2를 추론할 근거가 없으므로,
추측하지 않고 사람이 고르게 한다.

```python
class SimulationScenario(Base):
    """여행 정보로 자동 선정되는 사고 시나리오(L1 단위).

    선정 조건을 코드 분기가 아니라 행으로 두는 이유는 overlap_rule과 같다 —
    시나리오를 늘려도 선정 로직이 늘어나지 않는다.

    type_id는 반드시 L1 루트 행(incident_type.parent_id IS NULL)을 가리킨다.
    L2 세분화는 사용자가 화면에서 고르고, 그 선택은 요청 파라미터로만 전달된다
    (시나리오 행에 L2를 박아두지 않는다).
    """
    __tablename__ = "simulation_scenario"

    scenario_id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)        # "다이빙 중 다쳤다면"
    narrative = Column(Text, nullable=False)      # 사용자가 읽는 한 문장 상황 설명
    type_id = Column(Integer, ForeignKey("incident_type.type_id"), nullable=False)  # L1
    modifiers = Column(Text)                      # JSON, 예: {"activity": "스쿠버다이빙"}
    # 선정 조건 — 전부 null이면 항상 뜨는 기본 시나리오
    require_activity = Column(String)             # trip.activities에 이 값이 있으면
    require_rental_car = Column(Boolean)          # trip.rental_car
    require_alert_nationwide = Column(Boolean)    # 목적지가 전국 단위 경보 국가면
    sort_order = Column(Integer, default=0)
```

초기 시드:

| code | 선정 조건 | L1 | modifiers |
|---|---|---|---|
| `THEFT` | 항상 | PROP | — |
| `FLIGHT_DELAY` | 항상 | TRV | — |
| `ILLNESS` | 항상 | ILL | — |
| `DIVING_INJURY` | `activities`에 스쿠버다이빙 | INJ | `{"activity": "스쿠버다이빙"}` |
| `RENTAL_CAR_LIABILITY` | `rental_car = true` | LIA | — |
| `UNREST` | 전국 단위 여행경보 국가 | SPC | — |

항상 뜨는 3개 + 조건부 최대 3개. 화면에는 `sort_order` 순으로 최대 4개까지 노출한다.

`require_alert_nationwide`는 **전국 단위 경보만** 본다. 여행경보는 지역 단위라
(일본 3단계 = 후쿠시마 반경 30km, 필리핀 4단계 = 민다나오 일부; 3·4단계 72개국 중
52개국이 일부 지역 경보) 국가 단계로 판정하면 도쿄 여행자에게 시위 시나리오가 뜬다.
기존 여행경보 기능이 이미 "전국이 위험한 31개국"과 "일부 지역만 위험한 나라"를
구분해 다루므로, 그 구분을 그대로 재사용한다.

## 백엔드 API

```
GET /trips/{trip_id}/simulation
GET /trips/{trip_id}/simulation?scenario={code}&type_id={L2_type_id}   세분화 선택 시
```

세분화 파라미터가 없으면 L1 기준으로 계산한다. `type_id`가 넘어오면 그 값이 해당
시나리오 L1의 자식(`incident_type.parent_id == 시나리오.type_id`)인지 검증하고,
아니면 400으로 거절한다 — 다른 L1의 L2를 끼워 넣어 엉뚱한 판정을 만들지 못하게 한다.

응답 개요:

```
SimulationOut
  trip: { trip_id, destination, start_date, end_date }
  scenarios: [
    {
      code, title, narrative
      incident_type_name                 # 지금 계산에 쓰인 유형(L1 또는 선택된 L2)
      selected_type_id
      sub_types: [ { type_id, name } ]   # 이 L1의 L2 목록 — 사용자가 고를 수 있는 것
      results: [
        {
          insurer_name
          verdict: 직접 | 조건부 | 면책 | 확인불가
          coverage_name: str | null
          clause_quote: str | null           # 있을 때만
          clause_article_no: str | null
        }
      ]
    }
  ]
```

- `verdict`는 `_rank_maps`의 대표값을 그대로 쓴다 — 시뮬레이션 전용 판정 기준을
  새로 만들지 않는다.
- 매핑된 조항이 없는 보험사는 조용히 빼지 않고 **확인불가**로 남긴다(보험료 비교의
  `unavailable_insurers`와 같은 원칙 — 빠지면 "그 보험사가 더 나은가?"로 오독된다).
- 화면에 "이 시뮬레이션은 약관 조항 매핑에 근거한 예시이며, 실제 보험금 지급 여부는
  사고 경위와 보험사 심사에 따라 달라집니다"를 고정 문구로 표시한다.

---

# C. 홈 레이아웃 (작은 칸 4 → 6)

```
[ 내 여행 준비 ]           ← 큰 칸, 그대로
[ 사고가 발생했어요 ]

[내 보험]      [청구 전 점검]  [보험료 비교공시]
[약관 형광펜]  [현지에서]      [사고 시뮬레이션]
```

- `Home.tsx`의 `QUICK_ITEMS`에 두 항목 추가.
- `app.css:336` `.home__quick-grid`를 `repeat(4, 1fr)` 1줄 → `repeat(3, 1fr)` 2줄로.
  높이는 `calc(var(--home-h-quick) * 2 + var(--home-gap))`.
- `--home-h-quick` 상한을 줄여 히어로·큰 칸 예산을 침범하지 않게 재조정한다
  (`.home`은 남는 높이를 히어로가 흡수하는 구조라, 상한만 낮추면 자연히 흡수된다).
- `app.css:1988`의 세로 긴 프레임(`@container shell (min-height: 820px)`) 분기는
  `repeat(2,1fr)`로 접으면 3줄이 되어 넘친다 → **3열 2줄을 유지하되 타일만 가로형**
  (아이콘 옆 글자)으로 바꾼다. 기존에 이 분기가 노리던 "남는 세로를 칸이 직접 먹게
  한다"는 목적은 2줄이 된 것만으로 이미 달성된다.
- 아이콘: `Icon3D`에 쓸 자산 2개 필요(현지에서 / 시뮬레이션). 기존 자산 중 재활용
  가능한 것을 먼저 찾고, 없으면 추가한다.

---

# D. 라우팅

```tsx
<Route path="/onsite" element={<Onsite />} />
<Route path="/simulate" element={<Simulate />} />
```

둘 다 게스트 접근 허용. `/simulate`는 여행이 없으면 여행 준비(`/trip`)로 안내하고,
`/onsite`는 여행이 없으면 국가 직접 선택으로 떨어진다.

---

# E. 테스트

기존 pytest 56건에 추가한다.

**근거 검증(기존 규칙 그대로 적용)**
- `/onsite` 응답의 모든 `clause_quote`가 해당 `clause.text`의 부분 문자열인가
- 현지어 카드 응답에 **한국어 원문(`doc_name_ko`, `label_ko`)이 항상 존재**하는가
  — 현지어만 있고 한국어가 빈 행이 하나라도 있으면 실패
- `onsite_phrase_i18n`에 `kind='clause'` 같은 조항 원문 번역이 들어가지 않는가

**현지only 필터**
- `acquire_location == '현지only'` 인 서류만 1단 목록에 오는가
- 연결된 사고가 없을 때 `progress`가 `null`인가(진행률을 0/N으로 지어내지 않는다)

**시뮬레이션**
- `DIVING_INJURY` 시나리오에서, 면책 조항 원문에 "스쿠버다이빙"이 실제로 있는
  보험사는 `면책`이 대표값으로 올라오고 없는 보험사는 그렇지 않은가
- 매핑된 조항이 없는 보험사가 응답에서 빠지지 않고 `확인불가`로 남는가
- `simulate_coverages_for_type`이 `user_coverage`에 의존하지 않는가
  (등록 담보가 0인 사용자로도 결과가 나오는가)

**회귀**
- 기존 `relevant_coverages_for_type` 결과가 변하지 않는가(사고 접수 흐름 불변)

**빌드**
- `npm run build` 산출물에 서비스워커가 생성되는가

---

# F. 건드리는 파일

**신규**
```
frontend/src/pages/Onsite.tsx
frontend/src/pages/Simulate.tsx
backend/app/services/onsite.py
backend/app/services/onsite_i18n.py
backend/app/services/simulation.py
backend/app/services/clause_quote.py    coverage_overlap에 있던 인용 규칙을 공용화
backend/app/routers/onsite.py
backend/app/seed_country_language.py
backend/app/seed_onsite_phrases.py
backend/app/seed_simulation_scenarios.py
backend/tests/test_onsite.py
backend/tests/test_simulation.py
```

**수정**
```
frontend/src/pages/Home.tsx        QUICK_ITEMS 2개 추가
frontend/src/App.tsx               라우트 2개
frontend/src/app.css               quick-grid 3열 2줄 + 높이 예산
frontend/src/api.ts                타입·호출 추가
frontend/vite.config.ts            vite-plugin-pwa
frontend/package.json              devDependency 1개
backend/app/models/kb.py           CountryLanguage, OnsitePhraseI18n, SimulationScenario
backend/app/schemas.py             OnsitePackOut, SimulationOut
backend/app/routers/trips.py       /{trip_id}/onsite, /{trip_id}/simulation
backend/app/main.py                스키마 마이그레이션 + 신규 시드 자동 실행
render.yaml                        서비스워커 no-cache 헤더
README.md                          구현 현황 갱신
```

---

# G. 범위 밖 (의도적으로 뺀 것)

- **청구권 소멸시효 카운트다운** — DB의 400여 개 조항 원문에 `소멸시효`/`청구권`/`3년`이
  0건이다. 상법상 3년이 맞지만 이 프로젝트가 가진 근거는 약관뿐이라, 붙이면 근거 없는
  결과가 된다.
- **보험사 사고접수 연락처** — `insurer` 테이블에 연락처 필드가 없다. 이미 있는
  `official_url`만 쓴다.
- **오프라인 쓰기·동기화** — PWA는 열람만. 동기화 충돌은 별개 문제다.
- **현지어 음성 재생 / 실시간 통역** — 서류 요청 카드의 목적(문서 창구에 보여주기)에서
  벗어난다.
