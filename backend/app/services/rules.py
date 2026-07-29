"""
가입 전 추천 규칙 엔진 (ne.md 11.2 규칙 엔진 역할 / 7.4 능동형 질문과 별개의 결정적 로직).

이 모듈은 LLM을 쓰지 않는다. 여행정보(구조화된 값)를 받아 KB의 coverage/clause와
결정적으로 매칭한다. 근거 clause가 없는 항목은 절대 '추천'으로 만들지 않고
finding_type='보장공백', status='확인불가'로만 표시한다 (new.md finding_evidence_link 규칙).

5개 보험사(삼성화재/현대해상/메리츠화재/KB손보/DB손보)가 각자 다른 약관 문구를 갖고
있으므로(ne.md가 강조한 지점), 표준담보 1건당 삼성화재 것 하나만 보여주지 않고 KB에
적재된 모든 보험사의 대응 담보를 나란히 비교 대상으로 낸다.
"""
from sqlalchemy.orm import Session

from app.models.kb import Coverage, CoverageStd, Clause, Product, PolicyVersion, Insurer

# 삼성화재 약관 제5조 2항에 열거된 위험행위 목록(원문 근거: clause article_no='제5조(보험금을 지급하지 않는 사유)')
RISKY_ACTIVITY_KEYWORDS = [
    "전문등반", "등반", "암벽", "빙벽", "글라이더", "스카이다이빙",
    "스쿠버다이빙", "행글라이딩", "패러글라이딩", "수상보트",
]

# MVP KB에 존재하지 않는(=시드되지 않은) 대분류. 근거 없이 추천하지 않기 위해 명시적으로 '확인불가' 처리한다.
NOT_YET_IN_KB = [
    ("질병의료비", "해외여행 중 질병으로 인한 의료비 (해외발생 질병의료비 특약)"),
    ("휴대품손해", "여행중 휴대품손해(분실제외) 특약"),
    ("배상책임", "여행중 배상책임 특약"),
    ("항공기지연", "항공기 및 수하물 지연·결항 추가비용 특약"),
]


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
        "trip_days": trip_days,
        "purpose": purpose,
        "activities": activities,
        "companion_type": companion_type,
        "rental_car": rental_car,
        "risky_activity_detected": risky_hits,
        "risk_level": "높음" if risky_hits else ("보통" if trip_days and trip_days >= 7 else "낮음"),
    }


def _coverages_with_clauses(db: Session, std_code: str, clause_types: list[str]):
    """std_code에 해당하는 모든 보험사의 coverage를 (insurer, coverage, clauses) 리스트로 반환."""
    rows = (
        db.query(Insurer, Coverage)
        .join(PolicyVersion, Coverage.policy_version_id == PolicyVersion.policy_version_id)
        .join(Product, PolicyVersion.product_id == Product.product_id)
        .join(Insurer, Product.insurer_id == Insurer.insurer_id)
        .join(CoverageStd, Coverage.coverage_std_id == CoverageStd.coverage_std_id)
        .filter(CoverageStd.std_code == std_code)
        .order_by(Insurer.code)
        .all()
    )
    result = []
    for insurer, cov in rows:
        clauses = (
            db.query(Clause)
            .filter(Clause.coverage_id == cov.coverage_id, Clause.clause_type.in_(clause_types))
            .all()
        )
        result.append((insurer, cov, clauses))
    return result


