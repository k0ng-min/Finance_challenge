# 기존보험 연결 기능 설계

작성일: 2026-08-03

## 1. 배경과 목적

사용자가 이미 들고 있는 보험(실손의료비·상해보험·일상생활배상책임 등)을 서비스에 연결하면,
이번 여행에 드는 해외여행자보험을 **약관 원문 근거와 함께** 조정할 수 있게 한다.

### 1.1 최초 아이디어와 조사 결과의 차이

최초 요구사항은 "같은 보험사의 기존계약이 있으면 혜택이 있고, 그게 약관에 적혀 있는지 확인"이었다.
6개사 약관 DB(조항 363건) 전문 검색 결과 **관련 조항이 한 건도 없다**.

| 키워드 | 건수 | 키워드 | 건수 |
|---|---|---|---|
| 할인 | 0 | 기존계약 | 0 |
| 우대 | 0 | 다수계약 | 0 |
| 기가입 | 0 | 가입경력 | 0 |
| 장기계약 | 0 | 무사고 | 0 |

이는 데이터 누락이 아니라 구조적 사실이다. 보험료 할인율은 약관이 아니라 보험료산출방법서·
사업방법서(금감원 제출용, 비공개)와 각 사 마케팅 정책에 있다. 약관은 "보상하는 손해 / 면책 /
지급절차"만 다룬다.

따라서 기능의 축을 **"할인 혜택"에서 "중복보장 진단"으로 옮긴다.** 중복보장은 약관 원문에
실제 근거가 있으므로, 이 프로젝트의 절대 원칙("근거 없는 결과를 내지 않는다")을 지킬 수 있다.
할인·혜택 안내는 별도 데이터 소스(자동 크롤러 + 출처 등록대장)로 분리해 병행한다.

### 1.2 제공할 세 가지

1. **중복보장 진단** — 기존보험과 여행자보험 담보가 겹치는 지점을 약관 원문 근거로 제시
2. **공백 진단** — 기존보험이 커버하지 못하는 담보를 제시
3. **혜택·할인 안내** — 약관이 아닌 별도 출처에서 수집, 출처를 명시해 표시

## 2. 근거 데이터 현황 (검증 완료)

`backend/data/app.db` 실측 결과. 이 clause_id들이 `overlap_rule` 시드의 근거가 된다.

| clause_id | 보험사 | 조항 | 근거로 쓰는 내용 |
|---|---|---|---|
| 4, 13, 20, 26, 32, 38 | 6개사 전부 | 제3조 (1)상해-해외의료비 | "보험가입금액을 한도로 피보험자가 **실제 부담한** 의료비 전액을 보상합니다" → 실손보상 원칙 |
| 67 | 삼성화재 | [여행중 배상책임] 제4조(의무보험과의 관계) | "의무보험에서 보상하는 금액을 **초과할 때에 한하여 그 초과액만을 보상**" |
| 77 | 삼성화재 | \<붙임3\>국내 의료기관 의료비 중 보상하는 질병의료비 | 국내 치료 구간의 보상 범위 |
| 98 | 삼성화재 | 제1조(보상하는 손해) — 여권분실 | "보험금을 지급할 **다른 계약**이 체결되어 있고 … **비율에 따라** 보험금을 지급" |
| 252 | 현대해상 | [항공기납치보장] 제3조(다른 보험과의 관계) | "**다수의 계약**이 동시에 효력을 가질 경우 … 선정하는 **하나의 계약에서만** 보상" |

### 2.1 확보하지 못한 근거

- **"제11조(보험금의 분담)" 본문 없음.** clause #67이 이 조항을 참조하지만 본문 자체는 DB에 없다.
- 휴대품·기타 담보의 중복 조항 없음.
- `data/raw_pdfs/`가 로컬에 없어(gitignore) PDF 재추출은 이번 범위에서 제외한다.

→ 근거가 없는 조합은 `overlap_rule.clause_id = NULL`로 두고 화면에서 **"확인불가"**로 표시한다.
추측으로 채우지 않는다.

## 3. 데이터 모델

기존 `UserPolicy`는 "이번 여행에 든 여행자보험"이라 성격이 다르므로 재사용하지 않고 새 테이블을 만든다.

