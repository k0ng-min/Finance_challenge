"""보험사마다 제각각인 등급명을, 화면에서 하나의 "실속/표준/고급" 선택으로 다루기 위한
공통 매핑.

InsurerPremium·InsurerPlanCoverage·InsurerComparisonMetric 세 표 모두 등급명을
보험사가 실제 쓰는 이름 그대로 저장한다(예: 삼성 "표준플랜", 메리츠 "추천플랜") —
근거 없이 이름을 지어내지 않기 위해서다. 하지만 화면에서 "실속/표준/고급" 하나로
6개사를 한 번에 조작하려면, 그 3단계가 각 보험사의 어느 등급에 대응하는지 알아야
한다. 이 매핑은 가격 낮은 순(실속→표준→고급)이라는 원본 엑셀의 열 순서를 그대로
따른다 — seed_comparison_metrics.py의 _PLAN_ALIAS와 반드시 같은 대응을 쓴다(둘이
어긋나면 등급 선택기와 비교표가 서로 다른 등급을 가리키게 된다).
"""

TIER_LABELS: list[str] = ["실속", "표준", "고급"]

# 값이 None이면 그 보험사는 그 등급 상품을 팔지 않는다. 없는 등급을 있는 척 다른
# 플랜에 이어 붙이면, 팔지도 않는 등급으로 다른 보험사와 나란히 비교하게 된다.
TIER_PLAN_NAMES: dict[str, list[str | None]] = {
    "KAKAOPAY": ["라이트", "베이직", "플러스"],
    "HYUNDAI": ["실속형", "표준형", "고급형"],
    "KB": ["실속형", "표준형", "고급형"],
    "SAMSUNG": ["실속플랜", "표준플랜", "고급플랜"],
    "DB": ["실속형", "표준형", "고급형"],
    # 메리츠가 실제로 파는 건 실속플랜과 보장이큰플랜 둘뿐이다 — 고급 자리는 비운다.
    "MERITZ": ["실속플랜", "보장이큰플랜", None],
}


def plan_name_for_tier(insurer_code: str, tier_rank: int) -> str | None:
    """이 보험사에서 tier_rank(0=실속, 1=표준, 2=고급)에 해당하는 실제 등급명.

    그 등급 상품이 없으면 None이다(예: 메리츠 고급)."""
    names = TIER_PLAN_NAMES.get(insurer_code)
    if not names or tier_rank not in (0, 1, 2):
        return None
    return names[tier_rank]
