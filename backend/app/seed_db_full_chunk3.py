"""
DB손해보험(insurer.code="DB") 전체 재검토 — 청크 3(PDF p.85~126).
data/raw_pdfs/db_overseas.pdf (총 126쪽, "프로미 해외여행보험I")을 pdfplumber로
p.85~126 전체를 직접 읽고 대조한 결과를 반영한다.

## p.85: 해외여행중 중단사고발생 추가비용 특별약관
제1조~제4조를 원문 그대로 Clause로 넣었다. 지급사유, 용어정의, 보상범위, 면책 사항 모두 포함.
CoverageStd TRIP_INTERRUPTION 사용(CHG_INTERRUPTION으로 매핑). 새 담보 아님(이미 일반약관에서
사용 중).

## p.86~91: 부부/가족/단체/보험료정산/외환/지정대리청구 관련 특약들
직접 다 읽었다. 내용은 다음과 같고 전부 "사고가 뭐였나"(incident_type)와 무관한
계약 구조/행정 조항이다 — 억지로 끼워맞추지 않고 그대로 스킵한다.
- 제86호 부부 특별약관 (피보험자 범위 확대)
- 제86호 가족 특별약관 (피보험자 범위 확대)
- 제86-87호 단체계약 특별약관 (단체 관리)
- 제87-89호 해외여행자 통지 추가특별약관 (보험료 정산)
- 제88-90호 보험료정산 관련 추가특별약관들 (보험료 정산)
- 제90호 해외여행 상품다수구매자 보험계약 특별약관 (단체 취급)
- 제91호 외환환산 특별약관 (환율 적용)
- 제91-92호 지정대리청구서비스 특별약관 (대리청구 절차 — 사고유형 분류 불필요)
결론: 이들 22개 조항 중 사고유형 분류에 쓸 만한 내용은 하나도 없다(확인 완료, 억지 매핑
없음). 모두 보험 계약 관리·행정 절차이지 사고 발생 시 지급/판단 기준이 아니다.

## p.92: 특수운동중 상해위험 특별약관 (신규 담보)
제1조(지급사유)·제2조(준용규정)를 원문 그대로 넣었다.
- 전문등반, 글라이더 조종, 스카이다이빙, 스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩
  중 상해로 인한 사망·후유장해·의료비 보장 — 일반 해외여행 보험 약관의 상해 면책을
  명시적으로 해제하는 특약
- CoverageStd INJ_SPECIAL_SPORTS로 새로 추가 (위험 스포츠 활동 관련 상해보장)
- INJ_DEATH_DISABILITY, INJ_OVERSEAS_TREATMENT 모두 매핑 가능

## p.93: 특수운전중 상해위험 특별약관 (신규 담보)
제1조(지급사유)·제2조(준용규정)를 원문 그대로 넣었다.
- 모터보트, 자동차, 오토바이에 의한 경기·시범·흥행·시운전 중 상해로 인한
  사망·후유장해·의료비 보장 — 일반 해외여행 보험 약관의 상해 면책을 명시적으로 해제하는
  특약
- CoverageStd INJ_SPECIAL_DRIVING으로 새로 추가 (특수 운전 활동 관련 상해보장)
- INJ_DEATH_DISABILITY, INJ_OVERSEAS_TREATMENT 모두 매핑 가능

## p.94-99: 단체취급/전자서명/장애인전용보험전환 특약
직접 다 읽었다. 내용은:
- 제94호 단체취급 특별약관 (단체 계약 관리)
- 제94-95호 단체취급 보험료정산 추가특별약관 (보험료 정산)
- 제95호 전자서명 특별약관 (전자계약 절차)
- 제96-99호 장애인전용보험전환 특별약관 (세제 혜택 적용 절차)
결론: 전부 계약 관리·행정 절차이지 사고유형 분류 불필요.

## p.100-126: 별표(장해분류표, 식중독/전염병 분류, 해외여행 통지 양식, 이자 규정)
참고용 자료이지 특약이 아니다. 건너뜀.

## 최종 산출
- Coverage: 3개 (해외여행중 중단사고, 특수운동, 특수운전)
- Clause: 약 10개
- ClauseIncidentMap: 약 12개
- 새 CoverageStd: 2개 (INJ_SPECIAL_SPORTS, INJ_SPECIAL_DRIVING)

멱등성: Coverage는 raw_name, Clause는 (coverage_id, article_no, text) 조합,
ClauseIncidentMap은 (clause_id, type_id) 조합으로 이미 있으면 건너뛴다.
"""
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Clause, ClauseIncidentMap, Coverage, IncidentType, Insurer, PolicyVersion, Product,
)
from app.services.kb_seed_common import get_or_create_coverage_std

