"""사고 시뮬레이션 시나리오 시드(L1 단위).

시나리오는 L1 대분류에만 걸린다. L2 세분화는 화면에서 사용자가 직접 고른다 —
시뮬레이션에는 자유서술이 없어 L2를 추론할 근거가 없기 때문이다(추측하지 않는다).

선정 조건을 코드 분기가 아니라 행으로 두므로, 시나리오가 늘어도 services/simulation.py의
선정 로직은 늘어나지 않는다(seed_overlap_rules와 같은 원칙).

위험활동 시나리오는 services/rules.py의 RISKY_ACTIVITY_KEYWORDS에서 그대로 생성한다.
그 목록의 10개 키워드는 전부 6개사 약관 조항 원문에 실제로 등장하므로(면책 매핑 24건),
claim_review._activity_matches_waiver가 실제로 발동해서 "이 활동은 약관에 면책으로
명시돼 있다"가 조항 원문과 함께 나온다. 목록을 여기 다시 적지 않고 import하는 이유는,
한쪽만 바뀌어 서로 어긋나는 것을 막기 위해서다.
"""
import json

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.kb import IncidentType, SimulationScenario
from app.services.rules import RISKY_ACTIVITY_KEYWORDS

# (code, title, narrative, l1_code, modifiers, require_activity, require_rental_car,
#  require_alert_nationwide, sort_order)
BASE_SCENARIOS = [
    (
        "RENTAL_CAR_LIABILITY", "렌터카로 남의 차를 들이받았다면",
        "렌터카를 몰다 주차장에서 다른 차량의 문을 긁어, 상대방이 수리비를 청구했습니다.",
        "LIA", None, None, True, None, 20,
    ),
    (
        "UNREST", "현지 소요 사태에 휘말렸다면",
        "체류 중 도심에서 시위·소요가 벌어져 이동이 막히고 다치는 사람이 나왔습니다.",
        "SPC", None, None, None, True, 30,
    ),
    (
        "ILLNESS", "갑자기 아파서 병원에 갔다면",
        "여행 중 고열과 복통으로 현지 병원 응급실을 찾아 진료를 받았습니다.",
        "ILL", None, None, None, None, 40,
    ),
    (
        "THEFT", "가방을 도난당했다면",
        "카페에서 잠시 자리를 비운 사이 가방을 통째로 도난당했습니다.",
        "PROP", None, None, None, None, 50,
    ),
    (
        "FLIGHT_DELAY", "항공기가 오래 지연됐다면",
        "귀국편 항공기가 기상 문제로 예정보다 여러 시간 늦게 출발했습니다.",
        "TRV", None, None, None, None, 60,
    ),
]


def _risky_scenarios():
    """위험활동 키워드마다 상해(INJ) 시나리오 한 행씩.

    실제로는 여행에 적힌 활동과 맞는 한 건만 화면에 뜬다(services/simulation.py에서
    위험활동 시나리오는 최대 1건으로 줄인다) — '등반'이 '전문등반'의 부분 문자열이라
    둘이 동시에 걸리는 경우가 있기 때문이다.
    """
    rows = []
    for i, kw in enumerate(RISKY_ACTIVITY_KEYWORDS):
        rows.append((
            f"RISKY_{kw}", f"{kw} 중에 다쳤다면",
            f"여행에 적어두신 {kw} 도중 다쳐서 현지 병원에서 치료를 받았습니다.",
            "INJ", json.dumps({"activity": kw}, ensure_ascii=False), kw, None, None, 10 + i,
        ))
    return rows


def seed(db: Session) -> int:
    l1_by_code = {
        t.l1_code: t for t in
        db.query(IncidentType).filter(IncidentType.parent_id.is_(None)).all()
    }
    if not l1_by_code:
        raise ValueError("incident_type(L1)이 비어 있습니다. seed_incident_types를 먼저 실행하세요.")

    existing = {s.code for s in db.query(SimulationScenario).all()}
    added = 0
    for (code, title, narrative, l1_code, modifiers, activity,
         rental_car, alert_nationwide, order) in _risky_scenarios() + BASE_SCENARIOS:
        if code in existing:
            continue
        l1 = l1_by_code.get(l1_code)
        if l1 is None:
            raise ValueError(f"'{code}'가 가리키는 L1 '{l1_code}'를 찾을 수 없습니다.")
        db.add(SimulationScenario(
            code=code, title=title, narrative=narrative, type_id=l1.type_id,
            modifiers=modifiers, require_activity=activity,
            require_rental_car=rental_car, require_alert_nationwide=alert_nationwide,
            sort_order=order,
        ))
        added += 1
    return added


if __name__ == "__main__":
    session = SessionLocal()
    try:
        count = seed(session)
        session.commit()
        print(f"simulation_scenario {count}건 추가")
    finally:
        session.close()
