"""가중치 점수 순위 모델의 계약을 고정한다.

원래 불만은 "실속·표준·고급을 아무리 바꿔도 순위가 늘 똑같다"와 "내 여행 준비에서
고른 게 순위에 안 들어간다" 두 가지였다. 이 모델이 지키는 것은 넷이다.

  1. 등급을 올려 금액이 실제로 오르면 점수도 오른다. 금액이 그대로면 점수도 그대로다
     — 차이를 지어내지 않는다.
  2. 여행 준비에서 고른 것(걱정되는 사고유형·활동·기존보험 등)이 가중치로 들어간다.
  3. 자료가 없는 축은 0점이 아니라 "빼고 나머지로 다시 100%"다. 자료가 없다는 이유로
     불리해지지 않는다.
  4. 같은 입력에는 언제나 같은 순서.
"""
import pytest

from app.models.kb import Insurer, InsurerComparisonMetric, InsurerPremium
from app.services import ranking_score


def _insurer(db, code, name=None):
    row = Insurer(code=code, name=name or f"{code}보험")
    db.add(row)
    db.flush()
    return row


def _metric(db, insurer, plan_name, label, amount, category="의료비"):
    db.add(InsurerComparisonMetric(
        insurer_id=insurer.insurer_id, plan_name=plan_name, category=category,
        metric_label=label, value_text=str(amount), unit="만원",
        category_order=1, sort_order=0,
    ))


def _premium(db, insurer, plan_name, amount, sex="M", age=30, period_days=1):
    db.add(InsurerPremium(
        insurer_id=insurer.insurer_id, plan_name=plan_name, sex=sex, age=age,
        premium=amount, period_days=period_days,
    ))


@pytest.fixture
def kb(db_session):
    """세 등급 금액이 실제로 다른 보험사(HYUNDAI)와, 세 등급이 모두 같은 보험사(DB)."""
    hyundai = _insurer(db_session, "HYUNDAI", "현대해상")
    db_ins = _insurer(db_session, "DB", "DB손해보험")
    for plan, amount in [("실속형", 2000), ("표준형", 3000), ("고급형", 5000)]:
        _metric(db_session, hyundai, plan, "해외 상해의료비", amount)
        _metric(db_session, db_ins, plan, "해외 상해의료비", 5000)
    db_session.flush()
    return {"hyundai": hyundai, "db": db_ins}


def _amount(db, code, tier, priority=()):
    weights = ranking_score.incident_weights({"coverage_priority": list(priority)})
    return ranking_score.amount_score(db, code, tier, weights).score


def test_등급을_올려_금액이_실제로_오르면_점수도_오른다(db_session, kb):
    실속 = _amount(db_session, "HYUNDAI", 0)
    표준 = _amount(db_session, "HYUNDAI", 1)
    고급 = _amount(db_session, "HYUNDAI", 2)

    assert 실속 < 표준 < 고급


def test_등급을_올려도_금액이_그대로면_점수도_그대로다(db_session, kb):
    """차이를 지어내지 않는다 — 등급 사이에 실질 차이가 없으면 순서도 같아야 한다."""
    점수 = [_amount(db_session, "DB", tier) for tier in (0, 1, 2)]

    assert 점수[0] == 점수[1] == 점수[2]


def test_걱정되는_사고유형을_고르면_그_유형_항목의_비중이_커진다(db_session):
    """여행 준비에서 고른 게 순위에 실제로 들어가는지."""
    기본 = ranking_score.incident_weights({})
    상해우선 = ranking_score.incident_weights({"coverage_priority": ["INJ"]})

    assert 상해우선["INJ"] > 기본["INJ"]
    assert 상해우선["PROP"] == 기본["PROP"]


