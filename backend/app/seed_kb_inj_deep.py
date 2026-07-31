"""
KB손해보험 INJ 상해 딥다이브 1차분 — data/raw_pdfs/kb_overseas_15332_202004.pdf

삼성화재 딥다이브(seed_samsung_inj_deep.py)와 같은 방식으로 PDF 원문을 직접 대조해
확인한 두 가지를 반영한다:

1. clause_id=24(상해사망·후유장해 면책, 제5조)가 PDF p.20-21에서 "...아래에 열거된
   행위로 인하여" 까지만 저장되고 그 뒤(제3조 인용 및 ②항의 활동목록 1~3호 전체)가
   통째로 잘려 있었다. ②항의 "직업·직무·동호회 활동목적" 면책 사유(전문등반/스카이
   다이빙/스쿠버다이빙/모터보트·자동차·오토바이 경기 등 — incident.modifiers.activity와
   직결되는 부분)가 아예 빠져 있어서, 원문 전체로 갱신한다.
2. INJ_DOMESTIC_TREATMENT(귀국후 국내치료)에 매핑된 조항이 KB에는 하나도 없었다
   (기존 매핑은 삼성화재 clause_id=55뿐이었다). 실제로는 "기본형 해외여행 실손의료비
   특별약관" 제3조 (1)상해 "국내" 항목(p.98)이 정확히 이 유형이다 — 해외여행 중 입은
   상해로 귀국 후 국내에서 치료받는 경우를 다룬다. 기존 cov_id=11(기본형 해외여행
   실손의료비 특별약관 - (1)상해 해외의료비, 같은 특약의 하위 항목)에 조항만 추가한다.
   주의: KB PDF 표에는 이 행이 "국내"로만 라벨링되어 있고(삼성처럼 "국내(급여)"로
   세분화된 표기는 없음), pdfplumber 추출 시 표 열 라벨 "국내"가 본문 문장 중간
   ("...입은 상해로 보"+"국내"+"험기간 종료후...")에 끼어드는 현상이 있어 라벨을
   제거하고 문장을 복원했다.

이후 DB/현대/메리츠/카카오페이도 같은 방식으로 이어간다.
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
    "4. 피보험자의 임신, 출산(제왕절개를 포함합니다), 산후기. 그러나, 회사가 보장하는 보험금 "
    "지급사유로 인한 경우에는 보험금을 지급합니다. "
    "5. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동 "
    "② 회사는 다른 약정이 없으면 피보험자가 직업, 직무 또는 동호회 활동목적으로 아래에 열거된 "
    "행위로 인하여 제3조(보험금의 지급사유)의 상해 관련 보험금 지급사유가 발생한 때에는 해당 "
    "보험금을 지급하지 않습니다. "
    "1. 전문등반(전문적인 등산용구를 사용하여 암벽 또는 빙벽을 오르내리거나 특수한 기술, 경험, "
    "사전훈련을 필요로 하는 등반을 말합니다), 글라이더 조종, 스카이다이빙, 스쿠버다이빙, "
    "행글라이딩, 수상보트, 패러글라이딩 "
    "2. 모터보트, 자동차 또는 오토바이에 의한 경기, 시범, 흥행(이를 위한 연습을 포함합니다) "
    "또는 시운전(다만, 공용도로상에서 시운전을 하는 동안 보험금 지급사유가 발생한 경우에는 "
    "보장합니다) "
    "3. 선박승무원, 어부, 사공, 그밖에 선박에 탑승하는 것을 직무로 하는 사람이 직무상 선박에 "
    "탑승하고 있는 동안"
)

DOMESTIC_TREATMENT_TEXT = (
    "① 회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 국내 "
    "의료기관․약국에서 치료를 받은 때에는 <붙임2>에 따라 보상합니다. 다만, 해외여행 중에 "
    "피보험자가 입은 상해로 보험기간 종료후 30일(보험기간 종료일은 제외합니다) 이내에 의사의 "
    "치료를 받기 시작했을 때에는 의사의 치료를 받기 시작한 날부터 180일(통원은 180일 동안 "
    "외래는 방문 90회, 처방조제비는 처방전 90건)까지만(보험기간 종료일은 제외합니다) 보상합니다."
)


def run():
    db = SessionLocal()
    try:
        insurer = db.query(Insurer).filter_by(code="KB").first()
        if not insurer:
            print("KB손해보험이 아직 시딩되지 않았습니다. seed_kb를 먼저 실행하세요.")
            return
        policy_version = (
            db.query(PolicyVersion)
            .join(Product, Product.product_id == PolicyVersion.product_id)
            .filter(Product.insurer_id == insurer.insurer_id)
            .first()
        )

        # 1) DEATH_INJURY 면책 조항 원문 보정 (PDF p.20-21에서 "...아래에 열거된 행위로
        # 인하여"까지만 잘린 채로 시딩돼 있던 clause_id=24를 갱신)
        waiver = (
            db.query(Clause)
            .join(Coverage, Coverage.coverage_id == Clause.coverage_id)
            .filter(Clause.policy_version_id == policy_version.policy_version_id,
                    Clause.clause_type == "면책", Coverage.raw_name.like("상해사망%"))
            .first()
        )
        updated = False
        if waiver and "전문등반" not in waiver.text:
            waiver.text = DEATH_INJURY_WAIVER_FULL
            updated = True

        # 2) 귀국후 국내치료(INJ_DOMESTIC_TREATMENT) 조항 추가 — 기존 OVS_INJ_MED 담보에 상해
        # "국내" 항목만 새 조항으로 얹는다(같은 특약의 하위 항목이라 coverage_id 재사용).
        ovs_inj_med_coverage = (
            db.query(Coverage)
            .filter(Coverage.policy_version_id == policy_version.policy_version_id,
                    Coverage.raw_name.like("%상해 해외의료비%"))
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
                    article_no="제3조(보장종목별 보상내용) (1)상해-국내의료비",
                    text=DOMESTIC_TREATMENT_TEXT,
                    page_ref="p.98",
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
        print(f"KB INJ 딥다이브 1차: 면책조항 보정={updated}, 국내치료 조항 추가={inserted}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
