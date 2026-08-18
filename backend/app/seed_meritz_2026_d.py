"""
메리츠화재 다이렉트 해외여행보험 2026년판(약관번호 2607A) 청크 4(페이지 171-244).

## 출처
backend/data/processed/meritz_overseas_2607A_full_text.txt (파일 해시: f58406b6496f1031da5f5c870e73c65b7b85ef06d16e2b04448b53d21b61dbdd)

## 담당 페이지 범위
페이지 171-244

## 페이지별 실제 구성 (원문 정독 결과)

### 실제 특약(Coverage/Clause 대상) — 페이지 171-177, 187-188
1. 실손의료비 운동 및 기타위험 확장보상(전문등반 등)(Ⅰ) 추가특별약관 (p.171)
   - 전문등반·글라이더·스카이다이빙·스쿠버다이빙·행글라이딩·수상보트·패러글라이딩을
     "직업, 직무 또는 동호회 활동목적"으로 하다가 입은 상해는 기본형 실손의료비
     특별약관에서 원래 면책이나, 이 추가특약을 동시 가입하면 다시 보상한다.
     → 사고 판단에 직결(면책 예외 복원) CoverageStd: OVS_INJ_MED
2. 실손의료비 운동 및 기타위험 확장보상(자동차경기 등)(Ⅱ) 추가특별약관 (p.172)
   - 모터보트·자동차·오토바이 경기/시범/행사/시운전(공용도로 시운전 중 상해는 여전히
     제외)으로 인한 상해를 다시 보상. CoverageStd: OVS_INJ_MED
3. 국민건강보험 비가입자 추가특별약관 (p.173)
   - 국민건강보험 미적용자(외국인 등)를 국민건강보험 가입자와 동일한 기준으로 보상.
     보험금 산정 기준 자체를 바꾸는 조항이라 사고 판단과 관련. CoverageStd: OVS_INJ_MED
     (상해급여·질병급여 모두에 적용되나 기존에 재사용 가능한 std 중 상해의료비 쪽을 사용)
4. ( )보험금만의 지급 특별약관 (p.174)
   - 특정 보험금 종류만 지급하도록 제한하는 범용 템플릿(괄호 빈칸은 원문 그대로).
     CoverageStd 없음(어떤 보험금인지 특정되지 않은 서식 조항).
5. 상해사망 부보장 특별약관Ⅱ (p.175)
   - 특정 특별약관(괄호 빈칸)의 상해사망 보험금을 부보장. CoverageStd: DEATH_INJURY
6. 상해후유장해 부보장 특별약관Ⅱ (p.176)
   - 특정 특별약관(괄호 빈칸)의 상해후유장해 보험금을 부보장. CoverageStd: DEATH_INJURY
7. 여행 동반인 보장 특별약관 (p.177)
   - 보험증권에 기재된 여행 동반인을 피보험자로 확장. 피보험자 범위(자격) 자체를
     정하는 조항이라 청구 적격 판단에 관련. CoverageStd 없음(범위 확장 성격)
8. 해외발생 상해의료비 공제금액설정 추가특별약관Ⅱ (p.187)
   - 상해의료비(해외) 보상 시 자기부담금(공제금액, 원문 빈칸)을 초과하는 금액만
     보험가입금액 한도로 지급. CoverageStd: OVS_INJ_MED
9. 해외발생 질병의료비 공제금액설정 추가특별약관Ⅱ (p.188)
   - 질병의료비(해외) 버전. CoverageStd: OVS_ILL_MED

### 순수 계약행정 — 확인함, 무관 (원문 정독 후 판단)
- 지정대리청구서비스 특별약관 (p.178-180): 계약자가 보험금을 직접 청구할 수 없을 때
  대리청구인을 지정하는 절차. 사고 발생 여부·보상범위와 무관, 청구 대리인 지정 행정.
- 환율 특별약관 (p.181): 보험료/보험금을 원화로 환산할 때 적용하는 하나은행 고시환율
  기준일 정의. 지급액의 환전 계산방식일 뿐 담보·면책과 무관.
- 장애인전용보험전환 특별약관 (p.182-185): 소득세법상 세액공제를 위해 계약을
  장애인전용보험으로 전환하는 세무 행정 절차. 사고 판단과 무관.
- 예치보험료 정산 특별약관 (p.186): 피보험자 수 등이 수시로 변동하는 단체성 계약의
  보험료를 사후 정산하는 절차. 사고 판단과 무관.

### 참고자료(별표/부표) — Clause화 대상 아님, 확인함
- 【별표1】장해 분류표 (목차 p.177, 본문 p.189-212): 상해/질병 후유장해 지급률
  판정기준 총칙 + 신체부위별(눈/귀/코/씹어먹기·말하기/외모/척추/체간골/팔/다리/
  손가락/발가락/흉복부장기 및 비뇨생식기/신경계·정신행동) 상세 판정표. 다른
  특별약관(50%/80%/100%고도후유장해 등, 청크1에서 이미 처리)이 "장해분류표
  【별표1】참조"로 인용하는 원표(原表)이며, 표 자체는 특약 조항 구조(Coverage/Clause)가
  아니라 판정기준 원자료이므로 이번 시드에서는 별도 Clause로 만들지 않음.
- <부표1> 보험금을 지급할 때의 적립이율 계산 (p.213), <부표2> 동 적립이율(배상책임
  특별약관 제5조 관련, p.214), <부표3> 단기요율표 (p.215): 지연이자율/단기요율 수치표.
- 【별표2】해외여행통지 서식 (p.216), 【별표3】식중독 분류표(p.217), 【별표4】
  특정전염병 분류표(p.218), 【별표5】골절 분류표(p.219), 【별표6】골절(치아파절
  제외) 분류표(p.220): 각 담보(식중독보상금·특정감염병보상금·골절진단비 등)의
  질병분류코드(KCD) 대응표. 해당 담보들은 이번 청크 담당범위 밖(페이지 43-86,
  청크2)에서 정의되며, 이 표는 그 담보들이 참조하는 코드표이므로 별도 Clause화하지
  않음.
- 법률조문 해설 (p.221-242): 민법·전자서명법·신용정보법 등 약관 본문에 인용된
  법조문을 그대로 옮겨 적은 용어해설 부록. 특약 조항이 아니라 참고용 법령 발췌.
- 주요 민원/분쟁 사례 및 유의사항 (p.243-244): 목차상 존재하나, 추출된 원문에는
  표제(p.243 "주요 민원/분쟁 사례 및 유의사항")와 페이지번호(p.244 "- 232 -")만
  있고 본문 내용이 없음(원본 PDF에서 텍스트 추출이 되지 않은 것으로 보임). 실제
  조항 내용이 없으므로 Clause 대상 없음.

## CoverageStd 재사용
OVS_INJ_MED, OVS_ILL_MED, DEATH_INJURY (모두 기존 std_code 재사용, 새로 만든 코드 없음)

## 확인함/무관으로 처리한 특약 (요약)
지정대리청구서비스 특별약관, 환율 특별약관, 장애인전용보험전환 특별약관,
예치보험료 정산 특별약관 — 4건, 모두 원문 정독 후 순수 계약행정으로 판단.
"""

