"""
카카오페이손해보험 INJ 상해 딥다이브 — data/raw_pdfs/kakaopay_overseas_20241101.pdf

삼성화재(seed_samsung_inj_deep.py)에서 발견한 두 가지 문제를 카카오페이에서도 그대로
발견해 반영한다. PDF를 pdfplumber로 직접 열어 페이지 원문과 DB를 대조했다.

1. clause_id=36(상해사망·후유장해 면책, 제5조)이 PDF p.18~19에서 도중에 잘린 채로
   시딩돼 있었다. 정확히는 ②항 본문 "... 아래에 열거된 행위로 인하여" 바로 다음, 즉
   "제3조(보험금의 지급사유)의 상해 관련 보험금 지급사유가 발생한 때에는 해당 보험금을
   지급하지 않습니다."부터 시작해서 ②항의 위험행위 목록 전체
   (1.전문등반/글라이더조종/스카이다이빙/스쿠버다이빙/행글라이딩/수상보트/패러글라이딩,
   2.모터보트·자동차·오토바이 경기/시범/흥행/시운전, 3.선박 탑승 직무)가 통째로
   빠져 있었다 — incident.modifiers.activity와 직결되는 부분이라 심각하다.
   기존 텍스트(①항 전체 + ②항 도입부, 습관성유산 팝업 문구 포함)는 이미 PDF 원문과
   일치하므로 그대로 두고, 잘린 지점 뒤에 빠진 부분만 이어붙여 전체 원문을 복원한다.

2. INJ_DOMESTIC_TREATMENT(귀국후 국내치료)에 매핑된 조항이 카카오페이에는 하나도
   없었다(기존 매핑은 policy_version_id=1인 삼성화재 조항 하나뿐). 실제로는
   "기본형 해외여행 실손의료비 특별약관" 제3조(보장종목별 보상내용) 표의
   "(1)상해 국내(급여)" 항목(p.42)이 정확히 이 유형이다 — 해외여행 중 입은 상해로
   귀국 후 국내에서 치료받는 경우를 다룬다. 흥미롭게도 삼성화재의 동일 조항과
   문구가 한 글자도 다르지 않다(업계 공통 표준 약관 문구로 보인다).
   기존 OVS_INJ_MED 담보(coverage_id=17, 같은 특약의 하위 항목)에 조항만 추가한다.

이후 KB/DB/현대/메리츠도 같은 방식(PDF 직접 대조 후 갱신·추가)으로 이어간다.
"""
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import Clause, ClauseIncidentMap, Coverage, IncidentType, PolicyVersion, Product, Insurer

# 잘리기 전까지 DB에 이미 저장돼 있던(=PDF와 이미 일치 확인된) 부분. 이 문자열이 그대로
# 들어있는지로 "아직 안 고쳐진 상태"를 idempotent하게 판별한다.
DEATH_INJURY_WAIVER_TRUNCATED_PREFIX_MARKER = "아래에 열거된 행위로 인하여"

DEATH_INJURY_WAIVER_FULL = (
    "① 회사는 다음 중 어느 한가지로 보험금 지급사유가 발생한 때에는 보험금을 지급하지 "
    "않습니다. 1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 "
    "자유로운 의사결정을 할 수 없는 상태에서 자신을 해친 경우에는 보험금을 지급합니다. "
    "2. 보험수익자가 고의로 피보험자를 해친 경우. 다만, 그 보험수익자가 보험금의 일부 "
    "보험수익자인 경우에는 다른 보험수익자에 대한 보험금은 지급합니다. "
    "3. 계약자가 고의로 피보험자를 해친 경우 "
    "4. 피보험자의 임신, 출산(제왕절개를 포함합니다), 산후기. 그러나, 회사가 보장하는 "
    "보험금 지급사유와 보장개시일부터 2년이 지난 후에 발생한 습관성 유산, 불임 및 "
    "인공수정 관련 합병증으로 인한 경우에는 보험금을 지급합니다. "
    "[습관성 유산, 불임 및 인공수정] 한국표준질병·사인분류상의 N96~N98에 해당하는 질병을 "
    "말합니다. "
    "5. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동 "
    "② 회사는 다른 약정이 없으면 피보험자가 직업, 직무 또는 동호회 활동목적으로 아래에 "
    "열거된 행위로 인하여 제3조(보험금의 지급사유)의 상해 관련 보험금 지급사유가 발생한 "
    "때에는 해당 보험금을 지급하지 않습니다. "
    "1. 전문등반(전문적인 등산용구를 사용하여 암벽 또는 빙벽을 오르내리거나 특수한 기술, "
    "경험, 사전훈련을 필요로 하는 등반을 말합니다), 글라이더 조종, 스카이다이빙, "
    "스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩 "
    "2. 모터보트, 자동차 또는 오토바이에 의한 경기, 시범, 흥행(이를 위한 연습을 "
    "포함합니다) 또는 시운전(다만, 공용도로상에서 시운전을 하는 동안 보험금 지급사유가 "
    "발생한 경우에는 보장합니다) "
    "3. 선박에 탑승하는 것을 직무로 하는 사람이 직무상 선박에 탑승하고 있는 동안"
)

# PDF p.42, "기본형 해외여행 실손의료비 특별약관" 제3조(보장종목별 보상내용) 표
# "(1)상해 국내(급여)" 항목. 삼성화재(p.57)와 문구가 완전히 동일하다.
DOMESTIC_TREATMENT_TEXT = (
    "① 회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 국내 "
    "의료기관ㆍ약국에서 치료를 받은 때에는 <붙임2>에 따라 보상합니다. 다만, 보험기간이 "
    "1년 미만인 경우에는 해외여행 중에 피보험자가 입은 상해로 보험기간 종료후 30일"
    "(보험기간 종료일은 제외합니다) 이내에 의사의 치료를 받기 시작했을 때에는 의사의 "
    "치료를 받기 시작한 날부터 180일(통원은 180일 동안 90회)까지만(보험기간 종료일은 "
    "제외합니다) 보상합니다."
)


def run():
    db = SessionLocal()
    try:
        insurer = db.query(Insurer).filter_by(code="KAKAOPAY").first()
        if not insurer:
            print("카카오페이손해보험이 아직 시딩되지 않았습니다. seed_kakaopay를 먼저 실행하세요.")
            return
        policy_version = (
            db.query(PolicyVersion)
            .join(Product, Product.product_id == PolicyVersion.product_id)
            .filter(Product.insurer_id == insurer.insurer_id)
            .first()
        )

        # 1) DEATH_INJURY 면책 조항 원문 보정 (잘린 채로 시딩돼 있던 clause_id 갱신)
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
            waiver.default_color = "빨강"
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
                    article_no="제3조(보장종목별 보상내용) (1)상해-국내(급여)의료비",
                    text=DOMESTIC_TREATMENT_TEXT,
                    page_ref="p.42",
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
        print(f"kakaopay INJ 딥다이브: 면책조항 보정={updated}, 국내치료 조항 추가={inserted}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
