"""
현대해상(HYUNDAI) ClauseTerm(금액·한도 수치화) + CoverageDocMap(필요서류) 채우기

ClauseTerm 추출 전략:
  1. 모든 Clause.text를 훑으면서 숫자 패턴 찾기:
     - "XXX원 한도/이상/까지"
     - "US $X 한도"
     - "X일" (면책일수, 보상일수)
     - "X시간 이상" (지연 기준)
     - "X%" (자기부담금)
     - "1일당 XXX원" (정액)
  2. 각 숫자마다 raw_text_is_grounded()로 원문 검증
  3. 원문에 명확한 서류명이 있으면 이를 근거로 CoverageDocMap 구성

CoverageDocMap 채우기 전략:
  1. 기존 RequiredDocStd 재사용 (CLAIM_FORM, ID_CARD, MEDICAL_* 등)
  2. 새 코드 생성 (POLICE_REPORT, FLIGHT_DELAY_CERT, BAGGAGE_IRREGULARITY, PASSPORT_REISSUE_RECEIPT, LIABILITY_EVIDENCE)
  3. 모든 새 담보(원래 4개 제외)에 최소 CLAIM_FORM+ID_CARD 연결
  4. 담보 성격에 맞춰 추가 서류 연결

건너뜀:
  - 계약행정 조항 (서류 요청, 관리 규정 등)
  - 순수 지급사유 설명 (숫자 없음)
  - 표 형식 깨짐으로 수치를 명확히 뽑을 수 없는 조항
"""
import re
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Insurer, Product, PolicyVersion, Clause, Coverage, ClauseTerm,
    CoverageDocMap, IncidentType, ClauseIncidentMap
)
from app.services.kb_seed_common import (
    raw_text_is_grounded, get_or_create_doc_std,
    seed_common_doc_std
)


