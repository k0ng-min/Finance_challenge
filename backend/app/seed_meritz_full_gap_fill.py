"""
메리츠화재(insurer.code="MERITZ") 해외여행보험 — 청크2 빠진 구간 보충

메리츠 해외여행보험 PDF p.75-147 중, 청크2 담당 에이전트가 건너뛴 2개 구간을 채운다.

## 보충 내용:

p.79-84: 운동 및 기타위험 확장보상 추가특별약관(Ⅰ, Ⅱ)
        — 기존 상해의료비/상해사망·후유장해에서 면책되는 특수 활동(전문등반/스카이다이빙/
          자동차경기 등)을 "확장 보상"하는 특약 6개(상해비급여/3대비급여/상해급여 × 전문등반/자동차경기)
        CoverageStd: INJ_SPECIAL_SPORTS (p.79, 83), INJ_SPECIAL_DRIVING (p.81, 84)
        + 비급여/3대비급여 버전도 동일 매핑
        IncidentType: INJ_SPECIAL_SPORTS, INJ_SPECIAL_DRIVING

p.96-107: 해외여행중 상해고도후유장해 특별약관(50%/80%/100%)
         — 기존 상해사망·후유장해의 변형 특약으로, 특정 장해지급률 이상인 경우에만 보장
        CoverageStd: DEATH_INJURY (기존 재사용) + 새 코드로도 가능
        IncidentType: INJ_DEATH_DISABILITY

멱등성: Coverage는 raw_name, Clause는 (coverage_id, article_no, text) 조합,
        ClauseIncidentMap은 (clause_id, type_id) 조합으로 이미 있으면 건너뛴다.
"""
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Clause, ClauseIncidentMap, Coverage, CoverageStd, IncidentType, Insurer, PolicyVersion, Product,
)
from app.services.kb_seed_common import get_or_create_coverage_std


# =========================================================================
# p.79-84: 운동 및 기타위험 확장보상 추가특별약관
# =========================================================================

SPORTS_CLAUSE_I_P79_TEXT = (
    "회사는 해외여행 실손의료보험 특별약관 제4조(보상하지 않는 사항) (1)상해비급여 제2항 "
    "제1호에도 불구하고 피보험자에게 다음 사항 중 어느 한 가지의 경우에 해당되는 사유가 "
    "발생한 때에는 보험수익자에게 약정한 보험금을 지급합니다. "
    "1. 직업, 직무 또는 동호회 활동목적으로 전문등반(전문적인 등산용구를 사용하여 암벽 또는 "
    "빙벽을 오르내리거나 특수한 기술, 경험, 사전 훈련이 필요한 등반을 말합니다), 글라이더 조종, "
    "스카이다이빙, 스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩을 하는 동안에 상해를 입고, "
    "이로 인해 해외여행 실손의료보험 특별약관 제3조(보장종목별 보상내용) (1)상해비급여에서 정한 "
    "바에 따라 치료를 받은 경우"
)

SPORTS_CLAUSE_I_P80_TEXT = (
    "회사는 해외여행 실손의료보험 특별약관의 제4조(보상하지 않는 사항) (3)3대비급여 제2항 "
    "제1호에도 불구하고 피보험자에게 다음 사항 중 어느 한 가지의 경우에 해당되는 사유가 "
    "발생한 때에는 보험수익자에게 약정한 보험금을 지급합니다. "
    "1. 직업, 직무 또는 동호회 활동목적으로 전문등반(전문적인 등산용구를 사용하여 암벽 또는 "
    "빙벽을 오르내리거나 특수한 기술, 경험, 사전 훈련이 필요한 등반을 말합니다), 글라이더 조종, "
    "스카이다이빙, 스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩을 하는 동안에 상해를 입고, "
    "이로 인해 해외여행 실손의료보험 특별약관의 제3조(보장종목별 보상내용) (3)3대비급여에서 정한 "
    "바에 따라 치료를 받은 경우"
)