### 3.1 `external_policy` — 기존보험 1건

| 컬럼 | 타입 | 설명 |
|---|---|---|
| external_policy_id | PK | |
| user_id | FK app_user | |
| source | String | `manual` / `mock` / `codef` |
| kind | String | `MEDICAL_INDEMNITY`(실손) / `ACCIDENT`(상해) / `DAILY_LIABILITY`(일상생활배상책임) / `DRIVER`(운전자) / `OTHER` |
| insurer_name_raw | String, nullable | 사용자가 모를 수 있음 |
| product_name_raw | String, nullable | |
| enrolled_ym | String, nullable | `YYYY-MM`. 실손 세대 판정에 사용 |
| indemnity_gen | Integer, nullable | 1~4. `enrolled_ym`에서 파생해 저장 |
| raw_payload | Text, nullable | CODEF 원본 JSON. `source='codef'`일 때만 |
| created_at | DateTime | |

### 3.2 `external_coverage` — 기존보험의 담보

| 컬럼 | 타입 | 설명 |
|---|---|---|
| external_coverage_id | PK | |
| external_policy_id | FK | |
| coverage_std_id | FK coverage_std, nullable | 표준담보 매핑 |
| raw_name | String | |
| subscribed_amount | String, nullable | |
| amount_source | String | `standard_terms` / `user_input` / `codef` / `unknown` |

`amount_source`를 두는 이유: 화면에서 "표준약관 기준 자동입력"과 "사용자가 직접 입력"을
구분해 표시해야 신뢰도를 정직하게 전달할 수 있다.

### 3.3 `overlap_rule` — 중복 판정 규칙 (시드 데이터)

이 설계의 핵심. 판정 로직을 코드에 숨기지 않고 **행마다 근거 조항을 물려서** 시드한다.
근거 없는 판정이 구조적으로 불가능해진다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| rule_id | PK | |
| external_kind | String | `external_policy.kind` 값 |
| coverage_std_id | FK coverage_std | 여행자보험 표준담보 |
| scope | String | 같은 담보 안에서 갈리는 구간. `전체` / `해외 의료기관` / `국내 의료기관` |
| relation | String | 아래 5종 |
| clause_id | FK clause, nullable | 근거 조항. NULL이면 확인불가 |
| note | Text | 화면 문구의 기반 |