from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Clause, Coverage, PolicyVersion, Product,
)
from app.services.kb_seed_common import get_or_create_coverage_std

# ---------------------------------------------------------------------------
# 1. 실손의료비 운동 및 기타위험 확장보상(전문등반 등)(Ⅰ) 추가특별약관 (p.171)
# ---------------------------------------------------------------------------

CLAUSE_SPORTS1_ART1_TEXT = (
    "이 추가 특별약관은 기본형 해외여행 실손의료비 특별약관 제1조(보장종목)의 상해급여, "
    "비급여 해외여행 실손의료비 특별약관1(중증 비급여 실손의료비) 제1조(보장종목)의 상해비급여 "
    "및 3대비급여, 비급여 해외여행 실손의료비 특별약관2(비중증 비급여 실손의료비) 제1조"
    "(보장종목)의 상해비급여 및 비급여자기공명영상진단을 동시에 가입한 계약에 한해 적용합니다."
)

CLAUSE_SPORTS1_ART2_TEXT = (
    "회사는 기본형 해외여행 실손의료비 특별약관 제4조(보상하지 않는 사항) (1)상해급여 제2항 "
    "제1호, 비급여 해외여행 실손의료비 특별약관1(중증 비급여 실손의료비) 제4조(보상하지 않는 "
    "사항) (1)상해비급여 제2항 제1호 및 (3)3대비급여 제2항 제1호, 비급여 해외여행 실손의료비 "
    "특별약관2(비중증 비급여 실손의료비) 제4조(보상하지 않는 사항) (1)상해비급여 제2항 제1호 "
    "및 (3)비급여자기공명영상진단 제2항 제1호에도 불구하고 피보험자에게 아래에 해당되는 사유가 "
    "발생한 때에는 보험수익자에게 실손의료비 특별약관 보장종목별 보상내용에서 정한 보험금을 "
    "지급합니다."
)

