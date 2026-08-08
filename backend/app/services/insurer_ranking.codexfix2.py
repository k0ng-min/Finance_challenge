"""
보험사 랭킹 엔진.

핵심 원칙: **순위와 점수는 항상 코드(규칙)가 결정하고, 제미나이는 그 순위를 사람 말로
설명하는 역할만 한다.** 순위 산정 자체를 제미나이에게 맡기면 같은 조건에도 결과가
흔들리고 "왜 이 순위인지"가 재현되지 않는다 — 금융 서비스에서는 이게 치명적이다.
그래서 이 파일이 실제 약관 원문에서 확인 가능한 신호 + 여행 조건(trip_context)만으로
결정적으로 점수를 매기고, insurer_ranking_gemini.py는 그 결과를 그대로 받아 설명 문장만
자연어로 다듬는다(순서·점수는 절대 바꾸지 못하게 검증한다).

사용자가 고른 기준(티어)과 여행 조건(목적지·보장우선순위)이 점수에서 가장 큰 비중을
차지하도록, 관련 신호가 매칭될 때 큰 폭의 명시적 가점(±10~20)을 주고, 기본 신호(면책·
조건부 조항 수)는 상대적으로 작은 보정치로만 반영한다. 최종 점수는 항상 60~98 사이로
정규화해서 순위표에 마이너스 점수가 뜨지 않게 한다(점수의 절대값보다 "왜 이 순서인지"가
더 중요하므로, 상대적 우열만 보이면 충분하다).

주의: 보험다모아에서 수집한 7일 표준조건 비교공시 보험료는 별도 테이블에 있지만, 사용자의
실제 여행기간·담보구성·가입금액이 반영된 견적은 아니다. 따라서 이 숫자로 순위를 매기지 않고
랭킹이 확정된 뒤 참고 정보로만 붙인다.
대신 실제 약관 원문에서 보험사마다 실제로 다르게 쓰여 있는 신호만 사용한다:
  - exclusion_count / condition_count: 면책·조건부 조항 수
  - rescue_deductible_selectable: 구조송환비용 자기부담률을 가입자가 직접 선택할 수 있는지
  - rescue_war_excluded: 구조송환비용 면책범위에 전쟁·무력행사까지 포함되는지(좁을수록 유리)
  - rescue_lodging: 구조송환비용에 구원자 숙박비가 포함되는지
  - ovs_deductible_selectable: 해외상해의료비 자기부담금을 가입자가 선택할 수 있는지
  - rescue_flexible_days: 구조송환비용 발동 입원일수 요건을 가입자가 짧게(4·7일 등) 선택할 수 있는지
  - ovs_mandatory_docs: 해외상해의료비 청구 시 필수 제출서류 개수(적을수록 청구가 간편함)

동점이면 보험사 코드 순으로 정렬해 항상 같은 결과가 나오게 한다(임의성 없음).
"""
import math
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from app.models.kb import (
    Insurer, Product, PolicyVersion, Coverage, Clause, ClauseIncidentMap, ClauseTerm, CoverageDocMap, IncidentType,
)
from app.services.kb_provenance import ranking_eligible_insurer_codes

# 의료비 수준이 특히 높다고 널리 알려진 여행지(일반 상식 수준의 지리적 분류이며,
# 보험사별 데이터가 아니다) — 이 목적지일 때 해외상해의료비 관련 신호의 가중치를 높인다.
HIGH_MEDICAL_COST_DESTINATIONS = {"미국", "캐나다", "스위스"}

SCORE_MIN, SCORE_MAX = 60.0, 98.0


@dataclass
class InsurerSignals:
    insurer_id: int
    insurer_code: str
    insurer_name: str
    exclusion_count: int = 0
    condition_count: int = 0
    rescue_deductible_selectable: bool = False
    rescue_war_excluded: bool = False
    rescue_lodging: bool = False
    ovs_deductible_selectable: bool = False
    ovs_full_reimbursement: bool = False
    rescue_flexible_days: bool = False
    ovs_mandatory_docs: int = 0
    official_url: str | None = None
    reasons: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