def _extract_numbers(text: str):
    """조항 텍스트에서 숫자 패턴을 찾는 헬퍼.

    Returns: list of (term_type, value_num, unit, condition_text, raw_text)
    """
    results = []
    found_raw_texts = set()  # 중복 방지

    # 1. "US $X" 한도 패턴
    pattern_usd = r'US\s*\$[\d,]+(?:\.\d+)?'
    for match in re.finditer(pattern_usd, text):
        raw_text = match.group(0)
        if raw_text in found_raw_texts:
            continue

        # 숫자만 추출
        num_str = re.sub(r'[^\d.]', '', raw_text)
        value_num = float(num_str) if num_str else None

        # 주변 맥락 확인
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        context = text[start:end]

        if ('한도' in context or '이상' in context) and value_num:
            results.append((
                '지급한도', value_num, 'USD',
                f"US ${value_num}",
                raw_text
            ))
            found_raw_texts.add(raw_text)

    # 2. "X만원 한도/이상/까지" 또는 "XX,XXX원 한도/이상" 패턴
    pattern_krw_explicit = r'(\d+(?:,\d{3})*|\d+)만?원\s*(?:한도|이상|이내|까지|이하)?'
    for match in re.finditer(pattern_krw_explicit, text):
        raw_text = match.group(0)
        if raw_text in found_raw_texts:
            continue

        num_str = match.group(1).replace(',', '')
        try:
            value_num = float(num_str)
        except ValueError:
            continue

        # "만원"인 경우 처리
        if '만' in raw_text:
            value_num = value_num * 10000

        # 주변 맥락
        start = max(0, match.start() - 30)
        end = min(len(text), match.end() + 30)
        context = text[start:end]

        term_type = None
        if '공제' in context or '자기부담' in context:
            term_type = '자기부담금'
        elif any(x in raw_text for x in ['한도', '이내', '까지', '이상']):
            term_type = '지급한도'

        if term_type and value_num:
            results.append((
                term_type, value_num, '원',
                context.strip()[:100],
                raw_text
            ))
            found_raw_texts.add(raw_text)

    # 3. "X일" 패턴 (면책일수, 보상일수 구분)
    pattern_day = r'(\d+)일'
    for match in re.finditer(pattern_day, text):
        raw_text = match.group(0)
        if raw_text in found_raw_texts:
            continue

        value_num = float(match.group(1))

        start = max(0, match.start() - 60)
        end = min(len(text), match.end() + 60)
        context = text[start:end]

        term_type = None
        if '면책' in context or '입원' in context or '이상' in raw_text:
            term_type = '면책일수'
        elif '보상' in context or ('한도' in context or '까지' in context):
            term_type = '보상일수한도'

        if term_type:
            results.append((
                term_type, value_num, '일',
                context.strip()[:100],
                raw_text
            ))
            found_raw_texts.add(raw_text)

    # 4. "X시간 이상" 패턴 (항공기/수하물 지연)
    pattern_hour = r'(\d+)시간\s*(?:이상)?'
    for match in re.finditer(pattern_hour, text):
        raw_text = match.group(0)
        if raw_text in found_raw_texts:
            continue

        value_num = float(match.group(1))

        start = max(0, match.start() - 40)
        end = min(len(text), match.end() + 40)
        context = text[start:end]

        if '지연' in context or '결항' in context:
            results.append((
                '지연기준시간', value_num, '시간',
                context.strip()[:100],
                raw_text
            ))
            found_raw_texts.add(raw_text)

    # 5. "X%" 자기부담금 패턴
    pattern_pct = r'(\d+(?:\.\d+)?)%'
    for match in re.finditer(pattern_pct, text):
        raw_text = match.group(0)
        if raw_text in found_raw_texts:
            continue

        value_num = float(match.group(1))

        start = max(0, match.start() - 40)
        end = min(len(text), match.end() + 40)
        context = text[start:end]

        if '공제' in context or '자기부담' in context:
            results.append((
                '자기부담금', value_num, '%',
                context.strip()[:100],
                raw_text
            ))
            found_raw_texts.add(raw_text)

    # 6. "1일당 XXX원" 정액 패턴
    pattern_daily = r'1일당\s*(\d+(?:,\d{3})*|\d+)원'
    for match in re.finditer(pattern_daily, text):
        raw_text = match.group(0)
        if raw_text in found_raw_texts:
            continue

        num_str = match.group(1).replace(',', '')
        try:
            value_num = float(num_str)
        except ValueError:
            continue

        start = max(0, match.start() - 30)
        end = min(len(text), match.end() + 30)
        context = text[start:end]

        results.append((
            '1일당지급액', value_num, '원',
            context.strip()[:100],
            raw_text
        ))
        found_raw_texts.add(raw_text)

    return results


def _seed_clause_terms(db, pv):
    """모든 Clause에서 ClauseTerm 추출."""
    clauses = db.query(Clause).filter_by(policy_version_id=pv.policy_version_id).all()

    term_count_by_type = {}
    added_count = 0

    for clause in clauses:
        if not clause.text:
            continue

        # 이미 존재하는 ClauseTerm 확인해서 중복 방지
        existing_terms = db.query(ClauseTerm).filter_by(clause_id=clause.clause_id).all()
        existing_raw_texts = {t.raw_text for t in existing_terms}

        # 이 조항에서 숫자 추출
        extracted = _extract_numbers(clause.text)

        for term_type, value_num, unit, condition_text, raw_text in extracted:
            # 중복 체크
            if raw_text in existing_raw_texts:
                continue

            # raw_text 검증
            if not raw_text_is_grounded(clause.text, raw_text):
                continue

            # ClauseTerm 생성
            term = ClauseTerm(
                clause_id=clause.clause_id,
                term_type=term_type,
                value_num=value_num,
                unit=unit,
                basis=None,  # 의료비 관련 조항에서만 실손/정액 구분 가능
                condition_text=condition_text[:200] if condition_text else None,
                raw_text=raw_text,
                confidence=0.7  # 자동 추출이므로 신뢰도 낮게
            )

            db.add(term)
            added_count += 1
            term_count_by_type[term_type] = term_count_by_type.get(term_type, 0) + 1

    db.commit()
    return added_count, term_count_by_type