CLAUSE_SPORTS1_ART2_1_TEXT = (
    "1. 직업, 직무 또는 동호회 활동목적으로 전문등반(전문적인 등산용구를 사용하여 암벽 또는 "
    "빙벽을 오르내리거나 특수한 기술, 경험, 사전 훈련이 필요한 등반을 말합니다), 글라이더 조종, "
    "스카이다이빙, 스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩으로 인하여 생긴 상해"
)

CLAUSE_SPORTS1_ART3_TEXT = (
    "이 추가특별약관에서 정하지 않은 사항은 기본형 해외여행 실손의료비 특별약관, 비급여 해외여행 "
    "실손의료비 특별약관1(중증 비급여 실손의료비) 및 비급여 해외여행 실손의료비 특별약관2"
    "(비중증 비급여 실손의료비)를 따릅니다."
)

# ---------------------------------------------------------------------------
# 2. 실손의료비 운동 및 기타위험 확장보상(자동차경기 등)(Ⅱ) 추가특별약관 (p.172)
# ---------------------------------------------------------------------------

CLAUSE_SPORTS2_ART1_TEXT = CLAUSE_SPORTS1_ART1_TEXT  # 원문상 (Ⅰ)과 제1조 문구 동일

CLAUSE_SPORTS2_ART2_TEXT = (
    "회사는 기본형 해외여행 실손의료비 특별약관 제4조(보상하지 않는 사항) (1)상해급여 제2항 "
    "제2호, 비급여 해외여행 실손의료비 특별약관1(중증 비급여 실손의료비) 제4조(보상하지 않는 "
    "사항) (1)상해비급여 제2항 제2호 및 (3)3대비급여 제2항 제2호, 비급여 해외여행 실손의료비 "
    "특별약관2(비중증 비급여 실손의료비) 제4조(보상하지 않는 사항) (1)상해비급여 제2항 제2호 "
    "및 (3)비급여자기공명영상진단 제2항 제2호에도 불구하고 피보험자에게 아래에 해당되는 사유가 "
    "발생한 때에는 보험수익자에게 실손의료비 특별약관 보장종목별 보상내용에서 정한 보험금을 "
    "지급합니다."
)

CLAUSE_SPORTS2_ART2_1_TEXT = (
    "1. 직업, 직무 또는 동호회 활동목적으로 모터보트·자동차 또는 오토바이에 의한 경기, 시범, "
    "행사(이를 위한 연습을 포함합니다) 또는 시운전(다만, 공용도로에서 시운전을 하는 동안 "
    "발생한 상해는 제외)으로 인하여 생긴 상해"
)

CLAUSE_SPORTS2_ART3_TEXT = (
    "이 추가특별약관에서 정하지 않은 사항은 기본형 해외여행 실손의료비 특별약관, 비급여 해외여행 "
    "실손의료비 특별약관1(중증 비급여 실손의료비) 및 비급여 해외여행 실손의료비 특별약관2"
    "(비중증 비급여 실손의료비)를 따릅니다."
)

# ---------------------------------------------------------------------------
# 3. 국민건강보험 비가입자 추가특별약관 (p.173)
# ---------------------------------------------------------------------------

CLAUSE_NHI_ART1_TEXT = (
    "이 추가특별약관의 피보험자는 국민건강보험법의 적용을 받지 않는 자로 합니다."
)

CLAUSE_NHI_ART2_1_TEXT = (
    "보험기간 중에 피보험자가 국민건강보험법에 정한 자격을 취득하였을 때 계약자는 서면으로 "
    "회사에 알리고 보험증권에 확인을 받아야 합니다."
)

CLAUSE_NHI_ART2_2_TEXT = (
    "피보험자가 국민건강보험법에 정한 자격을 취득한 경우 그 사실이 발생된 날로부터 이 "
    "추가특별약관은 해지되며 회사는 경과하지 않은 기간에 대하여 일단위로 계산한 정해진 "
    "보험료를 환급하여 드립니다."
)

