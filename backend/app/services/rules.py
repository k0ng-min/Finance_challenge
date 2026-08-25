"""
가입 전 추천 규칙 엔진.

이 모듈은 LLM을 쓰지 않는다. 여행정보(구조화된 값)를 받아 KB의 coverage/clause와
결정적으로 매칭한다. 근거 clause가 없는 항목은 절대 '추천'으로 만들지 않고
finding_type='보장공백', status='확인불가'로만 표시한다.

판단축(사고 후 claim_review.py와 동일):
    Trip
     ↓ 사용자가 고른 coverage_priority(= IncidentType L1)
    IncidentType L1 + 그 아래 L2 전체
     ↓
    ClauseIncidentMap
     ↓
    보험사별 Coverage + Clause (직접/조건부/면책)

예전엔 표준담보코드(DEATH_INJURY/OVS_INJ_MED/...)를 이 파일에 하드코딩하고, 삼성화재
약관에서 뽑은 위험행위 키워드 목록으로 "이 활동은 면책"이라고 전 보험사에 똑같이
경고했다. 그래서 그 보험사 약관에 해당 활동이 실제로 적혀 있는지 확인하지 않은 채
단정적인 경고가 나갈 수 있었다. 이제 담보 후보는 조항↔사고유형 매핑에서만 나오고,
활동 면책 경고는 그 보험사 조항 원문에 활동명이 문자 그대로 있을 때만 낸다
(claim_review._activity_matches_waiver와 같은 grounding 규칙).
"""
from sqlalchemy.orm import Session

from app.models.kb import Clause, ClauseIncidentMap, Coverage, IncidentType, Insurer, PolicyVersion, Product
from app.services.claim_review import _activity_matches_waiver

# 사용자가 걱정되는 사고유형을 하나도 고르지 않았을 때 기본으로 훑는 L1.
# 예전 기본 추천 묶음(상해사망·해외상해의료비·휴대품손해·구조송환)과 같은 범위를
# 사고유형 축으로 옮겨놓은 것이다.
DEFAULT_L1_CODES = ("INJ", "ILL", "PROP", "EMG")

# 위험행위 후보를 문장에서 찾아내기 위한 힌트 목록(삼성화재 약관 제5조 2항 열거 항목).
# 이 목록은 risk_profile의 요약값(risk_level 등)에만 쓰고, 면책 경고의 근거로는 절대
# 쓰지 않는다 — 경고는 항상 해당 보험사 조항 원문 대조로만 만든다.
RISKY_ACTIVITY_KEYWORDS = [
    "전문등반", "등반", "암벽", "빙벽", "글라이더", "스카이다이빙",
    "스쿠버다이빙", "행글라이딩", "패러글라이딩", "수상보트",
]

_RELEVANCE_ORDER = {"직접": 0, "조건부": 1, "면책": 2}

# 결과 표시 순서. 사고유형을 여러 개 고르면 담보가 수십 건까지 나올 수 있어서, 근거 있는
# 결과를 버리지는 않되 먼저 봐야 하는 것부터 위로 올린다.
_FINDING_ORDER = {"제한조건": 0, "추천담보": 1, "보장공백": 2}


def _has_risky_activity(activities: list[str], purpose: str) -> list[str]:
    joined = " ".join(activities + [purpose or ""])
    return [kw for kw in RISKY_ACTIVITY_KEYWORDS if kw in joined]


def build_risk_profile(destination: str, start_date, end_date, purpose: str,
                        activities: list[str], companion_type: str | None,
                        rental_car: bool) -> dict:
    trip_days = (end_date - start_date).days + 1 if end_date and start_date else None
    risky_hits = _has_risky_activity(activities, purpose)
    return {
        "destination": destination,
        "start_date": str(start_date) if start_date else None,
        "end_date": str(end_date) if end_date else None,
        "trip_days": trip_days,
        "purpose": purpose,
        "activities": activities,
        "companion_type": companion_type,
        "rental_car": rental_car,
        "risky_activity_detected": risky_hits,
        "risk_level": "높음" if risky_hits else ("보통" if trip_days and trip_days >= 7 else "낮음"),
    }


