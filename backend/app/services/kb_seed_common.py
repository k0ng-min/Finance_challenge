"""
여러 보험사 KB 시드 스크립트가 공유하는 헬퍼.

required_doc_std(표준 청구서류)와 coverage_std(표준 담보)는 보험사 공통이어야 하므로
(각 보험사가 같은 서류 카테고리를 재사용) get_or_create로 중복 생성을 막는다.
"""
from app.models.kb import Insurer, Product, PolicyVersion, CoverageStd, RequiredDocStd


def raw_text_is_grounded(clause_text: str, raw_text: str) -> bool:
    """ClauseTerm.raw_text가 실제 조항 원문의 부분 문자열인지 확인한다.

    clause_spans_gemini._locate_spans와 같은 원칙: 원문에 문자 그대로 존재하지 않는
    발췌는 근거 없는 것으로 보고 거부한다("근거 없는 결과 금지"). ClauseTerm 행을
    만드는 모든 코드는 db.add 전에 이 함수로 검증해야 한다.
    """
    if not clause_text or not raw_text:
        return False
    return raw_text.strip() in clause_text


def get_or_create_coverage_std(db, std_code: str, std_name: str, category: str, is_base: bool) -> CoverageStd:
    obj = db.query(CoverageStd).filter_by(std_code=std_code).first()
    if obj:
        return obj
    obj = CoverageStd(std_code=std_code, std_name=std_name, category=category, is_base=is_base)
    db.add(obj)
    db.flush()
    return obj


def get_or_create_doc_std(db, doc_code: str, doc_name: str, acquire_location: str, note: str) -> RequiredDocStd:
    obj = db.query(RequiredDocStd).filter_by(doc_code=doc_code).first()
    if obj:
        return obj
    obj = RequiredDocStd(doc_code=doc_code, doc_name=doc_name, acquire_location=acquire_location, note=note)
    db.add(obj)
    db.flush()
    return obj


def seed_common_coverage_std(db):
    """MVP 3종 표준담보를 공통으로 보장(get_or_create)한다."""
    return {
        "DEATH_INJURY": get_or_create_coverage_std(db, "DEATH_INJURY", "상해사망·후유장해", "상해", True),
        "OVS_INJ_MED": get_or_create_coverage_std(db, "OVS_INJ_MED", "해외발생 상해의료비", "의료", False),
        "RESCUE": get_or_create_coverage_std(db, "RESCUE", "중대사고 구조송환비용", "구조", False),
    }


def seed_common_doc_std(db):
    """MVP 시드에서 쓰는 표준 청구서류 8종을 공통으로 보장(get_or_create)한다."""
    return {
        "CLAIM_FORM": get_or_create_doc_std(db, "CLAIM_FORM", "보험금 청구서(회사 양식)", "귀국가능", "보험사 홈페이지/앱에서 양식 다운로드 가능"),
        "MEDICAL_EXPENSE_CERT": get_or_create_doc_std(db, "MEDICAL_EXPENSE_CERT", "진료비계산서·영수증", "현지only", "현지 의료기관에서만 원본 발급 가능"),
        "MEDICAL_DETAIL_CERT": get_or_create_doc_std(db, "MEDICAL_DETAIL_CERT", "진료비세부내역서", "현지only", "실손의료비 청구 시 필요"),
        "TREATMENT_CERT": get_or_create_doc_std(db, "TREATMENT_CERT", "입원치료확인서/통원확인서", "현지only", "입원·통원 여부 확인용"),
        "PRESCRIPTION": get_or_create_doc_std(db, "PRESCRIPTION", "의사처방전(처방조제비 포함)", "현지only", "약제비 청구 시 필요"),
        "DISABILITY_CERT": get_or_create_doc_std(db, "DISABILITY_CERT", "장해진단서", "귀국가능", "후유장해 확정 후 국내에서도 발급 가능"),
        "DEATH_CERT": get_or_create_doc_std(db, "DEATH_CERT", "사망진단서", "현지only", "현지 의료기관·관공서 발급, 번역 공증 필요할 수 있음"),
        "ID_CARD": get_or_create_doc_std(db, "ID_CARD", "신분증(청구인)", "공통", "본인이 아닌 경우 인감증명서 또는 본인서명사실확인서 포함"),
    }


def seed_insurer_core(db, *, name, code, official_url,
                       product_name, product_code, channel, sale_start, collected_at,
                       version_label, effective_date, source_url,
                       file_hash=None) -> tuple[Insurer, Product, PolicyVersion]:
    insurer = db.query(Insurer).filter_by(code=code).first()
    if insurer:
        return None, None, None  # 이미 시드됨 (호출부에서 스킵 처리)

    insurer = Insurer(name=name, code=code, is_underwriter=True, official_url=official_url)
    db.add(insurer)
    db.flush()

    product = Product(
        insurer_id=insurer.insurer_id, name=product_name, product_code=product_code,
        channel=channel, sale_start=sale_start, sale_end=None,
        collected_at=collected_at, review_status="raw",
    )
    db.add(product)
    db.flush()

    pv = PolicyVersion(
        product_id=product.product_id, version_label=version_label,
        effective_date=effective_date, approval_no=None, source_url=source_url, file_hash=file_hash,
    )
    db.add(pv)
    db.flush()

    return insurer, product, pv
