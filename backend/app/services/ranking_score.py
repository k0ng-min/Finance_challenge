"""가중치 점수로 보험사 순위를 매기는 결정적 모델.

왜 필요했나
-----------
순위를 가르던 건 약관 근거 네 축과 Gemini의 판단뿐이었다. 네 축은 "그 보험사의 약관이
어떻게 쓰여 있는가"에서 나오는 값이라 사용자가 무엇을 골랐든, 등급을 무엇으로 바꾸든
변하지 않는다. 그래서 "내 여행 준비"에서 목적지·활동·걱정되는 사고유형·동행·기존보험을
다 물어봐 놓고 정작 순위에는 거의 반영하지 못했고, 실속·표준·고급을 바꿔도 순서가 늘
똑같았다.

무엇을 하나
-----------
(보험사 × 등급)마다 다섯 축의 점수를 0~1로 내고, 사용자가 고른 것으로 축과 사고유형의
가중치를 정해 합산한다.

  amount   — 사고유형별 보장금액 (등급에 따라 변한다)
  clause   — 약관 근거 네 축 (insurer_ranking.py가 계산한 단계)
  price    — 사용자의 나이·성별·등급에 맞는 직접조회/검증된 환산 보험료 지표
  overlap  — 기존보험과 겹치면 감점, 비는 곳을 메우면 가점
  activity — 활동·목적지 위험에 대한 대응

계수는 R이 만든다
-----------------
정규화 구간과 항목→사고유형 매핑, 축 비중은 analysis/ranking_weights.R이 실제 KB 값을
분석해 backend/app/data/ranking_weights.json으로 떨어뜨린 것이다. 여기서는 그 파일을
읽어 쓰기만 한다 — 서버 실행 경로에 R이 필요하지 않다.

등급마다 순서가 달라지는 원리
-----------------------------
항목별 정규화를 등급 안에서 하지 않고 보험사 × 등급 값을 한 묶음으로 한다.
등급을 올려도 금액이 그대로인 항목은 세 등급에서 같은 점수를 받고, 실제로 뛰는 항목만
등급 사이에 차이를 만든다. 그래서 차이를 지어내지 않으면서도 등급마다 순서가 달라진다.
"""
from __future__ import annotations

import functools
import json
import pathlib
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.kb import (
    PREMIUM_ORIGIN_DERIVED,
    PREMIUM_ORIGIN_DIRECT_QUOTE,
    PREMIUM_ORIGIN_IMPUTED,
    Insurer,
    InsurerComparisonMetric,
    InsurerPremium,
)
from app.services.coverage_overlap import diagnose, insurer_coverage_std_ids
from app.services.insurer_tiers import plan_name_for_tier

WEIGHTS_PATH = pathlib.Path(__file__).resolve().parents[1] / "data" / "ranking_weights.json"

L1_CODES = ("INJ", "ILL", "PROP", "LIA", "TRV", "CHG", "EMG", "SPC")

AXIS_LABELS = {
    "amount": "고른 사고에 보장금액이 커요",
    "clause": "약관 근거가 탄탄해요",
    "price": "보험료가 합리적이에요",
    "overlap": "이미 든 보험과 안 겹쳐요",
    "activity": "이번 여행 위험에 맞아요",
}

AVAILABLE = "AVAILABLE"
UNKNOWN = "UNKNOWN"
NOT_APPLICABLE = "NOT_APPLICABLE"

# 활동·동행·목적지 같은 선택이 어느 사고유형의 무게를 올리는지. 근거는 상식적인
# 대응이지 약관이 아니므로, 가중치를 올릴 뿐 "보장된다"고 말하지 않는다.
ACTIVITY_TO_INCIDENT: dict[str, tuple[str, ...]] = {
    "스키": ("INJ", "EMG"),
    "스노보드": ("INJ", "EMG"),
    "스쿠버다이빙": ("INJ", "EMG"),
    "서핑": ("INJ", "EMG"),
    "등산": ("INJ", "EMG"),
    "트래킹": ("INJ", "EMG"),
    "번지점프": ("INJ", "EMG"),
    "패러글라이딩": ("INJ", "EMG"),
    "오토바이": ("INJ", "LIA"),
    "렌터카": ("LIA",),
    "수영": ("INJ",),
    "골프": ("INJ", "LIA"),
}

