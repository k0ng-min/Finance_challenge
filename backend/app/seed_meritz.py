"""
메리츠화재 해외여행보험 실물 약관 KB 시드 스크립트.

원문 출처: data/raw_pdfs/meritz_overseas_udirect.pdf
주의: 메리츠화재 공식 도메인(meritzfire.com)에서 약관 PDF의 정적 다운로드 링크를 찾지 못해,
여행보험 판매 파트너사(유다이렉트, ud.udirect.co.kr)가 게시한 PDF를 사용했다. 본문에
"메리츠화재해상보험주식회사" 명의와 실제 조항 번호·본문이 포함되어 있어 내용 자체는 진본으로
판단되지만, 공식 도메인 출처가 아니므로 source_register.md에 review_status=raw로 명시하고
검수가 더 필요함을 표시한다.

삼성화재/현대해상과 동일한 표준담보 3종을 매핑한다. 메리츠는 상해사망·후유장해가
'보통약관'이 아니라 '특별약관'으로 구성되어 있고(보험사마다 상품 구조가 다름을 보여주는 실제 사례),
구조송환비용 면책조항이 지진·전쟁·방사능까지 명시하는 등 회사별 문구 차이가 실재한다.
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
            name="메리츠화재해상보험", code="MERITZ", official_url="https://www.meritzfire.com",
            product_name="해외여행보험", product_code="MERITZ-OVERSEAS", channel="다이렉트/제휴",
            sale_start=None, collected_at=dt.date(2026, 7, 29),
            version_label="udirect_수집본", effective_date=None,
            source_url="https://ud.udirect.co.kr/travel/meritz/files/overseas.pdf",
        )
        if insurer is None:
            print("이미 시드됨 (MERITZ). 스킵합니다.")
            return

        std = seed_common_coverage_std(db)
        std_death_injury, std_ovs_inj_med, std_rescue = std["DEATH_INJURY"], std["OVS_INJ_MED"], std["RESCUE"]

        cov_death_injury = Coverage(
            policy_version_id=pv.policy_version_id, coverage_std_id=std_death_injury.coverage_std_id,
            raw_name="상해 사망·후유장해 특별약관",  # 삼성/현대는 보통약관 기본담보, 메리츠는 특약으로 구성됨(실제 차이)
            definition=(
                "회사는 피보험자가 보험증권에 기재된 여행을 목적으로 주거지를 출발하여 여행을 마치고 주거지에 "
                "도착할 때까지의 여행 도중에 다음 중 어느 하나의 사유가 발생한 경우에는 보험수익자에게 약정한 "
                "보험금을 지급합니다. 1. 보험기간 중에 상해의 직접결과로써 사망한 경우(질병으로 인한 사망은 "
                "제외합니다): 사망보험금 2. 보험기간 중 상해로 장해분류표(【별표1】참조)에서 정한 각 장해지급률에 "
                "해당하는 장해상태가 되었을 때: 후유장해보험금"
            ),
            limit_amount="가입금액 한도 (증권 기재 보험가입금액)",
            deductible=None,
            waiting_condition="장해지급률 미확정 시 상해 발생일부터 180일 시점 진단 기준",
        )
        cov_ovs_inj_med = Coverage(
            policy_version_id=pv.policy_version_id, coverage_std_id=std_ovs_inj_med.coverage_std_id,
            raw_name="해외여행 실손의료보험 특별약관 - (1)상해의료비 해외",
            definition=(
                "회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 해외의료기관에서 "
                "의사(치료받는 국가의 법에서 정한 병원 및 의사의 자격을 가진 자에 한함)의 치료를 받은 때에는 "
                "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다."
            ),
            limit_amount="보험가입금액 한도, 실제 부담 의료비 전액 (척추지압술·침술은 건당 US$1,000 한도)",
            deductible="가입 플랜별 상이 (원문에 자기부담금 자기부담률 조항 포함, 표준화는 관문2에서 재확인 필요)",
            waiting_condition="보험기간 종료 후에도 종료일부터 180일까지 계속 치료 시 보상",
        )
        cov_rescue = Coverage(
            policy_version_id=pv.policy_version_id, coverage_std_id=std_rescue.coverage_std_id,
            raw_name="여행중 중대사고 구조송환비용 특별약관",
            definition=(
                "회사는 여행 도중 피보험자가 탑승한 항공기·선박의 행방불명·조난, 산악등반 중 조난, 긴급수색구조가 "
                "필요한 사고(경찰 등 공공기관 확인), 상해를 직접원인으로 사고일부터 1년 이내 사망 또는 약정 일수 "
                "이상 계속 입원, 질병을 직접원인으로 한 사망·약정 일수 이상 입원 시 수색구조비용·구원자 교통비·"
                "숙박비·이송비용·제잡비를 보상합니다."
            ),
            limit_amount="보상한도액 한도 (구원자 교통비 2명분, 숙박비 1인당 14박 한도, 제잡비 10만원 한도)",
            deductible="1사고당 10만원 차감 후 약정 자기부담률 적용",
            waiting_condition="입원의 경우 보험증권에 기재된 약정 일수 이상 계속 입원 필요",
        )
        db.add_all([cov_death_injury, cov_ovs_inj_med, cov_rescue])
        db.flush()

        clauses = [
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_death_injury.coverage_id,
                clause_type="보장정의", article_no="[상해 사망·후유장해 특별약관] 제1조(보험금의 지급사유)",
                text=(
                    "회사는 피보험자가 보험증권에 기재된 여행을 목적으로 주거지를 출발하여 여행을 마치고 주거지에 "
                    "도착할 때까지의 여행 도중에 다음 중 어느 하나의 사유가 발생한 경우에는 보험수익자에게 약정한 "
                    "보험금을 지급합니다. 1. 보험기간 중에 상해의 직접결과로써 사망한 경우(질병으로 인한 사망은 "
                    "제외합니다): 사망보험금 2. 보험기간 중 상해로 장해분류표(【별표1】참조)에서 정한 각 "
                    "장해지급률에 해당하는 장해상태가 되었을 때: 후유장해보험금"
                ),
                page_ref="p.85", embedding_id=None, default_color="파랑",
            ),
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_death_injury.coverage_id,
                clause_type="면책", article_no="[상해 사망·후유장해 특별약관] 제3조(보험금을 지급하지 않는 사유)",
                text=(
                    "① 회사는 다음 중 어느 한가지로 보험금 지급사유가 발생한 때에는 보험금을 지급하지 않습니다. "
                    "1. 피보험자가 고의로 자신을 해친 경우(심신상실 등 예외 있음) 2. 보험수익자가 고의로 피보험자를 "
                    "해친 경우 3. 계약자가 고의로 피보험자를 해친 경우 4. 피보험자의 임신, 출산(제왕절개 포함), "
                    "산후기 5. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동 ② 전문등반, 글라이더 조종, 스카이다이빙, "
                    "스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩 등 직업·직무·동호회 활동 목적의 위험 행위로 "
                    "인한 상해는 다른 약정이 없으면 보장하지 않습니다. (단, 메리츠는 '운동 및 기타위험 확장보상 "
                    "추가특별약관'을 별도로 가입하면 전문등반 등도 보장 가능 — 삼성/현대 약관에는 없는 확장특약)"
                ),
                page_ref="p.86-87", embedding_id=None, default_color="빨강",
            ),
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=None,
                clause_type="서류", article_no="[보통약관] 제7조(보험금의 청구)",
                text=(
                    "① 보험수익자는 다음의 서류를 제출하고 보험금을 청구하여야 합니다. 1. 청구서 (회사 양식) "
                    "2. 사고증명서 (진료비계산서, 진료비세부내역서, 입원치료확인서, 의사처방전(처방조제비) 등) "
                    "3. 신분증(주민등록증이나 운전면허증 등 본인임을 확인할 수 있는 사진이 붙은 정부기관에서 "
                    "발행한 신분증, 본인이 아닌 경우에는 본인의 인감증명서 또는 본인서명사실확인서 포함) "
                    "4. 그 밖에 보험수익자가 보험금 수령에 필요하여 제출하는 서류 ② 사고증명서는 의료법 제3조"
                    "(의료기관)에서 규정한 의료기관 또는 국외의 의료관련법에서 정한 의료기관에서 발급한 것이어야 "
                    "합니다."
                ),
                page_ref="p.27", embedding_id=None, default_color="노랑",
            ),
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_ovs_inj_med.coverage_id,
                clause_type="보장정의", article_no="[해외여행 실손의료보험 특별약관] 제3조(보장종목별 보상내용) (1)상해의료비 해외",
                text=(
                    "① 회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 해외의료기관에서 "
                    "의사(치료받는 국가의 법에서 정한 병원 및 의사의 자격을 가진 자에 한함)의 치료를 받은 때에는 "
                    "보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다. ② 척추지압술이나 "
                    "침술 치료로 인한 의료비는 하나의 상해에 대하여 US $1,000.00 한도로 보상하여 드립니다. "
                    "③ 유독가스 또는 유독물질을 우연히 일시에 흡입, 흡수 또는 섭취한 결과로 생긴 중독증상이 "
                    "포함됩니다. ④ 보험기간 종료일로부터 180일까지(종료일 제외) 계속 치료 시 보상합니다."
                ),
                page_ref="p.19-20", embedding_id=None, default_color="파랑",
            ),
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_rescue.coverage_id,
                clause_type="보장정의", article_no="[여행중 중대사고 구조송환비용 특별약관] 제1조(보험금의 지급사유)~제2조(비용의 범위)",
                text=(
                    "① 회사는 피보험자가 보험증권에 기재된 여행을 목적으로 주거지를 출발하여 여행을 마치고 주거지에 "
                    "도착할 때까지의 여행 도중에 탑승한 항공기 또는 선박이 행방불명 또는 조난된 경우 또는 산악등반 "
                    "중에 조난된 경우, 급격하고도 우연한 외래의 사고에 따라 긴급수색구조 등이 필요한 상태로 된 것이 "
                    "경찰 등의 공공기관에 의하여 확인된 경우, 상해를 직접원인으로 사고일부터 1년 이내 사망 또는 "
                    "약정 일수 이상 계속 입원한 경우, 질병을 직접원인으로 여행 도중 사망 또는 약정 일수 이상 "
                    "입원한 경우에 비용을 보상합니다. 비용의 범위: 1.수색구조비용 2.항공운임 등 교통비(구원자 "
                    "2명분 한도) 3.숙박비(구원자 2명분, 1인당 14박 한도) 4.이송비용 5.제잡비(10만원 한도)"
                ),
                page_ref="p.126", embedding_id=None, default_color="파랑",
            ),
            Clause(
                policy_version_id=pv.policy_version_id, coverage_id=cov_rescue.coverage_id,
                clause_type="면책", article_no="[여행중 중대사고 구조송환비용 특별약관] 제3조(보험금을 지급하지 않는 사유)",
                text=(
                    "회사는 아래의 사유를 원인으로 하여 생긴 손해는 보상하여 드리지 않습니다. 1. 계약자나 피보험자의 "
                    "고의 2. 보험수익자의 고의(일부수익자 예외) 3. 피보험자의 자해, 자살, 자살미수, 형법상의 "
                    "범죄행위 또는 폭력행위(정당방위·긴급피난·정당행위 예외) 4. 피보험자의 사형 5. 지진, 분화, "
                    "해일 또는 이와 비슷한 천재지변 6. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동, 소요, 노동쟁의 "
                    "기타 이들과 유사한 사태 7. 핵연료물질 관련 사고 8. 방사선을 쬐는 것 또는 방사능 오염 "
                    "(삼성화재보다 면책범위가 넓음 — 지진/천재지변, 방사능까지 명시)"
                ),
                page_ref="p.127", embedding_id=None, default_color="빨강",
            ),
        ]
        db.add_all(clauses)
        db.flush()
        clause_by_article = {c.article_no: c for c in clauses}
        common_doc_clause = clause_by_article["[보통약관] 제7조(보험금의 청구)"]

        docs_map = seed_common_doc_std(db)

        doc_maps = [
            CoverageDocMap(coverage_id=cov_death_injury.coverage_id, required_doc_std_id=docs_map["CLAIM_FORM"].required_doc_std_id, is_mandatory=True, clause_id=common_doc_clause.clause_id),
            CoverageDocMap(coverage_id=cov_death_injury.coverage_id, required_doc_std_id=docs_map["DEATH_CERT"].required_doc_std_id, is_mandatory=True, clause_id=common_doc_clause.clause_id),
            CoverageDocMap(coverage_id=cov_death_injury.coverage_id, required_doc_std_id=docs_map["DISABILITY_CERT"].required_doc_std_id, is_mandatory=False, clause_id=common_doc_clause.clause_id),
            CoverageDocMap(coverage_id=cov_death_injury.coverage_id, required_doc_std_id=docs_map["ID_CARD"].required_doc_std_id, is_mandatory=True, clause_id=common_doc_clause.clause_id),

            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=docs_map["CLAIM_FORM"].required_doc_std_id, is_mandatory=True, clause_id=common_doc_clause.clause_id),
            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=docs_map["MEDICAL_EXPENSE_CERT"].required_doc_std_id, is_mandatory=True, clause_id=common_doc_clause.clause_id),
            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=docs_map["MEDICAL_DETAIL_CERT"].required_doc_std_id, is_mandatory=True, clause_id=common_doc_clause.clause_id),
            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=docs_map["TREATMENT_CERT"].required_doc_std_id, is_mandatory=False, clause_id=common_doc_clause.clause_id),
            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=docs_map["PRESCRIPTION"].required_doc_std_id, is_mandatory=False, clause_id=common_doc_clause.clause_id),
            CoverageDocMap(coverage_id=cov_ovs_inj_med.coverage_id, required_doc_std_id=docs_map["ID_CARD"].required_doc_std_id, is_mandatory=True, clause_id=common_doc_clause.clause_id),

            CoverageDocMap(coverage_id=cov_rescue.coverage_id, required_doc_std_id=docs_map["CLAIM_FORM"].required_doc_std_id, is_mandatory=False, clause_id=common_doc_clause.clause_id),
            CoverageDocMap(coverage_id=cov_rescue.coverage_id, required_doc_std_id=docs_map["ID_CARD"].required_doc_std_id, is_mandatory=False, clause_id=common_doc_clause.clause_id),
        ]
        db.add_all(doc_maps)

        db.commit()
        print(f"메리츠화재 KB 시드 완료: coverage=3, clause={len(clauses)}, coverage_doc_map={len(doc_maps)}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