`(external_kind, coverage_std_id, scope)`가 유니크 키다. `scope`가 필요한 이유: 하나의
표준담보 안에서도 구간에 따라 판정이 갈린다. 예를 들어 `OVS_ILL_MED`(해외발생 질병의료비)는
해외 의료기관 구간에서는 기존 실손과 겹치지 않지만, 국내 의료기관 구간(clause #77)에서는
겹친다. 진단 엔진은 한 담보에 대해 매칭되는 모든 `scope` 행을 함께 반환한다.

`relation` 값:

| 값 | 뜻 | 화면 메시지 성격 |
|---|---|---|
| `NO_OVERLAP` | 안 겹침 | "기존보험으로 커버 안 됩니다 — 이 담보는 여전히 필요" |
| `DUPLICATE_PRORATA` | 실손형 중복 | "겹칩니다. 비례보상이라 두 개 들어도 더 받지 못합니다" |
| `DUPLICATE_FIXED` | 정액형 중복 | "겹치지만 정액이라 각각 다 받습니다" |
| `PARTIAL` | 일부만 겹침 | 겹치는 구간을 명시 |
| `UNKNOWN` | 근거 없음 | "확인불가" |

### 3.4 `insurer_discount` — 혜택·할인 (크롤러 산출물)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| discount_id | PK | |
| insurer_id | FK insurer | |
| title | String | 예: 온라인가입 할인 |
| raw_text | Text | 수집한 원문 문구 (가공 금지) |
| source_url | String | |
| collected_at | Date | |

## 4. 중복 판정 내용

조사 중 확인한 중요한 사실: **기존 실손의료보험은 해외 치료비를 보상하지 않는다**(국내 의료기관 한정).
따라서 "기존 실손이 있으니 해외의료비 특약을 빼라"는 흔한 조언은 틀렸다. 이를 근거로 보여주는 것이
이 기능의 핵심 가치다.

| 기존보험 kind | 여행자보험 담보(std_code) | scope | relation | 근거 clause_id |
|---|---|---|---|---|
| MEDICAL_INDEMNITY | OVS_INJ_MED 해외발생 상해의료비 | 해외 의료기관 | NO_OVERLAP | 4·13·20·26·32·38 |
| MEDICAL_INDEMNITY | OVS_ILL_MED 해외발생 질병의료비 | 해외 의료기관 | NO_OVERLAP | 4·13·20·26·32·38 |
| MEDICAL_INDEMNITY | OVS_ILL_MED 해외발생 질병의료비 | 국내 의료기관 | PARTIAL | 77 |
| DAILY_LIABILITY | LIABILITY 배상책임 | 전체 | DUPLICATE_PRORATA | 67 |
| ACCIDENT | DEATH_INJURY 상해사망·후유장해 | 전체 | DUPLICATE_FIXED | 담보 조항 |
| (any) | PASSPORT_LOSS 여권분실 | 전체 | DUPLICATE_PRORATA | 98 |
| (any) | HIJACK 항공기납치 | 전체 | DUPLICATE_PRORATA(택일) | 252 |
| 그 외 조합 | — | — | UNKNOWN | NULL |

clause #77은 `OVS_ILL_MED` 담보에 속하는 \<붙임3\> 조항이다(별도 표준담보가 아니다). 그래서
같은 `OVS_ILL_MED`에 대해 `scope`가 다른 두 행이 존재한다.

`ACCIDENT × DEATH_INJURY`의 근거는 정액 지급을 명시한 각 사 상해사망·후유장해 담보 조항
(coverage_std_id=1에 연결된 16건)에서 고른다. 시드 시 실제 clause_id를 확정해 기록한다.

## 5. 기존보험 수집 — Provider 인터페이스

```
backend/app/services/external_policy/
  base.py      ExternalPolicyProvider(ABC), ExternalPolicyDTO, ExternalCoverageDTO
  manual.py    ManualProvider
  mock.py      MockProvider
  codef.py     CodefProvider
  registry.py  get_provider(), list_available_providers()
```

```python
@dataclass
class ExternalCoverageDTO:
    raw_name: str
    coverage_std_code: str | None
    subscribed_amount: str | None
    amount_source: str

@dataclass
class ExternalPolicyDTO:
    source: str
    kind: str
    insurer_name_raw: str | None
    product_name_raw: str | None
    enrolled_ym: str | None
    coverages: list[ExternalCoverageDTO]
    raw_payload: dict | None

class ExternalPolicyProvider(ABC):
    name: str
    requires_login: bool

    @abstractmethod
    def fetch(self, *, user, credentials: dict) -> list[ExternalPolicyDTO]: ...
```

세 구현체가 **동일한 DTO**를 반환하므로, 저장·진단·화면은 수집 방식을 구분하지 않는다.

### 5.1 ManualProvider (`requires_login = False`)

사용자가 고른 체크리스트를 DTO로 변환한다. 게스트도 사용 가능.

입력 항목:
- 보험 종류 토글 (실손 / 상해 / 일상생활배상책임 / 운전자 / 기타)
- 보험사 (선택, 모름 허용)
- **실손을 고른 경우에만** 가입 년월

실손이면 `enrolled_ym` → 세대 판정 → 세대별 표준 보장구조로 `coverages`를 자동 채운다
(`amount_source = 'standard_terms'`). 사용자가 자기 가입금액을 몰라도 된다.

세대 경계:

| 세대 | 가입시기 |
|---|---|
| 1세대 | ~2009-09 |
| 2세대 | 2009-10 ~ 2017-03 |
| 3세대 | 2017-04 ~ 2021-06 |
| 4세대 | 2021-07 ~ |

근거: 실손의료보험은 2009년 표준화 이후 보험사별 보장내용이 동일하다. 보험다모아가
"4세대 실손의료보험은 보험회사별 보장내용은 모두 표준화되어있지만, 보험료는 사업비 구조,
적용위험률 등에 따라 다를 수 있습니다"라고 명시한다.

**시드 전 확인 필요**: 세대별 자기부담률·한도 수치는 금융감독원 「금융상품 표준약관」
(https://www.fss.or.kr/fss/bbs/B0000115/list.do?menuNo=200504) 의 실손의료보험 표준약관
원문과 대조한 뒤 시드한다. 원문 대조 없이 숫자를 넣지 않는다.

실손 외 종류(상해·일상생활배상책임·운전자)는 표준약관이 없어 회사·상품마다 담보가 다르다.
→ 종류만 저장하고 금액은 `amount_source = 'unknown'`으로 둔다. 중복 *판정* 자체는 종류만으로
가능하므로 진단 기능은 정상 동작한다(금액 계산만 못 한다).

### 5.2 MockProvider (`requires_login = True`)

CODEF 응답 형태를 흉내 낸 고정 샘플 2~3건을 반환한다. 연동 UX 전체(버튼 → 로딩 → 결과)를
실제 연동 없이 시연할 수 있다.

### 5.3 CodefProvider (`requires_login = True`)

이번 범위에서는 **스키마와 필드 매핑만 작성하고 호출부는 `NotImplementedError`로 둔다.**

CODEF 조사 결과:

| | 신용정보원 **내보험다보여** | 생명보험협회 **내보험찾아줌** |
|---|---|---|
| 경로 | `/insurance/each/credit4u/*` | `/insurance/each/cont/find` |
| 제공 | 계약정보 · 회원가입신청 · 아이디찾기 · 비밀번호변경 · 회원탈퇴 | 조회 1종 |
| 보장(담보) 상세 | 제공 O | **제공 X** — 계약 상태만 |
| 조회 범위 | 생·손보 '06년 이후, 공제 '09년 이후 | 유지 중 계약(만기 3년 경과분 제외) |

담보별 중복 판정에는 **내보험다보여만 사용 가능**하다. 내보험찾아줌은 보장내역을 주지 않는다.

**미구현으로 두는 이유(법적 제약):** 내보험다보여 회원가입에는 주민등록번호가 필요하다.
개인정보보호법 제24조의2에 따라 주민등록번호는 **법령에 구체적 근거가 있을 때만** 처리할 수
있고 정보주체 동의로는 갈음할 수 없다. 본 서비스에는 그 법령 근거가 없다. 따라서 실제 연동은
운영 주체가 법적 요건을 갖춘 뒤 `CodefProvider`만 채워 활성화한다.

### 5.4 Provider 선택

환경변수 `EXTERNAL_POLICY_PROVIDER`로 활성 Provider를 정한다(기본값: `manual,mock`).
`GET /users/{user_id}/external-policies/providers`가 현재 사용 가능한 목록을 반환하고,
프론트는 그에 따라 버튼을 그린다. → CODEF 미설정이면 버튼 자체가 보이지 않고, 나중에
환경변수만 켜면 나타난다. 프론트 코드 수정이 필요 없다.

## 6. 진단 엔진

`backend/app/services/coverage_overlap.py`

```python
def diagnose(db, *, external_policies, target_coverage_std_ids) -> OverlapReport
```

조회 시점에 매번 계산한다(저장하지 않는다). 약관 DB가 갱신되면 결과도 자동으로 따라오고,
데이터 규모가 작아(담보 수십 개) 성능 문제가 없다.

`OverlapReport` 구성:

| 필드 | 내용 |
|---|---|
| duplicates | 겹치는 담보 + relation + 근거 조항 인용 |
| gaps | 기존보험이 커버 못 하는 담보 |
| fixed_ok | 정액이라 중복수령 가능한 담보 |
| unknown | 근거가 없어 확인불가인 조합 |

각 항목은 근거 조항의 **원문 조각**을 함께 담는다. 그 조각은 반드시 `clause.text`의
부분 문자열이어야 하며, 벗어나면 반환하지 않는다(기존 `raw_text_is_grounded()`와 같은 원칙).

## 7. 혜택·할인 크롤러

`backend/app/crawl_discounts.py` — 기존 `crawl_premiums.py`의 세션 확보·재시도·요청 간격
(1.2초) 로직을 재사용한다. 대상 서버에 부담을 주지 않는다.

산출물 `backend/data/discounts.json`:

```json
{
  "source": "...",
  "source_url": "...",
  "collected_at": "2026-08-03",
  "records": [{"insurer_code": "SAMSUNG", "title": "...", "raw_text": "..."}],
  "unavailable": [{"insurer_code": "...", "reason": "..."}]
}
```

`seed_discounts.py`가 이를 `insurer_discount` 테이블로 적재한다.

**수집 실패 시 동작:** 이전 JSON을 그대로 유지하고, 화면에 수집일을 함께 표시한다.
못 찾은 보험사는 화면에 아예 표시하지 않는다. **추측으로 채우지 않는다.**

화면 표시 형식: 원문 문구 + "출처: ○○화재 공식 안내(2026-08-03 확인)".

수집 대상과 결과는 `docs/compliance/source_register.md`에 약관 PDF와 같은 형식으로 등록한다.

**리스크(기록용):** 할인 안내 페이지는 보험사마다 형식이 다르고 SPA인 곳이 많다
(메리츠·KB·카카오페이에서 이미 겪은 문제). 크롤 실패 가능성이 높다. 실패는 위 규칙대로
"표시하지 않음"으로 처리해 오답이 나가지 않게 한다.

## 8. API

```
GET    /users/{user_id}/external-policies                  목록
DELETE /users/{user_id}/external-policies/{id}             삭제
GET    /users/{user_id}/external-policies/providers        사용 가능한 수집 방식
POST   /users/{user_id}/external-policies/link             등록 — 모든 Provider 공통 진입점
GET    /users/{user_id}/coverage-overlap?trip_id=&product_id=   진단
GET    /insurers/{code}/discounts                          혜택·할인
```

등록 경로는 `/link` 하나로 통일한다. 요청 본문에 `provider`와 `credentials`를 담고,
서버는 `registry.get_provider(provider)`로 구현체를 골라 `fetch()`를 호출한 뒤 결과 DTO를
저장한다. 수동입력도 `provider='manual'`, `credentials={체크리스트 값}`으로 같은 경로를 탄다.
→ 수집 방식이 늘어도 라우터는 바뀌지 않는다.

권한은 기존 `verify_owner` 패턴을 따른다. `requires_login=True`인 Provider를 게스트가
호출하면 401로 거부한다.

## 9. 화면

| 위치 | 내용 |
|---|---|
| `MyPolicies.tsx` | "기존보험 연동" 섹션 추가 (로그인 계정) |
| `TripPrep.tsx` | 마지막 단계에 "기존보험 있으세요?" 선택 → 진단 결과 반영 |
| `IncidentReport.tsx` | 최종 단계에 동일 |

게스트가 수동입력으로 등록한 기존보험은, 나중에 로그인·가입하면 기존 게스트→계정 승계 패턴
(`AppUser.auth_provider`)을 그대로 타고 이어진다.

## 10. 에러 처리

| 상황 | 동작 |
|---|---|
| 근거 조항 없음 | "확인불가" 표시. 추측 금지 |
| CODEF 미설정 | providers API가 목록에서 제외 → 버튼 미표시 |
| 크롤 실패 | 이전 데이터 유지 + 수집일 표시. 없으면 미표시 |
| 실손 가입시기 미입력 | 세대 판정 불가 → 담보 자동채움 생략, 종류만 저장 |

## 11. 테스트

- **실손 세대 판정 경계값**: 2009-09/2009-10, 2017-03/2017-04, 2021-06/2021-07
- **Provider 계약 테스트**: 3종이 모두 동일한 `ExternalPolicyDTO` 형태를 반환하는지
- **overlap_rule 무결성**: `relation != 'UNKNOWN'`인 모든 행이 유효한 `clause_id`를 갖는지
- **인용 근거 검증**: 진단 결과가 담은 원문 조각이 실제 `clause.text`의 부분 문자열인지
- **게스트 경로**: 게스트가 `requires_login=True` Provider를 호출하면 거부되는지

## 12. 이번 범위에서 제외

- 약관 PDF 재추출 (`data/raw_pdfs/` 부재)
- CODEF 실제 API 호출 (법적 요건 미충족)
- 담보별 가입금액 기반 정밀 금액 계산 (실손 외에는 표준 데이터가 없음)