COMPANION_TO_INCIDENT: dict[str, tuple[str, ...]] = {
    "가족": ("LIA", "ILL"),
    "연인": ("LIA",),
    "친구": ("LIA",),
    "반려동물 동반": ("SPC", "LIA"),
}

# 기존보험 종류를 사고유형(L1)에 직접 매핑하던 표는 없앴다.
#
# 예전에는 MEDICAL_INDEMNITY → INJ·ILL, DRIVER → LIA 식으로 넓게 이어 붙이고 그 유형의
# 무게를 낮췄다. 그런데 근거 기반 중복 판정 엔진(services/coverage_overlap.py)은 바로
# 그 조합들을 UNKNOWN — "약관 근거를 확보하지 못했다" — 으로 판정하고 있었다. 한쪽은
# "모른다"고 말하면서 다른 쪽은 "이미 덮고 있다"고 감점했으니, 두 화면의 설명이 서로
# 어긋났다. 종류만 아는 기존보험으로 사고유형 전체를 기보장 처리하지 않는다.
#
# 기존보험의 영향은 이제 overlap 축 한 곳에서만, 실제 OverlapRule 근거로만 반영한다.


@dataclass
class AxisScore:
    """한 축의 결과. 화면에 "왜 이 순서인지"를 그대로 보여주기 위한 값이다."""
    code: str
    label: str
    score: float          # 0~1
    weight: float = 0.0   # 재정규화 뒤 실제로 쓰인 비중
    contribution: float = 0.0  # score * weight * 100
    available: bool = True
    detail: str = ""
    comparison_state: str = AVAILABLE

    def __post_init__(self) -> None:
        if not self.available and self.comparison_state == AVAILABLE:
            self.comparison_state = UNKNOWN


@dataclass
class InsurerScore:
    insurer_code: str
    insurer_name: str
    total: float
    axes: list[AxisScore] = field(default_factory=list)


