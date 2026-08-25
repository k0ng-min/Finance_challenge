"""여행경보 조회와, 그 경보를 약관 면책 조항에 잇는 로직.

지키는 경계가 둘 있다.

**경보 단계 자체는 보상 여부의 근거가 아니다.** 외교부 자료와 보험 약관은 출처가 다르므로,
경보가 높다고 "보상되지 않는다"고 말하지 않는다. 대신 "이 보험사 약관에 전쟁·내란 지역
면책 조항이 있다"는 사실을 조항 원문과 함께 알린다. 판단은 언제나 약관 원문이 하고, 경보는
그 조항을 꺼내볼 이유가 되는 데까지만 쓴다.

**경보 범위를 넓혀 말하지 않는다.** 외교부 경보는 국가가 아니라 지역 단위다. 일본의 3단계는
후쿠시마 원전 반경 30km, 필리핀의 4단계는 민다나오 일부다. 이것을 국가 전체 경보로 표시하면
도쿄·세부 여행자에게 출국권고가 뜬다. 그러면 사용자는 경보를 무시하게 되고, 정말 위험한
시리아에서도 똑같이 무시한다. 설계 근거는 docs/superpowers/specs/2026-08-11-travel-alert-region-design.md.
"""
from __future__ import annotations

import re
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

# baseline을 무엇을 보고 정했는지. 화면과 심사 자리에서 판정 근거를 설명할 수 있어야 한다.
BASIS_WHOLE = "전체행"       # region_ty가 '전체'인 행이 있었다
BASIS_REMAINDER = "나머지행"  # "…를 제외한 (전) 지역" 행 중 최저 단계
BASIS_LOCAL = "국지적"        # 둘 다 없다 — 특정 지역에만 경보가 걸린 나라

# "…를 제외한 지역" / "…제외 전 지역" — 경보 지역을 뺀 나머지 전역을 가리키는 문구.
#
# 단순히 '제외'가 들어갔는지만 보면 안 된다. 외교부 문구에는 특정 지역을 서술하면서
# 괄호로 단서를 다는 경우가 많고, 그것까지 "나머지 전역"으로 읽으면 엉뚱한 단계가 잡힌다.
#
#   시리아 3단계 "골란고원 일부(레바논 접경 및 UNDOF 분리선 4km 이내 지역 제외)"
#   러시아 3단계 "북카프카즈 지역(…) 및 우크라이나 접경지역(4단계 제외 로스토프, …)"
#   이집트 3단계 "중•북부 시나이 반도(1,2단계 지역 제외), 리비아 국경으로부터 30km까지"
#
# 이것들을 나머지 전역으로 읽으면 시리아 기본단계가 4가 아니라 3이 되고, 모스크바·카이로
# 여행자에게 자동으로 전쟁·내란 면책 조항이 붙는다. '제외' 뒤에 '지역'이 따라오는 형태만
# 나머지 전역으로 본다.
_REMAINDER_PATTERN = re.compile(r"제외한?\s*전?\s*지역")


@dataclass
class AlertRow:
    """경보 한 줄. 나라 전체일 수도 있고 특정 지역일 수도 있다."""
    alert_id: int | None
    level: int
    label: str
    region_type: str | None
    note: str | None
    issued_on: str | None

    def as_dict(self) -> dict:
        return {
            "alert_id": self.alert_id, "level": self.level, "label": self.label,
            "region_type": self.region_type, "note": self.note, "issued_on": self.issued_on,
        }


@dataclass
class CountryAlert:
    """한 나라의 경보를 '일반 지역 단계'와 '지역별 경보'로 나눠 담는다."""
    country_name: str
    baseline: AlertRow | None
    baseline_basis: str
    regions: list[AlertRow]
    source: str | None
    source_url: str | None

    def as_dict(self) -> dict:
        return {
            "country_name": self.country_name,
            "baseline": self.baseline.as_dict() if self.baseline else None,
            "baseline_basis": self.baseline_basis,
            "regions": [r.as_dict() for r in self.regions],
            "source": self.source,
            "source_url": self.source_url,
        }

    def alerting_regions(self) -> list[AlertRow]:
        """방문 여부를 물어볼 만한 지역 — 3단계 이상만."""
        return [r for r in self.regions if r.level >= CLAUSE_FROM_LEVEL]


def _to_row(row: TravelAlert) -> AlertRow:
    return AlertRow(
        alert_id=row.alert_id, level=row.level, label=LEVEL_LABELS.get(row.level, str(row.level)),
        region_type=row.region_type, note=row.note, issued_on=row.issued_on,
    )


def _is_whole_country(row: TravelAlert) -> bool:
    """'전체' / '전 지역' 어느 표기로 와도 나라 전체로 읽는다."""
    return (row.region_type or "").strip().startswith("전")


