from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models.kb import (
    Clause, ClauseIncidentMap, ClauseStandardMap, ClauseTerm, Coverage, CoverageDocMap, CoverageStd, IncidentType,
    Insurer, InsurerComparisonMetric, InsurerPlanCoverage, InsurerPremium, NonpaymentRate,
    PolicyVersion, Product, StandardClause,
)
from app.schemas import (
    ClauseOut, ClauseTermOut, ComparisonCategoryOut, ComparisonMetricOut, ComparisonMetricValueOut,
    InsurerComparisonOut, InsurerCoverageOut, InsurerIncidentCoverageOut, InsurerStandardComparisonOut,
    InsurerTierOut, InsurerRankingOut, InsurerPlanCoverageOut, InsurerPlanCoverageRowOut, InsurerPlanOut,
    InsurerPlansOut, InsurerPremiumCurveOut, InsurerPremiumOut, KbCheckOut, KbInsurerStatOut,
    KbStatsOut, NonpaymentRateOut,
    NonpaymentRatesOut, PremiumComparisonOut, PremiumPointOut, StandardClauseComparisonOut, StandardClauseOut,
)
from app.services.kb_seed_common import ADMIN_STD_CODES, raw_text_is_grounded
from app.services.insurer_ranking import TIERS, list_tiers, rank_insurers
from app.services.insurer_ranking_explain_gemini import explain_ranking
from app.services import ranking_score
from app.models.external import ExternalPolicy
from app.services.insurer_tiers import TIER_LABELS, plan_name_for_tier

router = APIRouter(prefix="/insurers", tags=["insurers"])

_RELEVANCE_ORDER = {"직접": 0, "조건부": 1, "면책": 2}
def _display_basis(basis: str | None) -> str:
    """원본 조회 전제를 기간 변환 없이 그대로 표시한다."""
    return basis or ""