def generate_pre_trip_findings(db: Session, risk_profile: dict) -> list[dict]:
    """
    반환 형식: [{finding_type, status, target_ref, insurer_code, insurer_name,
                 description, confidence, evidence: [(clause, highlight_color)]}]
    """
    findings: list[dict] = []
    risky_hits = risk_profile["risky_activity_detected"]

    # 1. 기본 담보: 상해사망·후유장해 (보험사별 비교)
    for insurer, cov, clauses in _coverages_with_clauses(db, "DEATH_INJURY", ["보장정의"]):
        if not clauses:
            continue
        findings.append({
            "finding_type": "추천담보",
            "status": "우선 검토 대상",
            "target_ref": cov.raw_name,
            "insurer_code": insurer.code,
            "insurer_name": insurer.name,
            "description": (
                f"[{insurer.name}] 해외여행 중 상해로 인한 사망·후유장해를 보장하는 기본 담보입니다. "
                "해외여행자보험 가입 시 가장 먼저 검토해야 하는 보장항목입니다."
            ),
            "confidence": "높음",
            "evidence": [(c, c.default_color) for c in clauses],
        })

    # 2. 기본 담보: 해외 상해의료비 (보험사별 비교)
    for insurer, cov, clauses in _coverages_with_clauses(db, "OVS_INJ_MED", ["보장정의"]):
        if not clauses:
            continue
        findings.append({
            "finding_type": "추천담보",
            "status": "우선 검토 대상",
            "target_ref": cov.raw_name,
            "insurer_code": insurer.code,
            "insurer_name": insurer.name,
            "description": (
                f"[{insurer.name}] 해외 의료기관에서 상해 치료를 받을 경우 실제 부담한 의료비를 보상하는 "
                f"담보입니다. 여행지({risk_profile['destination']})의 의료비 수준을 고려할 때 우선 검토가 "
                "필요합니다."
            ),
            "confidence": "높음",
            "evidence": [(c, c.default_color) for c in clauses],
        })

    # 3. 조건부 담보: 구조송환비용 (활동 위험도에 따라 confidence 차등, 보험사별 비교)
    for insurer, cov, clauses in _coverages_with_clauses(db, "RESCUE", ["보장정의"]):
        if not clauses:
            continue
        if risky_hits:
            desc = (
                f"[{insurer.name}] 여행 활동에 {', '.join(risky_hits)} 등 조난·구조 위험이 있는 활동이 "
                "포함되어 있어, 사고 시 수색구조비용·이송비용 부담이 커질 수 있는 담보입니다. 우선 검토를 "
                "권장합니다."
            )
            confidence = "높음"
        else:
            desc = (
                f"[{insurer.name}] 현재 입력된 활동만으로는 조난 위험이 높지 않으나, 해외 사고 발생 시 "
                "수색구조·이송 비용은 고액인 경우가 많아 보장 공백 방지 차원에서 검토를 권장하는 담보입니다."
            )
            confidence = "보통"
        findings.append({
            "finding_type": "추천담보",
            "status": "우선 검토 대상",
            "target_ref": cov.raw_name,
            "insurer_code": insurer.code,
            "insurer_name": insurer.name,
            "description": desc,
            "confidence": confidence,
            "evidence": [(c, c.default_color) for c in clauses],
        })

    # 4. 제한조건 경고: 위험행위 면책 (실제로 입력된 활동이 면책 대상에 해당할 때만, 보험사별 비교)
    if risky_hits:
        for std_code in ("DEATH_INJURY", "OVS_INJ_MED"):
            for insurer, cov, clauses in _coverages_with_clauses(db, std_code, ["면책"]):
                if not clauses:
                    continue
                findings.append({
                    "finding_type": "제한조건",
                    "status": "추가 확인 필요",
                    "target_ref": cov.raw_name,
                    "insurer_code": insurer.code,
                    "insurer_name": insurer.name,
                    "description": (
                        f"[{insurer.name}] 입력하신 활동({', '.join(risky_hits)})은 약관상 직업·직무·동호회 "
                        "활동 목적의 위험행위로 분류되어 별도 약정이 없으면 상해 관련 보험금이 지급되지 않을 수 "
                        "있는 조항입니다. 가입 전 보험사에 해당 활동의 보장 여부를 반드시 확인해야 합니다."
                    ),
                    "confidence": "높음",
                    "evidence": [(c, c.default_color) for c in clauses],
                })

    # 5. 보장 공백: KB에 아직 없는 담보는 절대 추천하지 않고 '확인불가'로 명시 (보험사 무관, 공통 1건)
    for label, note in NOT_YET_IN_KB:
        findings.append({
            "finding_type": "보장공백",
            "status": "확인불가",
            "target_ref": label,
            "insurer_code": None,
            "insurer_name": None,
            "description": (
                f"{note}은(는) 현재 시스템 KB에 약관이 적재되지 않아 적합도를 판단할 근거가 없습니다. "
                "필요 시 보험사 원문 약관을 별도로 확인하십시오."
            ),
            "confidence": None,
            "evidence": [],
        })

    return findings
