"""
삼성화재 PDF(data/raw_pdfs/samsung_overseas_50002_0_20240401.pdf, 총 252쪽) 전체 읽기 작업 중
p.149~174 구간(청크 E) 담당분.

pdfplumber로 해당 구간(및 인접 p.147~176)을 페이지별로 직접 추출해 전부 읽었다. 이 구간에는
아래 순서로 특별약관 16개가 있다(요청서의 "p.149 근처" 등은 근사치였고, 실제 페이지는 아래가
정확하다).

■ 사고유형과 실제로 관련 있어 Clause로 반영한 4건
1. 여행중 자택 도난손해(가재) 보장 특별약관 (p.149~152)
   제1조① "보험의 목적이 피보험자가 주민등록등본상 거주하고 있는 주택의 구내에 있는 동안
   강도 또는 절도로 인해... 손해를 보상"한다. 대상이 "피보험자가 휴대하는 휴대품"이 아니라
   "자택(주민등록등본상 거주 주택)"이다 — 실제로 기존 PROP_THEFT에 걸린 조항(coverage_id=19,
   clause_id=43)의 원문을 대조해보면 "이 보험의 목적은 피보험자가 여행 도중에 휴대하는
   피보험자 소유·사용·관리의 휴대품에 한합니다"로 명시돼 있어 대상이 명확히 다르다
   (자택 구내 vs 휴대품). 억지로 PROP_THEFT에 끼워맞추지 않고, incident_classify_gemini의
   create_reviewable_type과 같은 방식으로 PROP 산하에 needs_review=True L2를 새로 만들어
   매핑했다("사람이 나중에 재분류" 원칙).
2. 의사상자 상해위험 특별약관 (p.153)
   "직무외의 행위로 타인의 생명·신체·재산의 급박한 피해를 구제하다가 신체에 상해를 입어"
   법령상 의사상자로 판정되는 경우를 보상한다. 사망뿐 아니라 상해 전반을 포괄하는 개념이라
   기존 L2 중 가장 가까운 INJ_DEATH_DISABILITY에 "조건부"(의사상자 공식 판정이라는 추가
   요건이 있어야 지급)로 매핑했다. DEATH_INJURY 면책조항(제5조)이 배제하는 사유(고의자해·
   전쟁 등)와는 무관해 "면책의 예외조항" 성격은 아니고, 별도의 추가 보장(확장) 성격이다.
3. 전쟁위험 특별약관 (p.154)
   예상대로 "면책을 확장 취소"하는 특약이었다: "회사는 보통약관 제5조(보험금을 지급하지
   않는 사유) 제1항 제5호의 규정에도 불구하고 전쟁, 외국의 무력행사, 혁명, 내란, 폭동으로
   인하여... 지급사유가 발생하였을 경우에는... 보험금을... 지급합니다." 즉 이 특약에 가입하면
   전쟁 관련 상해도 보장한다 — SPC_WAR_TERROR에 relevance="직접"으로 매핑(가입 시 전쟁
   관련 사고의 지급 근거가 곧바로 이 조항이므로). 다만 제2조③에 "여행경로 변경을 알리지
   않으면 그 이후 사고는 보상하지 않는다"는 조건부 면책이 있어 이것도 별도 Clause로 넣고
   relevance="면책"으로 매핑했다.
4. 상해 사망위험 보상제외 특별약관(p.171) / 상해 후유장해위험 보상제외 특별약관(p.172)
   이름 그대로 "사망보험금을 보상하지 않습니다" / "후유장해보험금을 보상하지 않습니다"뿐인
   1줄짜리 옵션 특약이다. 새 CoverageStd를 만들지 않고 기존 DEATH_INJURY coverage_id(=1,
   raw_name="상해사망·후유장해 (보통약관)")에 면책 Clause 2건을 추가했다. 이 특약은 계약자가
   선택 가입해야 적용되는 "옵션성 면책"이라, 실제 청구 판단 시에는 해당 계약이 이 특약을
   실제로 부가했는지 별도 확인이 필요하다는 점을 여기 docstring에 남겨둔다(스키마에 "옵션
   여부" 필드가 없어 relevance="면책"으로만 표시).

■ 행정/계약구조 특약 11건 — 전부 pdfplumber로 원문을 펼쳐 읽었고, 전부 사고유형과 무관함을
   확인했다(Clause로 넣지 않음):
5. 부부확장 특별약관(p.155) — 피보험자 범위를 배우자까지 확장하는 정의 조항뿐. 무관.
6. 가족확장 특별약관(p.156) — 피보험자 범위를 가족(부모/자녀/형제자매/친족)까지 확장. 무관.
7. 단체계약 특별약관(p.157~159) — 단체보험 가입요건(1~3종 단체 정의), 상법 제735조의3
   적용, 단체요율, 개별계약 전환 등 계약 구조 조항. 무관.
8. 보험료정산 추가특별약관(p.160~161) — 단체 피보험자 증감에 따른 보험료 정산 절차. 무관.
9. 포괄계약 추가특별약관(p.162~163) — 여행업자·단체가 포괄적으로 가입자를 통지하는 절차,
   중복계약 확인의무 특칙. 무관.
10. 단체 포괄계약 추가특별약관(p.164) — 둘 이상 단체가 공동으로 포괄계약 체결시 요건. 무관.
11. 상품다수구매자 보험계약 특별약관(p.165~166) — 상품 구매자 100인 이상 단체가입 시
    보험료 정산 방식. 무관.
12. 지정대리청구서비스 특별약관(p.167~168) — 피보험자가 직접 청구 불가한 특별한 사정이
    있을 때 배우자/3촌 이내 친족을 대리청구인으로 지정하는 절차. 청구 "절차"이지 사고
    "유형"이 아니라서 무관으로 분류(추후 청구 프로세스 기능에서 참고할 수는 있음).
13. 단체급 특별약관(p.169~170) — 소속 단체(회사 등)를 통한 급여공제식 보험료 집금 절차.
    무관.
14. 환율 특별약관(Ⅱ)(p.173) — "보험금은 지급일의 1차고시 대고객 전신환 매도율로 환산한
    원화로 지급"— 지급 방식(환산 기준)일 뿐 사고유형과 무관.
15. 장애인전용보험전환 특별약관(p.174~175) — 소득세법상 세액공제 혜택을 위해 계약을
    장애인전용보험으로 전환하는 세제 특약. 무관.

건너뛴 부분: 자택 도난손해 특약의 제2조(보험의 목적의 범위: 가재도구·생활용품 항목 나열)와
제4~9조(청구서류·손해통지·지급보험금 계산·잔존물 등 절차 조항), 의사상자 특약 제2조(보험금액
산정 방식)는 사고유형 판단에 직접 쓰이지 않는 절차/산정 조항이라 Clause로 넣지 않고 생략했다
(핵심 보장정의·면책 조항만 반영). 전쟁위험 특약의 제2조①②(여행경로 변경 통지·해지권)와
제3조(해지의 장래효)도 계약관리 절차라 생략했다.

이 스크립트는 idempotent: Coverage/Clause/IncidentType 모두 존재 여부를 먼저 확인하고 없을
때만 추가한다. 실행은 요청받지 않았다 — 작성만 하고 run()은 호출하지 않았다.
"""
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import Clause, ClauseIncidentMap, Coverage, IncidentType, PolicyVersion, Product, Insurer
from app.services.kb_seed_common import get_or_create_coverage_std
from app.services.incident_classify_gemini import create_reviewable_type