CLAUSE_NHI_ART3_TEXT = (
    "기본형 해외여행 실손의료비 특별약관 제3조(보장종목별 보상내용)의 (1)상해급여 제3항 "
    "제1호 및 (2)질병급여 제2항 제1호에도 불구하고 국민건강보험 가입자와 동일한 기준으로 "
    "보상하여 드립니다."
)

CLAUSE_NHI_ART4_TEXT = (
    "이 추가특별약관에 정하지 않은 사항은 기본형 해외여행 실손의료비 특별약관을 따릅니다."
)

# ---------------------------------------------------------------------------
# 4. ( )보험금만의 지급 특별약관 (p.174) — 원문의 괄호 빈칸을 그대로 둔 범용 서식
# ---------------------------------------------------------------------------

CLAUSE_ONLY_BENEFIT_ART1_TEXT = (
    "회사는 ( )약관에 관계없이 ( )보험금만을 지급합니다."
)

CLAUSE_ONLY_BENEFIT_ART2_TEXT = (
    "이 특별약관에 정하지 않은 사항은 ( )약관을 따릅니다."
)

# ---------------------------------------------------------------------------
# 5. 상해사망 부보장 특별약관Ⅱ (p.175) — 원문의 괄호 빈칸을 그대로 둔 범용 서식
# ---------------------------------------------------------------------------

CLAUSE_DEATH_EXCL2_ART1_TEXT = (
    "회사는 ( ) 특별약관 제1조(보험금의 지급사유)에 정한 규정에도 불구하고 이 특약에 따라 "
    "상해사망 보험금을 드리지 않습니다."
)

CLAUSE_DEATH_EXCL2_ART2_TEXT = (
    "이 특별약관에 정하지 않은 사항은 ( )약관을 따릅니다."
)

# ---------------------------------------------------------------------------
# 6. 상해후유장해 부보장 특별약관Ⅱ (p.176) — 원문의 괄호 빈칸을 그대로 둔 범용 서식
# ---------------------------------------------------------------------------

CLAUSE_DISABILITY_EXCL2_ART1_TEXT = (
    "회사는 ( ) 특별약관 제1조(보험금의 지급사유)에 정한 규정에도 불구하고 이 특약에 따라 "
    "상해후유장해 보험금을 드리지 않습니다."
)

CLAUSE_DISABILITY_EXCL2_ART2_TEXT = (
    "이 특별약관에 정하지 않은 사항은 ( )약관을 따릅니다."
)

# ---------------------------------------------------------------------------
# 7. 여행 동반인 보장 특별약관 (p.177)
# ---------------------------------------------------------------------------

CLAUSE_COMPANION_ART1_TEXT = (
    "회사는 이 특별약관에 의하여 피보험자 본인(이하 “본인”이라 합니다) 및 보험증권에 기재된 "
    "피보험자의 여행 동반인을 보통약관(해당 특별약관을 포함합니다)의 피보험자로 합니다."
)

CLAUSE_COMPANION_DEF_TEXT = (
    "【여행 동반인】피보험자와 해외여행(여행사를 통한 패키지여행* 포함)을 함께 하는 사람 중 "
    "보험증권에 기재된 자\n"
    "* 여행사가 항공, 숙박, 여행지 등 모든 일정과 장소를 정하고 여행객은 정해진 일정대로 "
    "움직이는 여행 상품"
)

CLAUSE_COMPANION_ART2_TEXT = (
    "이 특별약관에 정하지 않은 사항은 보통약관 및 해당 특별약관을 따릅니다."
)

# ---------------------------------------------------------------------------
# 8. 해외발생 상해의료비 공제금액설정 추가특별약관Ⅱ (p.187)
# ---------------------------------------------------------------------------

CLAUSE_DEDUCT_INJ_ART1_1_TEXT = (
    "회사는 기본형 해외여행 실손의료비 특별약관 제3조(보장종목별 보상내용) 보장종목 "
    "(1)상해의료비(해외)의 제1항에도 불구하고 하나의 상해에 대하여 피보험자가 실제로 부담한 "
    "의료비 중 ( )원(이하 “공제금액”이라 합니다)을 초과하는 금액을 보험가입금액을 한도로 "
    "보상하여 드립니다."
)

