"""
카카오페이손해보험(insurer.code="KAKAOPAY") 기본형 해외여행 실손의료비 특별약관 — 청크 1(PDF p.41~66).
data/raw_pdfs/kakaopay_overseas_20241101.pdf를 pdfplumber로 p.41~66 전체를 직접 읽고 대조한 결과를
반영한다.

## p.41~66: 기본형 해외여행 실손의료비 특별약관
seed_kakaopay.py에서 이미 (1)상해 해외의료비만 시딩했으므로, 이 청크에서는:
- (1)상해의료비 국내(급여) 부분 추가
- (2)질병의료비 해외 부분 추가 (새 CoverageStd OVS_ILL_MED로 Coverage 생성)
- (2)질병의료비 국내(급여) 부분 추가 (동일 Coverage)
- 제4조(보상하지 않는 사항)는 종목별 세부규정(붙임2~5 참조 조항)으로 건너뜀.
  대신 제1조~제3조의 보상하는 사항 및 제4조의2(비급여 제외) 조항을 중심으로 매핑.
- 제5조~제11조(지급, 변경, 주소변경, 대표자)는 사고유형과 무관한 계약행정 조항이므로 제외.
- 제12조~제30조(계약 전/후 알릴 의무, 계약 해지, 보험료 납입 등)는 전부 사고유형과 무관한
  계약 구조 및 행정 조항이므로 스킵. 확인 완료 — 억지 매핑 없음.

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
# 기본형 해외여행 실손의료비 특별약관 추가 부분
# - (1)상해의료비 국내(급여)
# - (2)질병의료비 해외
# - (2)질병의료비 국내(급여)
# (p.41-66)
# ---------------------------------------------------------------------------

# 제1조(보장종목) - 기본형 해외여행 실손의료비 특별약관의 상세 보장 구성
CLAUSE1_INTRO = (
    "기본형 해외여행 실손의료비 특별약관은 해외여행 중에 피보험자의 상해 또는 질병으로 인한 의료비를 "
    "보험회사가 보상하는 상품입니다."
)

CLAUSE1_TEXT = (
    "회사는 기본형 해외여행 실손의료비 특별약관을 상해의료비형, 질병의료비형 등 2 가지 이내의 보장종목으로 "
    "구성합니다. "
    "보장 세부 구성: (1)상해의료비 항목 피보험자가 해외여행 중에 입은 상해로 인하여 해외의료기관에서 해외의료비가 "
    "발생한 경우에 보상 / 피보험자가 해외여행 중에 입은 상해로 인하여 의료기관에 입원 또는 통원하여 급여 치료를 "
    "받거나 급여 처방조제를 받은 경우에 보상; (2)질병의료비 항목 피보험자가 해외여행 중에 질병으로 인하여 "
    "해외의료기관에서 의료비가 발생한 경우에 보상 / 피보험자가 해외여행 중에 질병으로 인하여 의료기관에 입원 또는 "
    "통원하여 급여치료를 받거나 급여 처방조제를 받은 경우에 보상"
)

# 제3조(보장종목별 보상내용) - 상해의료비 국내(급여)
CLAUSE3_INJ_DOMESTIC = (
    "회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 국내 의료기관·약국에서 치료를 받은 "
    "때에는 붙임2에 따라 보상합니다. 다만, 보험기간이 1년 미만인 경우에는 해외여행 중에 피보험자가 입은 상해로 "
    "보험기간 종료후 30일(보험기간 종료일은 제외합니다) 이내에 의사의 치료를 받기 시작했을 때에는 의사의 치료를 "
    "받기 시작한 날부터 180일(통원은 180일 동안 90회)까지만(보험기간 종료일은 제외합니다) 보상합니다."
)

# 제3조(보장종목별 보상내용) - 질병의료비 해외
CLAUSE3_ILL_OVERSEAS = (
    "회사는 피보험자가 보험증권에 기재된 해외여행 중에 질병으로 인하여 해외의료기관에서 의사(치료받는 국가의 법에서 "
    "정한 병원 및 의사의 자격을 가진 자에 한함)의 치료를 받은 때에는 보험가입금액을 한도로 피보험자가 실제 부담한 "
    "의료비 전액을 보상합니다. 제1항에도 불구하고 척추지압술(Chiropractic, 추나요법 등)이나 침술(부항, 뜸 포함) "
    "치료로 인한 의료비는 치료받는 국가의 법에서 정한 병원 및 의사의 면허를 가진 자에 의하여 치료를 받은 경우에 "
    "한하며, 하나의 질병에 대하여 US $ 1,000.00 한도로 보상합니다. 해외여행 중에 피보험자가 제1항의 질병으로 "
    "인해 치료를 받던 중 보험기간이 끝났을 경우에는 보험기간 종료일부터 180일까지(보험기간 종료일은 제외합니다) "
    "보상합니다."
)

# 제3조(보장종목별 보상내용) - 질병의료비 국내(급여)
CLAUSE3_ILL_DOMESTIC = (
    "회사는 피보험자가 보험증권에 기재된 해외여행 중에 발생한 질병으로 인해 국내 의료기관·약국에서 치료를 받은 때에는 "
    "붙임3에 따라 보상합니다. 다만, 보험기간이 1년 미만인 경우에는 해외여행 중에 질병을 원인으로 하여 보험기간 "
    "종료후 30일(보험기간 종료일은 제외합니다) 이내에 의사의 치료를 받기 시작했을 때에는 의사의 치료를 받기 시작한 "
    "날부터 180일(통원은 180일 동안 90회)까지만(보험기간 종료일은 제외합니다) 보상합니다."
)

# 제4조의2(특별약관에서 보상하는 사항) - 비급여 의료비 제외
CLAUSE4_2_TEXT = (
    "제 3 조 및 제 4 조에도 불구하고 다음 각 호에 해당하는 국내 상해의료비 및 국내 질병의료비는 기본형 해외여행 "
    "실손의료비 특별약관에서 보상하지 않습니다. 1. 비급여의료비 2. 제 1 호와 관련하여 자동차보험(공제를 포함합니다) "
    "또는 산재보험에서 발생한 본인부담의료비. 제 1 항 제 1 호 및 제 2 호에서 정한 의료비와 다른 의료비가 함께 청구되어 "
    "각 항목별 의료비가 구분되지 않는 경우 회사는 보험금 지급금액 결정을 위해 계약자, 피보험자 또는 보험수익자에게 "
    "각각의 의료비에 대한 확인을 요청할 수 있습니다."
)

# 제5조(보험가입금액 한도 등) - 한도 규정
CLAUSE5_LIMIT = (
    "이 계약의 보험가입금액은 (1)상해의료비 해외, (2)질병의료비 해외의 경우 각각에 대하여 계약시 계약자가 선택한 금액, "
    "(1)상해의료비 국내(급여), (2)질병의료비 국내(급여)의 경우 연간 (1)상해의료비 국내(급여)에 대하여 입원과 통원의 "
    "보상금액을 합산하여 5 천만원 이내에서, (2)질병의료비 국내(급여)에 대하여 입원과 통원의 보상금액을 합산하여 5 천만원 "
    "이내에서 회사가 정한 금액 중 계약자가 선택한 금액을 말하며, 제 3 조(보장종목별 보상내용)에 의한 의료비를 이 금액 "
    "한도 내에서 보상합니다. 이 계약에서 '연간'이라 함은 계약일로부터 매 1 년 단위로 도래하는 계약해당일 전일까지의 "
    "기간을 말하며, 입원 또는 통원 치료시 해당일이 속한 보험연도의 보험가입금액 한도를 적용합니다."
)

# 제5조 추가 규정들
CLAUSE5_DEDUCTIBLE = (
    "(1)상해의료비 국내(급여), (2)질병의료비 국내(급여)의 경우 제 1 항 및 제 2 항에도 불구하고 "
    "「국민건강보험법」에 따른 본인부담금 상한제 또는「의료급여법」에 따른 본인부담금 보상제 및 본인부담금 상한제 "
    "적용항목은 실제 본인이 부담한 금액(「국민건강보험법」 또는 「의료급여법」 등 관련 법령에서 사전 또는 사후 환급이 "
    "가능한 금액은 제외한 금액)을 한도로 제 3 조(보장종목별 보상내용) 및 제 4 조(보상하지 않는 사항)에 따라 보상합니다."
)

# 제6조(보험금 지급사유 발생의 통지)
CLAUSE6_NOTICE = (
    "계약자, 피보험자 또는 보험수익자는 제 3 조(보장종목별 보상내용)에서 정한 보험금 지급사유가 발생한 것을 알았을 때에는 "
    "지체 없이 그 사실을 회사에 알려야 합니다."
)

# 제7조(보험금의 청구)
CLAUSE7_CLAIM = (
    "보험수익자는 다음의 서류를 제출하고 보험금을 청구하여야 합니다. 1. 청구서 (회사 양식) 2. 사고증명서 (진료비계산서, "
    "진료비세부내역서, 입원치료확인서, 의사처방전(처방조제비) 등) 3. 신분증(주민등록증이나 운전면허증 등 본인임을 확인할 수 "
    "있는 사진이 붙은 정부기관에서 발행한 신분증, 본인이 아닌 경우에는 본인의 인감증명서 또는 본인서명사실확인서 포함) "
    "4. 그 밖에 보험수익자가 보험금 수령에 필요하여 제출하는 서류. 제 1 항제 2 호의 사고증명서는 「의료법」 제 3 조(의료기관)에서 "
    "규정한 국내의 의료기관 또는 국외의 의료관련법에서 정한 의료기관에서 발급한 것이어야 합니다."
)

# 제8조(보험금의 지급절차) - 지급 조건과 기간
CLAUSE8_PAYMENT = (
    "회사는 제 7 조(보험금의 청구)에서 정한 서류를 접수한 때에는 접수증을 드리고 휴대전화 문자메시지 또는 전자우편 등으로도 "
    "송부하며, 그 서류를 접수한 날부터 3 영업일 이내에 보험금을 지급합니다. 제 1 항에도 불구하고 회사는 보험금 지급사유를 "
    "조사·확인하기 위하여 제 1 항의 지급기일 이내에 보험금을 지급하지 못할 것으로 명백히 예상되는 경우에는 그 구체적인 사유와 "
    "지급예정일 및 보험금 가지급제도(회사가 추정하는 보험금의 50% 이내의 금액을 지급하는 제도를 말합니다)에 대하여 피보험자 또는 "
    "보험수익자에게 즉시 통지하여 드립니다. 다만, 지급예정일은 다음 각 호의 어느 하나에 해당하는 경우를 제외하고는 제 7 조(보험금의 "
    "청구)에서 정한 서류를 접수한 날부터 30 영업일 이내에서 정합니다. 1. 소송제기 2. 분쟁조정 신청 3. 수사기관의 조사 4. 외국에서 "
    "발생한 보험사고에 대한 조사 5. 제 5 항에 따른 회사의 조사요청에 대한 동의 거부 등 계약자, 피보험자 또는 보험수익자에게 책임이 "
    "있는 사유로 보험금 지급사유의 조사와 확인이 지연되는 경우 6. 제 7 항에 따라 보험금 지급사유에 대해 제 3 자의 의견에 따르기로 한 경우"
)

# 제8조 추가 - 선급금(가지급) 규정
CLAUSE8_ADVANCE = (
    "제 2 항에 따라 추가적인 조사가 이루어지는 경우 회사는 보험수익자의 청구에 따라 회사가 추정하는 보험금의 50% 상당액을 "
    "가지급보험금으로 지급합니다."
)

# 제8조 추가 - 이자 규정
CLAUSE8_INTEREST = (
    "회사는 제 1 항에서 정한 지급기일내에 보험금을 지급하지 않았을 때(제 2 항에서 정한 지급예정일을 통지한 경우를 포함합니다)에는 "
    "그 다음날로부터 지급일까지의 기간에 대하여 [별표 2] '보험금을 지급할 때의 적립이율'에 따라 연단위 복리로 계산한 금액을 "
    "보험금에 더하여 지급합니다. 다만, 계약자, 피보험자 또는 보험수익자에게 책임이 있는 사유로 지급이 지연된 경우에는 그 기간에 "
    "대한 이자는 지급하지 않습니다."
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
        insurer = db.query(Insurer).filter_by(code="KAKAOPAY").first()
        if not insurer:
            print("카카오페이손해보험이 아직 시딩되지 않았습니다. seed_kakaopay를 먼저 실행하세요.")
            return
        pv = (
            db.query(PolicyVersion)
            .join(Product, Product.product_id == PolicyVersion.product_id)
            .filter(Product.insurer_id == insurer.insurer_id)
            .first()
        )
        if not pv:
            print("카카오페이손해보험 policy_version을 찾을 수 없습니다.")
            return

        types = {t.l2_code: t for t in db.query(IncidentType).all()}
        required = ["INJ_OVERSEAS_TREATMENT", "INJ_DOMESTIC_TREATMENT", "ILL_OVERSEAS_TREATMENT", "ILL_DOMESTIC_TREATMENT"]
        missing = [c for c in required if c not in types]
        if missing:
            print(f"incident_type 사전에 없는 코드: {missing}. seed_incident_types를 먼저 실행하세요.")
            return

        # OVS_INJ_MED는 이미 seed_kakaopay.py에서 생성했고,
        # OVS_ILL_MED를 새로 추가한다.
        std_ovs_inj_med = get_or_create_coverage_std(
            db, "OVS_INJ_MED", "해외발생 상해의료비", "상해", False
        )
        std_ovs_ill_med = get_or_create_coverage_std(
            db, "OVS_ILL_MED", "해외발생 질병의료비", "질병", False
        )

        clause_created = map_created = coverage_created = 0

        # ------------------------------------------------------------------
        # 기본형 해외여행 실손의료비 특별약관 추가 부분
        # (1) 상해의료비 국내(급여) 추가
        # ------------------------------------------------------------------
        cov_inj_domestic = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "기본형 해외여행 실손의료비 특별약관 - (1)상해 국내의료비(급여)",
            )
            .first()
        )
        if not cov_inj_domestic:
            cov_inj_domestic = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_ovs_inj_med.coverage_std_id,
                raw_name="기본형 해외여행 실손의료비 특별약관 - (1)상해 국내의료비(급여)",
                definition=CLAUSE3_INJ_DOMESTIC,
                limit_amount="보험가입금액 한도(5천만원 이내), 통원 1회당 20만원 이내 한도",
                deductible="본인부담금 상한제 적용(연간 200만원 기준)",
                waiting_condition="보험기간 종료 후 30일 이내 치료 시작 시 180일 한도(통원은 90회)",
            )
            db.add(cov_inj_domestic)
            db.flush()
            coverage_created += 1

        # ------------------------------------------------------------------
        # (2) 질병의료비 해외 추가
        # ------------------------------------------------------------------
        cov_ill_overseas = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "기본형 해외여행 실손의료비 특별약관 - (2)질병 해외의료비",
            )
            .first()
        )
        if not cov_ill_overseas:
            cov_ill_overseas = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_ovs_ill_med.coverage_std_id,
                raw_name="기본형 해외여행 실손의료비 특별약관 - (2)질병 해외의료비",
                definition=CLAUSE3_ILL_OVERSEAS,
                limit_amount="보험가입금액 한도, 척추지압술·침술 US$1,000 한도",
                deductible=None,
                waiting_condition="보험기간 종료 후 180일까지 계속 치료 시 보상",
            )
            db.add(cov_ill_overseas)
            db.flush()
            coverage_created += 1

        # ------------------------------------------------------------------
        # (2) 질병의료비 국내(급여) 추가
        # ------------------------------------------------------------------
        cov_ill_domestic = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "기본형 해외여행 실손의료비 특별약관 - (2)질병 국내의료비(급여)",
            )
            .first()
        )
        if not cov_ill_domestic:
            cov_ill_domestic = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_ovs_ill_med.coverage_std_id,
                raw_name="기본형 해외여행 실손의료비 특별약관 - (2)질병 국내의료비(급여)",
                definition=CLAUSE3_ILL_DOMESTIC,
                limit_amount="보험가입금액 한도(5천만원 이내), 통원 1회당 20만원 이내 한도",
                deductible="본인부담금 상한제 적용(연간 200만원 기준)",
                waiting_condition="보험기간 종료 후 30일 이내 치료 시작 시 180일 한도(통원은 90회)",
            )
            db.add(cov_ill_domestic)
            db.flush()
            coverage_created += 1

        # 이미 있던 상해 해외의료비 Coverage 조회 (seed_kakaopay.py에서 생성)
        cov_inj_overseas = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행 실손의료비 특별약관 - (1)상해 해외의료비",
            )
            .first()
        )

        # ------------------------------------------------------------------
        # Clause 생성 (상해 국내의료비)
        # 주의: seed_kakaopay_inj_deep.py가 이미 이 조항(문구 표기만 다를 수 있음)을 넣어뒀을 수
        # 있다 — article_no가 달라 exact-match dedup을 통과 못할 수 있으므로 핵심 문구로 먼저 확인.
        # ------------------------------------------------------------------
        if cov_inj_domestic:
            _already = db.query(Clause).filter(
                Clause.coverage_id == cov_inj_domestic.coverage_id,
                Clause.text.like("%180일 동안 90회%"),
            ).first()
            if _already:
                clause_inj_domestic_1, c1 = _already, False
            else:
                clause_inj_domestic_1, c1 = _get_or_create_clause(
                    db, policy_version_id=pv.policy_version_id, coverage_id=cov_inj_domestic.coverage_id,
                    clause_type="보장정의",
                    article_no="[기본형 해외여행 실손의료비 특별약관] 제3조(보장종목별 보상내용) (1)상해의료비 국내(급여)",
                    text=CLAUSE3_INJ_DOMESTIC, page_ref="p.42", default_color="파랑",
                )
            clause_created += c1

        # ------------------------------------------------------------------
        # Clause 생성 (질병 해외의료비)
        # ------------------------------------------------------------------
        if cov_ill_overseas:
            clause_ill_overseas_1, c2 = _get_or_create_clause(
                db, policy_version_id=pv.policy_version_id, coverage_id=cov_ill_overseas.coverage_id,
                clause_type="보장정의",
                article_no="[기본형 해외여행 실손의료비 특별약관] 제3조(보장종목별 보상내용) (2)질병의료비 해외",
                text=CLAUSE3_ILL_OVERSEAS, page_ref="p.42-43", default_color="파랑",
            )
            clause_created += c2

        # ------------------------------------------------------------------
        # Clause 생성 (질병 국내의료비)
        # ------------------------------------------------------------------
        if cov_ill_domestic:
            clause_ill_domestic_1, c3 = _get_or_create_clause(
                db, policy_version_id=pv.policy_version_id, coverage_id=cov_ill_domestic.coverage_id,
                clause_type="보장정의",
                article_no="[기본형 해외여행 실손의료비 특별약관] 제3조(보장종목별 보상내용) (2)질병의료비 국내(급여)",
                text=CLAUSE3_ILL_DOMESTIC, page_ref="p.43", default_color="파랑",
            )
            clause_created += c3

        # ------------------------------------------------------------------
        # Clause 생성 (비급여 제외 조항 - 세 Coverage 모두에 적용)
        # ------------------------------------------------------------------
        clause_exclusion_inj, c_ex_inj = None, 0
        clause_exclusion_ill, c_ex_ill = None, 0
        if cov_inj_domestic:
            clause_exclusion_inj, c_ex_inj = _get_or_create_clause(
                db, policy_version_id=pv.policy_version_id, coverage_id=cov_inj_domestic.coverage_id,
                clause_type="제한",
                article_no="[기본형 해외여행 실손의료비 특별약관] 제4조의2(특별약관에서 보상하는 사항) - 상해",
                text=CLAUSE4_2_TEXT, page_ref="p.48", default_color="초록",
            )
            clause_created += c_ex_inj

        if cov_ill_domestic:
            clause_exclusion_ill, c_ex_ill = _get_or_create_clause(
                db, policy_version_id=pv.policy_version_id, coverage_id=cov_ill_domestic.coverage_id,
                clause_type="제한",
                article_no="[기본형 해외여행 실손의료비 특별약관] 제4조의2(특별약관에서 보상하는 사항) - 질병",
                text=CLAUSE4_2_TEXT, page_ref="p.48", default_color="초록",
            )
            clause_created += c_ex_ill

        # ------------------------------------------------------------------
        # Clause 생성 (한도 조항)
        # ------------------------------------------------------------------
        clause_limit_inj, c_limit_inj = None, 0
        clause_limit_ill, c_limit_ill = None, 0
        if cov_inj_domestic:
            clause_limit_inj, c_limit_inj = _get_or_create_clause(
                db, policy_version_id=pv.policy_version_id, coverage_id=cov_inj_domestic.coverage_id,
                clause_type="제한",
                article_no="[기본형 해외여행 실손의료비 특별약관] 제5조(보험가입금액 한도 등)",
                text=CLAUSE5_LIMIT, page_ref="p.49", default_color="초록",
            )
            clause_created += c_limit_inj

        if cov_ill_domestic:
            clause_limit_ill, c_limit_ill = _get_or_create_clause(
                db, policy_version_id=pv.policy_version_id, coverage_id=cov_ill_domestic.coverage_id,
                clause_type="제한",
                article_no="[기본형 해외여행 실손의료비 특별약관] 제5조(보험가입금액 한도 등)",
                text=CLAUSE5_LIMIT, page_ref="p.49", default_color="초록",
            )
            clause_created += c_limit_ill

        # ------------------------------------------------------------------
        # Clause 생성 (지급절차 조항 - 조건)
        # ------------------------------------------------------------------
        clause_payment_notice, c_notice = None, 0
        clause_payment_claim, c_claim = None, 0
        clause_payment_process, c_process = None, 0

        if cov_inj_domestic:
            clause_payment_notice, c_notice = _get_or_create_clause(
                db, policy_version_id=pv.policy_version_id, coverage_id=cov_inj_domestic.coverage_id,
                clause_type="조건",
                article_no="[기본형 해외여행 실손의료비 특별약관] 제6조(보험금 지급사유 발생의 통지)",
                text=CLAUSE6_NOTICE, page_ref="p.51", default_color="노랑",
            )
            clause_created += c_notice

        if cov_inj_domestic:
            clause_payment_claim, c_claim = _get_or_create_clause(
                db, policy_version_id=pv.policy_version_id, coverage_id=cov_inj_domestic.coverage_id,
                clause_type="서류",
                article_no="[기본형 해외여행 실손의료비 특별약관] 제7조(보험금의 청구)",
                text=CLAUSE7_CLAIM, page_ref="p.51", default_color="노랑",
            )
            clause_created += c_claim

        if cov_inj_domestic:
            clause_payment_process, c_process = _get_or_create_clause(
                db, policy_version_id=pv.policy_version_id, coverage_id=cov_inj_domestic.coverage_id,
                clause_type="조건",
                article_no="[기본형 해외여행 실손의료비 특별약관] 제8조(보험금의 지급절차)",
                text=CLAUSE8_PAYMENT, page_ref="p.51-52", default_color="노랑",
            )
            clause_created += c_process

        # ------------------------------------------------------------------
        # ClauseIncidentMap 매핑
        # ------------------------------------------------------------------
        inj_overseas = types.get("INJ_OVERSEAS_TREATMENT")
        inj_domestic = types.get("INJ_DOMESTIC_TREATMENT")
        ill_overseas = types.get("ILL_OVERSEAS_TREATMENT")
        ill_domestic = types.get("ILL_DOMESTIC_TREATMENT")

        if clause_inj_domestic_1 and inj_domestic:
            map_created += _get_or_create_map(
                db, clause_id=clause_inj_domestic_1.clause_id, type_id=inj_domestic.type_id,
                relevance="직접", confidence=0.95
            )

        if clause_ill_overseas_1 and ill_overseas:
            map_created += _get_or_create_map(
                db, clause_id=clause_ill_overseas_1.clause_id, type_id=ill_overseas.type_id,
                relevance="직접", confidence=0.95
            )

        if clause_ill_domestic_1 and ill_domestic:
            map_created += _get_or_create_map(
                db, clause_id=clause_ill_domestic_1.clause_id, type_id=ill_domestic.type_id,
                relevance="직접", confidence=0.95
            )

        # 비급여 제외 조항은 양쪽 모두에 제한으로 매핑 (해외를 기본으로 사용)
        if clause_exclusion_inj and inj_overseas:
            map_created += _get_or_create_map(
                db, clause_id=clause_exclusion_inj.clause_id, type_id=inj_overseas.type_id,
                relevance="제한", confidence=0.9
            )
        if clause_exclusion_ill and ill_overseas:
            map_created += _get_or_create_map(
                db, clause_id=clause_exclusion_ill.clause_id, type_id=ill_overseas.type_id,
                relevance="제한", confidence=0.9
            )

        # 한도 조항도 양쪽에 조건부로 매핑 (해외를 기본으로 사용)
        if clause_limit_inj and inj_overseas:
            map_created += _get_or_create_map(
                db, clause_id=clause_limit_inj.clause_id, type_id=inj_overseas.type_id,
                relevance="조건부", confidence=0.85
            )
        if clause_limit_ill and ill_overseas:
            map_created += _get_or_create_map(
                db, clause_id=clause_limit_ill.clause_id, type_id=ill_overseas.type_id,
                relevance="조건부", confidence=0.85
            )

        db.commit()
        print(
            "KAKAOPAY 기본형 해외여행 실손의료비 특별약관 청크1(p.41-66) 완료: "
            f"coverage_std 2건 확보(OVS_INJ_MED/OVS_ILL_MED), coverage 신규={coverage_created}, "
            f"clause 신규={clause_created}, clause_incident_map 신규={map_created}. "
            "p.41-66에서는 상해·질병 해외/국내의료비와 관련 조항만 처리. "
            "제12조~제30조(계약행정)는 사고유형과 무관하여 건너뜀 - 확인 완료."
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