def _seed_coverage_doc_map(db, pv):
    """모든 Coverage에 필요서류 매핑.

    규칙:
    1. 모든 담보에 CLAIM_FORM + ID_CARD 기본 추가
    2. 담보 이름에 따라 추가 서류 결정
    3. 이미 매핑된 것은 스킵 (idempotent)
    """
    # 기존 and 새로운 RequiredDocStd 확보
    doc_stds = seed_common_doc_std(db)

    # 새로 만들 서류들
    doc_stds['POLICE_REPORT'] = get_or_create_doc_std(
        db, 'POLICE_REPORT', '현지 경찰 신고확인서(도난·분실·배상책임 사고)',
        '현지only', '도난/분실/배상책임 사고 시 현지 경찰서에서 발급'
    )
    doc_stds['FLIGHT_DELAY_CERT'] = get_or_create_doc_std(
        db, 'FLIGHT_DELAY_CERT', '항공기 지연·결항 확인서(항공사 발급)',
        '귀국가능', '항공사 발급, 탑승권 또는 예약 확인서 함께 제출'
    )
    doc_stds['BAGGAGE_IRREGULARITY'] = get_or_create_doc_std(
        db, 'BAGGAGE_IRREGULARITY', '수하물 지연·분실 확인서(항공사 발급, PIR)',
        '현지only', '수하물 지연/분실 시 항공사 PIR(Property Irregularity Report) 발급'
    )
    doc_stds['PASSPORT_REISSUE_RECEIPT'] = get_or_create_doc_std(
        db, 'PASSPORT_REISSUE_RECEIPT', '여권(여행증명서) 재발급 영수증·확인서',
        '귀국가능', '여권 분실 시 재발급 영수증 또는 여행증명서 재발급 확인서'
    )
    doc_stds['LIABILITY_EVIDENCE'] = get_or_create_doc_std(
        db, 'LIABILITY_EVIDENCE', '배상책임 관련 서류(합의서·손해배상 청구서·상대방 피해 확인서류)',
        '현지only', '배상책임 사고 시 상대방과의 합의서, 손해배상 청구서, 상대방 피해 증명서류'
    )

    # 담보별 추가 서류 매핑 규칙
    coverage_additional_docs = {
        # 의료비 관련
        ('상해', '의료'): ['MEDICAL_EXPENSE_CERT', 'MEDICAL_DETAIL_CERT', 'TREATMENT_CERT'],
        ('질병',): ['MEDICAL_EXPENSE_CERT', 'MEDICAL_DETAIL_CERT', 'TREATMENT_CERT', 'PRESCRIPTION'],

        # 사망/장해
        ('사망',): ['DEATH_CERT'],
        ('장해', '후유'): ['DISABILITY_CERT'],

        # 도난/분실
        ('도난', '분실', '자택'): ['POLICE_REPORT'],
        ('휴대품',): ['POLICE_REPORT'],

        # 항공기/수하물
        ('항공기', '지연', '결항'): ['FLIGHT_DELAY_CERT'],
        ('수하물', '짐'): ['BAGGAGE_IRREGULARITY'],

        # 여권/배상
        ('여권',): ['PASSPORT_REISSUE_RECEIPT', 'POLICE_REPORT'],
        ('배상책임', '배상'): ['LIABILITY_EVIDENCE', 'POLICE_REPORT'],

        # 식중독
        ('식중독',): ['MEDICAL_EXPENSE_CERT', 'MEDICAL_DETAIL_CERT', 'POLICE_REPORT'],
    }

    coverages = db.query(Coverage).filter_by(policy_version_id=pv.policy_version_id).all()
    added_count = 0

    for coverage in coverages:
        # 이미 이 담보에 매핑된 doc_code 조회
        existing_maps = db.query(CoverageDocMap).filter_by(coverage_id=coverage.coverage_id).all()
        from app.models.kb import RequiredDocStd
        existing_doc_codes = set()
        for existing_map in existing_maps:
            doc_std = db.query(RequiredDocStd).filter_by(
                required_doc_std_id=existing_map.required_doc_std_id
            ).first()
            if doc_std:
                existing_doc_codes.add(doc_std.doc_code)

        # 추가할 서류 목록 결정
        docs_to_add = ['CLAIM_FORM', 'ID_CARD']  # 기본 서류

        # 담보 이름에 따라 추가 서류 선택
        coverage_name = coverage.raw_name.lower()
        for keywords, docs in coverage_additional_docs.items():
            if any(keyword in coverage_name for keyword in keywords):
                docs_to_add.extend(docs)

        # 중복 제거
        docs_to_add = list(set(docs_to_add))

        # 추가
        for doc_code in docs_to_add:
            if doc_code not in existing_doc_codes:
                doc_std = doc_stds.get(doc_code)
                if doc_std:
                    is_mandatory = doc_code in [
                        'CLAIM_FORM', 'ID_CARD', 'MEDICAL_EXPENSE_CERT',
                        'DEATH_CERT', 'DISABILITY_CERT', 'POLICE_REPORT'
                    ]
                    coverage_doc = CoverageDocMap(
                        coverage_id=coverage.coverage_id,
                        required_doc_std_id=doc_std.required_doc_std_id,
                        is_mandatory=is_mandatory,
                        clause_id=None
                    )
                    db.add(coverage_doc)
                    added_count += 1

    db.commit()
    return added_count


