"""
현대해상 다이렉트 해외여행보험(CM8403, 2025-06-30 시행) 실물 약관 KB 시드 스크립트.

원문 출처: data/raw_pdfs/hyundai_overseas_CM8403_20250630.pdf
(docs/compliance/source_register.md 참조)

삼성화재와 동일한 표준담보 3종(DEATH_INJURY/OVS_INJ_MED/RESCUE)을 매핑하되,
조항 텍스트는 현대해상 원문을 그대로 인용한다. 두 회사가 같은 표준양식을 쓰는 조항도 있지만
"여행도중"의 정의(주거지 출발~주거지 도착 vs 해외여행 도중)처럼 실제 문구 차이가 있어
그대로 남겨 형광펜 근거의 정확성을 유지한다.
"""
import datetime as dt

from app.database import Base, SessionLocal, engine
from app import models
from app.models.kb import Coverage, Clause, CoverageDocMap
from app.services.kb_seed_common import seed_common_coverage_std, seed_common_doc_std, seed_insurer_core

Base.metadata.create_all(bind=engine)


def run():
    db = SessionLocal()
    try:
        insurer, product, pv = seed_insurer_core(
            db,
            name="현대해상화재보험", code="HYUNDAI", official_url="https://www.hi.co.kr",
            product_name="다이렉트 해외여행보험", product_code="CM8403", channel="다이렉트",
            sale_start=dt.date(2025, 6, 30), collected_at=dt.date(2026, 7, 29),
            version_label="CM8403_20250630", effective_date=dt.date(2025, 6, 30),
            source_url="https://direct.hi.co.kr/dhNAS/terms/CM8403_20250630.pdf",
            file_hash="294b8f4e9afd724c6eac94b6c25a0bd948e064b40d3817f6c40b6976035c72ed",
        )
        if insurer is None:
            print("이미 시드됨 (HYUNDAI). 스킵합니다.")
            return

        std = seed_common_coverage_std(db)
        std_death_injury, std_ovs_inj_med, std_rescue = std["DEATH_INJURY"], std["OVS_INJ_MED"], std["RESCUE"]

        cov_death_injury = Coverage(
            policy_version_id=pv.policy_version_id, coverage_std_id=std_death_injury.coverage_std_id,
            raw_name="상해사망·후유장해 (보통약관)",
            definition=(
                "회사는 피보험자가 보험증권에 기재된 여행을 목적으로 주거지를 출발하여 여행을 마치고 주거지에 "
                "도착할 때까지의 여행도중에 다음 중 어느 하나의 사유가 발생한 경우에는 보험수익자에게 약정한 "
                "보험금을 지급합니다. 1. 보험기간 중에 상해의 직접결과로써 사망한 경우(질병으로 인한 사망은 "
                "제외합니다): 사망보험금 2. 보험기간 중 상해로 장해분류표(<별표1> 참조)에서 정한 각 장해지급률에 "
                "해당하는 장해상태가 되었을 때: 후유장해보험금"
            ),
            limit_amount="가입금액 한도 (증권 기재 보험가입금액)",
            deductible=None,
            waiting_condition="장해지급률 미확정 시 상해 발생일부터 180일 시점 진단 기준",
        )
        cov_ovs_inj_med = Coverage(
            policy_version_id=pv.policy_version_id, coverage_std_id=std_ovs_inj_med.coverage_std_id,
            raw_name="해외여행 실손의료비 특별약관 - (1)상해 해외의료비",
            definition=(
                "회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 해외의료기관에서 "
                "의사(치료받는 국가의 법에서 정한 병원 및 의사의 면허를 가진 자에 한함)의 치료를 받은 때에는 "
                "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다."
            ),
            limit_amount="보험가입금액 한도, 실제 부담 의료비 전액 (척추지압술·침술은 건당 US$1,000 한도)",
            deductible="가입 시 선택한 자기부담금 있을 수 있음(플랜별 상이)",
            waiting_condition="보험기간 종료 후에도 종료일부터 180일까지 계속 치료 시 보상",
        )
        cov_rescue = Coverage(
            policy_version_id=pv.policy_version_id, coverage_std_id=std_rescue.coverage_std_id,
            raw_name="해외여행중 중대사고 구조송환비용 등 보장 특별약관",
            definition=(
                "회사는 해외여행 중 피보험자가 탑승한 항공기·선박의 행방불명·조난, 산악등반 중 조난, "
                "긴급수색구조가 필요한 사고(경찰 등 공공기관 확인), 상해를 직접원인으로 사고일부터 1년 이내 사망 "
                "또는 약정 일수 이상 계속 입원, 질병을 직접원인으로 한 사망·약정 일수 이상 입원 시 수색구조비용·"
                "구원자 교통비·숙박비·이송비용·제잡비를 보상합니다."
            ),
            limit_amount="보험가입금액 한도 (구원자 교통비 2명분, 제잡비 10만원 한도)",
            deductible="보험증권에 기재된 자기부담금 공제",
            waiting_condition="입원의 경우 보험증권에 기재된 약정 일수 이상 계속 입원 필요",
        )
        db.add_all([cov_death_injury, cov_ovs_inj_med, cov_rescue])
        db.flush()

        clauses = [
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_death_injury.coverage_id,
                clause_type="보장정의", article_no="제3조(보험금의 지급사유)",
                text=(
                    "회사는 피보험자가 보험증권에 기재된 여행을 목적으로 주거지를 출발하여 여행을 마치고 주거지에 "
                    "도착할 때까지의 여행도중에 다음 중 어느 하나의 사유가 발생한 경우에는 보험수익자에게 약정한 "
                    "보험금을 지급합니다. 1. 보험기간 중에 상해의 직접결과로써 사망한 경우(질병으로 인한 사망은 "
                    "제외합니다): 사망보험금 2. 보험기간 중 상해로 장해분류표(<별표1> 참조)에서 정한 각 "
                    "장해지급률에 해당하는 장해상태가 되었을 때: 후유장해보험금"
                ),
                page_ref="p.20", embedding_id=None, default_color="파랑",
            ),
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_death_injury.coverage_id,
                clause_type="면책", article_no="제5조(보험금을 지급하지 않는 사유)",
                text=(
                    "① 회사는 다음 중 어느 한가지로 보험금 지급사유가 발생한 때에는 보험금을 지급하지 않습니다. "
                    "1. 피보험자가 고의로 자신을 해친 경우(심신상실 등 예외 있음) 2. 보험수익자가 고의로 피보험자를 "
                    "해친 경우 3. 계약자가 고의로 피보험자를 해친 경우 4. 피보험자의 임신, 출산(제왕절개 포함), "
                    "산후기 5. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동 ② 전문등반, 글라이더 조종, 스카이다이빙, "
                    "스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩 등 직업·직무·동호회 활동 목적의 위험 행위로 "
                    "인한 상해는 다른 약정이 없으면 보장하지 않습니다."
                ),
                page_ref="p.20-21", embedding_id=None, default_color="빨강",
            ),
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=None,
                clause_type="서류", article_no="제7조(보험금의 청구)",
                text=(
                    "① 보험수익자는 다음의 서류를 제출하고 보험금을 청구하여야 합니다. 1. 청구서(회사 양식) "
                    "2. 사고증명서(진료비계산서, 사망진단서, 장해진단서, 입원치료확인서, 의사처방전(처방조제비) 등) "
                    "3. 신분증(주민등록증이나 운전면허증 등 사진이 붙은 정부기관발행 신분증) "
                    "4. 기타 보험수익자가 보험금의 수령에 필요하여 제출하는 서류 ② 사고증명서는 의료법 제3조"
                    "(의료기관)에서 규정한 국내의 병원이나 의원 또는 국외의 의료관련법에서 정한 의료기관에서 "
                    "발급한 것이어야 합니다."
                ),
                page_ref="p.22-23", embedding_id=None, default_color="노랑",
            ),
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_ovs_inj_med.coverage_id,
                clause_type="보장정의", article_no="제3조(보장종목별 보상내용) (1)상해-해외의료비",
                text=(
                    "① 회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 해외의료기관에서 "
                    "의사(치료받는 국가의 법에서 정한 병원 및 의사의 면허를 가진 자에 한함)의 치료를 받은 때에는 "
                    "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다. ② 척추지압술이나 "
                    "침술 치료로 인한 의료비는 하나의 상해에 대하여 US $1,000.00 한도로 보상합니다. ③ 유독가스 "
                    "또는 유독물질을 우연히 일시에 흡입·흡수·섭취한 결과로 생긴 중독증상이 포함됩니다. ④ 보험기간 "
                    "종료일부터 180일까지(종료일 제외) 계속 치료 시 보상합니다."
                ),
                page_ref="p.38-40", embedding_id=None, default_color="파랑",
            ),
            # 해외의료비 특약도 청구서류는 보통약관 공통 제7조를 따른다(원문에 별도 언급 없음).
            # RESCUE
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_rescue.coverage_id,
                clause_type="보장정의", article_no="제1조(보상하는 손해)~제2조(비용의 범위)",
                text=(
                    "① 회사는 해외여행 중에 피보험자가 탑승한 항공기 또는 선박이 행방불명 또는 조난된 경우, "
                    "산악등반 중 조난된 경우, 급격하고도 우연한 외래의 사고로 긴급수색구조 등이 필요한 상태로 된 것이 "
                    "경찰 등 공공기관에 의해 확인된 경우, 보통약관 제3조의 상해를 직접원인으로 사고일로부터 1년 "
                    "이내 사망하거나 약정 일수 이상 계속 입원한 경우, 질병을 직접원인으로 사망 또는 약정 일수 이상 "
                    "입원한 경우 비용을 보상합니다. 비용의 범위: 1.수색구조비용 2.항공운임 등 교통비(구원자 2명분 "
                    "한도) 3.숙박비(구원자 2명분 한도) 4.이송비용 5.제잡비(10만원 한도)"
                ),
                page_ref="p.87-88", embedding_id=None, default_color="파랑",
            ),
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_rescue.coverage_id,
                clause_type="면책", article_no="제3조(보상하지 않는 손해)",
                text=(
                    "회사는 보통약관 제5조(보험금을 지급하지 않는 사유) 제1항 제1호 내지 제3호(피보험자·보험수익자·"
                    "계약자의 고의)의 사유를 원인으로 하여 생긴 손해는 보상하여 드리지 않습니다."
                ),
                page_ref="p.87", embedding_id=None, default_color="빨강",
            ),
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_rescue.coverage_id,
                clause_type="조건", article_no="제6조(보상한도액)",
                text=(
                    "회사가 이 특별약관에 관하여 지급할 보험금은 보험기간을 통하여 이 특별약관의 보험가입금액을 "
                    "한도로 합니다. 지급할 보험금은 손해액에서 보험증권에 기재된 자기부담금을 공제한 금액으로 합니다."
                ),
                page_ref="p.87", embedding_id=None, default_color="노랑",
            ),
        ]
        db.add_all(clauses)
        db.flush()
        clause_by_article = {c.article_no: c for c in clauses}

        docs_map = seed_common_doc_std(db)

        doc_maps = [
            CoverageDocMap(coverage_id=cov_death_injury.coverage_id, required_doc_std_id=docs_map["CLAIM_FORM"].required_doc_std_id, is_mandatory=True, clause_id=clause_by_article["제7조(보험금의 청구)"].clause_id),
            CoverageDocMap(coverage_id=cov_death_injury.coverage_id, required_doc_std_id=docs_map["DEATH_CERT"].required_doc_std_id, is_mandatory=True, clause_id=clause_by_article["제7조(보험금의 청구)"].clause_id),
            CoverageDocMap(coverage_id=cov_death_injury.coverage_id, required_doc_std_id=docs_map["DISABILITY_CERT"].required_doc_std_id, is_mandatory=False, clause_id=clause_by_article["제7조(보험금의 청구)"].clause_id),
            CoverageDocMap(coverage_id=cov_death_injury.coverage_id, required_doc_std_id=docs_map["ID_CARD"].required_doc_std_id, is_mandatory=True, clause_id=clause_by_article["제7조(보험금의 청구)"].clause_id),

            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=docs_map["CLAIM_FORM"].required_doc_std_id, is_mandatory=True, clause_id=clause_by_article["제7조(보험금의 청구)"].clause_id),
            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=docs_map["MEDICAL_EXPENSE_CERT"].required_doc_std_id, is_mandatory=True, clause_id=clause_by_article["제7조(보험금의 청구)"].clause_id),
            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=docs_map["TREATMENT_CERT"].required_doc_std_id, is_mandatory=False, clause_id=clause_by_article["제7조(보험금의 청구)"].clause_id),
            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=docs_map["PRESCRIPTION"].required_doc_std_id, is_mandatory=False, clause_id=clause_by_article["제7조(보험금의 청구)"].clause_id),
            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=docs_map["ID_CARD"].required_doc_std_id, is_mandatory=True, clause_id=clause_by_article["제7조(보험금의 청구)"].clause_id),

            # RESCUE 서류도 원문 명시 없음 → is_mandatory=False, 보통약관 공통조항 추론 매핑
            CoverageDocMap(coverage_id=cov_rescue.coverage_id, required_doc_std_id=docs_map["CLAIM_FORM"].required_doc_std_id, is_mandatory=False, clause_id=clause_by_article["제7조(보험금의 청구)"].clause_id),
            CoverageDocMap(coverage_id=cov_rescue.coverage_id, required_doc_std_id=docs_map["ID_CARD"].required_doc_std_id, is_mandatory=False, clause_id=clause_by_article["제7조(보험금의 청구)"].clause_id),
        ]
        db.add_all(doc_maps)

        db.commit()
        print(f"현대해상 KB 시드 완료: coverage=3, clause={len(clauses)}, coverage_doc_map={len(doc_maps)}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
