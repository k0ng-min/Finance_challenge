# 지금 이 저장소가 담고 있는 것

`backend/scripts/generate_docs.py`가 만든다. 손으로 고치지 말고 스크립트를 다시 돌릴 것.

숫자를 여기 한 곳에 모으는 이유는 단순하다. 같은 값을 README와 등록부와 발표자료에
각각 적어 두면 반드시 어긋난다 — 실제로 어긋나 있었다. 다른 문서는 이 문서를 가리키고,
이 문서는 DB를 가리킨다.

## 지식베이스

<!-- generated:kb-counts start -->
| 항목 | 수 | 테이블 |
|---|---:|---|
| 보험사 | 7 | `insurer` |
| 약관 조항 | 558 | `clause` |
| 담보 | 170 | `coverage` |
| 표준담보 | 46 | `coverage_std` |
| 조항↔사고유형 매핑 | 711 | `clause_incident_map` |
| 정량조건(용어) | 174 | `clause_term` |
| 담보↔서류 매핑 | 633 | `coverage_doc_map` |
| 서류 세부요건 | 1 | `doc_requirement` |
| 중복 판정 규칙 | 7 | `overlap_rule` |
| 사고유형 | L1 8 · 전체 39 | `incident_type` |
| 표준약관 조문 | 11 | `standard_clause` |
| 표준약관 대조 | 11 | `clause_standard_map` |
| 여행경보 | 208 | `travel_alert` |
<!-- generated:kb-counts end -->

## 보험료·보장금액 (약관이 아닌 외부 자료)

<!-- generated:premium start -->
보험료는 7개사 **2,794행**(수집일 2026-08-17 ~ 2026-08-25). 약관에서 뽑은 값이 아니라 각 사 다이렉트 화면에서 가져온 외부 자료라, 행마다 어떤 경로로 만들어진 값인지를 함께 저장한다.

| value_origin | 행 | 뜻 |
|---|---:|---|
| `DIRECT_QUOTE` | 2,186 | 다이렉트 화면에서 그대로 조회한 값 |
| `DERIVED` | 486 | 조회값에서 기간 환산 등으로 유도한 값 |
| `IMPUTED` | 122 | 주변 값으로 메운 값 — 순위 계산에서 제외한다 |

등급별 담보 가입금액표는 7개사 483행, 보험사 공통 비교표는 420행이다.
<!-- generated:premium end -->

## 표준약관 대조

<!-- generated:standard start -->
금융감독원 표준약관 조문 11개 가운데 실제로 대조를 마친 것은 2개 조문이고, 보험사별로 세면 11칸이다(7개사 × 11조문 = 77칸이 전부 채워질 자리다). 근거를 확보하지 못한 칸은 "표준과 같다"고 단정하지 않고 비워 둔다.

| 표준 조문 | 대조된 보험사 수 |
|---|---:|
| 제3조 | 6 |
| 제4조 | 5 |
<!-- generated:standard end -->

## 검증

<!-- generated:verify start -->
백엔드 테스트 370건. API 66개(경로 60개).

KB 지문(`kb_content_sha256`): `4eca8a38c795653ab400ef683102a1139929655320b3d0793638e61a7cf29a93`
— 동결 시각 2026-08-30T12:21:42+00:00, 검증 시각 2026-08-18.
`cd backend && python scripts/validate_kb.py`가 이 지문과 실제 DB를 대조한다.
<!-- generated:verify end -->

## 이 문서가 답하지 않는 것

- 숫자가 **맞는지**는 세어서 알 수 있지만, 그 값이 **충분한지**는 아니다.
  예를 들어 정량조건 174건은 보험사마다 편차가 크다 —
  보험사별 내역은 `docs/compliance/source_register.md`를 볼 것.
- 출처·검증 상태·미완 사항(known_gap)은 사람이 원본을 확인해 적는 값이라
  여기서 자동으로 만들지 않는다.