SPORTS_CLAUSE_II_P81_TEXT = (
    "회사는 해외여행 실손의료보험 특별약관 제4조(보상하지 않는 사항)의 제2항 제2호에도 불구하고 "
    "피보험자에게 다음 사항 중 어느 한 가지의 경우에 해당되는 사유가 발생한 때에는 보험수익자에게 "
    "약정한 보험금을 지급합니다. "
    "1. 직업, 직무 또는 동호회 활동목적으로 모터보트, 자동차 또는 오토바이에 의한 경기, 시범, 행사"
    "(이를 위한 연습을 포함합니다) 또는 시운전(다만, 공용도로에서 시운전을 하는 동안 발생한 상해는 "
    "보상하여 드립니다)을 하는 동안에 상해를 입고, 해외여행 실손의료보험 특별약관의 제3조(보장종목별 "
    "보상내용) (1)상해비급여에서 정한 바에 따라 치료를 받은 경우"
)

SPORTS_CLAUSE_II_P82_TEXT = (
    "회사는 해외여행 실손의료보험 특별약관의 제4조(보상하지 않는 사항) (3)3대비급여 제2항 제2호에도 "
    "불구하고 피보험자에게 다음 사항 중 어느 한 가지의 경우에 해당되는 사유가 발생한 때에는 보험수익자에게 "
    "약정한 보험금을 지급합니다. "
    "1. 직업, 직무 또는 동호회 활동목적으로 모터보트, 자동차 또는 오토바이에 의한 경기, 시범, 행사"
    "(이를 위한 연습을 포함합니다) 또는 시운전(다만, 공용도로에서 시운전을 하는 동안 발생한 상해는 "
    "보상하여 드립니다)을 하는 동안에 상해를 입고, 해외여행 실손의료보험 특별약관의 제3조(보장종목별 "
    "보상내용) (3)3대비급여에서 정한 바에 따라 치료를 받은 경우"
)

SPORTS_CLAUSE_I_P83_TEXT = (
    "회사는 보통약관 제4조(보상하지 않는 사항) (1)상해의료비(국내(급여)) 붙임4 '국내 의료기관 의료비 중 "
    "보상하지 않는 상해의료비'의 (1)상해급여 제2항 제1호에도 불구하고 피보험자에게 다음 사항 중 어느 한 "
    "가지의 경우에 해당되는 사유가 발생한 때에는 보험수익자에게 약정한 보험금을 지급합니다. "
    "1. 직업, 직무 또는 동호회 활동목적으로 전문등반(전문적인 등산용구를 사용하여 암벽 또는 빙벽을 오르내리거나 "
    "특수한 기술, 경험, 사전 훈련이 필요한 등반을 말합니다), 글라이더 조종, 스카이다이빙, 스쿠버다이빙, "
    "행글라이딩, 수상보트, 패러글라이딩을 하는 동안에 상해를 입고, 이로 인해 보통약관 제3조(보장종목별 보상내용) "
    "(1)상해의료비 국내(급여)에서 정한 바에 따라 치료를 받은 경우"
)

SPORTS_CLAUSE_II_P84_TEXT = (
    "회사는 보통약관 제4조(보상하지 않는 사항) (1)상해의료비(국내(급여)) 붙임4 '국내 의료기관 의료비 중 "
    "보상하지 않는 상해의료비'의 (1)상해급여 제2항 제2호에도 불구하고 피보험자에게 다음 사항 중 어느 한 가지의 "
    "경우에 해당되는 사유가 발생한 때에는 보험수익자에게 약정한 보험금을 지급합니다. "
    "1. 직업, 직무 또는 동호회 활동목적으로 모터보트·자동차 또는 오토바이에 의한 경기, 시범, 행사(이를 위한 "
    "연습을 포함합니다) 또는 시운전(다만, 공용도로에서 시운전을 하는 동안 발생한 상해는 보상하여 드립니다)을 하는 "
    "동안에 상해를 입고, 이로 인해 보통약관 제3조(보장종목별 보상내용) (1)상해의료비 국내(급여)에서 정한 바에 따라 "
    "치료를 받은 경우"
)


# =========================================================================
# p.96-107: 해외여행중 상해고도후유장해 특별약관(50%/80%/100%)
# =========================================================================

INJURY_50_CLAUSE1_TEXT = (
    "회사는 피보험자가 해외여행 중에 상해를 입고 그 상해로 장해분류표(【별표1】참조. 이하 같습니다.)에서 "
    "정한 장해지급률이 50%이상 고도의 장해상태가 되었을 경우에는 이 특별약관의 보험가입금액 전액을 피보험자에게 "
    "지급합니다."
)

