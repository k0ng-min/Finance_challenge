"""여행경보 조회와, 그 경보를 약관 면책 조항에 잇는 로직.

지키는 경계가 하나 있다. **경보 단계 자체는 보상 여부의 근거가 아니다.** 외교부 자료와
보험 약관은 출처가 다르므로, 경보가 높다고 "보상되지 않는다"고 말하지 않는다. 대신
"이 보험사 약관에 전쟁·내란 지역 면책 조항이 있다"는 사실을 조항 원문과 함께 알린다.
판단은 언제나 약관 원문이 하고, 경보는 그 조항을 꺼내볼 이유가 되는 데까지만 쓴다.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.kb import (
    Clause, ClauseIncidentMap, Coverage, IncidentType, Insurer, PolicyVersion, Product, TravelAlert,
)

LEVEL_LABELS = {1: "여행유의", 2: "여행자제", 3: "출국권고", 4: "여행금지"}

# 이 단계부터 약관 면책 조항을 함께 보여준다. 1·2단계는 배지로만 알린다 —
# 여행유의·자제는 대부분의 나라에 붙어 있어서, 그때마다 면책을 꺼내면 경고가 무의미해진다.
CLAUSE_FROM_LEVEL = 3

# 전쟁·내란·테러 면책을 담고 있는 사고유형. 이미 6개사 조항이 매핑돼 있어 그대로 쓴다.
WAR_TERROR_L2 = "SPC_WAR_TERROR"


@dataclass
class AlertInfo:
    country_name: str
    level: int
    label: str
    region_type: str | None
    note: str | None
    issued_on: str | None
    source: str | None
    source_url: str | None


def find_alert(db: Session, destination: str | None) -> AlertInfo | None:
    """목적지의 여행경보. 자료에 없는 나라면 None — 추측하지 않는다."""
    if not destination:
        return None
    row = (
        db.query(TravelAlert)
        .filter(TravelAlert.country_name == destination.strip())
        .order_by(TravelAlert.level.desc())
        .first()
    )
    if row is None:
        return None
    return AlertInfo(
        country_name=row.country_name,
        level=row.level,
        label=LEVEL_LABELS.get(row.level, str(row.level)),
        region_type=row.region_type,
        note=row.note,
        issued_on=row.issued_on,
        source=row.source,
        source_url=row.source_url,
    )


def war_exclusion_clauses(db: Session):
    """전쟁·테러 면책으로 매핑된 조항을 (보험사, 담보, 조항)으로 돌려준다.

    담보가 아니라 조항 단위로 매핑돼 있어(clause_incident_map) 보험사마다 실제 문구가
    다른 것이 그대로 유지된다 — 어느 회사 약관에 뭐라고 적혀 있는지를 그대로 보여준다.
    """
    return (
        db.query(Insurer, Coverage, Clause)
        .join(Product, Product.insurer_id == Insurer.insurer_id)
        .join(PolicyVersion, PolicyVersion.product_id == Product.product_id)
        .join(Coverage, Coverage.policy_version_id == PolicyVersion.policy_version_id)
        .join(Clause, Clause.coverage_id == Coverage.coverage_id)
        .join(ClauseIncidentMap, ClauseIncidentMap.clause_id == Clause.clause_id)
        .join(IncidentType, IncidentType.type_id == ClauseIncidentMap.type_id)
        .filter(IncidentType.l2_code == WAR_TERROR_L2, ClauseIncidentMap.relevance == "면책")
        .order_by(Insurer.code, Clause.clause_id)
        .all()
    )


def build_alert_findings(db: Session, destination: str | None) -> list[dict]:
    """경보가 높은 지역이면 보험사별 면책 조항을 근거로 제한조건을 만든다.

    반환 형식은 rules.py의 finding과 같다(그대로 같은 저장·표시 경로를 탄다).
    경보가 없거나 낮으면 빈 목록 — 없는 위험을 만들어내지 않는다.
    """
    alert = find_alert(db, destination)
    if alert is None or alert.level < CLAUSE_FROM_LEVEL:
        return []

    findings: list[dict] = []
    seen_insurers: set[str] = set()
    for insurer, coverage, clause in war_exclusion_clauses(db):
        # 보험사당 한 건이면 충분하다 — 같은 취지의 조항이 여러 담보에 반복된다.
        if insurer.code in seen_insurers:
            continue
        seen_insurers.add(insurer.code)

        where = f"{alert.country_name}({alert.region_type})" if alert.region_type else alert.country_name
        findings.append({
            "finding_type": "제한조건",
            "status": "추가 확인 필요",
            "target_ref": coverage.raw_name,
            "insurer_code": insurer.code,
            "insurer_name": insurer.name,
            "description": (
                f"[{insurer.name}] 외교부가 {where}에 여행경보 {alert.level}단계"
                f"({alert.label})를 발령했습니다. 이 보험사 약관에는 전쟁·내란 등으로 생긴 손해를"
                " 보상하지 않는 조항이 있어, 아래 원문을 확인하고 가입 전 보험사에 이 지역이"
                " 보장 범위에 드는지 직접 물어보세요."
            ),
            "coverage_amount": coverage.limit_amount,
            "confidence": "높음",
            "evidence": [(clause, clause.default_color)],
        })
    return findings
