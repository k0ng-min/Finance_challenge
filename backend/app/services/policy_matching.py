"""
내 보험 보관함 등록 시 사용자가 입력한 원문(보험사명/상품명/담보명)을 KB와 매칭한다.

담보명 매칭은 app.services.nlu의 NLUEngine(현재 RuleBasedNLU)을 사용한다 — 나중에
자체 경량 모델로 교체될 자리이므로, 이 모듈은 NLUEngine 인터페이스에만 의존하고
구체 구현을 직접 import하지 않는다.

매칭 실패 시 raw_name만 저장하고 std/coverage 연결은 null로 둔다(new.md user_coverage
스키마가 이를 nullable로 정의한 이유). 약관에 존재하지만 사용자가 실제 가입하지
않은 담보는 추천하지 않는다는 ne.md 원칙의 전제가 되는 매칭이므로, 근거 없는 매칭을
만들지 않는다 — confidence가 낮으면 매칭 안 함으로 처리한다.
"""
from sqlalchemy.orm import Session

from app.models.kb import Insurer, Product, PolicyVersion, Coverage, CoverageStd
from app.services.nlu import NLUEngine

COVERAGE_MATCH_THRESHOLD = 0.45


def match_insurer(db: Session, insurer_name_raw: str) -> Insurer | None:
    if not insurer_name_raw:
        return None
    name = insurer_name_raw.strip()
    insurer = db.query(Insurer).filter(Insurer.name == name).first()
    if insurer:
        return insurer
    insurer = db.query(Insurer).filter(Insurer.code == name.upper()).first()
    if insurer:
        return insurer
    # 부분일치 (예: "카카오페이" -> "카카오페이손해보험")
    for candidate in db.query(Insurer).all():
        if name in candidate.name or candidate.name.replace("손해보험", "").replace("해상보험", "").strip() in name:
            return candidate
    return None


def match_product_and_version(db: Session, insurer: Insurer, product_name_raw: str) -> tuple[Product | None, PolicyVersion | None]:
    products = db.query(Product).filter(Product.insurer_id == insurer.insurer_id).all()
    if not products:
        return None, None
    product = None
    if product_name_raw:
        for p in products:
            if product_name_raw.strip() in p.name or p.name in product_name_raw.strip():
                product = p
                break
    if product is None:
        product = products[0]  # MVP: 보험사당 상품 1개만 시드되어 있으므로 기본값 사용
    pv = (
        db.query(PolicyVersion)
        .filter(PolicyVersion.product_id == product.product_id)
        .order_by(PolicyVersion.effective_date.desc().nullslast())
        .first()
    )
    return product, pv


def match_coverage(db: Session, nlu: NLUEngine, raw_name: str, policy_version: PolicyVersion | None):
    """
    반환: (coverage_id|None, coverage_std_id|None, confidence)
    policy_version이 있으면 그 안의 실제 coverage 후보와 매칭(가장 정확),
    없으면 전역 coverage_std 목록과 매칭한다(가입보험이 KB에 없는 상품인 경우).
    """
    if policy_version is not None:
        candidates = db.query(Coverage).filter(Coverage.policy_version_id == policy_version.policy_version_id).all()
        # 약관 원문 담보명(raw_name)은 보통 길고 boilerplate가 섞여 있어 사용자가 입력한 짧은 이름과
        # 문자열유사도가 낮게 나온다. 표준 담보명(std_name, 있으면)도 같은 coverage를 가리키는
        # 별도 후보로 넣고 둘 중 더 잘 맞는 쪽으로 매칭한다.
        pairs = []
        for c in candidates:
            pairs.append((str(c.coverage_id), c.raw_name))
            if c.coverage_std:
                pairs.append((str(c.coverage_id), c.coverage_std.std_name))
        best_key, confidence = nlu.normalize_coverage_name(raw_name, pairs)
        if best_key is not None and confidence >= COVERAGE_MATCH_THRESHOLD:
            cov = db.get(Coverage, int(best_key))
            return cov.coverage_id, cov.coverage_std_id, confidence
        return None, None, confidence

    std_list = db.query(CoverageStd).all()
    pairs = [(s.std_code, s.std_name) for s in std_list]
    best_code, confidence = nlu.normalize_coverage_name(raw_name, pairs)
    if best_code is not None and confidence >= COVERAGE_MATCH_THRESHOLD:
        std = db.query(CoverageStd).filter_by(std_code=best_code).first()
        return None, std.coverage_std_id, confidence
    return None, None, confidence