def run():
    """ClauseTerm + CoverageDocMap 채우기 (idempotent).

    현대해상(HYUNDAI)의 모든 Clause에서 금액·한도 수치를 뽑아내고,
    모든 Coverage에 필요서류를 매핑한다.

    건너뜀:
    - 계약행정 조항 (관리규정, 보험료 납입 등)
    - 순수 지급사유 설명 (숫자 없음)
    """
    db = SessionLocal()
    try:
        # 현대해상 확인
        insurer = db.query(Insurer).filter_by(code="HYUNDAI").first()
        if not insurer:
            print("현대해상(HYUNDAI)이 아직 시딩되지 않았습니다.")
            return

        # PolicyVersion 조회
        pv = (
            db.query(PolicyVersion)
            .join(Product, Product.product_id == PolicyVersion.product_id)
            .filter(Product.insurer_id == insurer.insurer_id)
            .first()
        )
        if not pv:
            print("PolicyVersion을 찾을 수 없습니다.")
            return

        # 1) ClauseTerm 추출
        print("[현대해상] ClauseTerm 추출 및 CoverageDocMap 채우기")
        print("=" * 60)

        print("\n1. ClauseTerm 추출 중...")
        term_added, term_distribution = _seed_clause_terms(db, pv)
        print(f"   추가된 ClauseTerm: {term_added}개")
        if term_distribution:
            print(f"   term_type별 분포:")
            for term_type, count in sorted(term_distribution.items()):
                print(f"     - {term_type}: {count}개")
        else:
            print(f"   (새로 추가된 ClauseTerm 없음)")

        # 2) CoverageDocMap 채우기
        print("\n2. CoverageDocMap 채우기 중...")
        doc_map_added = _seed_coverage_doc_map(db, pv)
        print(f"   추가된 CoverageDocMap: {doc_map_added}개")

        # 3) 최종 통계
        print("\n3. 최종 통계:")
        total_clauses = db.query(Clause).filter_by(policy_version_id=pv.policy_version_id).count()
        total_coverages = db.query(Coverage).filter_by(policy_version_id=pv.policy_version_id).count()
        total_terms = db.query(ClauseTerm).join(
            Clause, ClauseTerm.clause_id == Clause.clause_id
        ).filter(Clause.policy_version_id == pv.policy_version_id).count()
        total_doc_maps = db.query(CoverageDocMap).join(
            Coverage, CoverageDocMap.coverage_id == Coverage.coverage_id
        ).filter(Coverage.policy_version_id == pv.policy_version_id).count()

        print(f"   - Clause 총합: {total_clauses}개")
        print(f"   - ClauseTerm 총합: {total_terms}개")
        print(f"   - Coverage 총합: {total_coverages}개")
        print(f"   - CoverageDocMap 총합: {total_doc_maps}개")

        print("\n" + "=" * 60)
        print("완료!")

    finally:
        db.close()


if __name__ == "__main__":
    run()