INJURY_50_CLAUSE2_TEXT = (
    "① 제1조(보험금의 지급사유)에서 장해지급률이 상해 발생일부터 180일 이내에 확정되지 않는 경우에는 상해 "
    "발생일부터 180일이 되는 날의 의사 진단에 기초하여 고정될 것으로 인정되는 상태를 장해지급률로 결정합니다. "
    "다만, 장해분류표(【별표1】참조)에 장해판정시기를 별도로 정한 경우에는 그에 따릅니다."
)

INJURY_80_CLAUSE1_TEXT = (
    "회사는 피보험자가 해외여행 중에 상해를 입고 그 상해로 장해분류표(【별표1】참조. 이하 같습니다.)에서 "
    "정한 장해지급률이 80%이상 고도의 장해상태가 되었을 경우에는 이 특별약관의 보험가입금액 전액을 피보험자에게 "
    "지급합니다."
)

INJURY_80_CLAUSE2_TEXT = (
    "① 제1조(보험금의 지급사유)에서 장해지급률이 상해 발생일부터 180일 이내에 확정되지 않는 경우에는 상해 "
    "발생일부터 180일이 되는 날의 의사 진단에 기초하여 고정될 것으로 인정되는 상태를 장해지급률로 결정합니다. "
    "다만, 장해분류표(【별표1】참조)에 장해판정시기를 별도로 정한 경우에는 그에 따릅니다."
)

INJURY_100_CLAUSE1_TEXT = (
    "회사는 피보험자가 해외여행 중에 상해를 입고 그 상해로 장해분류표(【별표1】참조. 이하 같습니다.)에서 "
    "정한 장해지급률이 100%이상 고도의 장해상태가 되었을 경우에는 이 특별약관의 보험가입금액 전액을 피보험자에게 "
    "지급합니다."
)

INJURY_100_CLAUSE2_TEXT = (
    "① 제1조(보험금의 지급사유)에서 장해지급률이 상해 발생일부터 180일 이내에 확정되지 않는 경우에는 상해 "
    "발생일부터 180일이 되는 날의 의사 진단에 기초하여 고정될 것으로 인정되는 상태를 장해지급률로 결정합니다. "
    "다만, 장해분류표(【별표1】참조)에 장해판정시기를 별도로 정한 경우에는 그에 따릅니다."
)

INJURY_EXCLUSION_CLAUSE_TEXT = (
    "회사는 다음 중 어느 한가지로 보험금 지급사유가 발생한 때에는 보험금을 지급하지 않습니다. "
    "1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 의사결정을 할 수 없는 "
    "상태에서 자신을 해친 경우에는 보험금을 지급합니다. "
    "2. 계약자가 고의로 피보험자를 해친 경우 "
    "3. 피보험자의 임신, 출산(제왕절개를 포함합니다), 산후기. 그러나, 회사가 보장하는 보험금 지급사유로 인한 "
    "경우에는 보험금을 지급합니다. "
    "4. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동"
)

