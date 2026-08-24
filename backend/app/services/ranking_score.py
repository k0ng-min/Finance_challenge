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
  price    — 사용자의 나이·성별·등급·여행일수로 조회한 실제 보험료
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

from app.models.kb import Insurer, InsurerComparisonMetric, InsurerPremium
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

# 기존보험 종류가 어느 사고유형과 겹치는지. 겹치면 그 유형의 무게를 낮춘다 —
# 이미 받을 수 있는 보장에 또 돈을 쓰지 않게.
EXTERNAL_KIND_TO_INCIDENT: dict[str, tuple[str, ...]] = {
    "MEDICAL_INDEMNITY": ("INJ", "ILL"),
    "ACCIDENT": ("INJ",),
    "DAILY_LIABILITY": ("LIA",),
    "DRIVER": ("LIA",),
}


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
    return {code: w / total for code, w in kept.items()}


def incident_weights(
    trip_context: dict | None,
    *,
    age: int | None = None,
    external_kinds: list[str] | None = None,
) -> dict[str, float]:
    """사고유형별 무게. 여행 준비에서 고른 것이 전부 여기로 들어온다."""
    config = load_weights()
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
            weights[code] += 0.5

    # 3) 동행 — 가족이나 반려동물과 함께면 남에게 끼치는 손해 위험이 커진다.
    for code in COMPANION_TO_INCIDENT.get(context.get("companion_type") or "", ()):
        weights[code] += 0.4

    if context.get("rental_car"):
        weights["LIA"] += 0.6

    # 4) 목적지 위험도 — 여행경보가 걸린 곳은 질병·긴급지원 무게를 올린다.
    risk = context.get("risk_level")
    if risk in ("높음", "매우높음", "high"):
        weights["EMG"] += 0.6
        weights["ILL"] += 0.4

    # 5) 여행 기간 — 길수록 병에 걸리거나 일정이 틀어질 여지가 커진다.
    trip_days = context.get("trip_days") or 0
    if trip_days >= 8:
        weights["ILL"] += 0.3
        weights["CHG"] += 0.3

    # 6) 나이 — 고령일수록 질병·긴급지원 쪽 위험이 크다.
    if age is not None and age >= 60:
        weights["ILL"] += 0.5
        weights["EMG"] += 0.3

    # 7) 기존보험 — 이미 받을 수 있는 보장은 무게를 낮춘다(0 아래로는 내리지 않는다).
    for kind in external_kinds or []:
        for code in EXTERNAL_KIND_TO_INCIDENT.get(kind, ()):
            weights[code] = max(0.2, weights[code] - 0.5)

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
    """1일 보험료를 나이대 구간으로 편 점수. 쌀수록 높다.

    자료가 없는 보험사는 available=False로 두고, 총점 계산에서 이 축의 비중을 빼고
    나머지로 다시 100%를 맞춘다 — 자료가 없다는 이유로 불리해지지 않게."""
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

    daily = row.premium / max(row.period_days or 1, 1)
    band = str(min((age or 30) // 10 * 10, 70))
    norm = (config.get("premium_norm") or {}).get(band)
    if not norm or float(norm["max"]) <= float(norm["min"]):
        return AxisScore("price", AXIS_LABELS["price"], 0.5,
                         detail=f"{int(daily * max(trip_days, 1)):,}원 (기준 구간 없음)")
    low, high = float(norm["min"]), float(norm["max"])
    scaled = (daily - low) / (high - low)
    # 쌀수록 좋다 — 뒤집는다.
    score = max(0.0, min(1.0, 1.0 - scaled))
    total = int(daily * max(trip_days, 1))
    return AxisScore("price", AXIS_LABELS["price"], score,
                     detail=f"{max(trip_days, 1)}일 기준 약 {total:,}원")


def clause_score(entry: dict) -> AxisScore:
    """약관 근거 네 축의 단계(1~5)를 평균해 0~1로. insurer_ranking.py가 계산한 값이다."""
    dimensions = entry.get("dimensions") or []
    levels = [d.get("level") or 0 for d in dimensions]
    if not levels:
        return AxisScore("clause", AXIS_LABELS["clause"], 0.0, available=False,
                         detail="약관 근거 자료가 없어요")
    score = sum(levels) / (len(levels) * 5)
    return AxisScore("clause", AXIS_LABELS["clause"], score,
                     detail=f"약관 근거 {len(levels)}개 축 평균 {sum(levels) / len(levels):.1f}단계")


def overlap_score(db: Session, insurer_code: str, plan_tier: int,
                  weights: dict[str, float], external_kinds: list[str] | None) -> AxisScore:
    """기존보험과 겹치지 않는 쪽에 가점.

    겹치는 사고유형의 무게는 이미 incident_weights에서 낮췄다. 여기서는 "낮춰진 무게가
    실린 항목에서 이 보험사가 얼마나 잘하는가"를 본다 — 즉 비는 자리를 메우는 정도다."""
    if not external_kinds:
        return AxisScore("overlap", AXIS_LABELS["overlap"], 0.5,
                         detail="등록한 기존보험이 없어 겹침 없이 계산했어요")
    covered: set[str] = set()
    for kind in external_kinds:
        covered.update(EXTERNAL_KIND_TO_INCIDENT.get(kind, ()))
    gap_weights = {code: (0.0 if code in covered else w) for code, w in weights.items()}
    if sum(gap_weights.values()) <= 0:
        return AxisScore("overlap", AXIS_LABELS["overlap"], 0.5,
                         detail="기존보험이 대부분을 덮고 있어요")
    inner = amount_score(db, insurer_code, plan_tier, gap_weights)
    return AxisScore("overlap", AXIS_LABELS["overlap"], inner.score, available=inner.available,
                     detail="기존보험이 안 덮는 담보만 따로 계산했어요")


def activity_score(entry: dict, trip_context: dict | None) -> AxisScore:
    """활동·목적지 위험에 대한 대응. 약관 근거 축 중 '제한이 적음'을 그대로 쓴다.

    활동별 특약 유무를 조항으로 직접 판정하려면 활동마다 매핑이 필요한데, 지금 KB에는
    그 매핑이 없다. 없는 걸 지어내지 않고, 대신 이번 여행에 위험 요소가 있을 때
    "막히는 조건이 적은" 보험사에 가점을 준다."""
    context = trip_context or {}
    risky = bool(context.get("activities")) or context.get("risk_level") in ("높음", "매우높음", "high")
    dimensions = {d.get("code"): d for d in (entry.get("dimensions") or [])}
    restrictions = dimensions.get("restrictions")
    if restrictions is None:
        return AxisScore("activity", AXIS_LABELS["activity"], 0.0, available=False,
                         detail="제한조건 자료가 없어요")
    score = (restrictions.get("level") or 0) / 5
    if not risky:
        # 위험 요소를 고르지 않았으면 이 축이 순위를 크게 흔들 이유가 없다.
        score = 0.5 + (score - 0.5) * 0.4
    detail = "고른 활동·목적지 위험을 감안했어요" if risky else "위험 활동을 고르지 않아 영향을 줄였어요"
    return AxisScore("activity", AXIS_LABELS["activity"], score, detail=detail)


# 최종 점수에서 Gemini가 차지하는 몫. 순위는 재현 가능한 수식이 주로 정하고, 모델은
# 수식이 놓친 맥락(예: 이번 활동이 면책으로 걸려 있음)만 거든다.
GEMINI_RATIO = 0.2


def blend(*, weighted: float, gemini: float | None) -> float:
    """가중치 점수와 Gemini 점수를 8:2로 섞는다. Gemini가 없으면 가중치 점수 그대로 —
    순위가 LLM 가용성에 묶이지 않는다."""
    if gemini is None:
        return weighted
    return weighted * (1 - GEMINI_RATIO) + gemini * GEMINI_RATIO


def score_insurers(
    db: Session,
    *,
    tier_code: str,
    plan_tier: int,
    trip_context: dict | None,
    ranking: list[dict],
    age: int | None = None,
    sex: str | None = None,
    external_kinds: list[str] | None = None,
) -> list[InsurerScore]:
    """(보험사 × 등급)마다 다섯 축을 계산해 0~100 총점으로 합산하고 내림차순 정렬한다.

    동점이면 보험사 코드순 — 같은 입력에는 언제나 같은 순서가 나온다."""
    config = load_weights()
    axis_weights = (config.get("axis_weights") or {}).get(tier_code) or _default_axis_weights()
    context = trip_context or {}
    trip_days = int(context.get("trip_days") or 1)
    weights = incident_weights(context, age=age, external_kinds=external_kinds)

    results: list[InsurerScore] = []
    for entry in ranking:
        code = entry["insurer_code"]
        axes = [
            amount_score(db, code, plan_tier, weights),
            clause_score(entry),
            price_score(db, code, plan_tier, age=age, sex=sex, trip_days=trip_days),
            overlap_score(db, code, plan_tier, weights, external_kinds),
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
