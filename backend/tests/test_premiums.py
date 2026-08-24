from datetime import date

from app.models.kb import Insurer, InsurerPremium
from app.routers.insurers import _attach_published_premiums, get_premium_comparison


def _seed_premium(db_session, premium: int = 10_000) -> None:
    insurer = Insurer(name="테스트보험", code="TEST")
    db_session.add(insurer)
    db_session.flush()
    db_session.add(InsurerPremium(
        insurer_id=insurer.insurer_id,
        sex="M",
        age=30,
        plan_name="표준",
        is_standard_tier=True,
        premium=premium,
        period_days=7,
        product_name="테스트 해외여행보험",
        basis="보험기간 7일 / 표준보장 담보 기준",
        source="보험다모아",
        source_url="https://example.test/premiums",
        collected_at=date(2026, 8, 2),
    ))
    db_session.commit()


def test_published_premium_is_not_scaled_by_requested_trip_days(db_session):
    _seed_premium(db_session)

    results = [
        get_premium_comparison(age=30, sex="M", days=days, db=db_session)
        for days in (3, 7, 14)
    ]

    assert [r.items[0].published_premium for r in results] == [10_000, 10_000, 10_000]
    assert [r.premium_period_days for r in results] == [1, 1, 1]
    assert all("premium_total" not in r.model_dump() for r in results)


def test_ranking_receives_only_published_premium_and_metadata(db_session):
    _seed_premium(db_session)
    ranking = [{"insurer_code": "TEST"}]

    _attach_published_premiums(db_session, ranking, age=30, sex="M")

    item = ranking[0]
    assert item["published_premium"] == 10_000
    assert item["premium_period_days"] == 1
    assert item["premium_basis"] == "보험기간 1일 / 표준보장 담보 기준"
    assert item["premium_source"] == "보험다모아"
    assert "premium_total" not in item
    assert "premium_days" not in item


def test_가격표_등급명이_등급_매핑과_어긋나지_않는다():
    """가격 시트의 등급명과 실속/표준/고급 매핑이 어긋나면, 등급으로 가격을 못 찾아
    그 보험사만 조용히 값이 안 뜬다. 실제로 메리츠가 "보장이 큰 플랜"(띄어쓰기)과
    "보장이큰플랜" 사이에서 이렇게 어긋날 뻔했다."""
    from app.seed_premiums_actual import _PLAN_NAME_ALIASES, _SHEET_CONFIG
    from app.services.insurer_tiers import TIER_PLAN_NAMES

    for code, _vertical, standard_plan in _SHEET_CONFIG.values():
        known = set(TIER_PLAN_NAMES[code])
        aliased = set(_PLAN_NAME_ALIASES.get(code, {}).values())
        assert aliased <= known, f"{code}: 별칭이 등급 매핑에 없는 이름을 가리킨다 — {aliased - known}"
        assert standard_plan in known, f"{code}: 대표 등급 {standard_plan}이 등급 매핑에 없다"


def test_등급_매핑은_세_자리이고_빈자리는_실제로_안_파는_등급뿐이다():
    """등급 매핑에 빈자리가 있으면 그 등급 비교에서 보험사 하나가 통째로 빠진다.
    빠져도 되는 건 "그 등급을 실제로 안 판다"일 때뿐이고, "자료를 아직 못 구했다"는
    이유로 비워 두면 안 된다.

    한동안 메리츠 가격표에 가운데 등급 열이 없어 고급 자리를 비워 두었는데, 담보
    가입금액표에는 처음부터 세 등급이 다 있었다(= 자료 문제였지 상품 문제가 아니었다).
    2026-08-25 가격표로 세 등급이 채워져 메리츠는 다시 3등급이 됐다.
    지금 빈자리가 있어야 하는 보험사는 신한EZ손보(실속케어·안심케어 2등급)뿐이다."""
    from app.services.insurer_tiers import TIER_PLAN_NAMES

    TWO_TIER_ONLY = {"SHINHAN"}

    for code, names in TIER_PLAN_NAMES.items():
        assert len(names) == 3, f"{code}: 등급이 세 자리가 아니다"
        if code in TWO_TIER_ONLY:
            assert names[2] is None, f"{code}: 2등급 보험사인데 고급 자리가 채워져 있다"
            assert all(names[:2]), f"{code}: 실속·표준 자리가 비어 있다 — {names}"
        else:
            assert all(names), f"{code}: 비어 있는 등급 자리가 있다 — {names}"

    assert TIER_PLAN_NAMES["MERITZ"] == ["실속플랜", "추천플랜", "보장이큰플랜"]
    assert TIER_PLAN_NAMES["SHINHAN"] == ["실속케어", "안심케어", None]