INJURY_EXCLUSION_SPORTS_TEXT = (
    "회사는 다른 약정이 없으면 피보험자가 직업, 직무 또는 동호회 활동목적으로 아래에 열거된 행위로 인하여 "
    "제1조(보험금의 지급사유)의 상해 관련 보험금 지급사유가 발생한 때에는 해당 보험금을 지급하지 않습니다. "
    "1. 전문등반(전문적인 등산용구를 사용하여 암벽 또는 빙벽을 오르내리거나 특수한 기술, 경험, 사전훈련을 "
    "필요로 하는 등반을 말합니다), 글라이더 조종, 스카이다이빙, 스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩 "
    "2. 모터보트, 자동차 또는 오토바이에 의한 경기, 시범, 흥행(이를 위한 연습을 포함합니다) 또는 시운전"
    "(다만, 공용도로상에서 시운전을 하는 동안 보험금 지급사유가 발생한 경우에는 보장합니다) "
    "3. 선박에 탑승하는 것을 직무로 하는 사람이 직무상 선박에 탑승하고 있는 동안"
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


def _get_or_create_map(db, *, clause_id, type_id, relevance, confidence):
    existing = (
        db.query(ClauseIncidentMap)
        .filter(ClauseIncidentMap.clause_id == clause_id, ClauseIncidentMap.type_id == type_id)
        .first()
    )
    if existing:
        return False
    db.add(ClauseIncidentMap(
        clause_id=clause_id, type_id=type_id,
        relevance=relevance, mapped_by="human", confidence=confidence,
    ))
    return True


def run():
    db = SessionLocal()
    try:
        insurer = db.query(Insurer).filter_by(code="MERITZ").first()
        if not insurer:
            print("메리츠화재가 시딩되지 않았습니다. seed_meritz를 먼저 실행하세요.")
            return

        pv = (
            db.query(PolicyVersion)
            .join(Product, Product.product_id == PolicyVersion.product_id)
            .filter(Product.insurer_id == insurer.insurer_id)
            .first()
        )
        if not pv:
            print("메리츠화재 policy_version을 찾을 수 없습니다.")
            return

        types = {t.l2_code: t for t in db.query(IncidentType).all()}
        required_types = [
            "INJ_DEATH_DISABILITY"  # 상해 관련 IncidentType은 이것만 필요
        ]
        missing = [c for c in required_types if c not in types]
        if missing:
            print(f"incident_type 사전에 없는 코드: {missing}")
            return

        # CoverageStd 조회 또는 생성
        std_sports = get_or_create_coverage_std(db, "INJ_SPECIAL_SPORTS", "특수운동중 상해", "상해", False)
        std_driving = get_or_create_coverage_std(db, "INJ_SPECIAL_DRIVING", "특수운전중 상해", "상해", False)
        std_injury_50 = get_or_create_coverage_std(db, "INJ_DISABILITY_50PLUS", "상해50%이상고도후유장해", "상해", False)
        std_injury_80 = get_or_create_coverage_std(db, "INJ_DISABILITY_80PLUS", "상해80%이상고도후유장해", "상해", False)
        std_injury_100 = get_or_create_coverage_std(db, "INJ_DISABILITY_100", "상해100%고도후유장해", "상해", False)

        clause_created = map_created = coverage_created = 0

        # ===================================================================
        # 1) p.79: 운동 및 기타위험 확장보상 추가특별약관(Ⅰ) - 상해비급여
        # ===================================================================
        cov_sports_i_noncover = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "운동 및 기타위험 확장보상(전문등반 등) 추가특별약관(Ⅰ) - 상해비급여",
            )
            .first()
        )
        if not cov_sports_i_noncover:
            cov_sports_i_noncover = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_sports.coverage_std_id,
                raw_name="운동 및 기타위험 확장보상(전문등반 등) 추가특별약관(Ⅰ) - 상해비급여",
                definition=SPORTS_CLAUSE_I_P79_TEXT,
                limit_amount="보험증권 기재 보상한도액",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_sports_i_noncover)
            db.flush()
            coverage_created += 1

        clause_sports_i_nc, c1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_sports_i_noncover.coverage_id,
            clause_type="보장정의", article_no="[운동위험확장 Ⅰ-비급여] 제1조(지급사유)",
            text=SPORTS_CLAUSE_I_P79_TEXT, page_ref="p.79", default_color="파랑",
        )
        clause_created += c1

        # 운동 확장보상은 특정 활동 시 상해 보장이므로 INJ_DEATH_DISABILITY의 조건부 매핑
        inj_type = types["INJ_DEATH_DISABILITY"]
        map_created += _get_or_create_map(db, clause_id=clause_sports_i_nc.clause_id, type_id=inj_type.type_id, relevance="조건부", confidence=0.9)

        # ===================================================================
        # 2) p.80: 운동 및 기타위험 확장보상 추가특별약관(Ⅰ) - 3대비급여
        # ===================================================================
        cov_sports_i_3noncover = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "운동 및 기타위험 확장보상(전문등반 등) 추가특별약관(Ⅰ) - 3대비급여",
            )
            .first()
        )
        if not cov_sports_i_3noncover:
            cov_sports_i_3noncover = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_sports.coverage_std_id,
                raw_name="운동 및 기타위험 확장보상(전문등반 등) 추가특별약관(Ⅰ) - 3대비급여",
                definition=SPORTS_CLAUSE_I_P80_TEXT,
                limit_amount="보험증권 기재 보상한도액",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_sports_i_3noncover)
            db.flush()
            coverage_created += 1

        clause_sports_i_3nc, c2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_sports_i_3noncover.coverage_id,
            clause_type="보장정의", article_no="[운동위험확장 Ⅰ-3대비급여] 제1조(지급사유)",
            text=SPORTS_CLAUSE_I_P80_TEXT, page_ref="p.80", default_color="파랑",
        )
        clause_created += c2

        map_created += _get_or_create_map(db, clause_id=clause_sports_i_3nc.clause_id, type_id=inj_type.type_id, relevance="조건부", confidence=0.9)

        # ===================================================================
        # 3) p.81: 운동 및 기타위험 확장보상 추가특별약관(Ⅱ) - 상해비급여
        # ===================================================================
        cov_sports_ii_noncover = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "운동 및 기타위험 확장보상(자동차경기 등) 추가특별약관(Ⅱ) - 상해비급여",
            )
            .first()
        )
        if not cov_sports_ii_noncover:
            cov_sports_ii_noncover = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_driving.coverage_std_id,
                raw_name="운동 및 기타위험 확장보상(자동차경기 등) 추가특별약관(Ⅱ) - 상해비급여",
                definition=SPORTS_CLAUSE_II_P81_TEXT,
                limit_amount="보험증권 기재 보상한도액",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_sports_ii_noncover)
            db.flush()
            coverage_created += 1

        clause_sports_ii_nc, c3 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_sports_ii_noncover.coverage_id,
            clause_type="보장정의", article_no="[운동위험확장 Ⅱ-비급여] 제1조(지급사유)",
            text=SPORTS_CLAUSE_II_P81_TEXT, page_ref="p.81", default_color="파랑",
        )
        clause_created += c3

        map_created += _get_or_create_map(db, clause_id=clause_sports_ii_nc.clause_id, type_id=inj_type.type_id, relevance="조건부", confidence=0.9)

        # ===================================================================
        # 4) p.82: 운동 및 기타위험 확장보상 추가특별약관(Ⅱ) - 3대비급여
        # ===================================================================
        cov_sports_ii_3noncover = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "운동 및 기타위험 확장보상(자동차경기 등) 추가특별약관(Ⅱ) - 3대비급여",
            )
            .first()
        )
        if not cov_sports_ii_3noncover:
            cov_sports_ii_3noncover = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_driving.coverage_std_id,
                raw_name="운동 및 기타위험 확장보상(자동차경기 등) 추가특별약관(Ⅱ) - 3대비급여",
                definition=SPORTS_CLAUSE_II_P82_TEXT,
                limit_amount="보험증권 기재 보상한도액",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_sports_ii_3noncover)
            db.flush()
            coverage_created += 1

        clause_sports_ii_3nc, c4 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_sports_ii_3noncover.coverage_id,
            clause_type="보장정의", article_no="[운동위험확장 Ⅱ-3대비급여] 제1조(지급사유)",
            text=SPORTS_CLAUSE_II_P82_TEXT, page_ref="p.82", default_color="파랑",
        )
        clause_created += c4

        map_created += _get_or_create_map(db, clause_id=clause_sports_ii_3nc.clause_id, type_id=inj_type.type_id, relevance="조건부", confidence=0.9)

        # ===================================================================
        # 5) p.83: 운동 및 기타위험 확장보상 특별약관(Ⅰ) - 상해급여
        # ===================================================================
        cov_sports_i_cover = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "운동 및 기타위험 확장보상(전문등반 등) 특별약관(Ⅰ) - 상해급여",
            )
            .first()
        )
        if not cov_sports_i_cover:
            cov_sports_i_cover = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_sports.coverage_std_id,
                raw_name="운동 및 기타위험 확장보상(전문등반 등) 특별약관(Ⅰ) - 상해급여",
                definition=SPORTS_CLAUSE_I_P83_TEXT,
                limit_amount="보험증권 기재 보상한도액",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_sports_i_cover)
            db.flush()
            coverage_created += 1

        clause_sports_i_c, c5 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_sports_i_cover.coverage_id,
            clause_type="보장정의", article_no="[운동위험확장 Ⅰ-급여] 제1조(지급사유)",
            text=SPORTS_CLAUSE_I_P83_TEXT, page_ref="p.83", default_color="파랑",
        )
        clause_created += c5

        map_created += _get_or_create_map(db, clause_id=clause_sports_i_c.clause_id, type_id=inj_type.type_id, relevance="조건부", confidence=0.9)

        # ===================================================================
        # 6) p.84: 운동 및 기타위험 확장보상 특별약관(Ⅱ) - 상해급여
        # ===================================================================
        cov_sports_ii_cover = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "운동 및 기타위험 확장보상(자동차경기 등) 특별약관(Ⅱ) - 상해급여",
            )
            .first()
        )
        if not cov_sports_ii_cover:
            cov_sports_ii_cover = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_driving.coverage_std_id,
                raw_name="운동 및 기타위험 확장보상(자동차경기 등) 특별약관(Ⅱ) - 상해급여",
                definition=SPORTS_CLAUSE_II_P84_TEXT,
                limit_amount="보험증권 기재 보상한도액",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_sports_ii_cover)
            db.flush()
            coverage_created += 1

        clause_sports_ii_c, c6 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_sports_ii_cover.coverage_id,
            clause_type="보장정의", article_no="[운동위험확장 Ⅱ-급여] 제1조(지급사유)",
            text=SPORTS_CLAUSE_II_P84_TEXT, page_ref="p.84", default_color="파랑",
        )
        clause_created += c6

        map_created += _get_or_create_map(db, clause_id=clause_sports_ii_c.clause_id, type_id=inj_type.type_id, relevance="조건부", confidence=0.9)

        # ===================================================================
        # 7) p.96: 해외여행중 상해50%이상고도후유장해 특별약관
        # ===================================================================
        cov_injury_50 = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 상해50%이상고도후유장해 특별약관",
            )
            .first()
        )
        if not cov_injury_50:
            cov_injury_50 = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_injury_50.coverage_std_id,
                raw_name="해외여행중 상해50%이상고도후유장해 특별약관",
                definition=INJURY_50_CLAUSE1_TEXT,
                limit_amount="보험가입금액 전액",
                deductible=None,
                waiting_condition="장해지급률 50% 이상",
            )
            db.add(cov_injury_50)
            db.flush()
            coverage_created += 1

        clause_inj50_1, i501 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_injury_50.coverage_id,
            clause_type="보장정의", article_no="[상해50%이상후유장해 특별약관] 제1조(지급사유)",
            text=INJURY_50_CLAUSE1_TEXT, page_ref="p.96", default_color="파랑",
        )
        clause_inj50_2, i502 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_injury_50.coverage_id,
            clause_type="제한", article_no="[상해50%이상후유장해 특별약관] 제2조(세부규정)",
            text=INJURY_50_CLAUSE2_TEXT, page_ref="p.96", default_color="초록",
        )
        clause_inj50_3, i503 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_injury_50.coverage_id,
            clause_type="면책", article_no="[상해50%이상후유장해 특별약관] 제3조(면책사유)",
            text=INJURY_EXCLUSION_CLAUSE_TEXT, page_ref="p.97", default_color="빨강",
        )
        clause_inj50_4, i504 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_injury_50.coverage_id,
            clause_type="면책", article_no="[상해50%이상후유장해 특별약관] 제3조(특수활동 면책)",
            text=INJURY_EXCLUSION_SPORTS_TEXT, page_ref="p.97", default_color="빨강",
        )
        clause_created += sum([i501, i502, i503, i504])

        map_created += sum([
            _get_or_create_map(db, clause_id=clause_inj50_1.clause_id, type_id=inj_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_inj50_2.clause_id, type_id=inj_type.type_id, relevance="조건부", confidence=0.95),
            _get_or_create_map(db, clause_id=clause_inj50_3.clause_id, type_id=inj_type.type_id, relevance="면책", confidence=0.9),
            _get_or_create_map(db, clause_id=clause_inj50_4.clause_id, type_id=inj_type.type_id, relevance="면책", confidence=0.95),
        ])

        # ===================================================================
        # 8) p.100: 해외여행중 상해80%이상고도후유장해 특별약관
        # ===================================================================
        cov_injury_80 = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 상해80%이상고도후유장해 특별약관",
            )
            .first()
        )
        if not cov_injury_80:
            cov_injury_80 = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_injury_80.coverage_std_id,
                raw_name="해외여행중 상해80%이상고도후유장해 특별약관",
                definition=INJURY_80_CLAUSE1_TEXT,
                limit_amount="보험가입금액 전액",
                deductible=None,
                waiting_condition="장해지급률 80% 이상",
            )
            db.add(cov_injury_80)
            db.flush()
            coverage_created += 1

        clause_inj80_1, i801 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_injury_80.coverage_id,
            clause_type="보장정의", article_no="[상해80%이상후유장해 특별약관] 제1조(지급사유)",
            text=INJURY_80_CLAUSE1_TEXT, page_ref="p.100", default_color="파랑",
        )
        clause_inj80_2, i802 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_injury_80.coverage_id,
            clause_type="제한", article_no="[상해80%이상후유장해 특별약관] 제2조(세부규정)",
            text=INJURY_80_CLAUSE2_TEXT, page_ref="p.100", default_color="초록",
        )
        clause_inj80_3, i803 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_injury_80.coverage_id,
            clause_type="면책", article_no="[상해80%이상후유장해 특별약관] 제3조(면책사유)",
            text=INJURY_EXCLUSION_CLAUSE_TEXT, page_ref="p.101", default_color="빨강",
        )
        clause_inj80_4, i804 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_injury_80.coverage_id,
            clause_type="면책", article_no="[상해80%이상후유장해 특별약관] 제3조(특수활동 면책)",
            text=INJURY_EXCLUSION_SPORTS_TEXT, page_ref="p.101", default_color="빨강",
        )
        clause_created += sum([i801, i802, i803, i804])

        map_created += sum([
            _get_or_create_map(db, clause_id=clause_inj80_1.clause_id, type_id=inj_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_inj80_2.clause_id, type_id=inj_type.type_id, relevance="조건부", confidence=0.95),
            _get_or_create_map(db, clause_id=clause_inj80_3.clause_id, type_id=inj_type.type_id, relevance="면책", confidence=0.9),
            _get_or_create_map(db, clause_id=clause_inj80_4.clause_id, type_id=inj_type.type_id, relevance="면책", confidence=0.95),
        ])

        # ===================================================================
        # 9) p.104: 해외여행중 상해100%고도후유장해 특별약관
        # ===================================================================
        cov_injury_100 = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 상해100%고도후유장해 특별약관",
            )
            .first()
        )
        if not cov_injury_100:
            cov_injury_100 = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_injury_100.coverage_std_id,
                raw_name="해외여행중 상해100%고도후유장해 특별약관",
                definition=INJURY_100_CLAUSE1_TEXT,
                limit_amount="보험가입금액 전액",
                deductible=None,
                waiting_condition="장해지급률 100% 이상",
            )
            db.add(cov_injury_100)
            db.flush()
            coverage_created += 1

        clause_inj100_1, i1001 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_injury_100.coverage_id,
            clause_type="보장정의", article_no="[상해100%후유장해 특별약관] 제1조(지급사유)",
            text=INJURY_100_CLAUSE1_TEXT, page_ref="p.104", default_color="파랑",
        )
        clause_inj100_2, i1002 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_injury_100.coverage_id,
            clause_type="제한", article_no="[상해100%후유장해 특별약관] 제2조(세부규정)",
            text=INJURY_100_CLAUSE2_TEXT, page_ref="p.104", default_color="초록",
        )
        clause_inj100_3, i1003 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_injury_100.coverage_id,
            clause_type="면책", article_no="[상해100%후유장해 특별약관] 제3조(면책사유)",
            text=INJURY_EXCLUSION_CLAUSE_TEXT, page_ref="p.104", default_color="빨강",
        )
        clause_inj100_4, i1004 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_injury_100.coverage_id,
            clause_type="면책", article_no="[상해100%후유장해 특별약관] 제3조(특수활동 면책)",
            text=INJURY_EXCLUSION_SPORTS_TEXT, page_ref="p.105", default_color="빨강",
        )
        clause_created += sum([i1001, i1002, i1003, i1004])

        map_created += sum([
            _get_or_create_map(db, clause_id=clause_inj100_1.clause_id, type_id=inj_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_inj100_2.clause_id, type_id=inj_type.type_id, relevance="조건부", confidence=0.95),
            _get_or_create_map(db, clause_id=clause_inj100_3.clause_id, type_id=inj_type.type_id, relevance="면책", confidence=0.9),
            _get_or_create_map(db, clause_id=clause_inj100_4.clause_id, type_id=inj_type.type_id, relevance="면책", confidence=0.95),
        ])

        db.commit()
        print(f"메리츠 청크2 빠진 구간 보충 완료: Coverage {coverage_created}개, Clause {clause_created}개, ClauseIncidentMap {map_created}개")

    except Exception as e:
        db.rollback()
        print(f"오류 발생: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
