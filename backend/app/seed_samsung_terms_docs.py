"""
삼성화재: ClauseTerm(조항의 수치화 조건) + CoverageDocMap(필요서류) 채우기

ClauseTerm: 조항 원문에서 찾은 숫자 조건들 (지급한도/자기부담금/면책일수/지연기준시간 등)
- 모든 raw_text는 clause.text의 부분 문자열이어야 함 (raw_text_is_grounded 검증)
- term_type은 고정 어휘만 사용: 지급한도/자기부담금/지연기준시간/보상일수한도/면책일수/1일당지급액

CoverageDocMap: 각 담보와 필요서류의 매핑
- CLAIM_FORM(청구서) + ID_CARD(신분증)는 모든 담보의 기본
- 담보 성격별 추가 서류 매핑 (의료비 관련, 사망, 도난, 항공기 지연 등)
- idempotent: 이미 있는 매핑은 스킵

건너뜀:
- Clause 중 숫자가 없거나 이미 매핑된 ClauseTerm은 생략
- ClauseTerm raw_text 검증 실패 시 로그만 남기고 건너뜀
"""
import re
from app.database import SessionLocal
from app import models
from app.models.kb import (
    Insurer, Product, PolicyVersion, Coverage, Clause, ClauseTerm,
    RequiredDocStd, CoverageDocMap
)
from app.services.kb_seed_common import raw_text_is_grounded, get_or_create_doc_std


def extract_amount_with_unit(text: str) -> list[dict]:
    """텍스트에서 금액/숫자 조건들을 찾는다.

    반환: [{'value': 숫자, 'unit': 단위, 'raw': 원문발췌, 'context': 조건 설명}, ...]
    """
    results = []

    # 패턴들: USD, 원화, 일수, 회수, 퍼센트 등
    patterns = [
        # USD/통화
        (r'US\s*\$\s*([\d,\.]+)', 'USD'),
        # 만원, 천원 등 한글 금액
        (r'([\d,]+)\s*만원', '만원'),
        (r'([\d,]+)\s*천원', '천원'),
        (r'([\d,]+)\s*원', '원'),
        # 일수/박수
        (r'([\d]+)\s*일(?:까지|동안|이상)', '일'),
        (r'([\d]+)\s*박(?:을|을\s*한도)', '박'),
        # 시간
        (r'([\d]+)\s*시간\s*이상', '시간'),
        # 회수
        (r'([\d]+)\s*회(?:까지|동안)', '회'),
        # 퍼센트
        (r'([\d]+)\s*%', '%'),
    ]

    for pattern, unit in patterns:
        for match in re.finditer(pattern, text):
            try:
                value_str = match.group(1).replace(',', '')
                value = float(value_str)
                raw = match.group(0)
                # 문맥 추출: match 주변 50글자
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                results.append({
                    'value': value,
                    'unit': unit,
                    'raw': raw,
                    'context': context
                })
            except (ValueError, IndexError):
                pass

    return results


