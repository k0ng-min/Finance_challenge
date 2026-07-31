"""
메리츠화재해상보험 INJ 상해 딥다이브 — data/raw_pdfs/meritz_overseas_udirect.pdf (총 220페이지)
seed_samsung_inj_deep.py와 동일한 방식(PDF 원문 직접 대조 후 갱신·추가)으로 삼성화재에서
발견된 두 가지 문제를 메리츠화재에 대해서도 확인하고 고친 결과다.

1. clause_id=18([상해 사망·후유장해 특별약관] 제3조(보험금을 지급하지 않는 사유), coverage
   raw_name='상해 사망·후유장해 특별약관')이 DB에 "② 회사는 다른 약정이 없으면 피보험자가 직업,
   직무 또는 동호회 활동목적으로 아래에 열거된 행위로 인하여"에서 그대로 잘려 있었다. PDF
   p.86~87을 pdfplumber로 직접 대조한 결과, 실제로는 그 뒤에 "제1조(보험금의 지급사유)의 상해
   관련 보험금 지급사유가 발생한 때에는 해당 보험금을 지급하지 않습니다."라는 문구와 함께
   위험활동 목록 3개 항(①전문등반/글라이더조종/스카이다이빙/스쿠버다이빙/행글라이딩/수상보트/
   패러글라이딩, ②모터보트·자동차·오토바이 경기, ③선박 탑승을 직무로 하는 사람의 직무상 탑승)이
   이어진다. 삼성화재와 문구가 사실상 동일한 KIDI 표준 조항이지만, 이 파일에서는 메리츠 PDF
   p.86~87 원문을 별도로 재추출·검증해서 반영했다(재사용 아님).
2. INJ_DOMESTIC_TREATMENT(귀국후 국내치료)에 매핑된 조항이 메리츠에는 하나도 없었다. coverage_id
   8('해외여행 실손의료보험 특별약관 - (1)상해의료비 해외')에는 "해외" 항목 조항(clause_id=20)만
   있고 "국내(급여)" 항목 조항이 빠져 있었다. PDF p.20(기본형 해외여행 실손의료보험 제3조
   (보장종목별 보상내용) (1)상해의료비 국내(급여))에서 원문을 확인해 조항을 추가하고,
   IncidentType.l2_code="INJ_DOMESTIC_TREATMENT"(type_id=4)에 relevance="직접"로 매핑한다.

두 텍스트 모두 pdfplumber extract_text()로 해당 페이지를 재추출해 문장 단위로 원문에 실제
존재하는지 대조 검증했다(공백을 제거한 부분 문자열 매칭으로 모든 문장 조각의 존재를 확인).
"""
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import Clause, ClauseIncidentMap, Coverage, IncidentType, PolicyVersion, Product, Insurer

DEATH_INJURY_WAIVER_FULL = (
    "① 회사는 다음 중 어느 한가지로 보험금 지급사유가 발생한 때에는 보험금을 지급하지 않습니다. "
    "1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 의사결정을 "
    "할 수 없는 상태에서 자신을 해친 경우에는 보험금을 지급합니다. "
    "2. 보험수익자가 고의로 피보험자를 해친 경우. 다만, 그 보험수익자가 보험금의 일부 보험수익자인 "
    "경우에는 다른 보험수익자에 대한 보험금은 지급합니다. "
    "3. 계약자가 고의로 피보험자를 해친 경우 "
    "4. 피보험자의 임신, 출산(제왕절개를 포함합니다), 산후기. 그러나, 회사가 보장하는 보험금 지급사유로 "
    "인한 경우에는 보험금을 지급합니다. "
    "5. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동 "
    "② 회사는 다른 약정이 없으면 피보험자가 직업, 직무 또는 동호회 활동목적으로 아래에 열거된 행위로 "
    "인하여 제1조(보험금의 지급사유)의 상해 관련 보험금 지급사유가 발생한 때에는 해당 보험금을 지급하지 "
    "않습니다. "
    "1. 전문등반(전문적인 등산용구를 사용하여 암벽 또는 빙벽을 오르내리거나 특수한 기술, 경험, "
    "사전훈련을 필요로 하는 등반을 말합니다), 글라이더 조종, 스카이다이빙, 스쿠버다이빙, 행글라이딩, "
    "수상보트, 패러글라이딩 "
    "2. 모터보트, 자동차 또는 오토바이에 의한 경기, 시범, 흥행(이를 위한 연습을 포함합니다) 또는 "
    "시운전(다만, 공용도로상에서 시운전을 하는 동안 보험금 지급사유가 발생한 경우에는 보장합니다) "
    "3. 선박에 탑승하는 것을 직무로 하는 사람이 직무상 선박에 탑승하고 있는 동안"
)

