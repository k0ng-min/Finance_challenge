from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models.kb import (
    Clause, ClauseIncidentMap, Coverage, IncidentType, Insurer, InsurerPremium, PolicyVersion, Product,
)
from app.schemas import (
    ClauseOut, ClauseTermOut, InsurerCoverageOut, InsurerIncidentCoverageOut, InsurerTierOut, InsurerRankingOut,
    InsurerPremiumCurveOut, InsurerPremiumOut, PremiumComparisonOut, PremiumPointOut,
)
from app.services.insurer_ranking import list_tiers, rank_insurers

router = APIRouter(prefix="/insurers", tags=["insurers"])

_RELEVANCE_ORDER = {"직접": 0, "조건부": 1, "면책": 2}


def _latest_policy_version(db: Session, insurer_code: str) -> tuple[Insurer, PolicyVersion | None]:
    insurer = db.query(Insurer).filter(Insurer.code == insurer_code.upper()).first()
    if not insurer:
        raise HTTPException(status_code=404, detail="보험사를 찾을 수 없습니다.")
    product = db.query(Product).filter(Product.insurer_id == insurer.insurer_id).first()
    if not product:
        return insurer, None
    policy_version = (
        db.query(PolicyVersion)
        .filter(PolicyVersion.product_id == product.product_id)
        .order_by(PolicyVersion.effective_date.desc().nullslast())
        .first()
    )
    return insurer, policy_version


@router.get("/ranking-tiers", response_model=list[InsurerTierOut])
def get_ranking_tiers():
    return list_tiers()


@router.get("/premiums", response_model=PremiumComparisonOut)
def get_premium_comparison(age: int, sex: str, days: int = 1, order: str = "asc", db: Session = Depends(get_db)):
    """해당 나이·성별의 6개사 예시 보험료를 낮은 순으로 비교해서 돌려준다.

    이 숫자는 약관에서 뽑은 값이 아니라 보험다모아 비교공시에서 수집한 값이므로,
    산출 전제(basis)와 출처·수집일을 항상 같이 내려보낸다. 화면에서 숫자만 떼어
    보여주지 않기 위한 것이다.

    해당 나이가 가입연령 범위 밖이라 비교공시에 아예 나오지 않는 보험사는
    unavailable_insurers로 따로 알려준다 — 조용히 빠뜨리면 "그 보험사는 더 싼가?"
    하는 오해를 만든다."""
    sex = sex.upper()
    if sex not in ("M", "F"):
        raise HTTPException(status_code=400, detail="성별은 M 또는 F여야 합니다.")

    if days < 1:
        days = 1
    direction = InsurerPremium.premium.desc() if order == "desc" else InsurerPremium.premium.asc()
    rows = (
        db.query(InsurerPremium)
        .filter(InsurerPremium.age == age, InsurerPremium.sex == sex)
        .order_by(direction)
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="해당 나이·성별의 보험료 자료가 없습니다.")

    covered = {r.insurer_id for r in rows}
    unavailable = [
        i.name for i in db.query(Insurer).all()
        if i.insurer_id not in covered
        and db.query(InsurerPremium).filter(InsurerPremium.insurer_id == i.insurer_id).first() is not None
    ]

    first = rows[0]
    return PremiumComparisonOut(
        age=age, sex=sex,
        basis=first.basis, source=first.source, source_url=first.source_url,
        collected_at=first.collected_at,
        days=days,
        items=[
            InsurerPremiumOut(
                insurer_code=r.insurer.code, insurer_name=r.insurer.name,
                product_name=r.product_name, premium=r.premium,
                premium_total=r.premium * days, age_range=r.age_range,
            )
            for r in rows
        ],
        unavailable_insurers=unavailable,
    )


@router.get("/{insurer_code}/premiums", response_model=InsurerPremiumCurveOut)
def get_insurer_premium_curve(insurer_code: str, sex: str, db: Session = Depends(get_db)):
    """한 보험사의 나이별 보험료 곡선. 나이가 오를수록 보험료가 어떻게 뛰는지 보여주는 용도."""
    sex = sex.upper()
    if sex not in ("M", "F"):
        raise HTTPException(status_code=400, detail="성별은 M 또는 F여야 합니다.")

    insurer = db.query(Insurer).filter(Insurer.code == insurer_code.upper()).first()
    if not insurer:
        raise HTTPException(status_code=404, detail="보험사를 찾을 수 없습니다.")

    rows = (
        db.query(InsurerPremium)
        .filter(InsurerPremium.insurer_id == insurer.insurer_id, InsurerPremium.sex == sex)
        .order_by(InsurerPremium.age.asc())
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="해당 보험사의 보험료 자료가 없습니다.")

    return InsurerPremiumCurveOut(
        insurer_code=insurer.code, insurer_name=insurer.name,
        product_name=rows[0].product_name, sex=sex,
        points=[PremiumPointOut(age=r.age, premium=r.premium) for r in rows],
    )


@router.get("/{insurer_code}/coverages", response_model=list[InsurerCoverageOut])
def get_insurer_coverages(insurer_code: str, db: Session = Depends(get_db)):
    """해당 보험사가 실제로 파는 상품의 담보 목록(약관 원문 기준)을 그대로 돌려준다.
    보험 등록 시 사용자가 담보명을 자유 입력해 퍼지 매칭하는 대신, 이 목록에서 실제로
    가입한 담보를 그대로 고르게 해서 근거 없는 매칭을 원천적으로 없앤다."""
    insurer, policy_version = _latest_policy_version(db, insurer_code)
    if not policy_version:
        return []
    coverages = (
        db.query(Coverage)
        .filter(Coverage.policy_version_id == policy_version.policy_version_id)
        .all()
    )
    return [
        InsurerCoverageOut(
            coverage_id=c.coverage_id,
            std_code=c.coverage_std.std_code if c.coverage_std else None,
            std_name=c.coverage_std.std_name if c.coverage_std else None,
            raw_name=c.raw_name,
            definition=c.definition,
            limit_amount=c.limit_amount,
            deductible=c.deductible,
        )
        for c in coverages
    ]