def _candidate_activities(risk_profile: dict) -> list[str]:
    """면책 조항 원문과 대조해볼 활동 후보. 사용자가 입력한 활동을 그대로 쓰고,
    자유서술(purpose)에서 걸린 위험행위 키워드도 후보에 넣는다. 후보일 뿐이며,
    실제 경고 여부는 조항 원문에 있는지로만 결정된다."""
    activities = [a.strip() for a in (risk_profile.get("activities") or []) if a and a.strip()]
    for hit in risk_profile.get("risky_activity_detected") or []:
        if hit not in activities:
            activities.append(hit)
    return activities


def _grounded_activities(clause_text: str, activities: list[str]) -> list[str]:
    """이 조항 원문에 문자 그대로 등장하는 활동만 남긴다."""
    return [a for a in activities if _activity_matches_waiver(clause_text, {"activity": a})]


def resolve_type_ids(db: Session, l1_codes: list[str]) -> list[int]:
    """L1 코드 목록 → 그 L1 루트와 하위 L2 전체의 type_id.

    incident_type은 L1 루트 행과 L2 행이 모두 l1_code를 들고 있으므로 l1_code로
    한 번에 거른다(사고 후 흐름이 L2까지 내려가 매핑을 다는 것과 같은 범위)."""
    if not l1_codes:
        return []
    rows = (
        db.query(IncidentType)
        .filter(IncidentType.l1_code.in_(l1_codes), IncidentType.is_active.isnot(False))
        .all()
    )
    return [r.type_id for r in rows]


def _l1_names(db: Session, l1_codes: list[str]) -> dict[str, str]:
    """L1 코드 → 한글 표시명(루트 행 기준)."""
    rows = (
        db.query(IncidentType)
        .filter(IncidentType.l1_code.in_(l1_codes), IncidentType.l1_code == IncidentType.l2_code)
        .all()
    )
    return {r.l1_code: r.name for r in rows}


def _coverage_buckets(db: Session, type_ids: list[int]):
    """선택한 사고유형에 매핑된 조항을 (insurer, coverage) 단위로 묶는다.

    조항은 특정 보험사의 특정 PolicyVersion에 속하므로 이 묶음은 보험사별로 독립적이다
    — 다른 보험사가 같은 유형에 매핑돼 있지 않아도 이 보험사 결과에는 영향이 없다."""
    if not type_ids:
        return []
    rows = (
        db.query(Insurer, Coverage, ClauseIncidentMap, Clause)
        .join(Product, Product.insurer_id == Insurer.insurer_id)
        .join(PolicyVersion, PolicyVersion.product_id == Product.product_id)
        .join(Coverage, Coverage.policy_version_id == PolicyVersion.policy_version_id)
        .join(Clause, Clause.coverage_id == Coverage.coverage_id)
        .join(ClauseIncidentMap, ClauseIncidentMap.clause_id == Clause.clause_id)
        .filter(ClauseIncidentMap.type_id.in_(type_ids))
        .order_by(Insurer.code, Coverage.coverage_id)
        .all()
    )
    buckets: dict[int, dict] = {}
    for insurer, cov, cim, clause in rows:
        bucket = buckets.setdefault(cov.coverage_id, {
            "insurer": insurer, "coverage": cov, "links": [],
        })
        bucket["links"].append((cim, clause))
    return list(buckets.values())


def _dedup_clauses(links) -> list[Clause]:
    seen: set[int] = set()
    clauses: list[Clause] = []
    for _cim, clause in links:
        if clause.clause_id in seen:
            continue
        seen.add(clause.clause_id)
        clauses.append(clause)
    return clauses


