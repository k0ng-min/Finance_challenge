"""
현대해상(HYUNDAI) INJ 상해 딥다이브 1차분 — data/raw_pdfs/hyundai_overseas_CM8403_20250630.pdf

삼성화재에서 발견된 두 가지 문제를 현대해상에도 같은 방식으로 대조 확인한 결과:

1. 면책조항 잘림/파편화 문제 — 현대해상은 **이미 정상**이었다.
   clause_id=11("상해사망·후유장해 (보통약관)" 담보의 제5조 면책조항)을 PDF p.22
   (pdfplumber 0-based page index 21) 원문과 문자 단위로 대조(diff)한 결과 완전히 일치했다.
   ②항의 "직업·직무·동호회 활동목적" 위험행위 목록(전문등반/스카이다이빙/스쿠버다이빙/
   오토바이 경기/선박탑승 직무자 등 3개 호 전부)이 이미 원문 그대로 들어있었다.
   -> 이 스크립트에서는 안전을 위해 idempotent 가드(누락된 항목 문자열 존재 여부)만 남겨두고,
      실제로는 아무 것도 갱신하지 않을 것으로 예상된다(보고용으로 결과를 출력한다).

2. INJ_DOMESTIC_TREATMENT(귀국후 국내치료)에 매핑된 조항이 하나도 없었다 — 삼성화재와 동일한
   문제. 실제로는 "기본형 해외여행 급여 실손의료비보장 특별약관" 제3조(보장종목별 보상내용)
   (1)상해 해외의료비의 하위 항목 "국내(급여)"(PDF p.40, pdfplumber 0-based page index 39)에
   정확히 이 유형을 다루는 문장이 있다 — 해외여행 중 입은 상해로 귀국 후 국내 의료기관·약국에서
   치료받는 경우를 다룬다. 기존 OVS_INJ_MED 담보(coverage_id 재사용, 같은 특약의 하위 항목)에
   조항만 추가한다.

   원문에서 "국내(급여)"는 표(table) 레이아웃의 행 레이블이 본문 중간(문장 "보험기간 종료" 와
   "후 30일" 사이)에 끼어 추출된 것이었다 — pdfplumber가 표의 왼쪽 레이블 열을 오른쪽 본문 열과
   같은 줄로 합쳐 뽑아낸 표 추출 아티팩트다. 레이블을 제거하고 나머지 문장만 이어붙이면
   (다른 줄바꿈 지점과 동일한 규칙으로) 문법적으로 완전한 문장이 복원되므로, 해당 레이블만 제거하고
   나머지는 pdfplumber extract_text() 결과 그대로 사용했다.
"""
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import Clause, ClauseIncidentMap, Coverage, IncidentType, PolicyVersion, Product, Insurer

DEATH_INJURY_WAIVER_FULL = (
    "① 회사는 다음 중 어느 한가지로 보험금 지급사유가 발생한 때에는 보험금을 지급하지 않습니다. "
    "1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 의사결정을 할 수 없는 "
    "상태에서 자신을 해친 경우에는 보험금을 지급합니다. "
    "2. 보험수익자가 고의로 피보험자를 해친 경우. 다만, 그 보험수익자가 보험금의 일부 보험수익자인 경우에는 "
    "다른 보험수익자에 대한 보험금은 지급합니다. "
    "3. 계약자가 고의로 피보험자를 해친 경우 "
    "4. 피보험자의 임신, 출산(제왕절개를 포함합니다), 산후기. 그러나, 회사가 보장하는 보험금 지급사유와 보장"
    "개시일부터 2년이 지난 후에 발생한 습관성 유산, 불임 및 인공수정 관련 합병증으로 인한 경우에는 보험"
    "금을 지급합니다. "
    "5. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동 "
    "② 회사는 다른 약정이 없으면 피보험자가 직업, 직무 또는 동호회 활동목적으로 아래에 열거된 행위로 인하여 "
    "제3조(보험금의 지급사유)의 상해 관련 보험금 지급사유가 발생한 때에는 해당 보험금을 지급하지 않습니다. "
    "1. 전문등반(전문적인 등산용구를 사용하여 암벽 또는 빙벽을 오르내리거나 특수한 기술, 경험, 사전훈련을 "
    "필요로 하는 등반을 말합니다), 글라이더 조종, 스카이다이빙, 스쿠버다이빙, 행글라이딩, 수상보트, 패러글"
    "라이딩 "
    "2. 모터보트, 자동차 또는 오토바이에 의한 경기, 시범, 흥행(이를 위한 연습을 포함합니다) 또는 시운전(다만, "
    "공용도로상에서 시운전을 하는 동안 보험금 지급사유가 발생한 경우에는 보장합니다) "
    "3. 선박에 탑승하는 것을 직무로 하는 사람이 직무상 선박에 탑승하고 있는 동안"
)

DOMESTIC_TREATMENT_TEXT = (
    "① 회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 국내 의료기관․약국에서 "
    "치료를 받은 때에는 <붙임2>에 따라 보상합니다. 다만, 보험기간이 1년 미만인 경우에는 해외여행 중에 "
    "피보험자가 입은 상해로 보험기간 종료 후 30일(보험기간 종료일은 제외합니다) 이내에 의사의 치료를 받기 "
    "시작했을 때에는 의사의 치료를 받기 시작한 날부터 180일(통원은 180일 동안 90회)까지만(보험기간 "
    "종료일은 제외합니다) 보상합니다."
)


def run():
    db = SessionLocal()
    try:
        insurer = db.query(Insurer).filter_by(code="HYUNDAI").first()
        if not insurer:
            print("현대해상이 아직 시딩되지 않았습니다. seed_hyundai를 먼저 실행하세요.")
            return
        policy_version = (
            db.query(PolicyVersion)
            .join(Product, Product.product_id == PolicyVersion.product_id)
            .filter(Product.insurer_id == insurer.insurer_id)
            .first()
        )

        # 1) DEATH_INJURY 면책 조항 원문 보정. PDF p.22와 대조한 결과 이미 원문 전체가 들어있었으므로
        #    (모터보트/자동차/오토바이 경기, 선박탑승 직무자 항목까지 포함) 정상적으로는 아무 것도
        #    갱신하지 않는다. 혹시 DB가 예전 파편화된 버전으로 롤백돼 있는 경우를 대비한 idempotent 가드.
        waiver = (
            db.query(Clause)
            .join(Coverage, Coverage.coverage_id == Clause.coverage_id)
            .filter(Clause.policy_version_id == policy_version.policy_version_id,
                    Clause.clause_type == "면책", Coverage.raw_name.like("상해사망%"))
            .first()
        )
        updated = False
        if waiver and waiver.text != DEATH_INJURY_WAIVER_FULL and "선박에 탑승하는 것을 직무로" not in waiver.text:
            waiver.text = DEATH_INJURY_WAIVER_FULL
            updated = True

        # 2) 귀국후 국내치료(INJ_DOMESTIC_TREATMENT) 조항 추가 — 기존 OVS_INJ_MED 담보에 상해
        # "국내(급여)" 항목만 새 조항으로 얹는다(같은 특약의 하위 항목이라 coverage_id 재사용).
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
                    article_no="제3조(보장종목별 보상내용) (1)상해-국내(급여)",
                    text=DOMESTIC_TREATMENT_TEXT,
                    page_ref="p.40",
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
        print(f"hyundai INJ 딥다이브 1차: 면책조항 보정={updated}, 국내치료 조항 추가={inserted}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