def test_그_등급_상품이_없는_보험사는_순위에서_뺀다():
    """자료가 없는 게 아니라 상품 자체가 없다. 남겨두면 다른 축 점수만으로 순위가
    매겨져서, 팔지도 않는 등급의 보험사가 목록에 끼어든다.

    지금은 6개사 모두 세 등급을 다 파니 실제로 빠지는 보험사가 없다. 그래도 이
    장치는 남겨 둔다 — 등급이 두 개뿐인 보험사(예: 신한EZ손보)를 추가하는 순간
    다시 필요해지고, 그때 조용히 순위에 끼어드는 걸 막아 준다."""
    from app.routers.insurers import _drop_insurers_without_plan

    ranking = [
        {"insurer_code": "KB", "insurer_name": "KB손해보험"},
        {"insurer_code": "NOPLAN", "insurer_name": "등급없는보험"},
    ]

    kept, dropped = _drop_insurers_without_plan(ranking, plan_tier=2)
    assert [r["insurer_code"] for r in kept] == ["KB"]
    assert dropped == ["등급없는보험"]


def test_비교에서_빠진_보험사_안내에_조사가_맞게_붙는다():
    """안내 문구에 보험사 이름이 그대로 들어가므로 "신한EZ손해보험는"처럼 어색해지면 안 된다."""
    from app.routers.insurers import _subject_particle

    assert _subject_particle("신한EZ손해보험") == "은"   # 받침 ㅁ
    assert _subject_particle("메리츠화재") == "는"       # 받침 없음
    assert _subject_particle("KB") == "은"               # 한글이 아니면 판단 근거가 없다


def test_등급이_올라가면_보험료도_올라간다(kb_session):
    """실속 → 표준 → 고급 순서로 값이 커야 한다. 가격표의 등급 열을 엉뚱한 자리에
    이어 붙이면(예: 메리츠 "표준형" 열을 고급 자리에) 여기서 순서가 뒤집힌다.
    같은 나이·성별 안에서만 비교하므로 보험사끼리의 가격 차이는 섞이지 않는다."""
    from app.models.kb import Insurer, InsurerPremium
    from app.services.insurer_tiers import TIER_PLAN_NAMES

    rows = (
        kb_session.query(Insurer.code, InsurerPremium.plan_name, InsurerPremium.sex,
                         InsurerPremium.age, InsurerPremium.premium)
        .join(InsurerPremium, Insurer.insurer_id == InsurerPremium.insurer_id)
        .all()
    )
    assert rows, "보험료가 하나도 적재돼 있지 않다"
    by_key = {(code, plan, sex, age): premium for code, plan, sex, age, premium in rows}

    priced = {code for (code, _p, _s, _a) in by_key}
    assert priced, "보험료가 하나도 적재돼 있지 않다"

    for code, plan_names in TIER_PLAN_NAMES.items():
        if code not in priced:
            continue  # 아직 보험료를 확보하지 못한 보험사(현재 신한EZ손보)
        ages = {age for (c, _p, _s, age) in by_key if c == code}
        for sex in ("M", "F"):
            for age in sorted(ages):
                tiers = [by_key.get((code, name, sex, age)) for name in plan_names if name]
                if any(v is None for v in tiers):
                    continue  # 이 나이·성별은 가입연령 범위 밖
                assert tiers == sorted(tiers), (
                    f"{code} {sex} {age}세: 등급이 올라가는데 값이 내려간다 — {tiers}"
                )