def _premium_provenance(row: InsurerPremium) -> dict:
    return {
        "value_origin": row.value_origin or "UNKNOWN",
        "source_value": row.source_value,
        "source_period_days": row.source_period_days,
        "transformation": row.transformation,
        "transformation_reason": row.transformation_reason,
        "source_reference": row.source_reference,
    }


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
def get_premium_comparison(
    age: int,
    sex: str,
    days: int | None = None,
    order: str = "asc",
    plan_tier: int | None = None,  # 0=실속, 1=표준(기본), 2=고급 — insurer_tiers.TIER_LABELS
    db: Session = Depends(get_db),
):
    """해당 나이·성별의 보험료와 값의 생성 경로를 보험사별로 돌려준다.

    2026-08-19부터 보험다모아 비교공시(표준조건 한 값) 대신, 각 사 다이렉트 사이트에서
    직접조회값과 출처가 명시된 환산·추정값을 쓴다. plan_tier를 안 주면 보험사마다 표준
    등급(is_standard_tier) 하나만 대표로 내려준다 — 화면의 "실속/표준/고급" 전체
    선택기가 이 파라미터로 한 번에 모든 보험사 가격을 바꾼다.

    이 숫자는 약관에서 뽑은 값이 아니라 각 사 공시 화면에서 가져온 값이므로,
    산출 전제(basis)와 출처·수집일을 항상 같이 내려보낸다. 화면에서 숫자만 떼어
    보여주지 않기 위한 것이다.

    days는 구버전 클라이언트 호환을 위해 받지만 계산에는 사용하지 않는다. 조회값만
    확보한 상태에서 여행일수에 비례한다고 가정하면 근거 없는 보험료를 만들게 되기 때문이다.

    해당 나이가 가입연령 범위 밖이라 조회 자체가 안 되는 보험사는 unavailable_insurers로
    따로 알려준다 — 조용히 빠뜨리면 "그 보험사는 더 싼가?" 하는 오해를 만든다.
    아직 가격을 확보하지 못한 보험사는 그 보험사에 해당하는 행이 아예 없어서
    unavailable_insurers에도 잡히지 않는다 — 가격이 준비되는 대로
    app.seed_premiums_actual만 다시 돌리면 자동으로 나타난다. (2026-08-25 DB손해보험에 이어
    신한EZ손해보험까지 들어오면서 지금은 7개사 전부 가격이 있다. 보험사를 새로 추가하면
    다시 필요해진다.)"""
    sex = sex.upper()
    if sex not in ("M", "F"):
        raise HTTPException(status_code=400, detail="성별은 M 또는 F여야 합니다.")

    _ = days
    if plan_tier is not None:
        if plan_tier not in (0, 1, 2):
            raise HTTPException(status_code=400, detail="plan_tier는 0~2 사이여야 합니다.")
        rows = []
        for insurer in db.query(Insurer).all():
            plan_name = plan_name_for_tier(insurer.code, plan_tier)
            if plan_name is None:
                continue
            row = (
                db.query(InsurerPremium)
                .filter(
                    InsurerPremium.insurer_id == insurer.insurer_id,
                    InsurerPremium.age == age, InsurerPremium.sex == sex,
                    InsurerPremium.plan_name == plan_name,
                )
                .first()
            )
            if row:
                rows.append(row)
        rows.sort(key=lambda r: r.premium, reverse=(order == "desc"))
    else:
        # 보험사마다 실제로 파는 등급(플랜)이 여럿이라 (나이,성별) 하나에 여러 행이 걸린다 —
        # 등급을 안 골랐으면 보험사마다 표준 등급 하나만 대표로 보여준다.
        direction = InsurerPremium.premium.desc() if order == "desc" else InsurerPremium.premium.asc()
        rows = (
            db.query(InsurerPremium)
            .filter(InsurerPremium.age == age, InsurerPremium.sex == sex, InsurerPremium.is_standard_tier.is_(True))
            .order_by(direction)
            .all()
        )
    if not rows:
        raise HTTPException(status_code=404, detail="해당 나이·성별의 보험료 자료가 없습니다.")

    covered = {r.insurer_id for r in rows}
    all_insurers = db.query(Insurer).all()
    tracked_ids = {
        i.insurer_id for i in all_insurers
        if db.query(InsurerPremium).filter(InsurerPremium.insurer_id == i.insurer_id).first() is not None
    }
    # 이 보험사는 가격 자체를 추적 중인데 이 나이만 범위 밖인 경우(가입연령 초과/미달).
    unavailable = [i.name for i in all_insurers if i.insurer_id not in covered and i.insurer_id in tracked_ids]
    # 이 보험사는 애초에 가격을 하나도 못 구했다(아직 수집 전) — 나이와 무관하다.
    # 원인이 다르므로 화면 문구도 나눠 보여준다(그렇지 않으면 "가입연령 범위 밖"이라는
    # 틀린 이유를 사용자에게 전달하게 된다).
    no_data = [i.code for i in all_insurers if i.insurer_id not in tracked_ids]

    first = rows[0]
    # 조회일은 보험사마다 다르다(최초 6개사 2026-08-17, DB손보 08-23, 신한EZ손보 08-25).
    # 목록 첫 줄은 "제일 싼 보험사"일 뿐이라 그 값을 대표로 쓰면, 나중에 조회한 보험사가
    # 섞여 있어도 화면에는 옛 날짜가 뜬다. 가장 최근 조회일을 대표로 쓰고, 정확한 값은
    # 보험사마다 따로 붙여 보낸다.
    collected_dates = [r.collected_at for r in rows if r.collected_at]
    return PremiumComparisonOut(
        age=age, sex=sex,
        basis=_display_basis(first.basis), source=first.source, source_url=first.source_url,
        collected_at=max(collected_dates) if collected_dates else None,
        premium_period_days=first.period_days,
        no_data_insurer_codes=no_data,
        items=[
            InsurerPremiumOut(
                insurer_code=r.insurer.code, insurer_name=r.insurer.name,
                product_name=r.product_name, published_premium=r.premium,
                premium_period_days=r.period_days,
                age_range=r.age_range,
                basis=_display_basis(r.basis), source=r.source, source_url=r.source_url,
                collected_at=r.collected_at, **_premium_provenance(r),
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
        .filter(
            InsurerPremium.insurer_id == insurer.insurer_id, InsurerPremium.sex == sex,
            InsurerPremium.is_standard_tier.is_(True),
        )
        .order_by(InsurerPremium.age.asc())
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="해당 보험사의 보험료 자료가 없습니다.")

    return InsurerPremiumCurveOut(
        insurer_code=insurer.code, insurer_name=insurer.name,
        product_name=rows[0].product_name, sex=sex,
        premium_period_days=rows[0].period_days,
        basis=_display_basis(rows[0].basis), source=rows[0].source, source_url=rows[0].source_url,
        collected_at=rows[0].collected_at,
        points=[
            PremiumPointOut(
                age=r.age, published_premium=r.premium,
                premium_period_days=r.period_days, **_premium_provenance(r),
            )
            for r in rows
        ],
    )


@router.get("/{insurer_code}/plans", response_model=InsurerPlansOut)
def get_insurer_plans(
    insurer_code: str, age: int | None = None, sex: str | None = None, db: Session = Depends(get_db),
):
    """한 보험사가 실제로 파는 등급(플랜) 전부와 그 나이·성별 기준 가격.

    /{insurer_code}/premiums(등급 하나만 대표로 주는 곡선)와 달리 이건 등급을 직접
    고르는 화면(순위 상세, 보험 등록, 보험료 비교 세부설정)에 쓴다. age·sex를 안 주면
    가격 없이 등급 이름만 돌려준다 — 나이를 아직 모르는 단계(보험 등록 1단계 등)에서도
    등급 이름과 담보한도는 먼저 보여줄 수 있게 하기 위함이다."""
    insurer = db.query(Insurer).filter(Insurer.code == insurer_code.upper()).first()
    if not insurer:
        raise HTTPException(status_code=404, detail="보험사를 찾을 수 없습니다.")

    if age is None or not sex:
        # 등급 이름만 필요하면 InsurerPlanCoverage(담보한도표)에서 뽑는다 — 가격 자료가
        # 아직 없는 보험사도 등급 이름은 여기서 나온다.
        plan_names = (
            db.query(InsurerPlanCoverage.plan_name)
            .filter(InsurerPlanCoverage.insurer_id == insurer.insurer_id)
            .distinct()
            .all()
        )
        return InsurerPlansOut(
            insurer_code=insurer.code, insurer_name=insurer.name,
            plans=[InsurerPlanOut(plan_name=p[0], premium=0, is_standard_tier=False) for p in plan_names],
            price_unavailable=True,
        )

    normalized_sex = sex.upper()
    if normalized_sex not in ("M", "F"):
        raise HTTPException(status_code=400, detail="성별은 M 또는 F여야 합니다.")

    rows = (
        db.query(InsurerPremium)
        .filter(
            InsurerPremium.insurer_id == insurer.insurer_id, InsurerPremium.age == age,
            InsurerPremium.sex == normalized_sex,
        )
        .order_by(InsurerPremium.premium.asc())
        .all()
    )
    if not rows:
        return InsurerPlansOut(insurer_code=insurer.code, insurer_name=insurer.name, plans=[], price_unavailable=True)

    return InsurerPlansOut(
        insurer_code=insurer.code, insurer_name=insurer.name,
        premium_period_days=rows[0].period_days,
        plans=[
            InsurerPlanOut(
                plan_name=r.plan_name, premium=r.premium,
                premium_period_days=r.period_days,
                is_standard_tier=r.is_standard_tier,
                collected_at=r.collected_at,
                **_premium_provenance(r),
            )
            for r in rows
        ],
    )


@router.get("/{insurer_code}/plan-coverage", response_model=InsurerPlanCoverageOut)
def get_insurer_plan_coverage(insurer_code: str, db: Session = Depends(get_db)):
    """한 보험사의 등급별 담보 가입금액표(다이렉트 사이트에서 직접 조회한 값).

    나이·성별과 무관하다 — 원본 자료의 각주에 "담보한도는 통상 연령 무관하게 동일"이라고
    명시돼 있다(seed_plan_coverage.py 참고)."""
    insurer = db.query(Insurer).filter(Insurer.code == insurer_code.upper()).first()
    if not insurer:
        raise HTTPException(status_code=404, detail="보험사를 찾을 수 없습니다.")

    rows = (
        db.query(InsurerPlanCoverage)
        .filter(InsurerPlanCoverage.insurer_id == insurer.insurer_id)
        .order_by(InsurerPlanCoverage.sort_order.asc(), InsurerPlanCoverage.plan_name.asc())
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="해당 보험사의 담보 가입금액표가 없습니다.")

    plan_names: list[str] = []
    for r in rows:
        if r.plan_name not in plan_names:
            plan_names.append(r.plan_name)

    return InsurerPlanCoverageOut(
        insurer_code=insurer.code, insurer_name=insurer.name,
        plan_names=plan_names,
        rows=[
            InsurerPlanCoverageRowOut(
                plan_name=r.plan_name, coverage_label=r.coverage_label,
                amount_text=r.amount_text, unit=r.unit or "", sort_order=r.sort_order,
            )
            for r in rows
        ],
        source=rows[0].source, source_note=rows[0].source_note, collected_at=rows[0].collected_at,
    )


@router.get("/comparison-metrics", response_model=InsurerComparisonOut)
def get_insurer_comparison_metrics(plan_tier: int = 1, db: Session = Depends(get_db)):
    """전 보험사를 같은 담보 항목 기준으로 나란히 비교한 표(보장비교 종합).

    InsurerPlanCoverage(보험사별 원문 담보명)와 달리, 같은 항목끼리 미리 정리해 둔
    metric_label로 보험사×등급 값이 한 행에 나란히 나온다. plan_tier(0=실속,
    1=표준, 2=고급)로 등급 하나를 고르면 그 등급의 값만 돌려준다 — 사용자가
    "기준 다시 선택" 옆의 등급 선택기로 이 파라미터를 바꾼다."""
    if plan_tier not in (0, 1, 2):
        raise HTTPException(status_code=400, detail="plan_tier는 0~2 사이여야 합니다.")

    all_insurers = {i.insurer_id: i for i in db.query(Insurer).all()}
    wanted_plan_by_insurer = {
        insurer_id: plan_name_for_tier(insurer.code, plan_tier)
        for insurer_id, insurer in all_insurers.items()
    }

    rows = (
        db.query(InsurerComparisonMetric)
        .order_by(
            InsurerComparisonMetric.category_order.asc(),
            InsurerComparisonMetric.sort_order.asc(),
        )
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="보장비교 자료가 없습니다.")

    categories: dict[str, list] = {}
    category_order: dict[str, int] = {}
    metrics_by_key: dict[tuple[str, str], dict] = {}
    for r in rows:
        if r.plan_name != wanted_plan_by_insurer.get(r.insurer_id):
            continue
        category_order[r.category] = r.category_order
        key = (r.category, r.metric_label)
        metric = metrics_by_key.get(key)
        if metric is None:
            metric = {"metric_label": r.metric_label, "unit": r.unit or "", "values": []}
            metrics_by_key[key] = metric
            categories.setdefault(r.category, []).append(metric)
        insurer = all_insurers[r.insurer_id]
        metric["values"].append(ComparisonMetricValueOut(insurer_code=insurer.code, value_text=r.value_text))

    ordered_categories = [
        ComparisonCategoryOut(
            category=cat,
            metrics=[ComparisonMetricOut(**m) for m in metrics],
        )
        for cat, metrics in sorted(categories.items(), key=lambda kv: category_order[kv[0]])
    ]

    first = rows[0]
    return InsurerComparisonOut(
        tier_rank=plan_tier, tier_label=TIER_LABELS[plan_tier],
        categories=ordered_categories,
        source=first.source, source_note=first.source_note, collected_at=first.collected_at,
    )


def _attach_published_premiums(
    db: Session,
    ranking: list[dict],
    age: int | None,
    sex: str | None,
    tier_rank: int | None = None,
) -> None:
    """랭킹에 저장 보험료와 생성 경로를 붙인다.

    trip_days는 의도적으로 받지 않는다. 저장값을 일할 계산할 근거가 없기 때문이다.
    추천 가격축 사용 여부는 ranking_score.price_score가 value_origin으로 결정한다.

    tier_rank(0=실속, 1=표준, 2=고급)를 주면 보험사마다 그 등급의 가격을 붙인다 —
    화면의 "기준 다시 선택" 옆 등급 선택기가 이걸 쓴다. 안 주면(None) 예전처럼
    보험사마다 표준 등급(is_standard_tier) 하나만 붙인다.
    """
    if age is None or not sex:
        return
    normalized_sex = sex.upper()
    if normalized_sex not in ("M", "F"):
        return

    if tier_rank is not None:
        by_id: dict[int, InsurerPremium] = {}
        for insurer in db.query(Insurer).all():
            plan_name = plan_name_for_tier(insurer.code, tier_rank)
            if plan_name is None:
                continue
            row = (
                db.query(InsurerPremium)
                .filter(
                    InsurerPremium.insurer_id == insurer.insurer_id,
                    InsurerPremium.age == age, InsurerPremium.sex == normalized_sex,
                    InsurerPremium.plan_name == plan_name,
                )
                .first()
            )
            if row:
                by_id[insurer.insurer_id] = row
    else:
        rows = (
            db.query(InsurerPremium)
            .filter(
                InsurerPremium.age == age, InsurerPremium.sex == normalized_sex,
                InsurerPremium.is_standard_tier.is_(True),
            )
            .all()
        )
        by_id = {r.insurer_id: r for r in rows}
    all_insurers = db.query(Insurer).all()
    code_to_row = {
        insurer.code: by_id[insurer.insurer_id]
        for insurer in all_insurers
        if insurer.insurer_id in by_id
    }
    # 이 나이만 범위 밖인 건지, 이 보험사가 가격 자체를 아직 하나도 못 구한 건지 구분한다
    # (get_premium_comparison의 no_data_insurer_codes와 같은 원칙) — 안 그러면 가격을
    # 아직 못 구한 보험사도 "가입연령 범위 밖"이라는 틀린 이유로 안내하게 된다.
    tracked_codes = {
        insurer.code for insurer in all_insurers
        if db.query(InsurerPremium).filter(InsurerPremium.insurer_id == insurer.insurer_id).first() is not None
    }

    for item in ranking:
        row = code_to_row.get(item["insurer_code"])
        if row:
            item["published_premium"] = row.premium
            item["plan_name"] = row.plan_name
            item["premium_period_days"] = row.period_days
            item["premium_basis"] = _display_basis(row.basis)
            item["premium_source"] = row.source
            item["premium_source_url"] = row.source_url
            item["premium_collected_at"] = row.collected_at
            item["premium_value_origin"] = row.value_origin or "UNKNOWN"
            item["premium_source_value"] = row.source_value
            item["premium_source_period_days"] = row.source_period_days
            item["premium_transformation"] = row.transformation
            item["premium_transformation_reason"] = row.transformation_reason
            item["premium_source_reference"] = row.source_reference
            item["premium_note"] = None
        else:
            item["published_premium"] = None
            # 가격은 없어도 등급 이름은 안다(InsurerPlanCoverage에 담보한도표가 있다) —
            # 상세 화면에 들어갔을 때 목록에서 고른 등급 그대로 이어지게 채워 둔다.
            item["plan_name"] = plan_name_for_tier(item["insurer_code"], tier_rank) if tier_rank is not None else None
            item["premium_period_days"] = None
            item["premium_basis"] = None
            item["premium_source"] = None
            item["premium_source_url"] = None
            item["premium_collected_at"] = None
            item["premium_value_origin"] = None
            item["premium_source_value"] = None
            item["premium_source_period_days"] = None
            item["premium_transformation"] = None
            item["premium_transformation_reason"] = None
            item["premium_source_reference"] = None
            item["premium_note"] = (
                "이 나이·성별은 가입연령 범위 밖이에요"
                if item["insurer_code"] in tracked_codes
                else "아직 보험료 근거를 확보하지 못했어요"
            )


def _attach_plan_coverage_summary(db: Session, ranking: list[dict]) -> None:
    """랭킹 카드에 "등급별 담보 가입금액표를 볼 수 있는 보험사인지"만 붙인다.

    _attach_published_premiums와 같은 이유로 순위 점수(rank_insurers의 네 가지 근거 축)에는
    섞지 않는다 — 이 표는 약관 조항이 아니라 보험사 다이렉트 사이트에서 직접 조회한
    외부 값이라(InsurerPlanCoverage), 근거 축과 성격이 다르다. 순위 카드에서 "이 보험사는
    등급별 한도를 볼 수 있다"는 사실만 미리 보여주고, 실제 비교는 상세 화면의
    PlanCoverageBoard(스크롤 가능한 전체 표)에서 한다."""
    counts = dict(
        db.query(InsurerPlanCoverage.insurer_id, func.count(InsurerPlanCoverage.coverage_row_id))
        .group_by(InsurerPlanCoverage.insurer_id)
        .all()
    )
    code_to_count = {
        insurer.code: counts[insurer.insurer_id]
        for insurer in db.query(Insurer).all()
        if insurer.insurer_id in counts
    }
    for item in ranking:
        item["plan_coverage_item_count"] = code_to_count.get(item["insurer_code"])


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


@router.get("/nonpayment-rates", response_model=NonpaymentRatesOut)
def get_nonpayment_rates(db: Session = Depends(get_db)):
    """손해보험협회 공시 — 비교 대상 보험사의 보험금 부지급률·청구이후 해지비율(업계평균과 함께).

    전체 보험종목 기준 공시라 여행자보험만의 수치가 아니다 — "이 보험사가 전반적으로
    보험금을 얼마나 안 주는 편인가"를 보여주는 참고 지표로만 노출한다."""
    rows = db.query(NonpaymentRate).order_by(NonpaymentRate.rate_id).all()
    if not rows:
        raise HTTPException(status_code=404, detail="부지급률 공시 자료가 아직 적재되지 않았습니다.")

    def to_out(r: NonpaymentRate) -> NonpaymentRateOut:
        return NonpaymentRateOut(
            insurer_code=r.insurer.code if r.insurer else None,
            company_name=r.company_name, claim_count=r.claim_count,
            unpaid_count=r.unpaid_count, unpaid_rate=r.unpaid_rate,
            post_claim_cancel_rate=r.post_claim_cancel_rate,
        )

    industry = next((r for r in rows if r.company_name == "업계평균"), None)
    items = [to_out(r) for r in rows if r.insurer_id is not None]
    first = rows[0]
    return NonpaymentRatesOut(
        source=first.source, source_url=first.source_url, period=first.period,
        scope_note=first.scope_note, collected_at=first.collected_at,
        items=items, industry_average=to_out(industry) if industry else None,
    )


@router.get("/standard-clauses", response_model=list[StandardClauseOut])
def get_standard_clauses(standard_name: str = "해외여행 실손의료보험", db: Session = Depends(get_db)):
    """금융감독원 표준약관 조문 목록(원문). 정렬은 조 번호 오름차순."""
    rows = (
        db.query(StandardClause)
        .filter(StandardClause.standard_name == standard_name)
        .order_by(StandardClause.standard_clause_id.asc())
        .all()
    )
    return [StandardClauseOut.model_validate(r) for r in rows]


@router.get("/{insurer_code}/standard-comparison", response_model=InsurerStandardComparisonOut)
def get_insurer_standard_comparison(
    insurer_code: str, standard_name: str = "해외여행 실손의료보험", db: Session = Depends(get_db)
):
    """이 보험사 약관을 표준약관과 조문 단위로 대조한 결과.

    대응 조항을 못 찾아 clause_standard_map 행 자체가 없는 표준 조문은 목록에서
    조용히 빠진다 — 근거 없이 '표준과 같다'고 단정하지 않기 위함이다. 매핑 커버리지는
    docs/compliance/source_register.md에 별도로 기록한다(README "한계" 참고)."""
    insurer = db.query(Insurer).filter(Insurer.code == insurer_code.upper()).first()
    if not insurer:
        raise HTTPException(status_code=404, detail="보험사를 찾을 수 없습니다.")

    standard_clauses = (
        db.query(StandardClause)
        .filter(StandardClause.standard_name == standard_name)
        .order_by(StandardClause.standard_clause_id.asc())
        .all()
    )
    if not standard_clauses:
        raise HTTPException(status_code=404, detail="해당 표준약관 조문을 찾을 수 없습니다.")

    maps = (
        db.query(ClauseStandardMap)
        .filter(
            ClauseStandardMap.insurer_id == insurer.insurer_id,
            ClauseStandardMap.standard_clause_id.in_([s.standard_clause_id for s in standard_clauses]),
        )
        .all()
    )
    map_by_standard = {m.standard_clause_id: m for m in maps}

    items: list[StandardClauseComparisonOut] = []
    for s in standard_clauses:
        m = map_by_standard.get(s.standard_clause_id)
        if not m:
            continue
        items.append(StandardClauseComparisonOut(
            standard_clause_id=s.standard_clause_id,
            article_no=s.article_no,
            title=s.title,
            standard_text=s.text,
            anchor_phrase_standard=m.anchor_phrase_standard,
            relation=m.relation,
            insurer_clause_id=m.clause.clause_id if m.clause else None,
            insurer_article_no=m.clause.article_no if m.clause else None,
            insurer_text=m.clause.text if m.clause else None,
            anchor_phrase_insurer=m.anchor_phrase_insurer,
            note=m.note,
        ))

    first_standard = standard_clauses[0]
    return InsurerStandardComparisonOut(
        insurer_code=insurer.code, insurer_name=insurer.name, standard_name=standard_name,
        source_url=first_standard.source_url, amended_at=first_standard.amended_at,
        items=items,
    )


def _drop_insurers_without_plan(
    ranking: list[dict], plan_tier: int,
) -> tuple[list[dict], list[str]]:
    """그 등급 상품 자체가 없는 보험사를 순위에서 뺀다.

    "자료가 아직 없다"와 "그 등급을 팔지 않는다"는 다르다. 앞은 자료가 채워지면
    해결되지만, 뒤는 애초에 비교 대상이 아니다. 남겨두면 다른 축 점수만으로 순위가
    매겨져서 팔지도 않는 등급의 보험사가 목록에 끼어든다(예: 메리츠 고급)."""
    kept, dropped = [], []
    for item in ranking:
        if plan_name_for_tier(item["insurer_code"], plan_tier) is None:
            dropped.append(item.get("insurer_name") or item["insurer_code"])
        else:
            kept.append(item)
    return kept, dropped


def _subject_particle(word: str) -> str:
    """한국어 주격 조사 "은/는"을 앞 글자 받침으로 고른다.

    보험사 이름이 목록에 그대로 들어가므로 "신한EZ손해보험는"처럼 어색해지는 걸 막는다.
    한글이 아닌 글자로 끝나면(영문 약어 등) 판단할 근거가 없어 "은"으로 둔다."""
    last = word.strip()[-1:] if word.strip() else ""
    if "가" <= last <= "힣":
        return "은" if (ord(last) - 0xAC00) % 28 else "는"
    return "은"


def _external_policies(db: Session, user_id: int | None) -> list[ExternalPolicy]:
    """이 사용자가 등록해 둔 기존보험. 없으면 빈 목록 — 겹침 축을 중립으로 둔다.

    종류(kind)만 뽑아 넘기던 것을 행 그대로 넘긴다. 겹침 축이 중복 진단 화면과 같은
    엔진을 쓰게 됐고, 그 엔진이 기존보험 객체를 받기 때문이다."""
    if user_id is None:
        return []
    return db.query(ExternalPolicy).filter(ExternalPolicy.user_id == user_id).all()


def _deterministic_reasons(scored: "ranking_score.InsurerScore") -> list[str]:
    """Gemini 없이도 "왜 이 순서인가"를 말할 수 있는 설명. 축 계산에서 그대로 나온다.

    이 문장들이 기본값이고, Gemini는 그 위에 더 읽기 좋은 문장을 덮어쓸 뿐이다. 모델을
    끄든 켜든, 실패하든 성공하든 사용자는 언제나 근거가 붙은 설명을 본다 — 그리고 그
    근거는 총점을 실제로 만든 값 그 자체다.

    기여도가 큰 축부터 두 개까지 말한다. 셋 이상 늘어놓으면 무엇이 결정적이었는지가
    도리어 흐려진다."""
    usable = sorted(
        (a for a in scored.axes if a.available and a.contribution > 0),
        key=lambda a: -a.contribution,
    )
    reasons = [
        f"{axis.label} (+{axis.contribution:.1f}점) — {axis.detail}"
        for axis in usable[:2]
    ]
    dropped = [a for a in scored.axes if not a.available]
    if dropped:
        names = ", ".join(a.label for a in dropped)
        reasons.append(
            f"자료가 없는 축({names})은 0점으로 세지 않고 빼서, 나머지 축으로 다시 100%를 맞췄어요."
        )
    return reasons or [f"총점 {scored.total:.1f}점 — 쓸 수 있는 축 자료가 없었어요."]


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
    plan_tier: int | None = None,  # 0=실속, 1=표준(기본), 2=고급 — insurer_tiers.TIER_LABELS
    # 등록해 둔 기존보험을 순위에 반영하기 위한 것. 없으면 겹침 축을 중립으로 둔다.
    user_id: int | None = None,
    companion_type: str | None = None,
    rental_car: bool = False,
    db: Session = Depends(get_db),
):
    trip_context = None
    if destination or risk_level or trip_days or activities or coverage_priority or companion_type or rental_car:
        trip_context = {
            "destination": destination,
            "risk_level": risk_level,
            "trip_days": trip_days,
            "activities": [a.strip() for a in activities.split(",") if a.strip()] if activities else [],
            "coverage_priority": [p.strip() for p in coverage_priority.split(",") if p.strip()] if coverage_priority else [],
            "companion_type": companion_type,
            "rental_car": rental_car,
        }
    try:
        ranking = rank_insurers(db, tier, trip_context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 1차 약관 근거 순위에 여행 준비 선택과 등급별 보장금액·보험료를 결합해 다섯 축을
    # 결정적으로 점수화한다. 최종 순위와 총점은 ranking_score에서 확정하고, Gemini는
    # 그 결과를 설명하는 문장만 다듬는다.
    excluded_note = None
    if plan_tier is not None:
        ranking, dropped = _drop_insurers_without_plan(ranking, plan_tier)
        if dropped:
            names = ", ".join(dropped)
            excluded_note = (
                f"{names}{_subject_particle(dropped[-1])} {TIER_LABELS[plan_tier]} 등급 "
                "상품이 없어 이번 비교에서 빠졌어요."
            )
        external_policies = _external_policies(db, user_id)
        weighted = ranking_score.score_insurers(
            db,
            tier_code=tier,
            plan_tier=plan_tier,
            trip_context=trip_context,
            ranking=ranking,
            age=age,
            sex=sex,
            external_policies=external_policies,
        )

        # 순위와 총점은 여기서 끝난다. score_insurers()가 이미 (총점 내림차순, 동점이면
        # 보험사 코드순)으로 정렬해 돌려주므로 그 순서를 그대로 쓴다.
        #
        # 반올림한 점수로 다시 정렬하지 않는 것이 중요하다 — 61.234와 61.236은 반올림하면
        # 같은 61.23이 되고, 그때 정렬을 다시 하면 원래 앞서 있던 쪽이 뒤로 갈 수 있다.
        # 순서는 온전한 정밀도로 이미 정해졌고, 반올림은 표시용일 뿐이다.
        by_code = {entry["insurer_code"]: entry for entry in ranking}
        merged = []
        for index, scored in enumerate(weighted, start=1):
            entry = dict(by_code[scored.insurer_code])
            entry["rank"] = index
            entry["total_score"] = round(scored.total, 2)
            # 축별 점수·비중·기여도를 그대로 내려보낸다. "왜 이 순서인가"가 응답 안에서
            # 끝까지 되짚어져야 한다 — 총점은 available한 축들의 contribution 합이다.
            entry["axes"] = [vars(axis) for axis in scored.axes]
            entry["reasons"] = _deterministic_reasons(scored)
            entry["comparison_basis"] = (
                f"{tier} 기준 · {TIER_LABELS[plan_tier]} 등급 · 여행 준비 선택 반영"
            )
            merged.append(entry)

        # Gemini는 여기서 처음이자 마지막으로 등장하고, 하는 일은 문장을 다듬는 것뿐이다.
        # 순위·총점은 위에서 이미 확정됐고 아래 어디에서도 다시 건드리지 않는다.
        # 실패하면 위에서 축 근거로 만들어 둔 결정적 설명이 그대로 남는다.
        tier_meta = TIERS.get(tier, {})
        explanations = explain_ranking(
            db,
            tier_code=tier,
            tier_label=tier_meta.get("label", tier),
            tier_description=tier_meta.get("description", ""),
            plan_tier=plan_tier,
            trip_context=trip_context,
            ranked=merged,
        )
        if explanations:
            for entry in merged:
                said = explanations.get(entry["insurer_code"])
                if said:
                    entry["reasons"] = said

        ranking = merged

    # 나이·성별을 함께 받았으면 순위 카드에 보험료 provenance를 붙인다. trip_days로
    # 환산하지 않으며, 가격축은 DIRECT_QUOTE/검증된 DERIVED만 사용한다.
    _attach_published_premiums(db, ranking, age, sex, plan_tier)
    _attach_plan_coverage_summary(db, ranking)

    return InsurerRankingOut(tier_code=tier, ranking=ranking, excluded_note=excluded_note)


# --- 근거 검증 현황 ---------------------------------------------------------
# 이 프로젝트의 원칙은 "근거 없는 결과를 내지 않는다"인데, 그게 실제로 지켜지고 있다는
# 사실은 지금까지 README에만 있었다. 화면에서 확인할 수 있게 DB에서 직접 세어 내려준다.
#
# 숫자를 상수로 적어두지 않는 것이 이 엔드포인트의 핵심이다. 보험사가 하나 늘거나 조항이
# 다시 적재되면 문서의 숫자는 조용히 낡는데(실제로 README의 담보 수와 서류 연결률이
# 그렇게 낡아 있었다), 근거를 보여주겠다는 화면이 틀린 숫자를 보여주면 없느니만 못하다.

# 약관 KB는 배포 중에 바뀌지 않는다(재배포로만 바뀐다). 매 요청마다 조항 원문 558건을
# 전부 읽어 대조할 이유가 없어서 프로세스마다 한 번만 계산하고 재사용한다.
_kb_stats_cache: KbStatsOut | None = None


def _rate(passed: int, total: int) -> float:
    return round(passed / total * 100, 1) if total else 0.0


@router.get("/kb-stats", response_model=KbStatsOut)
def kb_stats(db: Session = Depends(get_db)) -> KbStatsOut:
    global _kb_stats_cache
    if _kb_stats_cache is not None:
        return _kb_stats_cache

    clause_texts = dict(db.query(Clause.clause_id, Clause.text).all())
    terms = db.query(ClauseTerm.clause_id, ClauseTerm.raw_text).all()
    grounded = sum(
        1 for clause_id, raw_text in terms
        if raw_text_is_grounded(clause_texts.get(clause_id) or "", raw_text or "")
    )

    # 분모는 "청구서류라는 개념이 성립하는 담보"만 센다. 지정대리청구·장애인전용보험 전환
    # 같은 제도성 특약(ADMIN_STD_CODES)과 표준담보에 아직 이어지지 않은 행은 청구할 서류가
    # 애초에 없어서, 전체 담보를 분모로 쓰면 "못 채운 자리"처럼 보이지만 실제로는 채울 것이
    # 없는 자리다. 반대로 이 예외를 화면에서 감추지도 않는다 — 아래 description에 밝힌다.
    coverage_rows = (
        db.query(Coverage.coverage_id, CoverageStd.std_code)
        .outerjoin(CoverageStd, CoverageStd.coverage_std_id == Coverage.coverage_std_id)
        .all()
    )
    coverage_ids = {cid for cid, _ in coverage_rows}
    claimable_ids = {
        cid for cid, std_code in coverage_rows
        if std_code and std_code not in ADMIN_STD_CODES
    }
    coverage_with_doc = claimable_ids & {r[0] for r in db.query(CoverageDocMap.coverage_id).distinct()}
    clause_with_incident = {r[0] for r in db.query(ClauseIncidentMap.clause_id).distinct()}

    checks = [
        KbCheckOut(
            code="clause_term_grounded",
            label="수치 조건이 원문에 실재하는가",
            description=(
                "지급한도·자기부담금 같은 숫자를 조항에서 뽑아 따로 저장할 때, 그 근거가 된 "
                "원문 조각이 조항 원문의 부분 문자열인지 한 건씩 다시 대조했습니다."
            ),
            passed=grounded, total=len(terms), rate=_rate(grounded, len(terms)),
        ),
        KbCheckOut(
            code="clause_incident_mapped",
            label="조항이 사고유형에 연결됐는가",
            description=(
                "어떤 사고에 어떤 조항이 걸리는지 미리 이어 둔 비율입니다. 이어지지 않은 조항은 "
                "안내에 쓰이지 않습니다 — 억지로 갖다 붙이지 않기 때문입니다."
            ),
            passed=len(clause_with_incident), total=len(clause_texts),
            rate=_rate(len(clause_with_incident), len(clause_texts)),
        ),
        KbCheckOut(
            code="coverage_doc_linked",
            label="담보에 필요서류가 붙었는가",
            description=(
                "담보별로 청구에 필요한 서류를 표준 서류 코드 14종에 이어 둔 비율입니다. "
                "지정대리청구·장애인전용보험 전환처럼 청구할 서류가 애초에 없는 제도성 특약은 "
                "세지 않습니다(전체 담보 "
                f"{len(coverage_ids)}건 중 {len(coverage_ids) - len(claimable_ids)}건)."
            ),
            passed=len(coverage_with_doc), total=len(claimable_ids),
            rate=_rate(len(coverage_with_doc), len(claimable_ids)),
        ),
    ]

    # 보험사별 규모와 "어느 판본을 읽었는지". 판본과 파일 지문도 근거의 일부다 —
    # 같은 보험사라도 판이 다르면 조항이 다르다.
    per_insurer: list[KbInsurerStatOut] = []
    for insurer in db.query(Insurer).order_by(Insurer.insurer_id).all():
        versions = (
            db.query(PolicyVersion)
            .join(Product, Product.product_id == PolicyVersion.product_id)
            .filter(Product.insurer_id == insurer.insurer_id)
            .all()
        )
        version_ids = [v.policy_version_id for v in versions]
        if not version_ids:
            continue
        clause_ids = [
            r[0] for r in db.query(Clause.clause_id)
            .filter(Clause.policy_version_id.in_(version_ids)).all()
        ]
        latest = max(versions, key=lambda v: (v.effective_date is not None, v.effective_date))
        per_insurer.append(KbInsurerStatOut(
            insurer_code=insurer.code,
            insurer_name=insurer.name,
            clause_count=len(clause_ids),
            coverage_count=db.query(Coverage)
                .filter(Coverage.policy_version_id.in_(version_ids)).count(),
            clause_term_count=db.query(ClauseTerm)
                .filter(ClauseTerm.clause_id.in_(clause_ids)).count() if clause_ids else 0,
            incident_map_count=db.query(ClauseIncidentMap)
                .filter(ClauseIncidentMap.clause_id.in_(clause_ids)).count() if clause_ids else 0,
            version_label=latest.version_label,
            effective_date=latest.effective_date,
            file_hash_prefix=(latest.file_hash or "")[:12] or None,
        ))

    _kb_stats_cache = KbStatsOut(
        insurer_count=len(per_insurer),
        clause_count=len(clause_texts),
        coverage_count=len(coverage_ids),
        clause_term_count=len(terms),
        incident_map_count=db.query(ClauseIncidentMap).count(),
        # L1 루트 행은 parent_id가 없다. 8개로 고정이고 늘리지 않는다(models/kb.py 참고).
        incident_type_l1_count=db.query(IncidentType).filter(IncidentType.parent_id.is_(None)).count(),
        incident_type_l2_count=db.query(IncidentType).filter(IncidentType.parent_id.isnot(None)).count(),
        checks=checks,
        insurers=per_insurer,
    )
    return _kb_stats_cache
