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

주의: 현재 KB에는 보험료(가격) 데이터가 없다. 6개 보험사 실제 약관은 "판매 조건" 문서이지
"요율표"가 아니고, 보험다모아 등 실시간 견적 시스템은 성별·생년월일 입력이 필요한 계산기라
정적으로 가져올 수 없다(직접 검색 확인함). 그래서 숫자 보험료로 순위를 매기지 않는다.
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
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from app.models.kb import Insurer, Product, PolicyVersion, Coverage, Clause, CoverageDocMap

# 의료비 수준이 특히 높다고 널리 알려진 여행지(일반 상식 수준의 지리적 분류이며,
# 보험사별 데이터가 아니다) — 이 목적지일 때 해외상해의료비 관련 신호의 가중치를 높인다.
HIGH_MEDICAL_COST_DESTINATIONS = {"미국", "캐나다", "스위스"}

SCORE_MIN, SCORE_MAX = 60.0, 98.0


@dataclass
class InsurerSignals:
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
    insurers = db.query(Insurer).order_by(Insurer.code).all()
    result = []
    for insurer in insurers:
        sig = InsurerSignals(insurer_code=insurer.code, insurer_name=insurer.name, official_url=insurer.official_url)

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


def _priority_selected(trip_context: dict | None, keyword: str) -> bool:
    if not trip_context:
        return False
    priorities = trip_context.get("coverage_priority") or []
    return any(keyword in p for p in priorities)


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


def rank_insurers(db: Session, tier_code: str, trip_context: dict | None = None) -> list[dict]:
    """순위·점수는 항상 이 함수(규칙 기반)가 결정한다. Gemini는 이 결과를 설명 문장으로만
    다듬을 뿐, 순서나 점수를 바꾸지 못한다(insurer_ranking_gemini.explain_ranking이 검증)."""
    if tier_code not in TIERS:
        raise ValueError(f"알 수 없는 랭킹 유형입니다: {tier_code}")

    score_fn = TIERS[tier_code]["score_fn"]
    signals = _collect_signals(db)
    raw = [score_fn(s, trip_context) for s in signals]
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