def extract_clause_terms(clause: Clause) -> list[dict]:
    """Clause에서 ClauseTerm 후보들을 추출한다.

    반환: [{'term_type': str, 'value_num': float, 'unit': str, 'condition_text': str,
             'raw_text': str, 'basis': str or None}, ...]
    """
    text = clause.text
    terms = []

    # 1) 지급한도 — "한도로", "한도" 근처의 숫자
    limit_pattern = r'([\d,\.]+)\s*(만원|천원|원|USD|US\$|달러).*?한도'
    for match in re.finditer(limit_pattern, text):
        raw = match.group(0)
        if raw_text_is_grounded(text, raw):
            value_str = match.group(1).replace(',', '')
            try:
                value = float(value_str)
                unit = '원' if '원' in match.group(2) else 'USD'
                terms.append({
                    'term_type': '지급한도',
                    'value_num': value,
                    'unit': unit,
                    'condition_text': f"한도: {raw[:80]}",
                    'raw_text': raw,
                    'basis': None
                })
            except ValueError:
                pass

    # 2) 보상일수한도 — "180일", "20일" 등 (시간 기준이 아닌 경우)
    days_pattern = r'([\d]+)\s*일(?:까지|동안)\s*(?:만|한도로|보상)'
    for match in re.finditer(days_pattern, text):
        raw = match.group(0)
        if raw_text_is_grounded(text, raw):
            try:
                value = float(match.group(1))
                terms.append({
                    'term_type': '보상일수한도',
                    'value_num': value,
                    'unit': '일',
                    'condition_text': f"보상기간: {raw}",
                    'raw_text': raw,
                    'basis': None
                })
            except ValueError:
                pass

    # 3) 1일당지급액 — "1일당 70,000원", "1일 XX원"
    per_day_pattern = r'(?:1\s*일당|1\s*일\s*)([\d,\.]+)\s*(?:원|USD|달러)'
    for match in re.finditer(per_day_pattern, text):
        raw = match.group(0)
        if raw_text_is_grounded(text, raw):
            value_str = match.group(1).replace(',', '')
            try:
                value = float(value_str)
                unit = '원' if '원' in match.group(0) else 'USD'
                terms.append({
                    'term_type': '1일당지급액',
                    'value_num': value,
                    'unit': unit,
                    'condition_text': f"일당: {raw}",
                    'raw_text': raw,
                    'basis': '정액'
                })
            except ValueError:
                pass

    # 4) 지연기준시간 — "4시간 이상", "12시간 이상"
    delay_hours_pattern = r'([\d]+)\s*시간\s*이상'
    for match in re.finditer(delay_hours_pattern, text):
        raw = match.group(0)
        if raw_text_is_grounded(text, raw):
            try:
                value = float(match.group(1))
                terms.append({
                    'term_type': '지연기준시간',
                    'value_num': value,
                    'unit': '시간',
                    'condition_text': f"지연 기준: {raw}",
                    'raw_text': raw,
                    'basis': None
                })
            except ValueError:
                pass

    # 5) 면책일수 — "2일 이상 입원"
    wait_days_pattern = r'([\d]+)\s*일\s*(?:이상\s*)?(?:입원|통원)'
    for match in re.finditer(wait_days_pattern, text):
        raw = match.group(0)
        if raw_text_is_grounded(text, raw):
            try:
                value = float(match.group(1))
                terms.append({
                    'term_type': '면책일수',
                    'value_num': value,
                    'unit': '일',
                    'condition_text': f"입원/통원 최소 기준: {raw}",
                    'raw_text': raw,
                    'basis': None
                })
            except ValueError:
                pass

    # 6) 자기부담금 — "10만원 공제", "공제 후 10%" 등
    # 복합 조건이 많으므로 명확한 경우만
    deductible_pattern = r'([\d,]+)\s*(?:만|천)?원\s*(?:공제|자기부담)'
    for match in re.finditer(deductible_pattern, text):
        raw = match.group(0)
        if raw_text_is_grounded(text, raw):
            value_str = match.group(1).replace(',', '')
            try:
                value = float(value_str)
                terms.append({
                    'term_type': '자기부담금',
                    'value_num': value,
                    'unit': '원',
                    'condition_text': f"자기부담: {raw}",
                    'raw_text': raw,
                    'basis': None
                })
            except ValueError:
                pass

    return terms


def seed_clause_terms(db):
    """삼성화재의 모든 Clause에서 ClauseTerm을 추출하고 저장한다."""
    samsung = db.query(Insurer).filter_by(code="SAMSUNG").first()
    if not samsung:
        print("삼성화재 없음")
        return 0

    pv = (db.query(PolicyVersion)
          .join(Product, Product.product_id == PolicyVersion.product_id)
          .filter(Product.insurer_id == samsung.insurer_id)
          .first())
    if not pv:
        print("PolicyVersion 없음")
        return 0

    clauses = db.query(Clause).filter_by(policy_version_id=pv.policy_version_id).all()

    added_count = 0
    for clause in clauses:
        terms = extract_clause_terms(clause)
        for term_dict in terms:
            # 중복 체크
            existing = (db.query(ClauseTerm)
                       .filter_by(
                           clause_id=clause.clause_id,
                           term_type=term_dict['term_type'],
                           raw_text=term_dict['raw_text']
                       )
                       .first())
            if existing:
                continue

            # raw_text 검증
            if not raw_text_is_grounded(clause.text, term_dict['raw_text']):
                print(f"  [SKIP] Clause {clause.clause_id}: raw_text not grounded: {term_dict['raw_text'][:50]}")
                continue

            # 저장
            ct = ClauseTerm(
                clause_id=clause.clause_id,
                term_type=term_dict['term_type'],
                value_num=term_dict['value_num'],
                unit=term_dict['unit'],
                basis=term_dict['basis'],
                condition_text=term_dict['condition_text'],
                raw_text=term_dict['raw_text'],
                confidence=None
            )
            db.add(ct)
            added_count += 1

    db.commit()
    return added_count