"""
여러 보험사 KB 시드 스크립트가 공유하는 헬퍼.

required_doc_std(표준 청구서류)와 coverage_std(표준 담보)는 보험사 공통이어야 하므로
(각 보험사가 같은 서류 카테고리를 재사용) get_or_create로 중복 생성을 막는다.
"""
from app.models.kb import Insurer, Product, PolicyVersion, CoverageStd, RequiredDocStd


def raw_text_is_grounded(clause_text: str, raw_text: str) -> bool:
    """ClauseTerm.raw_text가 실제 조항 원문의 부분 문자열인지 확인한다.

    clause_spans_gemini._locate_spans와 같은 원칙: 원문에 문자 그대로 존재하지 않는
    발췌는 근거 없는 것으로 보고 거부한다("근거 없는 결과 금지"). ClauseTerm 행을
    만드는 모든 코드는 db.add 전에 이 함수로 검증해야 한다.
    """
    if not clause_text or not raw_text:
        return False
    return raw_text.strip() in clause_text


def get_or_create_coverage_std(db, std_code: str, std_name: str, category: str, is_base: bool) -> CoverageStd:
    obj = db.query(CoverageStd).filter_by(std_code=std_code).first()
    if obj:
        return obj
    obj = CoverageStd(std_code=std_code, std_name=std_name, category=category, is_base=is_base)
    db.add(obj)
    db.flush()
    return obj


def get_or_create_doc_std(db, doc_code: str, doc_name: str, acquire_location: str, note: str) -> RequiredDocStd:
    obj = db.query(RequiredDocStd).filter_by(doc_code=doc_code).first()
    if obj:
        return obj
    obj = RequiredDocStd(doc_code=doc_code, doc_name=doc_name, acquire_location=acquire_location, note=note)
    db.add(obj)
    db.flush()
    return obj


def seed_common_coverage_std(db):
    """MVP 3종 표준담보를 공통으로 보장(get_or_create)한다."""
    return {
        "DEATH_INJURY": get_or_create_coverage_std(db, "DEATH_INJURY", "상해사망·후유장해", "상해", True),
        "OVS_INJ_MED": get_or_create_coverage_std(db, "OVS_INJ_MED", "해외발생 상해의료비", "의료", False),
        "RESCUE": get_or_create_coverage_std(db, "RESCUE", "중대사고 구조송환비용", "구조", False),
    }


def seed_common_doc_std(db):
    """MVP 시드에서 쓰는 표준 청구서류 8종을 공통으로 보장(get_or_create)한다."""
    return {
        "CLAIM_FORM": get_or_create_doc_std(db, "CLAIM_FORM", "보험금 청구서(회사 양식)", "귀국가능", "보험사 홈페이지/앱에서 양식 다운로드 가능"),
        "MEDICAL_EXPENSE_CERT": get_or_create_doc_std(db, "MEDICAL_EXPENSE_CERT", "진료비계산서·영수증", "현지only", "현지 의료기관에서만 원본 발급 가능"),
        "MEDICAL_DETAIL_CERT": get_or_create_doc_std(db, "MEDICAL_DETAIL_CERT", "진료비세부내역서", "현지only", "실손의료비 청구 시 필요"),
        "TREATMENT_CERT": get_or_create_doc_std(db, "TREATMENT_CERT", "입원치료확인서/통원확인서", "현지only", "입원·통원 여부 확인용"),
        "PRESCRIPTION": get_or_create_doc_std(db, "PRESCRIPTION", "의사처방전(처방조제비 포함)", "현지only", "약제비 청구 시 필요"),
        "DISABILITY_CERT": get_or_create_doc_std(db, "DISABILITY_CERT", "장해진단서", "귀국가능", "후유장해 확정 후 국내에서도 발급 가능"),
        "DEATH_CERT": get_or_create_doc_std(db, "DEATH_CERT", "사망진단서", "현지only", "현지 의료기관·관공서 발급, 번역 공증 필요할 수 있음"),
        "ID_CARD": get_or_create_doc_std(db, "ID_CARD", "신분증(청구인)", "공통", "본인이 아닌 경우 인감증명서 또는 본인서명사실확인서 포함"),
    }


def seed_insurer_core(db, *, name, code, official_url,
                       product_name, product_code, channel, sale_start, collected_at,
                       version_label, effective_date, source_url) -> tuple[Insurer, Product, PolicyVersion]:
    insurer = db.query(Insurer).filter_by(code=code).first()
    if insurer:
        return None, None, None  # 이미 시드됨 (호출부에서 스킵 처리)

    insurer = Insurer(name=name, code=code, is_underwriter=True, official_url=official_url)
    db.add(insurer)
    db.flush()

    product = Product(
        insurer_id=insurer.insurer_id, name=product_name, product_code=product_code,
        channel=channel, sale_start=sale_start, sale_end=None,
        collected_at=collected_at, review_status="raw",
    )
    db.add(product)
    db.flush()

    pv = PolicyVersion(
        product_id=product.product_id, version_label=version_label,
        effective_date=effective_date, approval_no=None, source_url=source_url, file_hash=None,
    )
    db.add(pv)
    db.flush()

    return insurer, product, pv