def _pick_baseline(rows: list[TravelAlert]) -> tuple[TravelAlert | None, str]:
    """그 나라 일반 지역의 단계를 고른다.

    최고 단계를 대표로 쓰면 안 된다 — 일본이 3단계(후쿠시마 30km), 필리핀이 4단계(민다나오
    일부)가 되어버린다. 3·4단계 72개국 중 52개국이 일부 지역 경보라 예외가 아니라 다수다.
    """
    whole = [r for r in rows if _is_whole_country(r)]
    if whole:
        # 정상 데이터라면 한 줄이다. 여러 줄이면 높은 쪽을 쓴다 — 나라 전체에 걸린 경보라
        # 여기서는 낮춰 잡을 이유가 없다.
        return max(whole, key=lambda r: r.level), BASIS_WHOLE

    # "1, 3, 4단계 지역을 제외한 지역"처럼 경보 지역을 뺀 나머지 전역을 가리키는 행.
    # 최저를 쓰는 이유: 이런 행이 여러 개 잡히면 더 좁은 범위를 말하는 쪽이 높은 단계다.
    # 나라 전체에 해당하는 것은 그중 가장 낮은 단계다.
    remainder = [r for r in rows if _REMAINDER_PATTERN.search(r.note or "")]
    if remainder:
        return min(remainder, key=lambda r: r.level), BASIS_REMAINDER

    return None, BASIS_LOCAL


def country_alert(db: Session, destination: str | None) -> CountryAlert | None:
    """목적지의 여행경보. 자료에 없는 나라면 None — 추측하지 않는다."""
    if not destination or not destination.strip():
        return None

    rows = (
        db.query(TravelAlert)
        .filter(TravelAlert.country_name == destination.strip())
        .order_by(TravelAlert.level.desc(), TravelAlert.alert_id)
        .all()
    )
    if not rows:
        return None

    base, basis = _pick_baseline(rows)
    # baseline으로 뽑힌 행은 지역경보에서 뺀다. base가 None이면 모든 행이 지역경보다.
    regions = [_to_row(r) for r in rows if r is not base]

    first = rows[0]
    return CountryAlert(
        country_name=first.country_name,
        baseline=_to_row(base) if base is not None else None,
        baseline_basis=basis,
        regions=regions,
        source=first.source,
        source_url=first.source_url,
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


def _where_text(alert: CountryAlert, row: AlertRow, from_region: bool) -> str:
    """경보가 걸린 곳을 문장에 넣을 형태로. 지역 경보면 어디인지 반드시 밝힌다."""
    if from_region and row.note:
        return f"{alert.country_name}의 {row.note}"
    if row.note and row.region_type and not row.region_type.strip().startswith("전"):
        return f"{alert.country_name}의 {row.note}"
    return alert.country_name


def build_alert_findings(
    db: Session,
    destination: str | None,
    visiting_region_ids: list[int] | None = None,
) -> list[dict]:
    """경보가 높은 곳으로 가면 보험사별 면책 조항을 근거로 제한조건을 만든다.

    두 경우에만 만든다.

    1. 그 나라 일반 지역 단계가 3단계 이상 (시리아·우크라이나 등)
    2. 3·4단계 지역경보가 있고, 사용자가 그 지역에 간다고 직접 체크한 경우 (일본의 후쿠시마 등)

    `visiting_region_ids`는 그 목적지의 지역경보 id만 인정한다 — 다른 나라의 alert_id를
    넣어 면책 카드를 억지로 띄우는 것을 막는다.

    반환 형식은 rules.py의 finding과 같다(그대로 같은 저장·표시 경로를 탄다).
    """
    alert = country_alert(db, destination)
    if alert is None:
        return []

    chosen = set(visiting_region_ids or [])
    triggers: list[tuple[AlertRow, bool]] = []
    if alert.baseline is not None and alert.baseline.level >= CLAUSE_FROM_LEVEL:
        triggers.append((alert.baseline, False))
    for row in alert.alerting_regions():
        if row.alert_id is not None and row.alert_id in chosen:
            triggers.append((row, True))

    if not triggers:
        return []

    # 여러 개가 걸리면 가장 높은 단계를 문장에 쓴다. 근거 조항은 어느 쪽이든 같다.
    row, from_region = max(triggers, key=lambda t: t[0].level)
    where = _where_text(alert, row, from_region)
    visited = "이 지역이 여행 경로에 포함된다고 하셨습니다. " if from_region else ""

    findings: list[dict] = []
    seen_insurers: set[str] = set()
    for insurer, coverage, clause in war_exclusion_clauses(db):
        # 보험사당 한 건이면 충분하다 — 같은 취지의 조항이 여러 담보에 반복된다.
        if insurer.code in seen_insurers:
            continue
        seen_insurers.add(insurer.code)

        findings.append({
            "finding_type": "제한조건",
            "status": "추가 확인 필요",
            "target_ref": coverage.raw_name,
            "insurer_code": insurer.code,
            "insurer_name": insurer.name,
            "description": (
                f"[{insurer.name}] 외교부가 {where}에 여행경보 {row.level}단계"
                f"({row.label})를 발령했습니다. {visited}이 보험사 약관에는 전쟁·내란 등으로"
                " 생긴 손해를 보상하지 않는 조항이 있어, 아래 원문을 확인하고 가입 전"
                " 보험사에 이 지역이 보장 범위에 드는지 직접 물어보세요."
            ),
            "coverage_amount": coverage.limit_amount,
            "confidence": "높음",
            "evidence": [(clause, clause.default_color)],
        })
    return findings