CLAUSE_DEDUCT_INJ_ART1_2_TEXT = (
    "제1항의 공제금액은 계약시 계약자가 선택한 자기부담금액을 말합니다."
)

CLAUSE_DEDUCT_INJ_ART2_TEXT = (
    "이 추가특별약관에서 정하지 않은 사항은 기본형 해외여행 실손의료비 특별약관을 따릅니다."
)

# ---------------------------------------------------------------------------
# 9. 해외발생 질병의료비 공제금액설정 추가특별약관Ⅱ (p.188)
# ---------------------------------------------------------------------------

CLAUSE_DEDUCT_ILL_ART1_1_TEXT = (
    "회사는 기본형 해외여행 실손의료비 특별약관 제3조(보장종목별 보상내용) 보장종목 "
    "(2)질병의료비(해외)의 제1항에도 불구하고 하나의 질병에 대하여 피보험자가 실제로 부담한 "
    "의료비 중 ( )원(이하 “공제금액”이라 합니다)을 초과하는 금액을 보험가입금액을 한도로 "
    "보상하여 드립니다."
)

CLAUSE_DEDUCT_ILL_ART1_2_TEXT = (
    "제1항의 공제금액은 계약시 계약자가 선택한 자기부담금액을 말합니다."
)

CLAUSE_DEDUCT_ILL_ART2_TEXT = (
    "이 추가특별약관에서 정하지 않은 사항은 기본형 해외여행 실손의료비 특별약관을 따릅니다."
)


def _add_clause(db, pv_id, coverage_id, clause_type, article_no, text, page_ref, color):
    clause = Clause(
        policy_version_id=pv_id,
        coverage_id=coverage_id,
        clause_type=clause_type,
        article_no=article_no,
        text=text,
        page_ref=page_ref,
        default_color=color,
    )
    existing = db.query(Clause).filter_by(policy_version_id=pv_id, text=clause.text).first()
    if not existing:
        db.add(clause)
    return clause