@router.get("/{insurer_code}/incident-types/{type_id}/coverages", response_model=list[InsurerIncidentCoverageOut])
def get_insurer_coverages_for_incident_type(insurer_code: str, type_id: int, db: Session = Depends(get_db)):
    """가입 전 화면에서 "이 보험사는 [사고유형]을 실제로 어떻게 보상하나"를 바로 보여주기
    위한 조회. 사용자가 등록한 보험(user_policy)이 아직 없는 단계이므로, 그 보험사가 파는
    상품의 KB(약관 원문) 자체에서 직접 찾는다 — claim_review.py의 사고 후 청구검토와 같은
    "직접/조건부/면책" 판단 로직을 재사용하되, 사용자 소유 담보가 아니라 보험사 전체 담보를
    대상으로 한다는 점만 다르다.

    type_id는 L1 대분류(예: INJ) 행을 받는다 — 실제 clause_incident_map 매핑은 전부 L2
    소분류에 걸려 있으므로, 그 L1의 자식 L2 전부를 함께 조회 대상에 넣는다."""
    insurer, policy_version = _latest_policy_version(db, insurer_code)
    if not policy_version:
        return []
    root = db.get(IncidentType, type_id)
    if not root:
        raise HTTPException(status_code=404, detail="사고유형을 찾을 수 없습니다.")
    type_ids = [root.type_id] + [c.type_id for c in root.children]

    maps = (
        db.query(ClauseIncidentMap)
        .join(Clause, Clause.clause_id == ClauseIncidentMap.clause_id)
        .join(Coverage, Coverage.coverage_id == Clause.coverage_id)
        .filter(Coverage.policy_version_id == policy_version.policy_version_id, ClauseIncidentMap.type_id.in_(type_ids))
        .all()
    )

    by_coverage: dict[int, list[ClauseIncidentMap]] = {}
    for m in maps:
        by_coverage.setdefault(m.clause.coverage_id, []).append(m)

    result: list[InsurerIncidentCoverageOut] = []
    for coverage_id, cov_maps in by_coverage.items():
        ranked = sorted(cov_maps, key=lambda m: _RELEVANCE_ORDER.get(m.relevance, 9))
        best_relevance = ranked[0].relevance
        seen_clause_ids: set[int] = set()
        clauses: list[ClauseOut] = []
        for m in ranked:
            if m.clause_id in seen_clause_ids:
                continue
            seen_clause_ids.add(m.clause_id)
            c = m.clause
            clauses.append(ClauseOut(
                clause_id=c.clause_id, article_no=c.article_no, text=c.text,
                page_ref=c.page_ref, default_color=c.default_color, highlight_color=c.default_color,
                terms=[ClauseTermOut.model_validate(t) for t in c.terms],
            ))
        cov = ranked[0].clause.coverage
        result.append(InsurerIncidentCoverageOut(
            coverage_id=coverage_id, coverage_name=cov.raw_name, relevance=best_relevance,
            limit_amount=cov.limit_amount, clauses=clauses,
        ))

    result.sort(key=lambda r: _RELEVANCE_ORDER.get(r.relevance, 9))
    return result


@router.get("/ranking", response_model=InsurerRankingOut)
@limiter.limit("20/minute")
def get_insurer_ranking(
    request: Request,
    tier: str,
    destination: str | None = None,
    risk_level: str | None = None,
    trip_days: int | None = None,
    activities: str | None = None,  # 쉼표로 구분된 문자열로 받는다
    coverage_priority: str | None = None,  # 쉼표로 구분된 문자열로 받는다
    age: int | None = None,
    sex: str | None = None,
    db: Session = Depends(get_db),
):
    trip_context = None
    if destination or risk_level or trip_days or activities or coverage_priority:
        trip_context = {
            "destination": destination,
            "risk_level": risk_level,
            "trip_days": trip_days,
            "activities": [a.strip() for a in activities.split(",") if a.strip()] if activities else [],
            "coverage_priority": [p.strip() for p in coverage_priority.split(",") if p.strip()] if coverage_priority else [],
        }
    try:
        ranking = rank_insurers(db, tier, trip_context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 나이·성별을 함께 받았으면 순위 카드에 바로 보여줄 예시 보험료를 붙인다. 순위·점수 자체는
    # 건드리지 않는다 — 보험료는 약관 근거가 아니라 외부 비교공시 값이므로 순위 산정에 섞지 않는다.
    if age is not None and sex:
        sex = sex.upper()
        if sex in ("M", "F"):
            rows = (
                db.query(InsurerPremium)
                .filter(InsurerPremium.age == age, InsurerPremium.sex == sex)
                .all()
            )
            by_id = {r.insurer_id: r for r in rows}
            code_to_row = {}
            for insurer in db.query(Insurer).all():
                row = by_id.get(insurer.insurer_id)
                if row:
                    code_to_row[insurer.code] = row
            days = trip_days if trip_days and trip_days > 0 else 1
            for item in ranking:
                row = code_to_row.get(item["insurer_code"])
                if row:
                    item["premium"] = row.premium
                    item["premium_days"] = days
                    item["premium_total"] = row.premium * days
                    item["premium_note"] = row.basis
                else:
                    item["premium"] = None
                    item["premium_total"] = None
                    item["premium_days"] = days
                    item["premium_note"] = "이 나이·성별은 가입연령 범위 밖이에요"

    return InsurerRankingOut(tier_code=tier, ranking=ranking)