def test_가격_자료가_없으면_그_축을_빼고_나머지로_다시_100퍼센트를_맞춘다(db_session, kb):
    """없는 자료를 0점으로 세면 자료가 없다는 이유만으로 순위가 밀린다."""
    _premium(db_session, kb["hyundai"], "표준형", 3000)
    db_session.flush()

    현대 = ranking_score.price_score(db_session, "HYUNDAI", 1, age=30, sex="M", trip_days=1)
    디비 = ranking_score.price_score(db_session, "DB", 1, age=30, sex="M", trip_days=1)

    assert 현대.available is True
    assert 디비.available is False
    assert 디비.score == 0.0  # 점수 자체는 0이지만 비중이 0이라 총점에 안 들어간다


def test_쓸_수_없는_축은_비중에서_빠지고_나머지가_100퍼센트가_된다():
    """Case B: UNKNOWN 축 제거 뒤 남은 가중치 합은 정확히 1이다."""
    axes = {"amount": 0.34, "clause": 0.32, "price": 0.10, "overlap": 0.14, "activity": 0.10}

    적용 = ranking_score.renormalize(axes, unavailable={"price"})

    assert "price" not in 적용
    assert sum(적용.values()) == 1.0
    # 남은 축끼리의 상대 비율은 그대로다.
    assert abs(적용["amount"] / 적용["clause"] - 0.34 / 0.32) < 1e-9


def test_available_false_axis_has_zero_weight_and_contribution(db_session, kb):
    """Case C: 비교 제외 축은 최종점수에 기여하지 않는다."""
    ranking = [{
        "insurer_code": "HYUNDAI",
        "insurer_name": "현대해상",
        "dimensions": [{
            "code": "condition_clarity",
            "level": 0,
            "available": False,
            "comparison_state": "UNKNOWN",
        }],
    }]

    scored = ranking_score.score_insurers(
        db_session, tier_code="균형형", plan_tier=1, trip_context={}, ranking=ranking,
        age=30, sex="M",
    )[0]
    excluded = [axis for axis in scored.axes if not axis.available]

    assert excluded
    assert all(axis.weight == 0.0 for axis in excluded)
    assert all(axis.contribution == 0.0 for axis in excluded)
    assert sum(axis.weight for axis in scored.axes if axis.available) == pytest.approx(1.0)
    assert scored.total == pytest.approx(
        sum(axis.contribution for axis in scored.axes if axis.available)
    )


def test_같은_입력이면_언제나_같은_순서다(db_session, kb):
    ranking = [
        {"insurer_code": "HYUNDAI", "insurer_name": "현대해상", "dimensions": []},
        {"insurer_code": "DB", "insurer_name": "DB손해보험", "dimensions": []},
    ]
    kwargs = dict(tier_code="균형형", plan_tier=1, trip_context={}, ranking=ranking, age=30, sex="M")

    첫번째 = ranking_score.score_insurers(db_session, **kwargs)
    두번째 = ranking_score.score_insurers(db_session, **kwargs)

    assert [s.insurer_code for s in 첫번째] == [s.insurer_code for s in 두번째]
    assert [round(s.total, 6) for s in 첫번째] == [round(s.total, 6) for s in 두번째]


def test_총점은_쓰인_축의_기여도_합과_같다(db_session, kb):
    ranking = [{"insurer_code": "HYUNDAI", "insurer_name": "현대해상", "dimensions": []}]

    scored = ranking_score.score_insurers(
        db_session, tier_code="균형형", plan_tier=1, trip_context={}, ranking=ranking,
        age=30, sex="M",
    )

    총점 = scored[0].total
    기여도합 = sum(axis.contribution for axis in scored[0].axes if axis.available)
    assert abs(총점 - 기여도합) < 1e-6


def test_점수를_섞는_수단_자체가_없다():
    """예전에는 blend()가 결정적 점수와 Gemini 점수를 8:2로 섞어 최종 총점을 만들었고,
    호출부가 그 총점으로 다시 정렬했다 — 모델이 순위를 바꿀 수 있었다. 그 함수를 없앴다.
    다시 생기면 순위가 또 LLM에 묶이므로 여기서 못 박아 둔다."""
    assert not hasattr(ranking_score, "blend"), "점수를 섞는 함수가 되살아났습니다"
    assert not hasattr(ranking_score, "GEMINI_RATIO")