# ---------------------------------------------------------------------------
# 1) 여행중 자택 도난손해(가재) 보장 특별약관 (p.149~152)
# ---------------------------------------------------------------------------
HOME_THEFT_DEFINITION_TEXT = (
    "① 회사는 보통약관 제3조에도 불구하고 보험기간 중 보험의 목적이 피보험자가 "
    "주민등록등본상 거주하고 있는 주택의 구내에 있는 동안 강도 또는 절도(그 미수를 "
    "포함합니다)로 인해 도난, 망가짐, 손상 및 파손된 손해(이하「도난손해」라 합니다)를 "
    "보상하여 드립니다."
)

HOME_THEFT_EXCLUSION_TEXT = (
    "회사는 아래와 같은 손해는 보상하지 않습니다. "
    "1. 보험계약자, 피보험자 또는 이들의 법정대리인의 고의 또는 중대한 과실로 생긴 "
    "도난손해 "
    "2. 보험계약자 및 피보험자의 가족, 친족, 사용인, 동거인, 숙박인, 감수인(監守人) 또는 "
    "당직자가 일으킨 행위 또는 이들이 가담하거나 묵인하에 생긴 도난 손해 "
    "3. 전쟁, 폭동, 소요 또는 이와 유사한 사변으로 생긴 도난 "
    "4. 화재나 지진, 분화, 해일, 폭발 또는 그 밖의 변재가 일어났을 때 생긴 도난 손해 "
    "5. 절도 또는 강도행위로 발생한 화재 및 폭발손해 "
    "6. 망실 또는 분실 손해 "
    "7. 사기 또는 횡령으로 인한 손해 "
    "8. 보험사고가 생긴 후 30일 이내에 알지 못한 도난 손해 "
    "9. 보험의 목적이 건물구내 밖에 있는 동안 생긴 도난 "
    "10. 외부로부터 침입흔적이 없는 도난 손해"
)