def run():
    """
    메리츠 2026년판 청크 4 시드 함수. 페이지 171-244 중 실제 특약(9건, 페이지
    171-177 및 187-188)을 Coverage/Clause로 시드한다. 나머지(지정대리청구·환율·
    장애인전용전환·예치보험료정산은 순수 계약행정, 별표/부표/법률조문해설/민원사례는
    참고자료·본문없음)는 DB화하지 않는다. 근거는 모듈 docstring 참조.

    멱등성: 같은 policy_version_id + clause.text 조합이 이미 있으면 건너뜀.
    """
    db = SessionLocal()
    try:
        product = db.query(Product).filter_by(product_code="MERITZ-OVERSEAS-2026").first()
        if not product:
            print("ERROR: Product MERITZ-OVERSEAS-2026이 없습니다. seed_meritz_2026_a.py를 먼저 실행하세요.")
            return

        pv = db.query(PolicyVersion).filter_by(
            product_id=product.product_id,
            version_label="메리츠일반-특종/상해/여행B-10-2607A"
        ).first()
        if not pv:
            print("ERROR: PolicyVersion이 없습니다. seed_meritz_2026_a.py를 먼저 실행하세요.")
            return

        pv_id = pv.policy_version_id

        # 이 청크가 이미 시드됐으면(Coverage 생성이 idempotent하지 않으므로) 통째로 건너뛴다.
        if db.query(Coverage).filter_by(policy_version_id=pv_id, raw_name="실손의료비 운동 및 기타위험 확장보상(전문등반 등)(Ⅰ) 추가특별약관").first():
            print("메리츠 2026년판 청크 4: 이미 시드됨, 건너뜀.")
            return

        # CoverageStd 조회/재사용 (신규 코드 없음)
        std_ovs_inj = get_or_create_coverage_std(db, "OVS_INJ_MED", "해외발생 상해의료비", "의료", is_base=False)
        std_ovs_ill = get_or_create_coverage_std(db, "OVS_ILL_MED", "해외발생 질병의료비", "의료", is_base=False)
        std_death = get_or_create_coverage_std(db, "DEATH_INJURY", "상해사망·후유장해", "상해", is_base=True)

        n_coverage = 0
        n_clause = 0

        # ===== 1. 실손의료비 운동 및 기타위험 확장보상(전문등반 등)(Ⅰ) 추가특별약관 =====
        cov = Coverage(
            policy_version_id=pv_id,
            coverage_std_id=std_ovs_inj.coverage_std_id,
            raw_name="실손의료비 운동 및 기타위험 확장보상(전문등반 등)(Ⅰ) 추가특별약관",
            definition=None, limit_amount=None, deductible=None,
            waiting_condition="전문등반·글라이더·스카이다이빙·스쿠버다이빙·행글라이딩·수상보트·패러글라이딩 직업/직무/동호회 활동 시 동시가입 필요",
        )
        db.add(cov); db.flush(); n_coverage += 1
        base = "[실손의료비 운동 및 기타위험 확장보상(전문등반 등)(Ⅰ) 추가특별약관]"
        _add_clause(db, pv_id, cov.coverage_id, "조건", f"{base} 제1조(추가특별약관의 적용)", CLAUSE_SPORTS1_ART1_TEXT, "p.171", "노랑"); n_clause += 1
        _add_clause(db, pv_id, cov.coverage_id, "보장정의", f"{base} 제2조(보험금의 지급사유)", CLAUSE_SPORTS1_ART2_TEXT, "p.171", "파랑"); n_clause += 1
        _add_clause(db, pv_id, cov.coverage_id, "보장정의", f"{base} 제2조 1호", CLAUSE_SPORTS1_ART2_1_TEXT, "p.171", "파랑"); n_clause += 1
        _add_clause(db, pv_id, cov.coverage_id, "공통", f"{base} 제3조(준용규정)", CLAUSE_SPORTS1_ART3_TEXT, "p.171", "회색"); n_clause += 1

        # ===== 2. 실손의료비 운동 및 기타위험 확장보상(자동차경기 등)(Ⅱ) 추가특별약관 =====
        cov = Coverage(
            policy_version_id=pv_id,
            coverage_std_id=std_ovs_inj.coverage_std_id,
            raw_name="실손의료비 운동 및 기타위험 확장보상(자동차경기 등)(Ⅱ) 추가특별약관",
            definition=None, limit_amount=None, deductible=None,
            waiting_condition="모터보트·자동차·오토바이 경기/시범/행사/시운전(공용도로 시운전 중 상해는 제외) 직업/직무/동호회 활동 시 동시가입 필요",
        )
        db.add(cov); db.flush(); n_coverage += 1
        base = "[실손의료비 운동 및 기타위험 확장보상(자동차경기 등)(Ⅱ) 추가특별약관]"
        _add_clause(db, pv_id, cov.coverage_id, "조건", f"{base} 제1조(추가특별약관의 적용)", CLAUSE_SPORTS2_ART1_TEXT, "p.172", "노랑"); n_clause += 1
        _add_clause(db, pv_id, cov.coverage_id, "보장정의", f"{base} 제2조(보험금의 지급사유)", CLAUSE_SPORTS2_ART2_TEXT, "p.172", "파랑"); n_clause += 1
        _add_clause(db, pv_id, cov.coverage_id, "보장정의", f"{base} 제2조 1호", CLAUSE_SPORTS2_ART2_1_TEXT, "p.172", "파랑"); n_clause += 1
        _add_clause(db, pv_id, cov.coverage_id, "공통", f"{base} 제3조(준용규정)", CLAUSE_SPORTS2_ART3_TEXT, "p.172", "회색"); n_clause += 1

        # ===== 3. 국민건강보험 비가입자 추가특별약관 =====
        cov = Coverage(
            policy_version_id=pv_id,
            coverage_std_id=std_ovs_inj.coverage_std_id,
            raw_name="국민건강보험 비가입자 추가특별약관",
            definition=None, limit_amount=None, deductible=None,
            waiting_condition="피보험자가 국민건강보험법 적용 대상이 아닌 경우에만 적용, 보험기간 중 자격취득 시 계약 해지",
        )
        db.add(cov); db.flush(); n_coverage += 1
        base = "[국민건강보험 비가입자 추가특별약관]"
        _add_clause(db, pv_id, cov.coverage_id, "조건", f"{base} 제1조(적용대상)", CLAUSE_NHI_ART1_TEXT, "p.173", "노랑"); n_clause += 1
        _add_clause(db, pv_id, cov.coverage_id, "조건", f"{base} 제2조 ①", CLAUSE_NHI_ART2_1_TEXT, "p.173", "노랑"); n_clause += 1
        _add_clause(db, pv_id, cov.coverage_id, "조건", f"{base} 제2조 ②", CLAUSE_NHI_ART2_2_TEXT, "p.173", "노랑"); n_clause += 1
        _add_clause(db, pv_id, cov.coverage_id, "보장정의", f"{base} 제3조(보장종목별 보상내용)", CLAUSE_NHI_ART3_TEXT, "p.173", "파랑"); n_clause += 1
        _add_clause(db, pv_id, cov.coverage_id, "공통", f"{base} 제4조(준용규정)", CLAUSE_NHI_ART4_TEXT, "p.173", "회색"); n_clause += 1

        # ===== 4. ( )보험금만의 지급 특별약관 =====
        cov = Coverage(
            policy_version_id=pv_id,
            coverage_std_id=None,
            raw_name="( )보험금만의 지급 특별약관",
            definition="원문에 괄호 빈칸(약관명/보험금명 미기재)으로 인쇄된 범용 서식 특약. 특정 기초 약관과 결합될 때 그 약관이 정한 보험금 중 지정된 하나만 지급하도록 제한.",
            limit_amount=None, deductible=None, waiting_condition=None,
        )
        db.add(cov); db.flush(); n_coverage += 1
        base = "[( )보험금만의 지급 특별약관]"
        _add_clause(db, pv_id, cov.coverage_id, "제한", f"{base} 제1조(보험금의 지급사유)", CLAUSE_ONLY_BENEFIT_ART1_TEXT, "p.174", "초록"); n_clause += 1
        _add_clause(db, pv_id, cov.coverage_id, "공통", f"{base} 제2조(준용규정)", CLAUSE_ONLY_BENEFIT_ART2_TEXT, "p.174", "회색"); n_clause += 1

        # ===== 5. 상해사망 부보장 특별약관Ⅱ =====
        cov = Coverage(
            policy_version_id=pv_id,
            coverage_std_id=std_death.coverage_std_id,
            raw_name="상해사망 부보장 특별약관Ⅱ",
            definition="원문에 괄호 빈칸(기초 특별약관명 미기재)으로 인쇄된 범용 서식 특약. 결합되는 기초 특별약관의 상해사망 보험금을 부보장.",
            limit_amount=None, deductible=None, waiting_condition=None,
        )
        db.add(cov); db.flush(); n_coverage += 1
        base = "[상해사망 부보장 특별약관Ⅱ]"
        _add_clause(db, pv_id, cov.coverage_id, "면책", f"{base} 제1조(보험금을 지급하지 않는 사유)", CLAUSE_DEATH_EXCL2_ART1_TEXT, "p.175", "빨강"); n_clause += 1
        _add_clause(db, pv_id, cov.coverage_id, "공통", f"{base} 제2조(준용규정)", CLAUSE_DEATH_EXCL2_ART2_TEXT, "p.175", "회색"); n_clause += 1

        # ===== 6. 상해후유장해 부보장 특별약관Ⅱ =====
        cov = Coverage(
            policy_version_id=pv_id,
            coverage_std_id=std_death.coverage_std_id,
            raw_name="상해후유장해 부보장 특별약관Ⅱ",
            definition="원문에 괄호 빈칸(기초 특별약관명 미기재)으로 인쇄된 범용 서식 특약. 결합되는 기초 특별약관의 상해후유장해 보험금을 부보장.",
            limit_amount=None, deductible=None, waiting_condition=None,
        )
        db.add(cov); db.flush(); n_coverage += 1
        base = "[상해후유장해 부보장 특별약관Ⅱ]"
        _add_clause(db, pv_id, cov.coverage_id, "면책", f"{base} 제1조(보험금을 지급하지 않는 사유)", CLAUSE_DISABILITY_EXCL2_ART1_TEXT, "p.176", "빨강"); n_clause += 1
        _add_clause(db, pv_id, cov.coverage_id, "공통", f"{base} 제2조(준용규정)", CLAUSE_DISABILITY_EXCL2_ART2_TEXT, "p.176", "회색"); n_clause += 1

        # ===== 7. 여행 동반인 보장 특별약관 =====
        cov = Coverage(
            policy_version_id=pv_id,
            coverage_std_id=None,
            raw_name="여행 동반인 보장 특별약관",
            definition=None, limit_amount=None, deductible=None,
            waiting_condition="보험증권에 기재된 여행 동반인만 피보험자로 인정",
        )
        db.add(cov); db.flush(); n_coverage += 1
        base = "[여행 동반인 보장 특별약관]"
        _add_clause(db, pv_id, cov.coverage_id, "보장정의", f"{base} 제1조(피보험자의 범위)", CLAUSE_COMPANION_ART1_TEXT, "p.177", "파랑"); n_clause += 1
        _add_clause(db, pv_id, cov.coverage_id, "보장정의", f"{base} 제1조(피보험자의 범위) - 여행 동반인 정의", CLAUSE_COMPANION_DEF_TEXT, "p.177", "파랑"); n_clause += 1
        _add_clause(db, pv_id, cov.coverage_id, "공통", f"{base} 제2조(준용규정)", CLAUSE_COMPANION_ART2_TEXT, "p.177", "회색"); n_clause += 1

        # ===== 8. 해외발생 상해의료비 공제금액설정 추가특별약관Ⅱ =====
        cov = Coverage(
            policy_version_id=pv_id,
            coverage_std_id=std_ovs_inj.coverage_std_id,
            raw_name="해외발생 상해의료비 공제금액설정 추가특별약관Ⅱ",
            definition=None, limit_amount=None,
            deductible="하나의 상해당 계약시 계약자가 선택한 자기부담금액(공제금액, 원문 금액 미기재) 초과분만 보험가입금액 한도로 보상",
            waiting_condition=None,
        )
        db.add(cov); db.flush(); n_coverage += 1
        base = "[해외발생 상해의료비 공제금액설정 추가특별약관Ⅱ]"
        _add_clause(db, pv_id, cov.coverage_id, "제한", f"{base} 제1조 ①", CLAUSE_DEDUCT_INJ_ART1_1_TEXT, "p.187", "초록"); n_clause += 1
        _add_clause(db, pv_id, cov.coverage_id, "조건", f"{base} 제1조 ②", CLAUSE_DEDUCT_INJ_ART1_2_TEXT, "p.187", "노랑"); n_clause += 1
        _add_clause(db, pv_id, cov.coverage_id, "공통", f"{base} 제2조(준용규정)", CLAUSE_DEDUCT_INJ_ART2_TEXT, "p.187", "회색"); n_clause += 1

        # ===== 9. 해외발생 질병의료비 공제금액설정 추가특별약관Ⅱ =====
        cov = Coverage(
            policy_version_id=pv_id,
            coverage_std_id=std_ovs_ill.coverage_std_id,
            raw_name="해외발생 질병의료비 공제금액설정 추가특별약관Ⅱ",
            definition=None, limit_amount=None,
            deductible="하나의 질병당 계약시 계약자가 선택한 자기부담금액(공제금액, 원문 금액 미기재) 초과분만 보험가입금액 한도로 보상",
            waiting_condition=None,
        )
        db.add(cov); db.flush(); n_coverage += 1
        base = "[해외발생 질병의료비 공제금액설정 추가특별약관Ⅱ]"
        _add_clause(db, pv_id, cov.coverage_id, "제한", f"{base} 제1조 ①", CLAUSE_DEDUCT_ILL_ART1_1_TEXT, "p.188", "초록"); n_clause += 1
        _add_clause(db, pv_id, cov.coverage_id, "조건", f"{base} 제1조 ②", CLAUSE_DEDUCT_ILL_ART1_2_TEXT, "p.188", "노랑"); n_clause += 1
        _add_clause(db, pv_id, cov.coverage_id, "공통", f"{base} 제2조(준용규정)", CLAUSE_DEDUCT_ILL_ART2_TEXT, "p.188", "회색"); n_clause += 1

        db.commit()
        print("메리츠 2026년판 청크 4(p.171-244) 시드 완료.")
        print(f"- Coverage: {n_coverage}개")
        print(f"- Clause: {n_clause}개")
        print("- 확인함/무관(순수 계약행정, 4건): 지정대리청구서비스, 환율, 장애인전용보험전환, 예치보험료정산 특별약관")
        print("- 확인함/참고자료(Clause화 대상 아님): 별표1(장해분류표) p.189-212, 부표1-3 p.213-215, "
              "별표2-6 p.216-220, 법률조문 해설 p.221-242, 주요 민원/분쟁 사례 p.243-244(본문 없음)")

    finally:
        db.close()


if __name__ == "__main__":
    run()