def generate_pre_trip_findings(db: Session, risk_profile: dict) -> list[dict]:
    """
    반환 형식: [{finding_type, status, target_ref, insurer_code, insurer_name,
                 description, coverage_amount, confidence, evidence: [(clause, highlight_color)]}]
    """
    findings: list[dict] = []
    selected = [c for c in (risk_profile.get("coverage_priority") or []) if c]
    l1_codes = selected or list(DEFAULT_L1_CODES)
    activities = _candidate_activities(risk_profile)
    destination = risk_profile.get("destination") or "여행지"

    type_ids = resolve_type_ids(db, l1_codes)
    names = _l1_names(db, l1_codes)
    covered_l1: set[str] = set()

    for bucket in _coverage_buckets(db, type_ids):
        insurer, cov, links = bucket["insurer"], bucket["coverage"], bucket["links"]
        for cim, _clause in links:
            covered_l1.add(cim.incident_type.l1_code)

        # 이 보험사 조항 원문에 활동명이 실제로 있는 면책 조항만 경고 근거가 된다.
        waiver_links = [
            (cim, clause, _grounded_activities(clause.text, activities))
            for cim, clause in links if cim.relevance == "면책"
        ]
        grounded_waivers = [(cim, clause, hits) for cim, clause, hits in waiver_links if hits]

        if grounded_waivers:
            hits = sorted({h for _cim, _clause, hs in grounded_waivers for h in hs})
            clauses = _dedup_clauses([(cim, clause) for cim, clause, _ in grounded_waivers])
            findings.append({
                "finding_type": "제한조건",
                "status": "추가 확인 필요",
                "target_ref": cov.raw_name,
                "insurer_code": insurer.code,
                "insurer_name": insurer.name,
                "description": (
                    f"[{insurer.name}] '{cov.raw_name}' 약관에서 입력하신 활동({', '.join(hits)})을 "
                    "직접 언급한 면책 조항이 확인됩니다. 별도 약정이 없으면 관련 보험금이 지급되지 "
                    "않을 수 있으니, 가입 전 보험사에 해당 활동의 보장 여부를 확인하세요."
                ),
                "coverage_amount": cov.limit_amount,
                "confidence": "높음",
                "evidence": [(c, c.default_color) for c in clauses],
            })
            continue

        # 면책 근거가 없으면 보장 쪽(직접/조건부) 조항으로 추천을 만든다.
        positive = [(cim, clause) for cim, clause in links if cim.relevance in ("직접", "조건부")]
        if not positive:
            continue
        best = min(positive, key=lambda pair: _RELEVANCE_ORDER.get(pair[0].relevance, 99))[0]
        clauses = _dedup_clauses(positive)
        type_names = sorted({cim.incident_type.name for cim, _ in positive})
        conditional = best.relevance == "조건부"
        findings.append({
            "finding_type": "추천담보",
            "status": "우선 검토 대상" if not conditional else "조건 확인 필요",
            "target_ref": cov.raw_name,
            "insurer_code": insurer.code,
            "insurer_name": insurer.name,
            "description": (
                f"[{insurer.name}] '{cov.raw_name}'은(는) 선택하신 사고유형({', '.join(type_names)})에 "
                f"대응하는 약관 조항이 확인된 담보입니다. 여행지({destination}) 조건과 함께 검토해 보세요."
                + ("" if not conditional else
                   " 다만 이 담보는 추가 요건이 충족될 때만 걸리는 조건부 조항이라 세부 요건을 확인해야 합니다.")
            ),
            "coverage_amount": cov.limit_amount,
            "confidence": "높음" if not conditional else "보통",
            "evidence": [(c, c.default_color) for c in clauses],
        })

    # 고른 사고유형 중 KB에 근거 조항이 하나도 없는 것은 조용히 빠뜨리지 않고 '확인불가'로 남긴다.
    # (예전엔 NOT_YET_IN_KB 상수로 손수 관리했는데, KB가 담보 122건·조항 400여 건으로 늘면서
    #  상수가 실제 DB와 어긋날 수 있어 매번 조회 결과로 판단한다.)
    for code in l1_codes:
        if code in covered_l1:
            continue
        label = names.get(code, code)
        findings.append({
            "finding_type": "보장공백",
            "status": "확인불가",
            "target_ref": label,
            "insurer_code": None,
            "insurer_name": None,
            "description": (
                f"'{label}' 유형은 현재 KB에 적재된 약관에서 대응하는 조항을 찾지 못해 적합도를 "
                "판단할 근거가 없습니다. 필요 시 보험사 원문 약관을 별도로 확인하십시오."
            ),
            "confidence": None,
            "evidence": [],
        })

    # 보험사별 조회 순서는 그대로 두고(같은 종류 안에서는 보험사 코드순) 종류만 앞으로 당긴다.
    findings.sort(key=lambda f: _FINDING_ORDER.get(f["finding_type"], 99))
    return findings