# ---------------------------------------------------------------------------
# 2) 의사상자 상해위험 특별약관 (p.153)
# ---------------------------------------------------------------------------
GOOD_SAMARITAN_TEXT = (
    "회사는 보험기간 중 보험증권에 기재된 피보험자가 직무외의 행위로 타인의 생명, 신체(의수, "
    "의족, 의안, 의치 등 신체보조장구는 제외합니다) 또는 재산의 급박한 피해를 구제하다가 신체에 "
    "상해를 입어 「의사상자 등 예우 및 지원에 관한 법률」및「동법 시행령」의 규정에 따라 "
    "의사상자로 판정되는 경우 이 특별약관에 따라 보상하여 드립니다."
)

# ---------------------------------------------------------------------------
# 3) 전쟁위험 특별약관 (p.154)
# ---------------------------------------------------------------------------
WAR_RISK_COVERAGE_TEXT = (
    "① 회사는 보통약관 제5조(보험금을 지급하지 않는 사유) 제1항 제5호의 규정에도 불구하고 "
    "전쟁, 외국의 무력행사, 혁명, 내란, 폭동으로 인하여 피보험자에게 제3조(보험금의 지급사유)에 "
    "정한 지급사유가 발생하였을 경우에는 각 호에 해당하는 보험금을 이 특별약관에 따라 "
    "보험수익자에게 지급합니다."
)

WAR_RISK_ROUTE_CHANGE_EXCLUSION_TEXT = (
    "③ 계약자 또는 피보험자가 제1항의 계약 후 알릴 의무를 이행하지 않은 경우에는 회사는 "
    "피보험자가 여행경로를 변경한 이후의 사고로 인한 상해에 대해서는 보상하여 드리지 않습니다."
)

# ---------------------------------------------------------------------------
# 4) 상해 사망위험 / 후유장해위험 보상제외 특별약관 (p.171, p.172)
# ---------------------------------------------------------------------------
DEATH_EXCLUSION_RIDER_TEXT = (
    "회사는 보통약관 제3조(보험금의 지급사유) 제1호에도 불구하고 사망보험금을 보상하지 "
    "않습니다."
)

DISABILITY_EXCLUSION_RIDER_TEXT = (
    "회사는 보통약관 제3조(보험금의 지급사유) 제2호에도 불구하고 후유장해보험금을 보상하지 "
    "않습니다."
)


def _get_or_create_coverage(db, policy_version_id, coverage_std, raw_name):
    cov = (
        db.query(Coverage)
        .filter(Coverage.policy_version_id == policy_version_id, Coverage.raw_name == raw_name)
        .first()
    )
    if cov:
        return cov, False
    cov = Coverage(
        policy_version_id=policy_version_id,
        coverage_std_id=coverage_std.coverage_std_id,
        raw_name=raw_name,
    )
    db.add(cov)
    db.flush()
    return cov, True


