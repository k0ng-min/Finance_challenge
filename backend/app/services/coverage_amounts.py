"""등록한 보험의 담보에 붙는 "그래서 얼마인가" — 등급별 가입금액 조회.

사고를 접수하면 청구 검토 결과에 그 사고와 관련된 담보들이 뜬다. 그런데 정작 사용자가
제일 먼저 보고 싶어 하는 금액이 대부분 비어 있었다. 이유는 데이터 쪽에 있다 — 금액을
약관 조항 원문(Coverage.limit_amount)에서만 찾고 있었는데, 그 값이 적힌 담보는 170개 중
27개뿐이다. 나머지는 "보험증권에 기재된 보험가입금액"처럼 금액을 증권으로 미룬다.

실제 금액은 다른 표에 있다. 보험사 공시 화면에서 받아온 등급별 담보 가입금액표
(InsurerComparisonMetric — 전 보험사를 같은 항목 이름으로 맞춰 놓은 비교표)에는 7개
보험사 × 등급마다 21개 항목이 빠짐없이 채워져 있다. 이 모듈은 약관 쪽 표준담보코드
(coverage_std.std_code)를 그 비교표의 항목 이름에 이어 준다.

주의할 점 두 가지.

1. **등급을 모르면 금액도 없다.** 이 표의 값은 "그 보험사의 그 등급" 기준이라, 등록할 때
   등급을 고르지 않았으면(UserPolicy.plan_name이 비었으면) 어느 열을 읽어야 할지 알 수
   없다. 그럴 때는 아무 값이나 고르지 않고 그냥 비운다.
2. **숫자가 아닌 표기는 금액이 아니다.** 원문에는 "-"(미가입), "가입"(한도 비공개),
   "미제공" 같은 표기가 섞여 있다. 그대로 내보내면 금액인 척 읽히므로 걸러낸다.
"""
from sqlalchemy.orm import Session

from app.models.kb import Insurer, InsurerComparisonMetric

#: 표준담보코드 -> 비교표의 항목 이름(metric_label). 값이 여러 개면 그 담보 하나가 비교표
#: 에서는 여러 줄로 갈려 있다는 뜻이라, 갈린 줄을 다 보여준다 — 예를 들어 "상해사망·후유
#: 장해"는 사망과 후유장해가 금액이 다를 수 있어 한 줄만 보여주면 절반이 사라진다.
#:
#: 비교표에 대응하는 항목이 없는 담보(반려동물 돌봄, 골프용품손해 등)는 아예 넣지 않는다.
#: 비슷해 보이는 항목에 억지로 이어 붙이면 다른 담보의 금액을 이 담보의 금액인 것처럼
#: 보여주게 된다.
STD_CODE_TO_METRIC_LABELS: dict[str, tuple[str, ...]] = {
    # --- 사망 · 후유장해 ---
    "DEATH_INJURY": ("상해사망보험금", "상해후유장해보험금"),
    "ILL_DEATH": ("질병사망/고도후유장해",),
    # 상해 고도후유장해(50%/80%/100% 이상) 특약은 각자 가입금액이 따로 있는데 비교표에는
    # 그 줄이 없다. 기본 후유장해보험금 줄을 대신 보여주면 다른 담보의 금액이 이 담보의
    # 금액인 것처럼 읽히므로 비워 둔다.
    # --- 의료비 ---
    "OVS_INJ_MED": ("해외 상해의료비",),
    "OVS_ILL_MED": ("해외 질병의료비",),
    "DOM_MED_SEVERE_NONCOV": ("국내 3대 비급여의료비",),
    "NON_COVERED_MED_MRI": ("국내 비급여 MRI/MRA",),
    # 비급여 상해의료비는 비교표의 "국내 상해의료비(급여)"와 다른 담보다 — 급여 금액을
    # 비급여 자리에 놓지 않는다.
    # --- 휴대품 · 도난 · 배상책임 ---
    "PERSONAL_EFFECTS": ("휴대품손해(분실제외)",),
    "HOME_THEFT": ("자택도난손해",),
    "LIABILITY": ("배상책임",),
    # --- 항공기 · 수하물 지연 ---
    "FLIGHT_DELAY": ("수하물/항공편 지연",),
    "TRV_BAGGAGE_DELAY": ("수하물/항공편 지연",),
    "DEPARTURE_DELAY": ("출국항공기지연(지수형)",),
    "INDEX_FLIGHT_DELAY": ("출국항공기지연(지수형)",),
    # --- 기타 특수담보 ---
    "PASSPORT_LOSS": ("여권분실 재발급비용",),
    "RESCUE": ("중대사고 구조송환비용",),
    "HIJACK": ("항공기납치위로금",),
    "TRIP_INTERRUPTION": ("여행중단 추가비용",),
    "FOOD_POISONING": ("식중독 보상",),
    "INFECTIOUS_DISEASE": ("특정전염병 보상금",),
    "INJ_HOSPITAL_ALLOWANCE": ("상해입원일당",),
    "INJURY_HOSPITAL_DAILY": ("상해입원일당",),
}


def _format(value_text: str, unit: str | None) -> str | None:
    """비교표 값 하나를 화면에 쓸 문자열로. 숫자가 아니면 None(= 금액 아님)."""
    value = (value_text or "").strip()
    if not value.isdigit():
        return None
    return f"{int(value):,}{unit or ''}"


def amount_for_std_code(
    db: Session, *, insurer_code: str | None, plan_name: str | None, std_code: str | None,
) -> str | None:
    """이 보험사·이 등급에서 그 표준담보의 가입금액. 근거가 없으면 None.

    돌려주는 문자열에는 어느 등급 기준인지가 항상 붙는다 — 같은 담보라도 등급마다 금액이
    두세 배씩 차이 나서, 등급을 빼면 근거 없는 숫자가 된다.
    """
    if not insurer_code or not plan_name or not std_code:
        return None
    labels = STD_CODE_TO_METRIC_LABELS.get(std_code)
    if not labels:
        return None

    insurer = db.query(Insurer).filter(Insurer.code == insurer_code).one_or_none()
    if not insurer:
        return None

    rows = (
        db.query(InsurerComparisonMetric)
        .filter(
            InsurerComparisonMetric.insurer_id == insurer.insurer_id,
            InsurerComparisonMetric.plan_name == plan_name,
            InsurerComparisonMetric.metric_label.in_(labels),
        )
        .all()
    )
    by_label = {row.metric_label: row for row in rows}

    parts: list[str] = []
    for label in labels:  # 비교표 순서가 아니라 매핑에 적은 순서를 따른다
        row = by_label.get(label)
        if not row:
            continue
        formatted = _format(row.value_text, row.unit)
        if not formatted:
            continue
        # 줄이 하나뿐이면 항목 이름을 다시 붙이지 않는다 — 담보 이름이 카드에 이미 있다.
        parts.append(formatted if len(labels) == 1 else f"{label} {formatted}")

    if not parts:
        return None
    return f"{' · '.join(parts)} ({plan_name} 기준)"