def _collect_signals(db: Session) -> list[InsurerSignals]:
    eligible_codes = ranking_eligible_insurer_codes()
    insurers = (
        db.query(Insurer)
        .filter(Insurer.code.in_(eligible_codes))
        .order_by(Insurer.code)
        .all()
    )
    result = []
    for insurer in insurers:
        sig = InsurerSignals(
            insurer_id=insurer.insurer_id, insurer_code=insurer.code, insurer_name=insurer.name,
            official_url=insurer.official_url,
        )

        coverages = (
            db.query(Coverage)
            .join(PolicyVersion, Coverage.policy_version_id == PolicyVersion.policy_version_id)
            .join(Product, PolicyVersion.product_id == Product.product_id)
            .filter(Product.insurer_id == insurer.insurer_id)
            .all()
        )
        for cov in coverages:
            clauses = db.query(Clause).filter(Clause.coverage_id == cov.coverage_id).all()
            sig.exclusion_count += sum(1 for c in clauses if c.clause_type == "면책")
            sig.condition_count += sum(1 for c in clauses if c.clause_type == "조건")

            if cov.coverage_std and cov.coverage_std.std_code == "RESCUE":
                if cov.deductible and "선택" in cov.deductible:
                    sig.rescue_deductible_selectable = True
                if cov.limit_amount and "숙박비" in cov.limit_amount:
                    sig.rescue_lodging = True
                exclusion_text = " ".join(c.text for c in clauses if c.clause_type == "면책")
                if "전쟁" in exclusion_text or "무력행사" in exclusion_text:
                    sig.rescue_war_excluded = True
                if cov.waiting_condition and "선택한 일수" in cov.waiting_condition:
                    sig.rescue_flexible_days = True
            if cov.coverage_std and cov.coverage_std.std_code == "OVS_INJ_MED":
                if cov.deductible and "선택" in cov.deductible:
                    sig.ovs_deductible_selectable = True
                if cov.limit_amount and "전액" in cov.limit_amount:
                    sig.ovs_full_reimbursement = True
                sig.ovs_mandatory_docs = db.query(CoverageDocMap).filter(
                    CoverageDocMap.coverage_id == cov.coverage_id, CoverageDocMap.is_mandatory.is_(True)
                ).count()

        sig.reasons = [
            f"면책 조항 {sig.exclusion_count}건 · 조건부 조항 {sig.condition_count}건",
            "구조송환 자기부담률을 가입자가 직접 선택 가능" if sig.rescue_deductible_selectable else "구조송환 자기부담률 선택 불가(플랜 고정)",
            "구조송환 면책범위에 전쟁·무력행사 포함(면책범위 넓음)" if sig.rescue_war_excluded else "구조송환 면책범위가 상대적으로 좁음(전쟁 관련 면책 없음)",
            "구조송환 시 구원자 숙박비 보장 포함" if sig.rescue_lodging else "구조송환 숙박비 보장 언급 없음",
            "해외상해의료비 자기부담금을 가입자가 선택 가능" if sig.ovs_deductible_selectable else "해외상해의료비 자기부담금 선택 불가/플랜 고정",
            "구조송환 발동 입원일수를 4·7·14일 중 선택 가능(짧게 선택 시 청구가 더 쉬움)" if sig.rescue_flexible_days else "구조송환 발동 입원일수가 14일 등으로 고정",
            f"해외의료비 청구 시 필수서류 {sig.ovs_mandatory_docs}종 필요",
        ]
        # 순위 카드에 짧게 붙일 실제 약관 근거 태그(가격이 아니라 "보장 조건" 사실만).
        sig.tags = [t for t in [
            "실손 의료비 전액 보장" if sig.ovs_full_reimbursement else None,
            "자기부담률 선택 가능" if sig.rescue_deductible_selectable else None,
            "구원자 숙박비 포함" if sig.rescue_lodging else None,
            "전쟁·무력행사도 면책범위 좁음" if not sig.rescue_war_excluded else None,
            "구조송환 입원일수 단축 선택 가능" if sig.rescue_flexible_days else None,
            "필수서류 적어 청구 간편" if sig.ovs_mandatory_docs <= 3 else None,
        ] if t]
        result.append(sig)
    return result


_L1_CODES = {"INJ", "ILL", "PROP", "LIA", "TRV", "CHG", "EMG", "SPC"}
# 내 여행(TripPrep) STEP4에서 이제 "보장 우선순위"를 예전처럼 자유 라벨("의료비" 등)이 아니라
# 사고유형 L1 코드로 고른다. 아래 점수 함수들은 그대로 예전 키워드("구조송환"/"의료비")를
# 쓰므로, 그 키워드가 실제로 어느 L1 코드(들)에 해당하는지만 매핑해서 재사용한다.
_KEYWORD_TO_L1 = {
    "구조송환": {"EMG"},
    "의료비": {"INJ", "ILL"},
}