def _get_or_create_clause(db, *, policy_version_id, coverage_id, clause_type, article_no, text, page_ref):
    existing = (
        db.query(Clause)
        .filter(Clause.coverage_id == coverage_id, Clause.text == text)
        .first()
    )
    if existing:
        return existing, False
    clause = Clause(
        policy_version_id=policy_version_id,
        coverage_id=coverage_id,
        clause_type=clause_type,
        article_no=article_no,
        text=text,
        page_ref=page_ref,
        default_color="파랑" if clause_type == "보장정의" else "빨강",
    )
    db.add(clause)
    db.flush()
    return clause, True


def _get_or_create_map(db, clause_id, type_id, relevance, mapped_by="human", confidence=1.0):
    existing = (
        db.query(ClauseIncidentMap)
        .filter(ClauseIncidentMap.clause_id == clause_id, ClauseIncidentMap.type_id == type_id)
        .first()
    )
    if existing:
        return existing, False
    m = ClauseIncidentMap(
        clause_id=clause_id, type_id=type_id, relevance=relevance,
        mapped_by=mapped_by, confidence=confidence,
    )
    db.add(m)
    db.flush()
    return m, True


def run():
    db = SessionLocal()
    stats = {"coverage_std": 0, "coverage": 0, "clause": 0, "map": 0, "incident_type": 0}
    try:
        insurer = db.query(Insurer).filter_by(code="SAMSUNG").first()
        if not insurer:
            print("삼성화재가 아직 시딩되지 않았습니다. seed_samsung을 먼저 실행하세요.")
            return
        policy_version = (
            db.query(PolicyVersion)
            .join(Product, Product.product_id == PolicyVersion.product_id)
            .filter(Product.insurer_id == insurer.insurer_id)
            .first()
        )
        pv_id = policy_version.policy_version_id

        # ---- 1) 자택 도난손해(가재) ----
        home_theft_std = get_or_create_coverage_std(db, "HOME_THEFT", "자택 도난손해(가재)", "휴대품", False)
        stats["coverage_std"] += 1
        home_theft_cov, created = _get_or_create_coverage(
            db, pv_id, home_theft_std, "여행중 자택 도난손해(가재) 보장 특별약관"
        )
        stats["coverage"] += int(created)

        home_theft_type = db.query(IncidentType).filter_by(l1_code="PROP", name="자택 도난손해(가재)").first()
        if not home_theft_type:
            home_theft_type = create_reviewable_type(db, "PROP", "자택 도난손해(가재)")
            stats["incident_type"] += 1

        def_clause, c1 = _get_or_create_clause(
            db, policy_version_id=pv_id, coverage_id=home_theft_cov.coverage_id,
            clause_type="보장정의",
            article_no="여행중 자택 도난손해(가재) 보장 특별약관 제1조(보상하는 손해)①",
            text=HOME_THEFT_DEFINITION_TEXT, page_ref="p.149",
        )
        stats["clause"] += int(c1)
        _, m1 = _get_or_create_map(db, def_clause.clause_id, home_theft_type.type_id, "직접")
        stats["map"] += int(m1)

        excl_clause, c2 = _get_or_create_clause(
            db, policy_version_id=pv_id, coverage_id=home_theft_cov.coverage_id,
            clause_type="면책",
            article_no="여행중 자택 도난손해(가재) 보장 특별약관 제3조(보상하지 않는 손해)",
            text=HOME_THEFT_EXCLUSION_TEXT, page_ref="p.150",
        )
        stats["clause"] += int(c2)
        _, m2 = _get_or_create_map(db, excl_clause.clause_id, home_theft_type.type_id, "면책")
        stats["map"] += int(m2)

        # ---- 2) 의사상자 상해위험 ----
        good_sam_std = get_or_create_coverage_std(db, "GOOD_SAMARITAN", "의사상자 상해위험", "상해", False)
        stats["coverage_std"] += 1
        good_sam_cov, created = _get_or_create_coverage(
            db, pv_id, good_sam_std, "의사상자 상해위험 특별약관"
        )
        stats["coverage"] += int(created)

        inj_death_type = db.query(IncidentType).filter_by(l2_code="INJ_DEATH_DISABILITY").first()

        good_sam_clause, c3 = _get_or_create_clause(
            db, policy_version_id=pv_id, coverage_id=good_sam_cov.coverage_id,
            clause_type="보장정의",
            article_no="의사상자 상해위험 특별약관 제1조(보상하는 손해)",
            text=GOOD_SAMARITAN_TEXT, page_ref="p.153",
        )
        stats["clause"] += int(c3)
        if inj_death_type:
            _, m3 = _get_or_create_map(db, good_sam_clause.clause_id, inj_death_type.type_id, "조건부")
            stats["map"] += int(m3)

        # ---- 3) 전쟁위험 ----
        war_std = get_or_create_coverage_std(db, "WAR_RISK", "전쟁위험", "특수", False)
        stats["coverage_std"] += 1
        war_cov, created = _get_or_create_coverage(db, pv_id, war_std, "전쟁위험 특별약관")
        stats["coverage"] += int(created)

        spc_war_type = db.query(IncidentType).filter_by(l2_code="SPC_WAR_TERROR").first()

        war_def_clause, c4 = _get_or_create_clause(
            db, policy_version_id=pv_id, coverage_id=war_cov.coverage_id,
            clause_type="보장정의",
            article_no="전쟁위험 특별약관 제1조(보상하는 손해)①",
            text=WAR_RISK_COVERAGE_TEXT, page_ref="p.154",
        )
        stats["clause"] += int(c4)
        if spc_war_type:
            _, m4 = _get_or_create_map(db, war_def_clause.clause_id, spc_war_type.type_id, "직접")
            stats["map"] += int(m4)

        war_excl_clause, c5 = _get_or_create_clause(
            db, policy_version_id=pv_id, coverage_id=war_cov.coverage_id,
            clause_type="면책",
            article_no="전쟁위험 특별약관 제2조(계약 후 알릴 의무의 특례)③",
            text=WAR_RISK_ROUTE_CHANGE_EXCLUSION_TEXT, page_ref="p.154",
        )
        stats["clause"] += int(c5)
        if spc_war_type:
            _, m5 = _get_or_create_map(db, war_excl_clause.clause_id, spc_war_type.type_id, "면책")
            stats["map"] += int(m5)

        # ---- 4) 상해 사망위험 / 후유장해위험 보상제외 (기존 DEATH_INJURY coverage_id 재사용) ----
        death_injury_cov = (
            db.query(Coverage)
            .filter(Coverage.policy_version_id == pv_id, Coverage.raw_name.like("상해사망%"))
            .first()
        )
        if death_injury_cov and inj_death_type:
            death_excl_clause, c6 = _get_or_create_clause(
                db, policy_version_id=pv_id, coverage_id=death_injury_cov.coverage_id,
                clause_type="면책",
                article_no="상해 사망위험 보상제외 특별약관 제1조(보험금을 지급하지 않는 사유)",
                text=DEATH_EXCLUSION_RIDER_TEXT, page_ref="p.171",
            )
            stats["clause"] += int(c6)
            _, m6 = _get_or_create_map(db, death_excl_clause.clause_id, inj_death_type.type_id, "면책")
            stats["map"] += int(m6)

            disability_excl_clause, c7 = _get_or_create_clause(
                db, policy_version_id=pv_id, coverage_id=death_injury_cov.coverage_id,
                clause_type="면책",
                article_no="상해 후유장해위험 보상제외 특별약관 제1조(보험금을 지급하지 않는 사유)",
                text=DISABILITY_EXCLUSION_RIDER_TEXT, page_ref="p.172",
            )
            stats["clause"] += int(c7)
            _, m7 = _get_or_create_map(db, disability_excl_clause.clause_id, inj_death_type.type_id, "면책")
            stats["map"] += int(m7)

        db.commit()
        print(f"samsung 청크E(p.149~174) 시딩 완료: {stats}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
