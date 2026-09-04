"""민감도 분석이 재는 대상과 재는 방법을 지킨다.

analysis/ranking_sensitivity.py는 순위가 정책 계수에 얼마나 기대는지를 재서 문서로
남긴다. 그 문서를 읽고 우리가 판단을 내리므로, 두 가지가 틀리면 안 된다.

  1. 분석용 입구(heuristics·axis_weights_override)를 만든 것 때문에 서비스 동작이
     달라지면 안 된다. 기본값으로 부르면 예전과 한 글자도 다르지 않아야 한다.
  2. 지표 계산이 틀리면 보고서 숫자가 통째로 거짓말이 된다. Kendall tau와 Spearman은
     손으로 답을 알 수 있는 경우로 못 박아 둔다.
"""
import pathlib
import sys

import pytest

from app.services import ranking_score

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "analysis"))
import ranking_sensitivity as rs  # noqa: E402


# --- 1) 입구를 만든 것이 서비스 동작을 바꾸지 않았다 -------------------------

def test_기본_계수는_예전에_함수에_박혀_있던_숫자_그대로다():
    """dataclass로 꺼낸 것은 정리이지 변경이 아니다. 값이 바뀌면 순위가 조용히 달라진다."""
    h = ranking_score.DEFAULT_HEURISTICS
    assert h.priority_multiplier is None  # None이면 ranking_weights.json을 따른다
    assert h.activity_bump == 0.5
    assert h.companion_bump == 0.4
    assert h.rental_car_bump == 0.6
    assert h.risk_emergency_bump == 0.6
    assert h.risk_illness_bump == 0.4
    assert h.long_trip_bump == 0.3
    assert h.long_trip_days == 8
    assert h.senior_illness_bump == 0.5
    assert h.senior_emergency_bump == 0.3
    assert h.senior_age == 60


def test_계수를_안_넘기면_넘긴_기본값과_결과가_같다():
    context = {
        "activities": ["스키"], "coverage_priority": ["INJ"],
        "companion_type": "가족", "rental_car": True,
        "risk_level": "높음", "trip_days": 14,
    }
    without = ranking_score.incident_weights(context, age=65)
    with_default = ranking_score.incident_weights(
        context, age=65, heuristics=ranking_score.DEFAULT_HEURISTICS
    )
    assert without == with_default


def test_계수를_흔들면_무게가_실제로_따라_움직인다():
    """입구가 이름만 있고 아무 일도 안 하면 분석이 통째로 무의미해진다."""
    import dataclasses

    context = {"activities": ["스키"]}
    base = ranking_score.incident_weights(context)
    louder = ranking_score.incident_weights(
        context,
        heuristics=dataclasses.replace(ranking_score.DEFAULT_HEURISTICS, activity_bump=1.0),
    )
    assert louder["INJ"] > base["INJ"]
    assert louder["INJ"] - base["INJ"] == pytest.approx(0.5)
    # 그 활동과 무관한 사고유형은 그대로다.
    assert louder["PROP"] == base["PROP"]


# --- 2) 지표 계산이 맞다 -----------------------------------------------------

def test_순서가_그대로면_상관은_1이다():
    order = ["A", "B", "C", "D"]
    assert rs.kendall_tau(order, order) == 1.0
    assert rs.spearman(order, order) == 1.0


def test_순서가_완전히_뒤집히면_상관은_마이너스_1이다():
    assert rs.kendall_tau(["A", "B", "C"], ["C", "B", "A"]) == -1.0
    assert rs.spearman(["A", "B", "C"], ["C", "B", "A"]) == -1.0


def test_이웃_두_개만_바뀌면_손으로_센_값과_같다():
    """4개 중 한 쌍만 어긋난다 → 일치 5, 불일치 1 → tau = (5-1)/6."""
    base = ["A", "B", "C", "D"]
    moved = ["B", "A", "C", "D"]
    assert rs.kendall_tau(base, moved) == pytest.approx(4 / 6)
    # Spearman: d^2 합이 2, n=4 → 1 - 6*2/(4*15)
    assert rs.spearman(base, moved) == pytest.approx(1 - 12 / 60)


def test_항목_집합이_다르면_상관을_내지_않는다():
    """등급 때문에 보험사가 빠지는 경우가 있다. 그때 억지로 숫자를 만들면 거짓말이 된다."""
    assert rs.kendall_tau(["A", "B"], ["A", "C"]) is None
    assert rs.spearman(["A", "B"], ["A", "C"]) is None


def test_비교_결과가_Top1과_Top3를_제대로_본다():
    base = ["A", "B", "C", "D"]
    result = rs.compare(base, ["A", "C", "B", "D"])
    assert result["top1_kept"] is True
    assert result["top3_set_kept"] is True      # 구성은 그대로
    assert result["top3_order_kept"] is False   # 순서는 바뀌었다
    assert result["max_abs_rank_change"] == 1

    flipped = rs.compare(base, ["D", "B", "C", "A"])
    assert flipped["top1_kept"] is False
    assert flipped["top3_set_kept"] is False
    assert flipped["max_abs_rank_change"] == 3


# --- 3) 시나리오를 골라내지 않았다 -------------------------------------------

def test_시나리오는_계수가_안_걸리는_경우까지_포함한다():
    """좋은 결과가 나오는 시나리오만 남기면 분석이 아무 말도 하지 않는 것과 같다.
    계수가 거의 안 걸리는 경우와 전부 걸리는 경우가 둘 다 있어야 한다."""
    keys = {s.key for s in rs.SCENARIOS}
    assert "plain" in keys, "계수가 거의 안 걸리는 시나리오가 빠졌습니다"
    assert "everything" in keys, "계수가 전부 걸리는 시나리오가 빠졌습니다"
    assert len(rs.SCENARIOS) >= 6

    # 서비스가 실제로 쓰는 비교 기준을 한 종류만 보지 않는다.
    tiers = {s.tier for s in rs.SCENARIOS}
    assert len(tiers) >= 3
    # 등급도 세 자리를 모두 밟는다 — 등급마다 보장금액이 달라 순위가 달라질 수 있다.
    assert {s.plan_tier for s in rs.SCENARIOS} == {0, 1, 2}


def test_흔드는_계수_목록이_실제_계수와_어긋나지_않는다():
    """계수를 새로 추가했는데 분석 목록에 넣는 걸 잊으면, 그 계수는 영영 안 재진다."""
    import dataclasses

    fields = {f.name for f in dataclasses.fields(ranking_score.Heuristics)}
    # 비율로 흔들지 않기로 한 정수 문턱값만 빠져 있어야 한다.
    assert set(rs.PERTURBABLE) | {"long_trip_days", "senior_age"} == fields