DOMESTIC_TREATMENT_TEXT = (
    "① 회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 국내 의료기관"
    "․약국에서 치료를 받은 때에는 붙임2에 따라 보상합니다. 다만, 보험기간이 1년 미만인 경우에는 "
    "해외여행 중에 피보험자가 입은 상해로 보험기간 종료후 30일(보험기간 종료일은 제외합니다) 이내에 "
    "의사의 치료를 받기 시작했을 때에는 의사의 치료를 받기 시작한 날부터 180일(통원은 180일 동안 "
    "90회)까지만(보험기간 종료일은 제외합니다) 보상합니다."
)


def run():
    db = SessionLocal()
    try:
        insurer = db.query(Insurer).filter_by(code="MERITZ").first()
        if not insurer:
            print("메리츠화재가 아직 시딩되지 않았습니다. seed_meritz를 먼저 실행하세요.")
            return
        policy_version = (
            db.query(PolicyVersion)
            .join(Product, Product.product_id == PolicyVersion.product_id)
            .filter(Product.insurer_id == insurer.insurer_id)
            .first()
        )

        # 1) 상해 사망·후유장해 특별약관 면책(제3조) 조항 원문 보정 — "아래에 열거된 행위로 인하여"에서
        # 잘린 채로 시딩돼 있던 clause_id=18을 PDF p.86~87 원문 전체로 갱신한다.
        waiver = (
            db.query(Clause)
            .join(Coverage, Coverage.coverage_id == Clause.coverage_id)
            .filter(Clause.policy_version_id == policy_version.policy_version_id,
                    Clause.clause_type == "면책", Coverage.raw_name.like("상해 사망%"))
            .first()
        )
        updated = False
        if waiver and "선박에 탑승하는 것을 직무로" not in waiver.text:
            waiver.text = DEATH_INJURY_WAIVER_FULL
            waiver.page_ref = "p.86-87"
            updated = True

        # 2) 귀국후 국내치료(INJ_DOMESTIC_TREATMENT) 조항 추가 — 기존 OVS_INJ_MED 담보(coverage_id=8,
        # '해외여행 실손의료보험 특별약관 - (1)상해의료비 해외')에는 "해외" 항목 조항만 있고 "국내(급여)"
        # 항목이 빠져 있었다. PDF p.20에서 확인한 원문으로 같은 담보에 조항만 추가한다(coverage_id 재사용).
        ovs_inj_med_coverage = (
            db.query(Coverage)
            .filter(Coverage.policy_version_id == policy_version.policy_version_id,
                    Coverage.raw_name.like("%상해의료비 해외%"))
            .first()
        )
        inserted = False
        if ovs_inj_med_coverage:
            exists = (
                db.query(Clause)
                .filter(Clause.coverage_id == ovs_inj_med_coverage.coverage_id,
                        Clause.text == DOMESTIC_TREATMENT_TEXT)
                .first()
            )
            if not exists:
                new_clause = Clause(
                    policy_version_id=policy_version.policy_version_id,
                    coverage_id=ovs_inj_med_coverage.coverage_id,
                    clause_type="보장정의",
                    article_no="[해외여행 실손의료보험 특별약관] 제3조(보장종목별 보상내용) (1)상해의료비 국내(급여)",
                    text=DOMESTIC_TREATMENT_TEXT,
                    page_ref="p.20",
                    default_color="파랑",
                )
                db.add(new_clause)
                db.flush()

                domestic_type = db.query(IncidentType).filter_by(l2_code="INJ_DOMESTIC_TREATMENT").first()
                if domestic_type:
                    db.add(ClauseIncidentMap(
                        clause_id=new_clause.clause_id, type_id=domestic_type.type_id,
                        relevance="직접", mapped_by="human", confidence=1.0,
                    ))
                inserted = True

        db.commit()
        print(f"meritz INJ 딥다이브: 면책조항 보정={updated}, 국내치료 조항 추가={inserted}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