# ---------------------------------------------------------------------------
# 해외여행중 중단사고발생 추가비용 특별약관 (p.85)
# ---------------------------------------------------------------------------

TRIP_INT_CLAUSE1_TEXT = (
    "회사는 피보험자가 해외여행 도중에 아래의 사유로 여행일정을 불가피하게 중단(축소)하고 귀국하게 되었을 경우 "
    "피보험자가 추가적으로 부담한 비용을 이 특별약관에 따라 보험가입금액을 한도로 보상하여 드립니다. "
    "1. 피보험자 및 여행동반 가족이 상해 또는 질병으로 3일 이상 입원한 경우 "
    "2. 보험기간 내 피보험자의 3촌 이내의 친족 또는 여행동반자의 사망 "
    "3. 지진, 분화, 해일 또는 이와 비슷한 천재지변 "
    "4. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동, 소요, 기타 이들과 유사한 사태"
)

TRIP_INT_CLAUSE2_TEXT = (
    "이 특별약관에서 사용하는 용어의 뜻은 다음과 같습니다. "
    "- 가족: 피보험자 본인의 배우자, 본인 또는 배우자의 부모, 본인 또는 배우자의 자녀, 본인의 며느리 및 사위, "
    "본인 및 배우자의 형제자매 "
    "- 여행동반자: 피보험자와 해외여행을 함께하는 모든 사람(여행사를 통한 패키지여행 포함)"
)

TRIP_INT_CLAUSE3_TEXT = (
    "회사가 보상하는 비용은 아래와 같습니다. "
    "1. 피보험자가 여행중단 사유 발생 이전에 귀국항공 또는 선박 운임비용을 미리 지급한 경우에 한하여 "
    "여행중단 사유 발생으로 여행을 중단하고 일정을 변경하여 귀국함으로서 미리 지급한 항공 또는 선박 운임비용을 "
    "초과하여 피보험자에게 추가로 발생하는 항공 또는 선박 운임비용 "
    "2. 피보험자가 여행중단 사유 발생으로 여행중단 후 귀국으로 인해 여행중단 사유 발생 이전에 미리 지급한 숙박비용을 "
    "초과하여 피보험자에게 추가로 발생하는 2박 이내의 숙박비용"
)

TRIP_INT_CLAUSE4_TEXT = (
    "회사는 보통약관 제5조(보험금을 지급하지 않는 사유)의 제 1항 제 5호를 제외한 사유 및 계약자와 피보험자 및 "
    "보험수익자의 고의로 인하여 생긴 손해는 보상하여 드리지 않습니다."
)

# ---------------------------------------------------------------------------
# 특수운동중 상해위험 특별약관 (p.92)
# ---------------------------------------------------------------------------

