"""
카카오페이손해보험(KAKAOPAY) ClauseTerm(수치 조건) 및 CoverageDocMap(필요서류) 시딩.

담당 범위:
- ClauseTerm 추출: 지급한도, 자기부담금, 보상일수한도, 면책일수, 1일당지급액
- CoverageDocMap: 12개 Coverage 모두에 필수서류(CLAIM_FORM, ID_CARD) 연결,
  담보 성격별로 추가서류 매핑.

Clause가 이미 DB에 34개 저장되어 있으므로, 원문에서 숫자와 서류 조건을 추출한다.
"""

from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Insurer, Product, PolicyVersion, Clause, Coverage,
    ClauseTerm, RequiredDocStd, CoverageDocMap
)
from app.services.kb_seed_common import raw_text_is_grounded, get_or_create_doc_std


def run():
    db = SessionLocal()
    try:
        # 1) 카카오페이 Insurer/PolicyVersion 조회
        insurer = db.query(Insurer).filter_by(code="KAKAOPAY").first()
        if not insurer:
            print("카카오페이손해보험이 아직 시딩되지 않았습니다.")
            return

        pv = (db.query(PolicyVersion)
              .join(Product, Product.product_id == PolicyVersion.product_id)
              .filter(Product.insurer_id == insurer.insurer_id)
              .first())
        if not pv:
            print("카카오페이의 PolicyVersion을 찾을 수 없습니다.")
            return

        print(f"Processing KAKAOPAY (PolicyVersion ID: {pv.policy_version_id})")

        # 2) 필수 RequiredDocStd 준비 (공통 + 신규)
        doc_stds = {}

        # 기존 의료 관련 서류
        doc_stds["CLAIM_FORM"] = get_or_create_doc_std(
            db, "CLAIM_FORM", "보험금 청구서(회사 양식)", "귀국가능",
            "보험사 홈페이지/앱에서 양식 다운로드 가능"
        )
        doc_stds["ID_CARD"] = get_or_create_doc_std(
            db, "ID_CARD", "신분증(청구인)", "공통",
            "본인이 아닌 경우 인감증명서 또는 본인서명사실확인서 포함"
        )
        doc_stds["MEDICAL_EXPENSE_CERT"] = get_or_create_doc_std(
            db, "MEDICAL_EXPENSE_CERT", "진료비계산서·영수증", "현지only",
            "현지 의료기관에서만 원본 발급 가능"
        )
        doc_stds["MEDICAL_DETAIL_CERT"] = get_or_create_doc_std(
            db, "MEDICAL_DETAIL_CERT", "진료비세부내역서", "현지only",
            "실손의료비 청구 시 필요"
        )
        doc_stds["TREATMENT_CERT"] = get_or_create_doc_std(
            db, "TREATMENT_CERT", "입원치료확인서/통원확인서", "현지only",
            "입원·통원 여부 확인용"
        )
        doc_stds["PRESCRIPTION"] = get_or_create_doc_std(
            db, "PRESCRIPTION", "의사처방전(처방조제비 포함)", "현지only",
            "약제비 청구 시 필요"
        )
        doc_stds["DISABILITY_CERT"] = get_or_create_doc_std(
            db, "DISABILITY_CERT", "장해진단서", "귀국가능",
            "후유장해 확정 후 국내에서도 발급 가능"
        )
        doc_stds["DEATH_CERT"] = get_or_create_doc_std(
            db, "DEATH_CERT", "사망진단서", "현지only",
            "현지 의료기관·관공서 발급, 번역 공증 필요할 수 있음"
        )

        # 새로 만들 비의료 관련 서류 (이 코드들만 써야 충돌 방지)
        doc_stds["POLICE_REPORT"] = get_or_create_doc_std(
            db, "POLICE_REPORT", "현지 경찰 신고확인서(도난·분실·배상책임 사고)",
            "현지only", "도난·분실·배상책임 관련"
        )
        doc_stds["BAGGAGE_IRREGULARITY"] = get_or_create_doc_std(
            db, "BAGGAGE_IRREGULARITY", "수하물 지연·분실 확인서(항공사 발급, PIR)",
            "현지only", "항공사 PIR(Property Irregularity Report)"
        )
        doc_stds["FLIGHT_DELAY_CERT"] = get_or_create_doc_std(
            db, "FLIGHT_DELAY_CERT", "항공기 지연·결항 확인서(항공사 발급)",
            "현지only", "항공사 공식 지연/결항 확인서"
        )

        db.flush()

        # 3) ClauseTerm 추출 및 추가 (idempotent)
        clauses = db.query(Clause).filter(
            Clause.policy_version_id == pv.policy_version_id
        ).all()

        term_count = 0
        term_type_dist = {}

        for clause in clauses:
            clause_text = clause.text

            # Clause 38: 해외의료비 - 척추지압술/침술 한도 (US $1,000)
            if clause.clause_id == 38:
                # "하나의 상해에 대하여 US $1,000.00 한도로 보상합니다"
                if "US $1,000.00" in clause_text:
                    raw = "US $1,000.00 한도로 보상합니다"
                    if raw_text_is_grounded(clause_text, raw):
                        existing = db.query(ClauseTerm).filter(
                            ClauseTerm.clause_id == clause.clause_id,
                            ClauseTerm.term_type == "지급한도",
                            ClauseTerm.value_num == 1000
                        ).first()
                        if not existing:
                            term = ClauseTerm(
                                clause_id=clause.clause_id,
                                term_type="지급한도",
                                value_num=1000,
                                unit="USD",
                                basis="실손",
                                condition_text="척추지압술(Chiropractic, 추나요법 등)이나 침술(부항, 뜸 포함) 치료로 인한 의료비",
                                raw_text=raw,
                            )
                            db.add(term)
                            term_count += 1
                            term_type_dist["지급한도"] = term_type_dist.get("지급한도", 0) + 1

            # Clause 41: 구조송환비용 자기부담금 (10만원 공제 후 10% / 20%)
            if clause.clause_id == 41:
                # "10만원을 공제한 후 자기부담률 10%" / "20%"
                raw1 = "10만원을 공제한 후 자기부담률 10%"
                if raw_text_is_grounded(clause_text, raw1):
                    existing = db.query(ClauseTerm).filter(
                        ClauseTerm.clause_id == clause.clause_id,
                        ClauseTerm.term_type == "자기부담금",
                        ClauseTerm.condition_text == "10만원 공제 후 10% 적용"
                    ).first()
                    if not existing:
                        term = ClauseTerm(
                            clause_id=clause.clause_id,
                            term_type="자기부담금",
                            value_num=None,  # 복합 조건이므로 숫자 하나로 표현 불가
                            unit=None,
                            basis=None,
                            condition_text="10만원 공제 후 10% 적용",
                            raw_text=raw1,
                        )
                        db.add(term)
                        term_count += 1
                        term_type_dist["자기부담금"] = term_type_dist.get("자기부담금", 0) + 1

                raw2 = "10만원을 공제한 후 자기부담률 20%"
                if raw_text_is_grounded(clause_text, raw2):
                    existing = db.query(ClauseTerm).filter(
                        ClauseTerm.clause_id == clause.clause_id,
                        ClauseTerm.term_type == "자기부담금",
                        ClauseTerm.condition_text == "10만원 공제 후 20% 적용"
                    ).first()
                    if not existing:
                        term = ClauseTerm(
                            clause_id=clause.clause_id,
                            term_type="자기부담금",
                            value_num=None,
                            unit=None,
                            basis=None,
                            condition_text="10만원 공제 후 20% 적용",
                            raw_text=raw2,
                        )
                        db.add(term)
                        term_count += 1
                        term_type_dist["자기부담금"] = term_type_dist.get("자기부담금", 0) + 1

            # Clause 53: 휴대물품 1개당 20만원 한도
            # (Coverage raw_name이 이미 "해외여행중 휴대물품손해(분실제외/1개당 20만원 한도)")
            if clause.clause_id == 53:
                # "이 보험의 목적은 피보험자가 여행 도중에 휴대하는 피보험자 소유·사용·관리의 휴대품에 한합니다"
                # 실제 한도는 이 조항보다는 coverage에 명시되어 있으나, 명시적 숫자 문자열을 찾기 어려움
                # 건너뜀: coverage 이름에는 있지만 clause.text에는 명시적으로 없음
                pass

            # Clause 60, 184, 186: 국내의료비 보상일수 (180일 한도, 통원 90회)
            if clause.clause_id in [60, 184]:
                # "180일(통원은 180일 동안 90회)까지만"
                raw_180 = "180일"
                if raw_text_is_grounded(clause_text, raw_180):
                    existing = db.query(ClauseTerm).filter(
                        ClauseTerm.clause_id == clause.clause_id,
                        ClauseTerm.term_type == "보상일수한도",
                        ClauseTerm.value_num == 180
                    ).first()
                    if not existing:
                        term = ClauseTerm(
                            clause_id=clause.clause_id,
                            term_type="보상일수한도",
                            value_num=180,
                            unit="일",
                            basis="실손",
                            condition_text="해외여행 중 입은 상해로 국내 의료기관에서 치료받을 때 보장 기간",
                            raw_text="의사의 치료를 받기 시작한 날부터 180일",
                        )
                        db.add(term)
                        term_count += 1
                        term_type_dist["보상일수한도"] = term_type_dist.get("보상일수한도", 0) + 1

            if clause.clause_id in [186]:
                # 질병 국내의료비도 동일 구조
                raw_180 = "180일"
                if raw_text_is_grounded(clause_text, raw_180):
                    existing = db.query(ClauseTerm).filter(
                        ClauseTerm.clause_id == clause.clause_id,
                        ClauseTerm.term_type == "보상일수한도",
                        ClauseTerm.value_num == 180
                    ).first()
                    if not existing:
                        term = ClauseTerm(
                            clause_id=clause.clause_id,
                            term_type="보상일수한도",
                            value_num=180,
                            unit="일",
                            basis="실손",
                            condition_text="해외여행 중 발생한 질병으로 국내 의료기관에서 치료받을 때 보장 기간",
                            raw_text="의사의 치료를 받기 시작한 날부터 180일",
                        )
                        db.add(term)
                        term_count += 1
                        term_type_dist["보상일수한도"] = term_type_dist.get("보상일수한도", 0) + 1

            # Clause 189, 190: 국내 의료비 한도 (5천만원)
            if clause.clause_id in [189, 190]:
                raw_50m = "5 천만원"
                if raw_text_is_grounded(clause_text, raw_50m):
                    existing = db.query(ClauseTerm).filter(
                        ClauseTerm.clause_id == clause.clause_id,
                        ClauseTerm.term_type == "지급한도",
                        ClauseTerm.value_num == 50000000
                    ).first()
                    if not existing:
                        cov_type = "상해" if clause.clause_id == 189 else "질병"
                        term = ClauseTerm(
                            clause_id=clause.clause_id,
                            term_type="지급한도",
                            value_num=50000000,
                            unit="원",
                            basis="실손",
                            condition_text=f"국내 {cov_type}의료비 연간 보험가입금액 한도(입원+통원 합산)",
                            raw_text="5 천만원 이내에서",
                        )
                        db.add(term)
                        term_count += 1
                        term_type_dist["지급한도"] = term_type_dist.get("지급한도", 0) + 1

            # Clause 302: 상해입원일당 (1일 이상 입원, 180일 한도, 1일당 지급액)
            if clause.clause_id == 302:
                # "1 일이상 입원하여" — 면책일수
                raw_min = "1 일이상 입원"
                if raw_text_is_grounded(clause_text, raw_min):
                    existing = db.query(ClauseTerm).filter(
                        ClauseTerm.clause_id == clause.clause_id,
                        ClauseTerm.term_type == "면책일수",
                        ClauseTerm.value_num == 1
                    ).first()
                    if not existing:
                        term = ClauseTerm(
                            clause_id=clause.clause_id,
                            term_type="면책일수",
                            value_num=1,
                            unit="일",
                            basis="정액",
                            condition_text="해외 의료기관에 입원하여 지급되기 위한 최소 입원일수",
                            raw_text="1 일이상 입원",
                        )
                        db.add(term)
                        term_count += 1
                        term_type_dist["면책일수"] = term_type_dist.get("면책일수", 0) + 1

                # "180 일을 한도" — 보상일수 한도
                raw_limit = "180 일을 한도로"
                if raw_text_is_grounded(clause_text, raw_limit):
                    existing = db.query(ClauseTerm).filter(
                        ClauseTerm.clause_id == clause.clause_id,
                        ClauseTerm.term_type == "보상일수한도",
                        ClauseTerm.value_num == 180
                    ).first()
                    if not existing:
                        term = ClauseTerm(
                            clause_id=clause.clause_id,
                            term_type="보상일수한도",
                            value_num=180,
                            unit="일",
                            basis="정액",
                            condition_text="1회 입원당 지급받을 수 있는 최대 일수",
                            raw_text="1 회 입원당 180 일을 한도로",
                        )
                        db.add(term)
                        term_count += 1
                        term_type_dist["보상일수한도"] = term_type_dist.get("보상일수한도", 0) + 1

                # 1일당 지급액은 보험가입금액으로 정의되므로 미리 정할 수 없음 (고객이 선택)
                # raw_text_is_grounded로 검증 가능한 명시적 숫자가 없음

            # Clause 305: 질병입원일당 (4일 이상, 30일 한도, 3일 초과부터 지급)
            if clause.clause_id == 305:
                # "4 일 이상 계속 입원" — 면책일수
                raw_min = "4 일 이상"
                if raw_text_is_grounded(clause_text, raw_min):
                    existing = db.query(ClauseTerm).filter(
                        ClauseTerm.clause_id == clause.clause_id,
                        ClauseTerm.term_type == "면책일수",
                        ClauseTerm.value_num == 4
                    ).first()
                    if not existing:
                        term = ClauseTerm(
                            clause_id=clause.clause_id,
                            term_type="면책일수",
                            value_num=4,
                            unit="일",
                            basis="정액",
                            condition_text="질병으로 해외 의료기관에 입원하여 지급되기 위한 최소 연속 입원일수",
                            raw_text="4 일 이상 계속 입원",
                        )
                        db.add(term)
                        term_count += 1
                        term_type_dist["면책일수"] = term_type_dist.get("면책일수", 0) + 1

                # "30 일을 최고한도로" — 보상일수 한도
                raw_limit = "30 일을 최고한도로"
                if raw_text_is_grounded(clause_text, raw_limit):
                    existing = db.query(ClauseTerm).filter(
                        ClauseTerm.clause_id == clause.clause_id,
                        ClauseTerm.term_type == "보상일수한도",
                        ClauseTerm.value_num == 30
                    ).first()
                    if not existing:
                        term = ClauseTerm(
                            clause_id=clause.clause_id,
                            term_type="보상일수한도",
                            value_num=30,
                            unit="일",
                            basis="정액",
                            condition_text="1회 입원당 지급받을 수 있는 최대 일수",
                            raw_text="1 회 입원당 30 일을 최고한도로",
                        )
                        db.add(term)
                        term_count += 1
                        term_type_dist["보상일수한도"] = term_type_dist.get("보상일수한도", 0) + 1

        db.flush()
        print(f"ClauseTerm 추가: {term_count}개")
        print(f"  term_type 분포: {term_type_dist}")

        # 4) CoverageDocMap 채우기 (완전성 원칙: 12개 Coverage 모두 CLAIM_FORM + ID_CARD 최소)
        coverages = db.query(Coverage).filter(
            Coverage.policy_version_id == pv.policy_version_id
        ).all()

        coverage_doc_count = 0
        for cov in coverages:
            # CLAIM_FORM (필수 기본)
            existing_claim = db.query(CoverageDocMap).filter(
                CoverageDocMap.coverage_id == cov.coverage_id,
                CoverageDocMap.required_doc_std_id == doc_stds["CLAIM_FORM"].required_doc_std_id
            ).first()
            if not existing_claim:
                db.add(CoverageDocMap(
                    coverage_id=cov.coverage_id,
                    required_doc_std_id=doc_stds["CLAIM_FORM"].required_doc_std_id,
                    is_mandatory=True,
                    clause_id=None
                ))
                coverage_doc_count += 1

            # ID_CARD (필수 기본)
            existing_id = db.query(CoverageDocMap).filter(
                CoverageDocMap.coverage_id == cov.coverage_id,
                CoverageDocMap.required_doc_std_id == doc_stds["ID_CARD"].required_doc_std_id
            ).first()
            if not existing_id:
                db.add(CoverageDocMap(
                    coverage_id=cov.coverage_id,
                    required_doc_std_id=doc_stds["ID_CARD"].required_doc_std_id,
                    is_mandatory=True,
                    clause_id=None
                ))
                coverage_doc_count += 1

            # 담보 성격별 추가 서류
            cov_name = cov.raw_name.lower()

            # 의료비 관련 (상해/질병 의료비)
            if "의료비" in cov_name or "질병" in cov_name or "상해" in cov_name:
                # 해외 의료비: MEDICAL_EXPENSE_CERT, MEDICAL_DETAIL_CERT, TREATMENT_CERT
                if "해외" in cov_name or "overseas" in cov_name.lower():
                    for doc_code in ["MEDICAL_EXPENSE_CERT", "MEDICAL_DETAIL_CERT", "TREATMENT_CERT"]:
                        existing = db.query(CoverageDocMap).filter(
                            CoverageDocMap.coverage_id == cov.coverage_id,
                            CoverageDocMap.required_doc_std_id == doc_stds[doc_code].required_doc_std_id
                        ).first()
                        if not existing:
                            db.add(CoverageDocMap(
                                coverage_id=cov.coverage_id,
                                required_doc_std_id=doc_stds[doc_code].required_doc_std_id,
                                is_mandatory=True,
                                clause_id=None
                            ))
                            coverage_doc_count += 1

                # 국내 의료비: MEDICAL_DETAIL_CERT, TREATMENT_CERT
                if "국내" in cov_name:
                    for doc_code in ["MEDICAL_DETAIL_CERT", "TREATMENT_CERT"]:
                        existing = db.query(CoverageDocMap).filter(
                            CoverageDocMap.coverage_id == cov.coverage_id,
                            CoverageDocMap.required_doc_std_id == doc_stds[doc_code].required_doc_std_id
                        ).first()
                        if not existing:
                            db.add(CoverageDocMap(
                                coverage_id=cov.coverage_id,
                                required_doc_std_id=doc_stds[doc_code].required_doc_std_id,
                                is_mandatory=True,
                                clause_id=None
                            ))
                            coverage_doc_count += 1

            # 입원일당 관련: TREATMENT_CERT, DISABILITY_CERT (후유장해 시)
            if "입원일당" in cov_name:
                for doc_code in ["TREATMENT_CERT", "DISABILITY_CERT"]:
                    existing = db.query(CoverageDocMap).filter(
                        CoverageDocMap.coverage_id == cov.coverage_id,
                        CoverageDocMap.required_doc_std_id == doc_stds[doc_code].required_doc_std_id
                    ).first()
                    if not existing:
                        db.add(CoverageDocMap(
                            coverage_id=cov.coverage_id,
                            required_doc_std_id=doc_stds[doc_code].required_doc_std_id,
                            is_mandatory=True,
                            clause_id=None
                        ))
                        coverage_doc_count += 1

            # 사망 관련: DEATH_CERT, DISABILITY_CERT
            if "사망" in cov_name or "후유장해" in cov_name:
                if "사망" in cov_name:
                    existing = db.query(CoverageDocMap).filter(
                        CoverageDocMap.coverage_id == cov.coverage_id,
                        CoverageDocMap.required_doc_std_id == doc_stds["DEATH_CERT"].required_doc_std_id
                    ).first()
                    if not existing:
                        db.add(CoverageDocMap(
                            coverage_id=cov.coverage_id,
                            required_doc_std_id=doc_stds["DEATH_CERT"].required_doc_std_id,
                            is_mandatory=True,
                            clause_id=None
                        ))
                        coverage_doc_count += 1
                if "장해" in cov_name or "후유" in cov_name:
                    existing = db.query(CoverageDocMap).filter(
                        CoverageDocMap.coverage_id == cov.coverage_id,
                        CoverageDocMap.required_doc_std_id == doc_stds["DISABILITY_CERT"].required_doc_std_id
                    ).first()
                    if not existing:
                        db.add(CoverageDocMap(
                            coverage_id=cov.coverage_id,
                            required_doc_std_id=doc_stds["DISABILITY_CERT"].required_doc_std_id,
                            is_mandatory=True,
                            clause_id=None
                        ))
                        coverage_doc_count += 1

            # 구조송환: 특별서류 없음 (의료 관련만 필요)

            # 휴대물품: POLICE_REPORT (도난 시)
            if "휴대물품" in cov_name or "baggage" in cov_name.lower():
                existing = db.query(CoverageDocMap).filter(
                    CoverageDocMap.coverage_id == cov.coverage_id,
                    CoverageDocMap.required_doc_std_id == doc_stds["POLICE_REPORT"].required_doc_std_id
                ).first()
                if not existing:
                    db.add(CoverageDocMap(
                        coverage_id=cov.coverage_id,
                        required_doc_std_id=doc_stds["POLICE_REPORT"].required_doc_std_id,
                        is_mandatory=False,  # "도난·절취의 경우" — 선택적
                        clause_id=None
                    ))
                    coverage_doc_count += 1

        db.flush()
        print(f"CoverageDocMap 추가: {coverage_doc_count}개")
        print(f"  담보별 필요서류 연결 완료 (12개 Coverage)")

        # 5) Commit
        db.commit()
        print("\nKAKAOPAY ClauseTerm & CoverageDocMap 시딩 완료!")
        print(f"Summary:")
        print(f"  - ClauseTerm: {term_count}개 ({', '.join(f'{k}:{v}' for k, v in sorted(term_type_dist.items()))})")
        print(f"  - CoverageDocMap: {coverage_doc_count}개 신규 연결")
        print(f"  - RequiredDocStd: 기존 8개 + 신규 3개 = 11개 (중복 방지, get_or_create)")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    run()