def seed_coverage_doc_map(db):
    """삼성화재의 모든 담보에 필요서류를 매핑한다.

    원칙:
    1. 모든 담보에 CLAIM_FORM + ID_CARD 기본 적용
    2. 담보 성격에 따라 추가 서류 적용
    3. idempotent: 이미 있는 매핑은 스킵
    """
    samsung = db.query(Insurer).filter_by(code="SAMSUNG").first()
    if not samsung:
        return 0, []

    pv = (db.query(PolicyVersion)
          .join(Product, Product.product_id == PolicyVersion.product_id)
          .filter(Product.insurer_id == samsung.insurer_id)
          .first())
    if not pv:
        return 0, []

    # 필수 서류 미리 생성/조회
    doc_standards = {}
    # 의료 관련 (기존 8개)
    doc_standards['CLAIM_FORM'] = get_or_create_doc_std(
        db, 'CLAIM_FORM', '보험금 청구서(회사 양식)', '귀국가능',
        '보험사 홈페이지/앱에서 양식 다운로드 가능'
    )
    doc_standards['ID_CARD'] = get_or_create_doc_std(
        db, 'ID_CARD', '신분증(청구인)', '공통',
        '본인이 아닌 경우 인감증명서 또는 본인서명사실확인서 포함'
    )
    doc_standards['MEDICAL_EXPENSE_CERT'] = get_or_create_doc_std(
        db, 'MEDICAL_EXPENSE_CERT', '진료비계산서·영수증', '현지only',
        '현지 의료기관에서만 원본 발급 가능'
    )
    doc_standards['MEDICAL_DETAIL_CERT'] = get_or_create_doc_std(
        db, 'MEDICAL_DETAIL_CERT', '진료비세부내역서', '현지only',
        '실손의료비 청구 시 필요'
    )
    doc_standards['TREATMENT_CERT'] = get_or_create_doc_std(
        db, 'TREATMENT_CERT', '입원치료확인서/통원확인서', '현지only',
        '입원·통원 여부 확인용'
    )
    doc_standards['PRESCRIPTION'] = get_or_create_doc_std(
        db, 'PRESCRIPTION', '의사처방전(처방조제비 포함)', '현지only',
        '약제비 청구 시 필요'
    )
    doc_standards['DISABILITY_CERT'] = get_or_create_doc_std(
        db, 'DISABILITY_CERT', '장해진단서', '귀국가능',
        '후유장해 확정 후 국내에서도 발급 가능'
    )
    doc_standards['DEATH_CERT'] = get_or_create_doc_std(
        db, 'DEATH_CERT', '사망진단서', '현지only',
        '현지 의료기관·관공서 발급, 번역 공증 필요할 수 있음'
    )

    # 비의료 관련 (새로 추가)
    doc_standards['POLICE_REPORT'] = get_or_create_doc_std(
        db, 'POLICE_REPORT', '현지 경찰 신고확인서(도난·분실·배상책임 사고)', '현지only',
        '도난·분실·배상책임 사고 시 현지 경찰 신고 필수'
    )
    doc_standards['FLIGHT_DELAY_CERT'] = get_or_create_doc_std(
        db, 'FLIGHT_DELAY_CERT', '항공기 지연·결항 확인서(항공사 발급)', '현지only',
        '항공사에서만 발급 가능'
    )
    doc_standards['BAGGAGE_IRREGULARITY'] = get_or_create_doc_std(
        db, 'BAGGAGE_IRREGULARITY', '수하물 지연·분실 확인서(항공사 발급, PIR)', '현지only',
        'Property Irregularity Report(PIR): 항공사 수하물 관련 공식 문서'
    )
    doc_standards['PASSPORT_REISSUE_RECEIPT'] = get_or_create_doc_std(
        db, 'PASSPORT_REISSUE_RECEIPT', '여권(여행증명서) 재발급 영수증·확인서', '귀국가능',
        '현지 또는 귀국 후 발급 가능'
    )
    doc_standards['LIABILITY_EVIDENCE'] = get_or_create_doc_std(
        db, 'LIABILITY_EVIDENCE', '배상책임 관련 서류(합의서·손해배상 청구서·상대방 피해 확인서류)', '귀국가능',
        '배상책임 사고 관련 증거 자료'
    )

    coverages = db.query(Coverage).filter_by(policy_version_id=pv.policy_version_id).all()

    added_count = 0
    new_doc_codes = []

    for coverage in coverages:
        raw_name = coverage.raw_name.lower()

        # 기본 서류 (모든 담보)
        for doc_code in ['CLAIM_FORM', 'ID_CARD']:
            existing = (db.query(CoverageDocMap)
                       .filter_by(coverage_id=coverage.coverage_id,
                                 required_doc_std_id=doc_standards[doc_code].required_doc_std_id)
                       .first())
            if not existing:
                db.add(CoverageDocMap(
                    coverage_id=coverage.coverage_id,
                    required_doc_std_id=doc_standards[doc_code].required_doc_std_id,
                    is_mandatory=True,
                    clause_id=None
                ))
                added_count += 1

        # 담보 성격별 추가 서류
        docs_to_add = []

        if '의료비' in raw_name or '치료' in raw_name:
            # 의료비 관련 담보
            docs_to_add.extend(['MEDICAL_EXPENSE_CERT', 'MEDICAL_DETAIL_CERT', 'TREATMENT_CERT'])
            if '처방' in raw_name or '약' in raw_name:
                docs_to_add.append('PRESCRIPTION')

        if '사망' in raw_name:
            docs_to_add.append('DEATH_CERT')

        if '장해' in raw_name or '후유' in raw_name:
            docs_to_add.append('DISABILITY_CERT')

        if '도난' in raw_name or '분실' in raw_name or '휴대품' in raw_name:
            docs_to_add.extend(['POLICE_REPORT'])
            if '분실' in raw_name:
                docs_to_add.append('PASSPORT_REISSUE_RECEIPT')

        if '항공기' in raw_name or '항공' in raw_name or '비행' in raw_name:
            docs_to_add.append('FLIGHT_DELAY_CERT')

        if '수하물' in raw_name or '짐' in raw_name:
            docs_to_add.append('BAGGAGE_IRREGULARITY')

        if '여권' in raw_name:
            docs_to_add.extend(['PASSPORT_REISSUE_RECEIPT', 'POLICE_REPORT'])

        if '배상' in raw_name or '책임' in raw_name:
            docs_to_add.extend(['POLICE_REPORT', 'LIABILITY_EVIDENCE'])

        # 중복 제거
        docs_to_add = list(set(docs_to_add))

        # 추가 서류 매핑
        for doc_code in docs_to_add:
            if doc_code not in doc_standards:
                continue
            existing = (db.query(CoverageDocMap)
                       .filter_by(coverage_id=coverage.coverage_id,
                                 required_doc_std_id=doc_standards[doc_code].required_doc_std_id)
                       .first())
            if not existing:
                db.add(CoverageDocMap(
                    coverage_id=coverage.coverage_id,
                    required_doc_std_id=doc_standards[doc_code].required_doc_std_id,
                    is_mandatory=True,
                    clause_id=None
                ))
                added_count += 1
                if doc_code not in new_doc_codes:
                    new_doc_codes.append(doc_code)

    db.commit()
    return added_count, new_doc_codes


def run():
    """idempotent한 실행 함수."""
    db = SessionLocal()
    try:
        print("=" * 60)
        print("삼성화재 ClauseTerm + CoverageDocMap 채우기")
        print("=" * 60)

        # 1) ClauseTerm 추출
        print("\n[1/2] ClauseTerm 추출 중...")
        clause_terms_added = seed_clause_terms(db)
        print(f"  추가된 ClauseTerm: {clause_terms_added}개")

        # 2) CoverageDocMap 매핑
        print("\n[2/2] CoverageDocMap 매핑 중...")
        doc_maps_added, new_docs = seed_coverage_doc_map(db)
        print(f"  추가된 CoverageDocMap: {doc_maps_added}개")
        if new_docs:
            print(f"  새로 사용된 RequiredDocStd 코드: {', '.join(sorted(set(new_docs)))}")

        print("\n" + "=" * 60)
        print("완료")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    run()