def _priority_selected(trip_context: dict | None, keyword: str) -> bool:
    if not trip_context:
        return False
    priorities = trip_context.get("coverage_priority") or []
    l1_matches = _KEYWORD_TO_L1.get(keyword, set())
    if any(p in l1_matches for p in priorities):
        return True
    return any(keyword in p for p in priorities)  # 예전 자유 라벨 데이터 호환용 폴백


def _high_medical_cost(trip_context: dict | None) -> bool:
    if not trip_context:
        return False
    return trip_context.get("destination") in HIGH_MEDICAL_COST_DESTINATIONS


# 각 점수 함수: 기본 신호는 작은 보정치로, 사용자가 고른 티어·여행조건과 직접 맞아떨어지는
# 신호는 큰 가점(±10~20)으로 반영해서 "사용자가 고른 기준"이 점수를 실제로 주도하게 한다.
def _score_stable(s: InsurerSignals, ctx: dict | None) -> float:
    score = -(s.exclusion_count * 1.5 + s.condition_count * 2)
    if s.rescue_war_excluded:
        score -= 12 if _priority_selected(ctx, "구조송환") else 5
    else:
        score += 6 if _priority_selected(ctx, "구조송환") else 2
    return score


def _score_value(s: InsurerSignals, ctx: dict | None) -> float:
    score = -(s.exclusion_count * 0.5 + s.condition_count * 0.5)
    if s.rescue_deductible_selectable:
        score += 15 if _priority_selected(ctx, "구조송환") else 5
    if s.ovs_deductible_selectable:
        bonus = 15 if _priority_selected(ctx, "의료비") else 5
        if _high_medical_cost(ctx):
            bonus *= 1.4
        score += bonus
    return score


def _score_max(s: InsurerSignals, ctx: dict | None) -> float:
    score = s.condition_count * 0.5
    if s.rescue_lodging:
        score += 15 if _priority_selected(ctx, "구조송환") else 6
    if s.rescue_deductible_selectable:
        score += 5
    if not s.rescue_war_excluded:
        score += 5
    if s.ovs_full_reimbursement and _priority_selected(ctx, "의료비"):
        score += 8
    return score


def _score_easy_claim(s: InsurerSignals, ctx: dict | None) -> float:
    score = -(s.ovs_mandatory_docs * 4)
    if s.rescue_flexible_days:
        score += 18 if _priority_selected(ctx, "구조송환") else 10
    if s.rescue_deductible_selectable:
        score += 6
    return score


def _score_balanced(s: InsurerSignals, ctx: dict | None) -> float:
    return (_score_stable(s, ctx) + _score_value(s, ctx) + _score_max(s, ctx)) / 3


TIERS = {
    "안정형": {
        "label": "안정형",
        "description": "면책·조건부 조항이 적어 보험금 지급 분쟁 소지가 낮은 보험사를 우선합니다.",
        "score_fn": _score_stable,
    },
    "실속형": {
        "label": "실속형",
        "description": "자기부담률을 직접 선택할 수 있는 등 가입자에게 유리한 조건을 우선합니다.",
        "score_fn": _score_value,
    },
    "최대보장형": {
        "label": "최대보장형",
        "description": "구원자 숙박비 지원 등 부가 혜택이 가장 넓은 보험사를 우선합니다.",
        "score_fn": _score_max,
    },
    "간편청구형": {
        "label": "간편청구형",
        "description": "필수 제출서류가 적고 구조송환 발동 요건(입원일수)을 짧게 선택할 수 있어 청구 과정이 간단한 보험사를 우선합니다.",
        "score_fn": _score_easy_claim,
    },
    "균형형": {
        "label": "균형형",
        "description": "안정성·실속·보장범위를 고르게 반영한 균형 잡힌 순위입니다.",
        "score_fn": _score_balanced,
    },
}


def list_tiers() -> list[dict]:
    return [{"tier_code": code, "label": v["label"], "description": v["description"]} for code, v in TIERS.items()]


def _normalize(raw_scores: list[float]) -> list[float]:
    """마이너스 점수가 뜨지 않도록, 순위 안에서의 상대적 우열을 60~98 구간으로 다시 매핑한다."""
    lo, hi = min(raw_scores), max(raw_scores)
    if hi - lo < 1e-9:
        return [round((SCORE_MIN + SCORE_MAX) / 2, 1) for _ in raw_scores]
    return [round(SCORE_MIN + (v - lo) / (hi - lo) * (SCORE_MAX - SCORE_MIN), 1) for v in raw_scores]