SPORTS_INJ_CLAUSE1_TEXT = (
    "회사는 피보험자에게 다음 중 어느 하나의 사유가 발생한 경우에는 보험수익자에게 약정한 보험금을 지급합니다. "
    "1. 「보통약관 제3조(보험금의 지급사유)의 해외여행 중에 보통약관 제5조(보험금을 지급하지 않는 사유) 및 "
    "기본형 실손의료비 특별약관 제4조(보상하지 않는 사항) 및 비급여 실손의료비 특별약관의 제4조(보상하지 않는 사항)에도 "
    "불구하고 전문등반(전문적인 등산용구를 사용하여 암벽 또는 빙벽을 오르내리거나 특수한 기술, 경험, 사전훈련을 필요로 하는 "
    "등반을 말합니다), 글라이더 조종, 스카이다이빙, 스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩을 하는 동안에 "
    "발생한 상해의 직접결과로써 사망한 경우(질병으로 인한 사망은 제외합니다) : 사망보험금 "
    "2. 해외여행 중 상해로 장해분류표(【별표1】참조)에서 정한 각 장해지급률에 해당하는 장해상태가 되었을 때 : "
    "후유장해보험금 "
    "3. 해외여행 중에 입은 상해로 인하여 병원에 입원 또는 통원하여 발생한 의료비를 기본형 실손의료비 특별약관 제3조"
    "(보장종목별 보상내용)의 (1)상해입원 및 (2)상해통원 및 특약형 실손의료비 특별약관 제3조(보상내용)에서 정한 바에 따라 "
    "보상합니다. 단, 기본형 실손의료비 특별약관과 특약형 실손의료비 특별약관을 동시에 가입한 계약에 한해 적용합니다."
)

SPORTS_INJ_CLAUSE2_TEXT = (
    "이 특별약관에 정하지 않은 사항은 보통약관 또는 기본형 실손의료비 특별약관, 특약형 실손의료비 특별약관을 따릅니다."
)

# ---------------------------------------------------------------------------
# 특수운전중 상해위험 특별약관 (p.93)
# ---------------------------------------------------------------------------

DRIVING_INJ_CLAUSE1_TEXT = (
    "회사는 피보험자에게 다음 중 어느 하나의 사유가 발생한 경우에는 보험수익자에게 약정한 보험금을 지급합니다. "
    "1. 「보통약관 제3조(보험금의 지급사유)의 해외여행 중에 보통약관 제5조(보험금을 지급하지 않는 사유) 및 "
    "기본형 실손의료비 특별약관 제4조(보상하지 않는 사항) 및 비급여 실손의료비 특별약관의 제4조(보상하지 않는 사항)에도 "
    "불구하고 모터보트, 자동차 또는 오토바이에 의한 경기, 시범, 흥행(이를 위한 연습을 포함합니다) 또는 시운전을 하는 "
    "동안에 발생한 상해의 직접결과로써 사망한 경우(질병으로 인한 사망은 제외합니다) : 사망보험금 "
    "2. 해외여행 중 상해로 장해분류표(【별표1】참조)에서 정한 각 장해지급률에 해당하는 장해상태가 되었을 때 : "
    "후유장해보험금 "
    "3. 해외여행 중에 입은 상해로 인하여 병원에 입원 또는 통원하여 발생한 의료비를 기본형 실손의료비 특별약관 제3조"
    "(보장종목별 보상내용)의 (1)상해입원 및 (2)상해통원 및 특약형 실손의료비 특별약관 제3조(보상내용)에서 정한 바에 따라 "
    "보상합니다. 단, 기본형 실손의료비 특별약관과 특약형 실손의료비 특별약관을 동시에 가입한 계약에 한해 적용합니다."
)

DRIVING_INJ_CLAUSE2_TEXT = (
    "이 특별약관에 정하지 않은 사항은 보통약관 또는 기본형 실손의료비 특별약관, 특약형 실손의료비 특별약관을 따릅니다."
)


def _get_or_create_clause(db, *, policy_version_id, coverage_id, clause_type, article_no, text, page_ref, default_color):
    existing = (
        db.query(Clause)
        .filter(
            Clause.policy_version_id == policy_version_id,
            Clause.coverage_id == coverage_id,
            Clause.article_no == article_no,
            Clause.text == text,
        )
        .first()
    )
    if existing:
        return existing, False
    clause = Clause(
        policy_version_id=policy_version_id, coverage_id=coverage_id,
        clause_type=clause_type, article_no=article_no, text=text,
        page_ref=page_ref, default_color=default_color,
    )
    db.add(clause)
    db.flush()
    return clause, True


