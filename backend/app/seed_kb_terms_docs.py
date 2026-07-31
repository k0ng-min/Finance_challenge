"""
KB손해보험 ClauseTerm(수치 조건) 및 CoverageDocMap(필요서류) 채우기
"""
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Insurer, Product, PolicyVersion, Coverage, Clause,
    ClauseTerm, CoverageDocMap, RequiredDocStd
)
from app.services.kb_seed_common import (
    raw_text_is_grounded, get_or_create_doc_std
)


def run():
    """Idempotent run function."""
    db = SessionLocal()
    try:
        # KB 보험사 조회
        insurer = db.query(Insurer).filter_by(code="KB").first()
        if not insurer:
            print("KB손해보험 데이터가 없습니다.")
            return

        # PolicyVersion 조회
        pv = (
            db.query(PolicyVersion)
            .join(Product, Product.product_id == PolicyVersion.product_id)
            .filter(Product.insurer_id == insurer.insurer_id)
            .first()
        )
        if not pv:
            print("KB 정책 버전이 없습니다.")
            return

        print("=" * 80)
        print("KB손해보험 ClauseTerm 및 CoverageDocMap 채우기 시작")
        print("=" * 80)

        # ========== 1. ClauseTerm 추출 ==========
        print("\n[1] ClauseTerm 추출 중...")
        clause_terms_added = 0

        # 이미 추가된 ClauseTerm 개수 파악
        existing_terms = db.query(ClauseTerm).filter(
            ClauseTerm.clause_id.in_(
                db.query(Clause.clause_id).filter(
                    Clause.policy_version_id == pv.policy_version_id
                )
            )
        ).count()
        print(f"  기존 ClauseTerm: {existing_terms}개")

        # Clause별로 숫자 조건 추출
        clauses = db.query(Clause).filter(Clause.policy_version_id == pv.policy_version_id).all()

        for clause in clauses:
            text = clause.text

            # 각 Clause에서 추출 가능한 숫자 패턴들
            terms_to_add = []

            # Clause 26 (cov_id=11): "US $1,000.00 한도" - 척추지압술/침술
            if clause.clause_id == 26 and "US $1,000.00" in text:
                terms_to_add.append({
                    'term_type': '지급한도',
                    'value_num': 1000.0,
                    'unit': 'USD',
                    'basis': '정액',
                    'condition_text': '척추지압술/침술 치료, 하나의 상해에 대한',
                    'raw_text': 'US $1,000.00 한도로 보상합니다'
                })

            # Clause 58 (cov_id=11): "180일" 및 "90회" - 귀국후 국내치료
            if clause.clause_id == 58:
                if "180일" in text and "외래는 방문 90회" in text:
                    terms_to_add.append({
                        'term_type': '보상일수한도',
                        'value_num': 180.0,
                        'unit': '일',
                        'basis': None,
                        'condition_text': '통원 기간 한도',
                        'raw_text': '의사의 치료를 받기 시작한 날부터 180일'
                    })
                    terms_to_add.append({
                        'term_type': '보상일수한도',
                        'value_num': 90.0,
                        'unit': '회',
                        'basis': None,
                        'condition_text': '외래 방문 횟수 한도',
                        'raw_text': '외래는 방문 90회, 처방조제비는 처방전 90건'
                    })

            # Clause 266 (cov_id=12): "14박분" - 숙박비 한도
            if clause.clause_id == 266 and "14박분" in text:
                terms_to_add.append({
                    'term_type': '보상일수한도',
                    'value_num': 14.0,
                    'unit': '일',
                    'basis': None,
                    'condition_text': '구원자당 숙박비 한도',
                    'raw_text': '1명당 14박분을 한도로 합니다'
                })

            # Clause 268 (cov_id=82): "매일 70,000원" - 1일당지급액
            if clause.clause_id == 268 and "70,000원" in text:
                terms_to_add.append({
                    'term_type': '1일당지급액',
                    'value_num': 70000.0,
                    'unit': '원',
                    'basis': '정액',
                    'condition_text': '항공기 납치 기간 동안 1일 지급액',
                    'raw_text': '매일 70,000원씩 지급하여 드립니다'
                })

            # Clause 269 (cov_id=82): "12시간" 지연기준, "20일" 한도
            if clause.clause_id == 269:
                if "12시간" in text:
                    terms_to_add.append({
                        'term_type': '지연기준시간',
                        'value_num': 12.0,
                        'unit': '시간',
                        'basis': None,
                        'condition_text': '목적지 도착예정시간 이후 지연 기준',
                        'raw_text': '당해 항공기의 목적지 도착예정시간에서 12시간이 지난 이후부터'
                    })
                if "20일" in text:
                    terms_to_add.append({
                        'term_type': '보상일수한도',
                        'value_num': 20.0,
                        'unit': '일',
                        'basis': None,
                        'condition_text': '항공기 납치 보상 기간 한도',
                        'raw_text': '20일을 한도로 제1조(보험금의 지급사유)에 정한 보험금을 지급'
                    })

            # Clause 277 (cov_id=86): "2일 이상 계속 입원" - 면책일수
            if clause.clause_id == 277 and "2일 이상 계속 입원" in text:
                terms_to_add.append({
                    'term_type': '면책일수',
                    'value_num': 2.0,
                    'unit': '일',
                    'basis': None,
                    'condition_text': '식중독으로 인한 입원 최소 기간',
                    'raw_text': '2일 이상 계속 입원하여 의사의 치료를 받은 경우'
                })

            # Clause 280 (cov_id=88): 항공기 지연 관련 시간 조건들
            if clause.clause_id == 280:
                if "4시간 내에" in text or "4시간이상 지연" in text:
                    terms_to_add.append({
                        'term_type': '지연기준시간',
                        'value_num': 4.0,
                        'unit': '시간',
                        'basis': None,
                        'condition_text': '항공편 지연·결항 기준시간',
                        'raw_text': '출발예정시각으로부터 4시간 내에'
                    })
                if "6시간 이후에" in text:
                    terms_to_add.append({
                        'term_type': '지연기준시간',
                        'value_num': 6.0,
                        'unit': '시간',
                        'basis': None,
                        'condition_text': '수하물 도착 지연 기준시간',
                        'raw_text': '항공편의 예정된 도착시각으로부터 6시간 이후에'
                    })
                if "24시간 내에" in text:
                    terms_to_add.append({
                        'term_type': '지연기준시간',
                        'value_num': 24.0,
                        'unit': '시간',
                        'basis': None,
                        'condition_text': '위탁수하물 도착 지연 기준시간',
                        'raw_text': '목적지에 도착한 후 24시간 내에'
                    })

            # Clause 283 (cov_id=89): 수하물 지연 관련 시간 조건들
            if clause.clause_id == 283:
                if "4시간이상 지연" in text:
                    terms_to_add.append({
                        'term_type': '지연기준시간',
                        'value_num': 4.0,
                        'unit': '시간',
                        'basis': None,
                        'condition_text': '항공편 지연·결항 기준시간',
                        'raw_text': '항공편이 4시간이상 지연, 취소'
                    })
                if "6시간 이후에" in text:
                    terms_to_add.append({
                        'term_type': '지연기준시간',
                        'value_num': 6.0,
                        'unit': '시간',
                        'basis': None,
                        'condition_text': '수하물 도착 지연 기준시간',
                        'raw_text': '항공편의 예정된 도착시각으로부터 6시간 이후에'
                    })
                if "24시간 내에" in text:
                    terms_to_add.append({
                        'term_type': '지연기준시간',
                        'value_num': 24.0,
                        'unit': '시간',
                        'basis': None,
                        'condition_text': '위탁수하물 도착 지연 기준시간',
                        'raw_text': '목적지에 도착한 후 24시간 내에'
                    })

            # Grounding 검증 후 추가
            for term_data in terms_to_add:
                if not raw_text_is_grounded(text, term_data['raw_text']):
                    print(f"  WARNING: clause_id={clause.clause_id}의 raw_text가 원문과 일치하지 않음")
                    continue

                # 중복 체크
                existing = db.query(ClauseTerm).filter(
                    ClauseTerm.clause_id == clause.clause_id,
                    ClauseTerm.term_type == term_data['term_type'],
                    ClauseTerm.value_num == term_data['value_num']
                ).first()

                if not existing:
                    term = ClauseTerm(
                        clause_id=clause.clause_id,
                        term_type=term_data['term_type'],
                        value_num=term_data['value_num'],
                        unit=term_data['unit'],
                        basis=term_data['basis'],
                        condition_text=term_data['condition_text'],
                        raw_text=term_data['raw_text'],
                        confidence=None
                    )
                    db.add(term)
                    clause_terms_added += 1

        db.commit()
        print(f"  ClauseTerm 추가: {clause_terms_added}개")

        # ========== 2. CoverageDocMap 추가 ==========
        print("\n[2] CoverageDocMap(필요서류) 채우기 중...")

        # 기존 RequiredDocStd 확인 및 필요한 것 생성
        claim_form = get_or_create_doc_std(
            db, "CLAIM_FORM", "보험금 청구서(회사 양식)", "귀국가능",
            "보험사 홈페이지/앱에서 양식 다운로드 가능"
        )
        id_card = get_or_create_doc_std(
            db, "ID_CARD", "신분증(청구인)", "공통",
            "본인이 아닌 경우 인감증명서 또는 본인서명사실확인서 포함"
        )
        medical_expense_cert = get_or_create_doc_std(
            db, "MEDICAL_EXPENSE_CERT", "진료비계산서·영수증", "현지only",
            "현지 의료기관에서만 원본 발급 가능"
        )
        medical_detail_cert = get_or_create_doc_std(
            db, "MEDICAL_DETAIL_CERT", "진료비세부내역서", "현지only",
            "실손의료비 청구 시 필요"
        )
        treatment_cert = get_or_create_doc_std(
            db, "TREATMENT_CERT", "입원치료확인서/통원확인서", "현지only",
            "입원·통원 여부 확인용"
        )
        death_cert = get_or_create_doc_std(
            db, "DEATH_CERT", "사망진단서", "현지only",
            "현지 의료기관·관공서 발급, 번역 공증 필요할 수 있음"
        )

        # 새로 만들 코드들
        police_report = get_or_create_doc_std(
            db, "POLICE_REPORT", "현지 경찰 신고확인서(도난·분실·배상책임 사고)",
            "현지only", "도난·분실·배상책임 관련 사고 발생 시 필요"
        )
        flight_delay_cert = get_or_create_doc_std(
            db, "FLIGHT_DELAY_CERT", "항공기 지연·결항 확인서(항공사 발급)",
            "현지only", "항공사 또는 공항 운영사에서 발급"
        )
        baggage_irregularity = get_or_create_doc_std(
            db, "BAGGAGE_IRREGULARITY", "수하물 지연·분실 확인서(항공사 발급, PIR)",
            "현지only", "항공사에서 발급하는 수하물 분실 보고서(PIR: Property Irregularity Report)"
        )
        passport_reissue = get_or_create_doc_std(
            db, "PASSPORT_REISSUE_RECEIPT", "여권(여행증명서) 재발급 영수증·확인서",
            "현지only", "재외공관에서 발급한 여행증명서 및 여권 재발급 영수증"
        )
        liability_evidence = get_or_create_doc_std(
            db, "LIABILITY_EVIDENCE", "배상책임 관련 서류(합의서·손해배상 청구서·상대방 피해 확인서류)",
            "현지only", "배상책임 사고의 합의 및 피해 입증 관련"
        )

        db.commit()

        # Coverage별로 필요서류 연결
        coverage_doc_map_added = 0

        coverage_doc_specs = {
            # cov_id 47: 질병사망 및 80%이상후유장해 - 의료비 관련
            47: [
                (claim_form, True, None),
                (id_card, True, None),
                (death_cert, False, None),
                (medical_expense_cert, False, None),
                (medical_detail_cert, False, None),
                (treatment_cert, False, None),
            ],
            # cov_id 48: 배상책임
            48: [
                (claim_form, True, None),
                (id_card, True, None),
                (liability_evidence, True, 140),  # clause_id=140에서 "손해배상금 및 그 밖의 비용을 지급하였음을 증명하는 서류"
                (police_report, False, None),  # 도난·분실일 경우
            ],
            # cov_id 82: 항공기납치
            82: [
                (claim_form, True, None),
                (id_card, True, None),
            ],
            # cov_id 83: 항공기탑승중 상해위험
            83: [
                (claim_form, True, None),
                (id_card, True, None),
                (treatment_cert, False, None),
                (medical_expense_cert, False, None),
            ],
            # cov_id 84: 여권분실
            84: [
                (claim_form, True, None),
                (id_card, True, None),
                (passport_reissue, True, 272),  # clause_id=272에서 여권분실신고/여행증명서 발급
                (police_report, False, None),  # 도난 신고 시
            ],
            # cov_id 85: 여행중단 사고발생
            85: [
                (claim_form, True, None),
                (id_card, True, None),
            ],
            # cov_id 86: 식중독
            86: [
                (claim_form, True, None),
                (id_card, True, None),
                (treatment_cert, True, 277),  # clause_id=277에서 입원치료확인 필요
                (medical_expense_cert, False, None),
                (medical_detail_cert, False, None),
            ],
            # cov_id 87: 특정전염병
            87: [
                (claim_form, True, None),
                (id_card, True, None),
                (treatment_cert, True, 279),  # clause_id=279에서 진단/치료 관련
                (medical_expense_cert, False, None),
            ],
            # cov_id 88: 항공기 지연
            88: [
                (claim_form, True, None),
                (id_card, True, None),
                (flight_delay_cert, True, 280),  # clause_id=280에서 항공기 지연 증명 필요
            ],
            # cov_id 89: 수하물 지연
            89: [
                (claim_form, True, None),
                (id_card, True, None),
                (baggage_irregularity, True, 283),  # clause_id=283에서 수하물 분실/지연 증명 필요
            ],
            # cov_id 90: 질병의료비 특별약관
            90: [
                (claim_form, True, None),
                (id_card, True, None),
                (medical_expense_cert, False, None),
                (medical_detail_cert, False, None),
                (treatment_cert, False, None),
            ],
        }

        for cov_id, doc_specs in coverage_doc_specs.items():
            coverage = db.query(Coverage).filter(Coverage.coverage_id == cov_id).first()
            if not coverage:
                print(f"  WARNING: Coverage {cov_id} not found")
                continue

            for required_doc_std, is_mandatory, clause_id in doc_specs:
                # 중복 체크
                existing = db.query(CoverageDocMap).filter(
                    CoverageDocMap.coverage_id == cov_id,
                    CoverageDocMap.required_doc_std_id == required_doc_std.required_doc_std_id
                ).first()

                if not existing:
                    doc_map = CoverageDocMap(
                        coverage_id=cov_id,
                        required_doc_std_id=required_doc_std.required_doc_std_id,
                        is_mandatory=is_mandatory,
                        clause_id=clause_id
                    )
                    db.add(doc_map)
                    coverage_doc_map_added += 1

        db.commit()
        print(f"  CoverageDocMap 추가: {coverage_doc_map_added}개")

        # ========== 요약 ==========
        print("\n" + "=" * 80)
        print("완료 요약:")
        print(f"  - ClauseTerm 추가: {clause_terms_added}개")
        print(f"  - CoverageDocMap 추가: {coverage_doc_map_added}개")
        print(f"  - 새로 생성된 RequiredDocStd: 5개 (POLICE_REPORT, FLIGHT_DELAY_CERT, BAGGAGE_IRREGULARITY, PASSPORT_REISSUE_RECEIPT, LIABILITY_EVIDENCE)")
        print("=" * 80)

    except Exception as e:
        db.rollback()
        print(f"오류 발생: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