@functools.lru_cache(maxsize=1)
def load_weights() -> dict:
    """R이 만든 계수 파일. 없으면 최소 기본값으로 돈다 — 계수가 없다고 순위 화면이
    통째로 죽지는 않게 한다."""
    try:
        return json.loads(WEIGHTS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {
            "priority_multiplier": 3.0,
            "priced_insurers": [],
            "axis_weights": {},
            "metric_to_incident": {},
            "metric_norm": {},
            "premium_norm": {},
        }


def _default_axis_weights() -> dict[str, float]:
    return {"amount": 0.34, "clause": 0.28, "price": 0.16, "overlap": 0.12, "activity": 0.10}


def renormalize(weights: dict[str, float], unavailable: set[str]) -> dict[str, float]:
    """쓸 수 없는 축을 빼고 남은 축의 비중을 다시 100%로 맞춘다.

    없는 자료를 0점으로 세면 "자료가 없다"가 "나쁘다"로 읽힌다. 보험료가 아직 없는
    보험사가 그 이유만으로 순위에서 밀리면 안 된다."""
    kept = {code: w for code, w in weights.items() if code not in unavailable}
    total = sum(kept.values())
    if total <= 0:
        return {}
    normalized = {code: w / total for code, w in kept.items()}
    # 부동소수점 나눗셈 뒤에도 API에 내려가는 비중 합이 정확히 1.0이 되게 마지막
    # 축에 미세한 반올림 잔차를 모은다. 축 사이의 실질 비율은 바뀌지 않는다.
    last_code = next(reversed(normalized))
    normalized[last_code] = 1.0 - sum(
        weight for code, weight in normalized.items() if code != last_code
    )
    return normalized


@dataclass(frozen=True)
class Heuristics:
    """개인화에 쓰는 정책 계수.

    이 값들은 약관에서 뽑아낸 것이 아니다. "스키를 타면 상해 무게를 얼마나 올릴까"에
    정답이 있는 게 아니라, 우리가 정한 것이다. 그래서 코드 여기저기 숫자로 흩어 두지
    않고 한 자리에 모아 이름을 붙였다 — 정책이라는 사실이 드러나야 하고, 값을 바꿔
    가며 결과가 얼마나 흔들리는지 재 볼 수 있어야 한다
    (analysis/ranking_sensitivity.py가 이 dataclass를 그대로 흔든다).

    기본값은 예전에 함수 안에 박혀 있던 숫자 그대로다 — 이 묶음을 만든 것으로 서비스
    동작이 달라지지는 않는다.
    """

    #: 사용자가 직접 고른 사고유형의 무게에 곱하는 값. None이면 ranking_weights.json.
    priority_multiplier: float | None = None
    #: 위험한 활동 하나가 관련 사고유형에 더하는 무게.
    activity_bump: float = 0.5
    #: 동행 유형이 관련 사고유형에 더하는 무게.
    companion_bump: float = 0.4
    #: 렌터카를 몬다고 답했을 때 배상책임에 더하는 무게.
    rental_car_bump: float = 0.6
    #: 여행경보가 걸린 목적지에서 긴급지원·질병에 더하는 무게.
    risk_emergency_bump: float = 0.6
    risk_illness_bump: float = 0.4
    #: 긴 여행에서 질병·일정변경에 더하는 무게, 그리고 "길다"의 기준(일).
    long_trip_bump: float = 0.3
    long_trip_days: int = 8
    #: 고령에서 질병·긴급지원에 더하는 무게, 그리고 "고령"의 기준(세).
    senior_illness_bump: float = 0.5
    senior_emergency_bump: float = 0.3
    senior_age: int = 60


DEFAULT_HEURISTICS = Heuristics()


def incident_weights(
    trip_context: dict | None,
    *,
    age: int | None = None,
    heuristics: Heuristics = DEFAULT_HEURISTICS,
) -> dict[str, float]:
    """사고유형별 무게. 여행 준비에서 고른 것이 전부 여기로 들어온다."""
    config = load_weights()
    multiplier = heuristics.priority_multiplier
    if multiplier is None:
        multiplier = float(config.get("priority_multiplier", 3.0))
    context = trip_context or {}
    weights = {code: 1.0 for code in L1_CODES}

    # 1) 걱정되는 사고유형 — 사용자가 직접 고른 것이라 가장 크게 반영한다.
    for code in context.get("coverage_priority") or []:
        if code in weights:
            weights[code] *= multiplier

    # 2) 활동 — 스키·스쿠버처럼 다칠 위험이 큰 활동은 상해·긴급지원 무게를 올린다.
    for activity in context.get("activities") or []:
        for code in ACTIVITY_TO_INCIDENT.get(activity, ()):
            weights[code] += heuristics.activity_bump

    # 3) 동행 — 가족이나 반려동물과 함께면 남에게 끼치는 손해 위험이 커진다.
    for code in COMPANION_TO_INCIDENT.get(context.get("companion_type") or "", ()):
        weights[code] += heuristics.companion_bump

    if context.get("rental_car"):
        weights["LIA"] += heuristics.rental_car_bump

    # 4) 목적지 위험도 — 여행경보가 걸린 곳은 질병·긴급지원 무게를 올린다.
    risk = context.get("risk_level")
    if risk in ("높음", "매우높음", "high"):
        weights["EMG"] += heuristics.risk_emergency_bump
        weights["ILL"] += heuristics.risk_illness_bump

    # 5) 여행 기간 — 길수록 병에 걸리거나 일정이 틀어질 여지가 커진다.
    trip_days = context.get("trip_days") or 0
    if trip_days >= heuristics.long_trip_days:
        weights["ILL"] += heuristics.long_trip_bump
        weights["CHG"] += heuristics.long_trip_bump

    # 6) 나이 — 고령일수록 질병·긴급지원 쪽 위험이 크다.
    if age is not None and age >= heuristics.senior_age:
        weights["ILL"] += heuristics.senior_illness_bump
        weights["EMG"] += heuristics.senior_emergency_bump

    # 기존보험은 여기서 다루지 않는다 — 위 주석 참고. overlap 축이 근거로만 반영한다.
    return weights


def _amount_rows(db: Session, insurer_code: str, plan_tier: int) -> list[InsurerComparisonMetric]:
    plan_name = plan_name_for_tier(insurer_code, plan_tier)
    if plan_name is None:
        return []
    insurer = db.query(Insurer).filter(Insurer.code == insurer_code).first()
    if insurer is None:
        return []
    return (
        db.query(InsurerComparisonMetric)
        .filter(
            InsurerComparisonMetric.insurer_id == insurer.insurer_id,
            InsurerComparisonMetric.plan_name == plan_name,
        )
        .order_by(InsurerComparisonMetric.category_order, InsurerComparisonMetric.sort_order)
        .all()
    )


def _to_number(value_text: str | None) -> float | None:
    if value_text is None:
        return None
    text = value_text.replace(",", "").strip()
    if not text or text in {"-", "미보장", "없음"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def amount_score(db: Session, insurer_code: str, plan_tier: int, weights: dict[str, float]) -> AxisScore:
    """사고유형 무게를 반영한 보장금액 점수.

    항목마다 R이 뽑아 둔 구간(보험사 × 등급 전체 값의 min~max)으로 0~1로 편 뒤,
    그 항목이 걸린 사고유형의 무게로 가중평균한다. 등급 안에서 다시 펴지 않는 것이
    요점이다 — 그래야 "등급을 올려도 안 변하는 항목"이 세 등급에서 같은 점수를 받는다."""
    config = load_weights()
    norms = config.get("metric_norm", {})
    mapping = config.get("metric_to_incident", {})

    numerator = 0.0
    denominator = 0.0
    used = 0
    for row in _amount_rows(db, insurer_code, plan_tier):
        shares = mapping.get(row.metric_label)
        norm = norms.get(row.metric_label)
        amount = _to_number(row.value_text)
        if not shares or not norm or amount is None:
            continue
        low, high = float(norm["min"]), float(norm["max"])
        # 구간이 한 점이면(모든 보험사·등급이 같은 금액) 이 항목은 아무것도 가르지
        # 못한다. 0.5를 줘서 점수에 영향은 남기되 순위를 흔들지는 않게 한다.
        scaled = 0.5 if high <= low else (amount - low) / (high - low)
        for incident, share in shares.items():
            weight = weights.get(incident, 1.0) * float(share)
            numerator += scaled * weight
            denominator += weight
        used += 1

    if denominator <= 0:
        return AxisScore("amount", AXIS_LABELS["amount"], 0.0, available=False,
                         detail="이 등급의 보장금액 자료가 없어요")
    score = numerator / denominator
    return AxisScore("amount", AXIS_LABELS["amount"], score,
                     detail=f"보장금액 {used}개 항목을 고른 사고 비중으로 계산했어요")


def price_score(
    db: Session, insurer_code: str, plan_tier: int, *, age: int | None, sex: str | None,
    trip_days: int,
) -> AxisScore:
    """비교 가능한 보험료 지표를 나이대 구간으로 편 점수. 쌀수록 높다.

    DIRECT_QUOTE와 변환 근거가 완전한 DERIVED만 사용한다. IMPUTED/UNKNOWN은
    available=False로 두고 나머지 축 비중을 다시 100%로 맞춘다."""
    config = load_weights()
    plan_name = plan_name_for_tier(insurer_code, plan_tier)
    insurer = db.query(Insurer).filter(Insurer.code == insurer_code).first()
    if plan_name is None or insurer is None:
        return AxisScore("price", AXIS_LABELS["price"], 0.0, available=False,
                         detail="보험료 자료가 아직 없어요")

    query = db.query(InsurerPremium).filter(
        InsurerPremium.insurer_id == insurer.insurer_id,
        InsurerPremium.plan_name == plan_name,
    )
    if age is not None:
        query = query.filter(InsurerPremium.age == age)
    if sex:
        query = query.filter(InsurerPremium.sex == sex)
    row = query.first()
    if row is None:
        return AxisScore("price", AXIS_LABELS["price"], 0.0, available=False,
                         detail="보험료 자료가 아직 없어요")

    if row.value_origin == PREMIUM_ORIGIN_IMPUTED:
        return AxisScore(
            "price", AXIS_LABELS["price"], 0.0, available=False,
            detail="산술 보간한 추정 보험료라 추천 점수에서 제외했어요",
        )
    if row.value_origin == PREMIUM_ORIGIN_DERIVED and not all((
        row.source_value is not None,
        row.source_period_days,
        row.transformation,
        row.transformation_reason,
    )):
        return AxisScore(
            "price", AXIS_LABELS["price"], 0.0, available=False,
            detail="환산 근거가 완전하지 않아 추천 점수에서 제외했어요",
        )
    if row.value_origin not in {PREMIUM_ORIGIN_DIRECT_QUOTE, PREMIUM_ORIGIN_DERIVED}:
        return AxisScore(
            "price", AXIS_LABELS["price"], 0.0, available=False,
            detail="보험료 출처 성격을 확인할 수 없어 추천 점수에서 제외했어요",
        )

    daily = row.premium / max(row.period_days or 1, 1)
    if row.value_origin == PREMIUM_ORIGIN_DERIVED:
        price_detail = f"비교용 1일 환산 보험료 {int(daily):,}원"
    elif row.period_days == 1:
        price_detail = f"1일 직접 조회 보험료 {int(row.premium):,}원"
    else:
        price_detail = (
            f"{row.period_days}일 직접 조회값의 비교용 1일 환산지수 {int(daily):,}원"
        )
    band = str(min((age or 30) // 10 * 10, 70))
    norm = (config.get("premium_norm") or {}).get(band)
    if not norm or float(norm["max"]) <= float(norm["min"]):
        return AxisScore("price", AXIS_LABELS["price"], 0.5,
                         detail=f"{price_detail} (정규화 기준 구간 없음)")
    low, high = float(norm["min"]), float(norm["max"])
    scaled = (daily - low) / (high - low)
    # 쌀수록 좋다 — 뒤집는다.
    score = max(0.0, min(1.0, 1.0 - scaled))
    _ = trip_days  # 여행기간 선형 비례 근거가 없어 실제 N일 가격을 만들지 않는다.
    return AxisScore("price", AXIS_LABELS["price"], score, detail=price_detail)


def clause_score(entry: dict) -> AxisScore:
    """비교 가능한 약관 축만 평균한다. UNKNOWN/N/A는 0점이 아니라 제외다."""
    dimensions = entry.get("dimensions") or []
    comparable = [
        dimension
        for dimension in dimensions
        if dimension.get("available", (dimension.get("level") or 0) > 0)
        and dimension.get("comparison_state", AVAILABLE) == AVAILABLE
    ]
    levels = [dimension.get("level") or 0 for dimension in comparable]
    if not levels:
        return AxisScore("clause", AXIS_LABELS["clause"], 0.0, available=False,
                         detail="비교 가능한 약관 근거 축이 없어 총점에서 제외했어요")
    score = sum(levels) / (len(levels) * 5)
    return AxisScore("clause", AXIS_LABELS["clause"], score,
                     detail=(
                         f"비교 가능한 약관 근거 {len(levels)}/{len(dimensions)}개 축 평균 "
                         f"{sum(levels) / len(levels):.1f}단계"
                     ))


#: 근거로 확인된 관계마다 "보완효용"을 얼마로 볼지.
#
#   NO_OVERLAP        겹치지 않는다는 근거가 있다 → 온전히 새로 얻는 보장
#   PARTIAL           일부만 겹친다는 근거가 있다 → 절반만 인정
#   DUPLICATE_PRORATA 비례분담·1개 계약 한정 지급이 근거로 확인됐다 → 새로 얻는 것이 없다
#
# DUPLICATE_FIXED와 UNKNOWN은 이 표에 없다. 둘 다 중립이라 분모에도 들어가지 않는다.
#   DUPLICATE_FIXED — 정액 담보는 계약마다 각각 지급된다. 겹친다는 이유만으로 깎으면
#                     사실과 반대되는 감점이 된다.
#   UNKNOWN         — 근거가 없다는 뜻이지 "겹친다"도 "안 겹친다"도 아니다.
COMPLEMENT_VALUE = {
    "NO_OVERLAP": 1.0,
    "PARTIAL": 0.5,
    "DUPLICATE_PRORATA": 0.0,
}


def overlap_score(db: Session, insurer_code: str,
                  external_policies: list | None) -> AxisScore:
    """기존보험 위에 이 보험사가 얼마나 '새로' 얹어 주는지를, 약관 근거로만 판단한다.

    사고유형(L1)을 넓게 기보장 처리하던 예전 방식을 버리고, 중복 진단 화면과 똑같은
    엔진(services/coverage_overlap.diagnose)을 그대로 쓴다. 대상 담보만 다르다 — 저기선
    "내가 등록한 여행자보험"이고 여기선 "후보 보험사가 파는 담보"다. 판정 규칙과 근거
    조항은 같으므로 두 화면의 설명이 어긋날 수 없다.

    근거로 판정된 관계가 하나도 없으면 점수를 만들지 않고 축을 내린다(available=False).
    모르는 것을 0점으로 세면 "자료가 없다"가 "겹친다"로 읽히고, 그건 틀린 감점이다.
    """
    if not external_policies:
        return AxisScore("overlap", AXIS_LABELS["overlap"], 0.5,
                         detail="등록한 기존보험이 없어 겹침 없이 계산했어요")

    target_ids = insurer_coverage_std_ids(db, insurer_code)
    if not target_ids:
        return AxisScore("overlap", AXIS_LABELS["overlap"], 0.0, available=False,
                         detail="이 보험사의 담보 자료가 없어 겹침을 판단하지 않았어요")

    report = diagnose(db, external_policies=external_policies, target_coverage_std_ids=target_ids)

    judged = [
        f for f in (report.duplicates + report.gaps)
        if f.relation in COMPLEMENT_VALUE
    ]
    fixed = len(report.fixed_ok)
    unknown = len(report.unknown)

    if not judged:
        return AxisScore(
            "overlap", AXIS_LABELS["overlap"], 0.0, available=False,
            detail=(f"기존보험과의 관계를 확인할 약관 근거가 없어 이 축은 빼고 계산했어요"
                    f" (근거 없음 {unknown}건" + (f", 정액 중복 {fixed}건" if fixed else "") + ")"),
        )

    score = sum(COMPLEMENT_VALUE[f.relation] for f in judged) / len(judged)

    counts: dict[str, int] = {}
    for f in judged:
        counts[f.relation] = counts.get(f.relation, 0) + 1
    parts = []
    if counts.get("NO_OVERLAP"):
        parts.append(f"안 겹침 {counts['NO_OVERLAP']}건")
    if counts.get("PARTIAL"):
        parts.append(f"일부 겹침 {counts['PARTIAL']}건")
    if counts.get("DUPLICATE_PRORATA"):
        parts.append(f"비례분담 중복 {counts['DUPLICATE_PRORATA']}건")
    neutral = []
    if fixed:
        neutral.append(f"정액 중복 {fixed}건은 각각 다 받으므로 감점하지 않았어요")
    if unknown:
        neutral.append(f"근거 없는 {unknown}건은 중립으로 뒀어요")

    detail = "약관 근거로 " + " · ".join(parts)
    if neutral:
        detail += " (" + ", ".join(neutral) + ")"
    return AxisScore("overlap", AXIS_LABELS["overlap"], score, detail=detail)


def activity_score(entry: dict, trip_context: dict | None) -> AxisScore:
    """활동·목적지 위험에 대한 대응. 약관 근거 축 중 '제한이 적음'을 그대로 쓴다.

    활동별 특약 유무를 조항으로 직접 판정하려면 활동마다 매핑이 필요한데, 지금 KB에는
    그 매핑이 없다. 없는 걸 지어내지 않고, 대신 이번 여행에 위험 요소가 있을 때
    "막히는 조건이 적은" 보험사에 가점을 준다."""
    context = trip_context or {}
    risky = bool(context.get("activities")) or context.get("risk_level") in ("높음", "매우높음", "high")
    dimensions = {d.get("code"): d for d in (entry.get("dimensions") or [])}
    restrictions = dimensions.get("restrictions")
    restriction_available = (
        restrictions is not None
        and restrictions.get("available", (restrictions.get("level") or 0) > 0)
        and restrictions.get("comparison_state", AVAILABLE) == AVAILABLE
    )
    if not restriction_available:
        return AxisScore("activity", AXIS_LABELS["activity"], 0.0, available=False,
                         detail="제한조건이 미검증 상태라 총점에서 제외했어요")
    score = (restrictions.get("level") or 0) / 5
    if not risky:
        # 위험 요소를 고르지 않았으면 이 축이 순위를 크게 흔들 이유가 없다.
        score = 0.5 + (score - 0.5) * 0.4
    detail = "고른 활동·목적지 위험을 감안했어요" if risky else "위험 활동을 고르지 않아 영향을 줄였어요"
    return AxisScore("activity", AXIS_LABELS["activity"], score, detail=detail)


# 예전에는 여기에 GEMINI_RATIO = 0.2과 blend()가 있었다. 결정적 점수와 Gemini 점수를
# 8:2로 섞어 최종 총점을 만들었고, 호출부가 그 총점으로 다시 정렬했다 — 즉 모델이 순위를
# 바꿀 수 있었다. 금융상품 추천에서 그건 감당하기 어려운 성질이다. 같은 자료·같은 입력인데
# 모델이 바뀌면 순서가 바뀌고, "왜 1위인가"의 마지막 20%를 수식으로 되짚을 수 없다.
#
# 이제 총점은 이 파일의 계산만으로 끝난다. 모델은 확정된 순위를 받아 문장만 쓴다
# (services/insurer_ranking_explain_gemini.py).


def score_insurers(
    db: Session,
    *,
    tier_code: str,
    plan_tier: int,
    trip_context: dict | None,
    ranking: list[dict],
    age: int | None = None,
    sex: str | None = None,
    external_policies: list | None = None,
    heuristics: Heuristics = DEFAULT_HEURISTICS,
    axis_weights_override: dict[str, float] | None = None,
) -> list[InsurerScore]:
    """(보험사 × 등급)마다 다섯 축을 계산해 0~100 총점으로 합산하고 내림차순 정렬한다.

    동점이면 보험사 코드순 — 같은 입력에는 언제나 같은 순서가 나온다.

    heuristics·axis_weights_override는 민감도 분석용 입구다. 서비스는 둘 다 건드리지
    않고 기본값으로 부르므로 동작이 달라지지 않는다. 이 입구가 있어야 "계수를 조금
    흔들면 순위가 얼마나 흔들리는가"를 서비스 코드를 복제하지 않고 실제 경로 그대로
    잴 수 있다(analysis/ranking_sensitivity.py).
    """
    config = load_weights()
    axis_weights = (
        axis_weights_override
        or (config.get("axis_weights") or {}).get(tier_code)
        or _default_axis_weights()
    )
    context = trip_context or {}
    trip_days = int(context.get("trip_days") or 1)
    weights = incident_weights(context, age=age, heuristics=heuristics)

    results: list[InsurerScore] = []
    for entry in ranking:
        code = entry["insurer_code"]
        axes = [
            amount_score(db, code, plan_tier, weights),
            clause_score(entry),
            price_score(db, code, plan_tier, age=age, sex=sex, trip_days=trip_days),
            overlap_score(db, code, external_policies),
            activity_score(entry, context),
        ]
        unavailable = {axis.code for axis in axes if not axis.available}
        applied = renormalize(axis_weights, unavailable)
        total = 0.0
        for axis in axes:
            axis.weight = applied.get(axis.code, 0.0)
            axis.contribution = axis.score * axis.weight * 100
            if axis.available:
                total += axis.contribution
        results.append(InsurerScore(
            insurer_code=code,
            insurer_name=entry.get("insurer_name") or code,
            total=total,
            axes=axes,
        ))

    results.sort(key=lambda r: (-r.total, r.insurer_code))
    return results