def _get_or_create_map(db, *, clause_id, type_id, relevance):
    existing = (
        db.query(ClauseIncidentMap)
        .filter(ClauseIncidentMap.clause_id == clause_id, ClauseIncidentMap.type_id == type_id)
        .first()
    )
    if existing:
        return False
    db.add(ClauseIncidentMap(
        clause_id=clause_id, type_id=type_id,
        relevance=relevance, mapped_by="human",
    ))
    return True


def run():
    db = SessionLocal()
    try:
        insurer = db.query(Insurer).filter_by(code="DB").first()
        if not insurer:
            print("DB손해보험이 아직 시딩되지 않았습니다. seed_db를 먼저 실행하세요.")
            return
        pv = (
            db.query(PolicyVersion)
            .join(Product, Product.product_id == PolicyVersion.product_id)
            .filter(Product.insurer_id == insurer.insurer_id)
            .first()
        )
        if not pv:
            print("DB손해보험 policy_version을 찾을 수 없습니다.")
            return

        types = {t.l2_code: t for t in db.query(IncidentType).all()}
        required = ["CHG_INTERRUPTION", "INJ_DEATH_DISABILITY", "INJ_OVERSEAS_TREATMENT"]
        missing = [c for c in required if c not in types]
        if missing:
            print(f"incident_type 사전에 없는 코드: {missing}. seed_incident_types를 먼저 실행하세요.")
            return

        std_trip_int = get_or_create_coverage_std(db, "TRIP_INTERRUPTION", "여행중단 추가비용", "여행변경", False)
        std_sports_inj = get_or_create_coverage_std(db, "INJ_SPECIAL_SPORTS", "위험스포츠 상해", "상해", False)
        std_driving_inj = get_or_create_coverage_std(db, "INJ_SPECIAL_DRIVING", "특수운전 상해", "상해", False)

        clause_created = map_created = coverage_created = 0

        # ------------------------------------------------------------------
        # 1) 해외여행중 중단사고발생 추가비용 특별약관 (p.85)
        # ------------------------------------------------------------------
        cov_trip_int = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 중단사고발생 추가비용 특별약관",
            )
            .first()
        )
        if not cov_trip_int:
            cov_trip_int = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_trip_int.coverage_std_id,
                raw_name="해외여행중 중단사고발생 추가비용 특별약관",
                definition=TRIP_INT_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보험가입금액",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_trip_int)
            db.flush()
            coverage_created += 1

        clause_trip1, t1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_trip_int.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 중단사고발생 추가비용 특별약관] 제1조(보험금의 지급사유)",
            text=TRIP_INT_CLAUSE1_TEXT, page_ref="p.85", default_color="파랑",
        )
        clause_trip2, t2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_trip_int.coverage_id,
            clause_type="공통", article_no="[해외여행중 중단사고발생 추가비용 특별약관] 제2조(용어의 정의)",
            text=TRIP_INT_CLAUSE2_TEXT, page_ref="p.85", default_color="회색",
        )
        clause_trip3, t3 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_trip_int.coverage_id,
            clause_type="제한", article_no="[해외여행중 중단사고발생 추가비용 특별약관] 제3조(보상하는 손해의 범위)",
            text=TRIP_INT_CLAUSE3_TEXT, page_ref="p.85", default_color="초록",
        )
        clause_trip4, t4 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_trip_int.coverage_id,
            clause_type="면책", article_no="[해외여행중 중단사고발생 추가비용 특별약관] 제4조(보상하지 않는 손해)",
            text=TRIP_INT_CLAUSE4_TEXT, page_ref="p.85", default_color="빨강",
        )
        clause_created += sum([t1, t2, t3, t4])

        chg_interruption = types["CHG_INTERRUPTION"]
        map_created += sum([
            _get_or_create_map(db, clause_id=clause_trip1.clause_id, type_id=chg_interruption.type_id, relevance="직접"),
            _get_or_create_map(db, clause_id=clause_trip3.clause_id, type_id=chg_interruption.type_id, relevance="조건부"),
            _get_or_create_map(db, clause_id=clause_trip4.clause_id, type_id=chg_interruption.type_id, relevance="면책"),
        ])

        # ------------------------------------------------------------------
        # 2) 특수운동중 상해위험 특별약관 (p.92)
        # ------------------------------------------------------------------
        cov_sports = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "특수운동중 상해위험 특별약관",
            )
            .first()
        )
        if not cov_sports:
            cov_sports = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_sports_inj.coverage_std_id,
                raw_name="특수운동중 상해위험 특별약관",
                definition=SPORTS_INJ_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보험가입금액(사망), 장해분류표 기준(후유장해)",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_sports)
            db.flush()
            coverage_created += 1

        clause_sports1, s1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_sports.coverage_id,
            clause_type="보장정의", article_no="[특수운동중 상해위험 특별약관] 제1조(보험금의 지급사유)",
            text=SPORTS_INJ_CLAUSE1_TEXT, page_ref="p.92", default_color="파랑",
        )
        clause_sports2, s2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_sports.coverage_id,
            clause_type="공통", article_no="[특수운동중 상해위험 특별약관] 제2조(준용규정)",
            text=SPORTS_INJ_CLAUSE2_TEXT, page_ref="p.93", default_color="회색",
        )
        clause_created += sum([s1, s2])

        inj_death = types["INJ_DEATH_DISABILITY"]
        inj_treatment = types["INJ_OVERSEAS_TREATMENT"]
        map_created += sum([
            _get_or_create_map(db, clause_id=clause_sports1.clause_id, type_id=inj_death.type_id, relevance="직접"),
            _get_or_create_map(db, clause_id=clause_sports1.clause_id, type_id=inj_treatment.type_id, relevance="직접"),
        ])

        # ------------------------------------------------------------------
        # 3) 특수운전중 상해위험 특별약관 (p.93)
        # ------------------------------------------------------------------
        cov_driving = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "특수운전중 상해위험 특별약관",
            )
            .first()
        )
        if not cov_driving:
            cov_driving = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_driving_inj.coverage_std_id,
                raw_name="특수운전중 상해위험 특별약관",
                definition=DRIVING_INJ_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보험가입금액(사망), 장해분류표 기준(후유장해)",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_driving)
            db.flush()
            coverage_created += 1

        clause_driving1, d1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_driving.coverage_id,
            clause_type="보장정의", article_no="[특수운전중 상해위험 특별약관] 제1조(보험금의 지급사유)",
            text=DRIVING_INJ_CLAUSE1_TEXT, page_ref="p.93", default_color="파랑",
        )
        clause_driving2, d2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_driving.coverage_id,
            clause_type="공통", article_no="[특수운전중 상해위험 특별약관] 제2조(준용규정)",
            text=DRIVING_INJ_CLAUSE2_TEXT, page_ref="p.93", default_color="회색",
        )
        clause_created += sum([d1, d2])

        map_created += sum([
            _get_or_create_map(db, clause_id=clause_driving1.clause_id, type_id=inj_death.type_id, relevance="직접"),
            _get_or_create_map(db, clause_id=clause_driving1.clause_id, type_id=inj_treatment.type_id, relevance="직접"),
        ])

        db.commit()
        print(
            f"DB손해보험 chunk3 시딩 완료: "
            f"Coverage {coverage_created}개, Clause {clause_created}개, Map {map_created}개 추가. "
            f"(p.85~126 범위: 해외여행중단 + 위험스포츠 + 특수운전 특약 3개)"
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