_USD_TO_KRW = 1300  # 서로 다른 단위(원/USD)로 적힌 지급한도를 상대적으로 비교하기 위한
                     # 내부용 근사 환율일 뿐이다 — 사용자에게 실제 금액으로 노출하지 않는다.


def _max_payout_for_l1(db: Session, insurer_id: int, l1_codes: set[str]) -> float:
    """이 보험사가 선택된 사고유형(L1)에 대해 실제 약관 원문에서 숫자로 뽑아낸(ClauseTerm)
    지급한도 중 가장 큰 값을 원화 환산으로 돌려준다(비교 가능한 원/USD 단위만 사용).

    많은 담보의 지급한도가 "가입금액 한도"처럼 고정 숫자가 아니라 가입자가 정하는 금액이라
    ClauseTerm에 값이 없는 경우가 흔하다 — 그런 경우는 근거 없는 숫자를 지어내지 않고
    그냥 0(이 신호로는 가점 없음)을 돌려준다."""
    if not l1_codes:
        return 0.0
    type_ids = [t.type_id for t in db.query(IncidentType).filter(IncidentType.l1_code.in_(l1_codes)).all()]
    if not type_ids:
        return 0.0
    terms = (
        db.query(ClauseTerm)
        .join(Clause, Clause.clause_id == ClauseTerm.clause_id)
        .join(Coverage, Coverage.coverage_id == Clause.coverage_id)
        .join(PolicyVersion, PolicyVersion.policy_version_id == Coverage.policy_version_id)
        .join(Product, Product.product_id == PolicyVersion.product_id)
        .join(ClauseIncidentMap, ClauseIncidentMap.clause_id == Clause.clause_id)
        .filter(
            Product.insurer_id == insurer_id,
            ClauseTerm.term_type == "지급한도",
            ClauseTerm.unit.in_(["원", "USD"]),
            ClauseIncidentMap.type_id.in_(type_ids),
            ClauseIncidentMap.relevance == "직접",
        )
        .all()
    )
    best = 0.0
    for t in terms:
        if t.value_num is None:
            continue
        krw = t.value_num * _USD_TO_KRW if t.unit == "USD" else t.value_num
        best = max(best, krw)
    return best


def _incident_type_bonus(db: Session, insurer_id: int, trip_context: dict | None) -> float:
    """선택한 사고유형의 실제 지급한도가 클수록 순위에 완만한 가점을 준다(로그 스케일 —
    한도 차이가 수십~수백 배 나도 점수가 튀지 않게). 비교 가능한 숫자가 아예 없으면
    0(중립)이다 — 근거 없이 특정 보험사를 유·불리하게 만들지 않는다."""
    if not trip_context:
        return 0.0
    l1_codes = {p for p in (trip_context.get("coverage_priority") or []) if p in _L1_CODES}
    if not l1_codes:
        return 0.0
    max_krw = _max_payout_for_l1(db, insurer_id, l1_codes)
    if max_krw <= 0:
        return 0.0
    return min(10.0, math.log10(max_krw + 1) * 1.2)


def rank_insurers(db: Session, tier_code: str, trip_context: dict | None = None) -> list[dict]:
    """순위·점수는 항상 이 함수(규칙 기반)가 결정한다. Gemini는 이 결과를 설명 문장으로만
    다듬을 뿐, 순서나 점수를 바꾸지 못한다(insurer_ranking_gemini.explain_ranking이 검증)."""
    if tier_code not in TIERS:
        raise ValueError(f"알 수 없는 랭킹 유형입니다: {tier_code}")

    score_fn = TIERS[tier_code]["score_fn"]
    signals = _collect_signals(db)
    raw = [
        score_fn(s, trip_context) + _incident_type_bonus(db, s.insurer_id, trip_context)
        for s in signals
    ]
    normalized = _normalize(raw)

    scored = sorted(zip(normalized, signals), key=lambda t: (-t[0], t[1].insurer_code))

    ranking = []
    for i, (score, s) in enumerate(scored):
        ranking.append({
            "rank": i + 1,
            "insurer_code": s.insurer_code,
            "insurer_name": s.insurer_name,
            "score": score,
            "reasons": s.reasons,
            "tags": s.tags,
            "official_url": s.official_url,
        })

    from app.services.insurer_ranking_gemini import explain_ranking
    explained = explain_ranking(db, tier_code, TIERS[tier_code]["label"], TIERS[tier_code]["description"], trip_context, ranking)
    return explained if explained is not None else ranking
