"""
KB손해보험(insurer.code="KB") 전체 청크 1 — p.54~57 특약 분류.
data/raw_pdfs/kb_overseas_15332_202004.pdf (총 169쪽)의 p.54~57 범위를
pdfplumber로 직접 읽고 대조한 결과를 반영한다.

## p.54~55 (해외여행중 질병사망 및 80%이상후유장해 특별약관)
제1조(보험금의 지급사유)·제2조(보험금 지급에 관한 세부규정) — 질병사망 및 80%이상
후유장해 보장. 제3조(준용규정)는 순수 참조조항이라 ClauseIncidentMap에 매핑하지 않는다.
CoverageStd: ILL_DEATH로 매핑.

## p.56~57 (해외여행중 배상책임 특별약관)
제1조(보상하는 손해) — 신체의 장해 및 재물의 손해에 대한 배상책임 보상 범위 정의.
제2조(보상하지 않는 손해) — 면책사유(천재지변, 전쟁, 직무수행, 친족, 항공기 등).
제3조(손해의 통지 및 조사) — 손해통지 의무 및 조사권.
제4조(보험금의 청구) — 청구서류 요건.
제5조(보험금의 지급절차) — 보험금 지급한도 및 지급이율.
CoverageStd: LIABILITY로 매핑. 대인/대물/임차물(호텔객실) 배상책임 모두 포함하므로
LIA_PERSONAL·LIA_PROPERTY·LIA_LODGING 모두에 직접 또는 면책으로 매핑.

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
# 해외여행중 질병사망 및 80%이상후유장해 특별약관 (p.54-55)
# ---------------------------------------------------------------------------

ILL_DEATH_CLAUSE1_TEXT = (
    "① 회사는 피보험자에게 보통약관 제3조(보험금의 지급사유)의 여행 도중에 다음 사항 중 어느 "
    "한 가지의 경우에 해당되는 사유가 발생한 때에는 보험수익자에게 약정한 보험가입금액 전액을 "
    "지급합니다. "
    "1. 보험기간 중에 질병으로 인하여 사망한 경우 : 사망보험금 "
    "2. 보험기간 중 진단확정된 질병으로 장해분류표([별표1]참조. 이하 같습니다)에서 정한 장해지급률이 "
    "80%이상에 해당하는 장해상태가 되었을 때 : 후유장해보험금 "
    "② 제1항에도 불구하고 여행 도중에 발생한 질병을 직접원인으로 하여 보험기간 마지막날로부터 30일 "
    "이내에 사망하거나 또는 80% 이상에 해당하는 장해상태가 되었을 때에도 동일하게 보상하여 드립니다."
)

ILL_DEATH_CLAUSE2_TEXT = (
    "① [호스피스·완화의료 및 임종과정에 있는 환자의 연명의료 결정에 관한 법률]에 따른 연명의료중단등결정 "
    "및 그 이행으로 피보험자가 사망하는 경우 연명의료중단등결정 및 그 이행은 제1조(보험금의 지급사유) "
    "제1항 제1호 '사망'의 원인 및 '사망보험금' 지급에 영향을 미치지 않습니다. "
    "② 제1조(보험금의 지급사유) 제1항 제2호에서 장해지급률이 질병의 진단 확정일부터 180일 이내에 "
    "확정되지 않는 경우에는 질병의 진단확정일부터 180일이 되는 날의 의사 진단에 기초하여 고정될 것으로 "
    "인정되는 상태를 장해지급률로 결정합니다. 다만, 장해분류표([별표1] 참조)에 장해판정시기를 별도로 "
    "정한 경우에는 그에 따릅니다. "
    "③ 제2항에 따라 장해지급률이 결정되었으나 그 이후 보장받을 수 있는 기간(계약의 효력이 없어진 경우에는 "
    "질병의 진단확정일부터 1년 이내)에 장해상태가 더 악화된 때에는 그 악화된 장해상태를 기준으로 "
    "장해지급률을 결정합니다. "
    "④ 장해분류표에 해당되지 않는 후유장해는 피보험자의 직업, 연령, 신분 또는 성별 등에 관계없이 신체의 "
    "장해정도에 따라 장해분류표의 구분에 준하여 지급액을 결정합니다. 다만, 장해분류표의 각 장해분류별 "
    "최저 지급률 장해정도에 이르지 않는 후유장해에 대하여는 후유장해보험금을 지급하지 않습니다. "
    "⑤ 보험수익자와 회사가 제1조(보험금의 지급사유)의 보험금 지급사유에 대해 합의하지 못할 때는 보험수익자와 "
    "회사가 함께 제3자를 정하고 그 제3자의 의견에 따를 수 있습니다. 제3자는 의료법 제3조(의료기관)에 규정한 "
    "종합병원 소속 전문의 중에 정하며, 보험금 지급사유 판정에 드는 의료비용은 회사가 전액 부담합니다. "
    "⑥ 같은 질병으로 두 가지 이상의 후유장해가 생긴 경우에는 후유장해 지급률을 합산하여 지급합니다. "
    "다만, 장해분류표의 각 신체부위별 판정기준에 별도로 정한 경우에는 그 기준에 따릅니다. "
    "⑦ 다른 질병로 인하여 후유장해가 2회 이상 발생하였을 경우에는 그 때마다 이에 해당하는 후유장해지급률을 "
    "결정합니다. 그러나 그 후유장해가 이미 후유장해보험금을 지급받은 동일한 부위에 가중된 때에는 최종 "
    "장해상태에 해당하는 후유장해보험금에서 이미 지급받은 후유장해보험금을 차감하여 지급합니다. "
    "다만, 장해분류표의 각 신체부위별 판정기준에서 별도로 정한 경우에는 그 기준에 따릅니다. "
    "⑧ 이미 이 특별약관에서 후유장해보험금 지급사유에 해당되지 않았거나(보장개시 이전의 원인에 의하거나 "
    "또는 그 이전에 발생한 후유장해를 포함합니다), 후유장해보험금이 지급되지 않았던 피보험자에게 그 신체의 "
    "동일 부위에 또다시 제7항에 규정하는 후유장해상태가 발생하였을 경우에는 직전까지의 후유장해에 대한 "
    "후유장해보험금이 지급된 것으로 보고 최종 후유장해 상태에 해당되는 후유장해보험금에서 이를 차감하여 지급합니다."
)

ILL_DEATH_CLAUSE3_TEXT = "이 특별약관에 정하지 않은 사항은 보통약관을 따릅니다."


# ---------------------------------------------------------------------------
# 해외여행중 배상책임 특별약관 (p.56-57 이상)
# ---------------------------------------------------------------------------

LIA_CLAUSE1_TEXT = (
    "회사는 피보험자가 보통약관 제3조(보험금의 지급사유)의 여행 도중에 생긴 우연한 사고(이하 "
    "[사고]라 합니다)로 피해자의 신체의 장해 또는 재물의 손해에 대한 법률상의 배상책임을 부담함으로써 "
    "입은 아래의 손해를 이 특별약관에 따라 보상하여 드립니다. "
    "1. 피보험자가 피해자에게 지급할 책임을 지는 법률상의 손해배상금 "
    "2. 계약자 또는 피보험자가 지출한 아래의 비용 "
    "가. 피보험자가 제9조(손해방지의무) 제1항 제1호의 손해의 방지 또는 경감을 위하여 지출한 필요 또는 "
    "유익하였던 비용. "
    "나. 피보험자가 제9조(손해방지의무) 제1항 제2호의 제3자로부터 손해의 배상을 받을 수 있는 그 권리를 "
    "지키거나 행사하기 위하여 지출한 필요 또는 유익하였던 비용 "
    "다. 피보험자가 지급한 소송비용, 변호사보수, 중재, 화해 또는 조정에 관한 비용 "
    "라. 보험증권상의 보상한도액내의 금액에 대한 공탁보증보험료. 그러나 회사는 그러한 보증을 제공할 책임은 "
    "부담하지 않습니다. "
    "마. 피보험자가 제10조(손해배상청구에 대한 회사의 해결) 제2항 및 제3항의 회사의 요구에 따르기 위하여 "
    "지출한 비용"
)

LIA_CLAUSE2_TEXT = (
    "① 회사는 아래의 사유로 생긴 손해는 보상하여 드리지 않습니다. "
    "1. 계약자나 피보험자의 고의 "
    "2. 지진, 분화, 해일 또는 이와 비슷한 천재지변 "
    "3. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동, 소요, 기타 이들과 유사한 사태 "
    "4. 핵연료 물질(사용이 끝난 연료를 포함합니다. 이하 같습니다) 또는 핵연료 물질에 의하여 오염된 물질"
    "(원자핵분열 생성물을 포함합니다)의 방사성, 폭발성 또는 그 밖의 유해한 특성에 의한 사고 "
    "5. 제4호 이외의 방사선을 쬐는 것 또는 방사능 오염 "
    "② 회사는 아래의 손해배상책임을 부담하게 됨으로써 입은 손해는 보상하여 드리지 않습니다. "
    "1. 피보험자의 직무수행을 직접적인 원인으로 하는 배상책임 "
    "2. 피보험자의 직무용으로만 사용되는 동산의 소유, 사용 또는 관리로 인한 배상책임 "
    "3. 피보험자가 소유, 사용 또는 관리하는 부동산으로 인한 배상책임 "
    "4. 피보험자의 근로자가 피보험자의 업무에 종사 중에 입은 신체의 장해로 인한 배상책임. "
    "단, 피보험자의 가사사용인에 대하여는 이와 같지 않습니다. "
    "5. 피보험자와 타인간에 손해배상에 관한 약정이 있는 경우, 그 약정에 의하여 가중된 배상책임 "
    "6. 피보험자와 세대를 같이하는 친족(민법 제777조규정의 범위와 같습니다) 및 여행과정을 같이 하는 "
    "친족에 대한 배상책임 "
    "7. 피보험자가 소유, 사용 또는 관리하는 재물이 손해를 입었을 경우에 그 재물에 대하여 정당한 권리를 "
    "가진 사람에게 부담하는 손해에 대한 배상책임. 단, 호텔의 객실이나 객실내의 동산에 끼치는 손해에 "
    "대하여는 이와 같지 않습니다. "
    "8. 피보험자의 심신상실로 인한 배상책임 "
    "9. 피보험자 또는 피보험자의 지시에 따른 폭행 또는 구타로 인한 배상책임 "
    "10. 항공기, 선박, 차량(원동력이 인력에 의한 것을 제외합니다), 총기(공기총은 제외합니다) "
    "의 소유, 사용 또는 관리로 인한 배상책임"
)

LIA_CLAUSE3_TEXT = (
    "① 계약자 또는 피보험자는 아래와 같은 사실이 있는 경우에는 지체없이 그 내용을 회사에 알려야 합니다. "
    "1. 사고가 발생하였을 경우 사고가 발생한 때와 곳, 피해자의 주소와 성명, 사고상황 및 이들 사항의 증인이 "
    "있을 경우 그 주소와 성명 "
    "2. 피해자로부터 손해배상청구를 받았을 경우 "
    "3. 피해자로부터 손해배상책임에 관한 소송을 제기 받았을 경우 "
    "② 계약자 또는 피보험자가 제1항 각호의 통지를 게을리하여 손해가 증가된 때에는 회사는 그 증가된 손해를 "
    "보상하여 드리지 않으며, 제1항 제3호의 통지를 게을리 한 때에는 소송비용과 변호사비용도 보상하여 드리지 "
    "않습니다. 다만, 계약자 또는 피보험자가 상법 제657조 제1항에 의해 보험사고의 발생을 회사에 알린 경우에는 "
    "제1조(보상하는 손해) 제1호 및 제2호 '다'목 또는 '라'목의 비용에 대하여 보상한도액을 한도로 보상하여 "
    "드립니다."
)

LIA_CLAUSE4_DOC_TEXT = (
    "① 피보험자가 보험금을 청구할 때에는 다음의 서류를 회사에 제출하여야 합니다. "
    "1. 보험금 청구서 "
    "2. 신분증(주민등록증 또는 운전면허증 등 사진이 부착된 정부기관발행 신분증, 본인이 아닌 경우에는 "
    "본인의 인감증명서 또는 본인서명사실확인서 포함) "
    "3. 손해배상금 및 그 밖의 비용을 지급하였음을 증명하는 서류 "
    "4. 회사가 요구하는 그 밖의 서류"
)

LIA_CLAUSE5_TEXT = (
    "① 회사는 제4조(보험금의 청구)에서 정한 서류를 접수한 때에는 접수증을 교부하고, 그 서류를 접수받은 후 "
    "지체없이 지급할 보험금을 결정하고 지급할 보험금이 결정되면 7일 이내에 이를 지급하여 드립니다. "
    "또한, 지급할 보험금이 결정되기 전이라도 피보험자의 청구가 있을 때에는 회사가 추정한 보험금의 50% "
    "상당액을 가지급보험금으로 지급합니다. "
    "② 회사는 제1항의 지급보험금이 결정된 후 7일(이하 '지급기일'이라 합니다)이 지나도록 보험금을 지급하지 "
    "않았을 때에는 지급기일의 다음날부터 지급일까지의 기간에 대하여 [부표] '보험금을 지급할 때의 적립이율'에 "
    "따라 연단위 복리로 계산한 금액을 보험금에 더하여 지급합니다. 그러나 피보험자의 책임있는 사유로 지체된 "
    "경우에는 그 해당기간에 대한 이자를 더하여 지급하지 않습니다."
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
        insurer = db.query(Insurer).filter_by(code="KB").first()
        if not insurer:
            print("KB손해보험이 아직 시딩되지 않았습니다. seed_kb를 먼저 실행하세요.")
            return
        pv = (
            db.query(PolicyVersion)
            .join(Product, Product.product_id == PolicyVersion.product_id)
            .filter(Product.insurer_id == insurer.insurer_id)
            .first()
        )
        if not pv:
            print("KB policy_version을 찾을 수 없습니다.")
            return

        types = {t.l2_code: t for t in db.query(IncidentType).all()}
        required = ["ILL_DEATH_DISABILITY", "LIA_PERSONAL", "LIA_PROPERTY", "LIA_LODGING"]
        missing = [c for c in required if c not in types]
        if missing:
            print(f"incident_type 사전에 없는 코드: {missing}. seed_incident_types를 먼저 실행하세요.")
            return

        std_ill_death = get_or_create_coverage_std(db, "ILL_DEATH", "해외여행중 질병사망 및 80%이상후유장해", "질병", False)
        std_liability = get_or_create_coverage_std(db, "LIABILITY", "해외여행중 배상책임", "배상책임", False)

        clause_created = map_created = coverage_created = 0

        # ------------------------------------------------------------------
        # 1) 해외여행중 질병사망 및 80%이상후유장해 특별약관 (p.54-55)
        # ------------------------------------------------------------------
        cov_ill = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 질병사망 및 80%이상후유장해 특별약관",
            )
            .first()
        )
        if not cov_ill:
            cov_ill = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_ill_death.coverage_std_id,
                raw_name="해외여행중 질병사망 및 80%이상후유장해 특별약관",
                definition=ILL_DEATH_CLAUSE1_TEXT,
                limit_amount="장해분류표([별표1]) 기준 80%이상 후유장해시 지급",
                deductible=None,
                waiting_condition="질병 진단확정일부터 180일 이내 미확정시 180일 시점 의사진단 기준 적용(제2조②)",
            )
            db.add(cov_ill)
            db.flush()
            coverage_created += 1

        clause_ill_1, c1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_ill.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 질병사망 및 80%이상후유장해 특별약관] 제1조(보험금의 지급사유)",
            text=ILL_DEATH_CLAUSE1_TEXT, page_ref="p.54", default_color="파랑",
        )
        clause_ill_2, c2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_ill.coverage_id,
            clause_type="제한", article_no="[해외여행중 질병사망 및 80%이상후유장해 특별약관] 제2조(보험금 지급에 관한 세부규정)",
            text=ILL_DEATH_CLAUSE2_TEXT, page_ref="p.54-55", default_color="초록",
        )
        clause_ill_3, c3 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_ill.coverage_id,
            clause_type="공통", article_no="[해외여행중 질병사망 및 80%이상후유장해 특별약관] 제3조(준용규정)",
            text=ILL_DEATH_CLAUSE3_TEXT, page_ref="p.55", default_color="회색",
        )
        clause_created += sum([c1, c2, c3])

        ill_death_type = types["ILL_DEATH_DISABILITY"]
        map_created += sum([
            _get_or_create_map(db, clause_id=clause_ill_1.clause_id, type_id=ill_death_type.type_id, relevance="직접", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_ill_2.clause_id, type_id=ill_death_type.type_id, relevance="제한", confidence=0.9),
        ])

        # ------------------------------------------------------------------
        # 2) 해외여행중 배상책임 특별약관 (p.56-57 이상)
        # ------------------------------------------------------------------
        cov_lia = (
            db.query(Coverage)
            .filter(
                Coverage.policy_version_id == pv.policy_version_id,
                Coverage.raw_name == "해외여행중 배상책임 특별약관",
            )
            .first()
        )
        if not cov_lia:
            cov_lia = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=std_liability.coverage_std_id,
                raw_name="해외여행중 배상책임 특별약관",
                definition=LIA_CLAUSE1_TEXT,
                limit_amount="보험증권 기재 보상한도액(1회 사고당) 및 총 보상한도액",
                deductible=None,
                waiting_condition=None,
            )
            db.add(cov_lia)
            db.flush()
            coverage_created += 1

        clause_lia_1, l1 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_lia.coverage_id,
            clause_type="보장정의", article_no="[해외여행중 배상책임 특별약관] 제1조(보상하는 손해)",
            text=LIA_CLAUSE1_TEXT, page_ref="p.56", default_color="파랑",
        )
        clause_lia_2, l2 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_lia.coverage_id,
            clause_type="면책", article_no="[해외여행중 배상책임 특별약관] 제2조(보상하지 않는 손해)",
            text=LIA_CLAUSE2_TEXT, page_ref="p.56-57", default_color="빨강",
        )
        clause_lia_3, l3 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_lia.coverage_id,
            clause_type="조건", article_no="[해외여행중 배상책임 특별약관] 제3조(손해의 통지 및 조사)",
            text=LIA_CLAUSE3_TEXT, page_ref="p.57", default_color="노랑",
        )
        clause_lia_4, l4 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_lia.coverage_id,
            clause_type="서류", article_no="[해외여행중 배상책임 특별약관] 제4조(보험금의 청구)",
            text=LIA_CLAUSE4_DOC_TEXT, page_ref="p.57", default_color="노랑",
        )
        clause_lia_5, l5 = _get_or_create_clause(
            db, policy_version_id=pv.policy_version_id, coverage_id=cov_lia.coverage_id,
            clause_type="제한", article_no="[해외여행중 배상책임 특별약관] 제5조(보험금의 지급절차)",
            text=LIA_CLAUSE5_TEXT, page_ref="p.57", default_color="초록",
        )
        clause_created += sum([l1, l2, l3, l4, l5])

        lia_personal = types["LIA_PERSONAL"]
        lia_property = types["LIA_PROPERTY"]
        lia_lodging = types["LIA_LODGING"]

        map_created += sum([
            # 제1조(보상하는 손해): 신체의 장해(대인) 및 재물의 손해(대물) 직접 매핑
            _get_or_create_map(db, clause_id=clause_lia_1.clause_id, type_id=lia_personal.type_id, relevance="직접", confidence=0.9),
            _get_or_create_map(db, clause_id=clause_lia_1.clause_id, type_id=lia_property.type_id, relevance="직접", confidence=0.9),
            # 제2조(보상하지 않는 손해): 전반적으로 면책사유. 다만 제7호의 호텔 객실 예외는 LIA_LODGING의 보장 근거
            _get_or_create_map(db, clause_id=clause_lia_2.clause_id, type_id=lia_personal.type_id, relevance="면책", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_lia_2.clause_id, type_id=lia_property.type_id, relevance="면책", confidence=1.0),
            _get_or_create_map(db, clause_id=clause_lia_2.clause_id, type_id=lia_lodging.type_id, relevance="직접", confidence=0.85),
            # 제3조(손해통지 조건)
            _get_or_create_map(db, clause_id=clause_lia_3.clause_id, type_id=lia_personal.type_id, relevance="조건부", confidence=0.8),
            _get_or_create_map(db, clause_id=clause_lia_3.clause_id, type_id=lia_property.type_id, relevance="조건부", confidence=0.8),
            # 제5조(지급절차 및 한도)
            _get_or_create_map(db, clause_id=clause_lia_5.clause_id, type_id=lia_personal.type_id, relevance="제한", confidence=0.9),
            _get_or_create_map(db, clause_id=clause_lia_5.clause_id, type_id=lia_property.type_id, relevance="제한", confidence=0.9),
            _get_or_create_map(db, clause_id=clause_lia_5.clause_id, type_id=lia_lodging.type_id, relevance="제한", confidence=0.8),
        ])

        db.commit()
        print(
            "KB 전체 재검토 청크1(p.54-57) 완료: "
            f"coverage_std 2건 확보(ILL_DEATH/LIABILITY), coverage 신규={coverage_created}, "
            f"clause 신규={clause_created}, clause_incident_map 신규={map_created}."
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
