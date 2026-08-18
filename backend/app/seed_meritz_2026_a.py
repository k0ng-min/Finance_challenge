"""
메리츠화재 다이렉트 해외여행보험 2026년판(약관번호 2607A) 청크 1(페이지 1-42).

## 출처
backend/data/processed/meritz_overseas_2607A_full_text.txt (파일 해시: f58406b6496f1031da5f5c870e73c65b7b85ef06d16e2b04448b53d21b61dbdd)

## 담당 페이지 범위
- 페이지 1-34: 다이렉트 해외여행보험 보통약관
- 페이지 35-42: 특별약관 (초기 7개)

## 페이지별 구성

### 페이지 1-34 (보통약관)
다이렉트 해외여행보험 보통약관 제1~41조
- 제1관(제1~2조): 목적 및 용어의 정의
- 제2관(제3~5조): 보험금의 지급
- 제3관(제6~8조): 보험금 지급사유 통지/청구/지급절차
- 제4관(제9~12조): 보험금 지급 변경, 주소변경, 보험수익자 지정
- 제5관(제13~16조): 계약 전 알릴 의무 등
- 제6관(제17~32조): 보험계약 성립, 청약철회, 약관 교부, 계약 무효, 계약내용 변경, 보험료 납입/환급
- 제7관(제33~41조): 분쟁 조정, 관할법원, 소멸시효, 약관 해석, 설명서 교부, 손해배상책임, 개인정보 보호

확인 결과: 보통약관은 순수 계약 절차/행정 조항으로 이미 DB에 기존 담보들과 함께 저장되어 있으므로
새로 추가하지 않는다. 단, 이 스크립트에서는 Product/PolicyVersion을 최초로 생성한다.

### 페이지 35-42 (특별약관)
이 범위에서 발견한 특별약관 7개:

1. 상해 사망·후유장해 부보장 특별약관 (페이지 35-36)
   - 제1조: 보험금을 지급하지 않는 사유 (면책)
   - 제2조: 준용규정
   - CoverageStd: DEATH_INJURY (기재 보장에서 제외하는 특약)

2. 상해 사망 부보장 특별약관 (페이지 36)
   - 제1조: 보험금을 지급하지 않는 사유 (면책)
   - 제2조: 준용규정
   - CoverageStd: DEATH_INJURY

3. 상해 후유장해 부보장 특별약관 (페이지 37)
   - 제1조: 보험금을 지급하지 않는 사유 (면책)
   - 제2조: 준용규정
   - CoverageStd: DEATH_INJURY

4. 해외여행중 상해50%이상고도후유장해 특별약관 (페이지 38)
   - 제1조: 보험금의 지급사유 (보장정의)
   - 제2조: 준용규정
   - CoverageStd: DEATH_INJURY (고도후유장해로 정액 지급)

5. 해외여행중 상해80%이상고도후유장해 특별약관 (페이지 39)
   - 제1조: 보험금의 지급사유 (보장정의)
   - 제2조: 준용규정
   - CoverageStd: DEATH_INJURY

6. 해외여행중 상해100%고도후유장해 특별약관 (페이지 40)
   - 제1조: 보험금의 지급사유 (보장정의)
   - 제2조: 준용규정
   - CoverageStd: DEATH_INJURY

7. 질병사망 및 질병80%이상후유장해 특별약관 (페이지 41-42)
   - 제1조: 보험금의 지급사유 (보장정의, 2항)
   - 제2조: 보험금 지급에 관한 세부규정 (9항)
   - 제3조: 준용규정
   - CoverageStd: ILL_DEATH

## CoverageStd 재사용
- DEATH_INJURY: 상해사망·후유장해 (기본형, is_base=True)
- ILL_DEATH: 질병사망·고도후유장해 (기본형, is_base=True)

## 새로 만든 CoverageStd
없음. 기존 28개 중 위 2개를 재사용.

## 확인함/무관으로 처리한 특약
없음. 페이지 1-42 범위의 모든 특약을 확인 완료.

## 건너뛴 부분
보통약관(페이지 1-34): 계약 절차/행정 조항으로 이미 기존 시드에서 다루어짐.
"""

from datetime import date
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Clause, Coverage, Insurer, PolicyVersion, Product,
)
from app.services.kb_seed_common import get_or_create_coverage_std

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

PRODUCT_CODE = "MERITZ-OVERSEAS-2026"
VERSION_LABEL = "메리츠일반-특종/상해/여행B-10-2607A"
FILE_HASH = "f58406b6496f1031da5f5c870e73c65b7b85ef06d16e2b04448b53d21b61dbdd"
COLLECTED_AT = date(2026, 8, 18)

# ---------------------------------------------------------------------------
# 특별약관 1: 상해 사망·후유장해 부보장 특별약관 (페이지 35-36)
# ---------------------------------------------------------------------------

# 제1조 - 면책 조항
CLAUSE_INJURY_DEATH_EXCL_1_1_TEXT = (
    "회사는 보통약관 제3조(보험금의 지급사유) 및 제4조(보험금 지급에 관한 세부규정)에 정"
    "한 규정에도 불구하고 이 특별약관에 따라 상해 사망·후유장해 보험금을 드리지 않습니다."
)

CLAUSE_INJURY_DEATH_EXCL_1_2_TEXT = (
    "이 특별약관에 정하지 않은 사항은 보통약관을 따릅니다."
)

# ---------------------------------------------------------------------------
# 특별약관 2: 상해 사망 부보장 특별약관 (페이지 36)
# ---------------------------------------------------------------------------

CLAUSE_INJURY_DEATH_ONLY_EXCL_1_1_TEXT = (
    "회사는 보통약관 제3조(보험금의 지급사유) 및 제4조(보험금 지급에 관한 세부규정)에 정"
    "한 규정에도 불구하고 이 특별약관에 따라 상해 사망 보험금을 드리지 않습니다."
)

CLAUSE_INJURY_DEATH_ONLY_EXCL_1_2_TEXT = (
    "이 특별약관에 정하지 않은 사항은 보통약관을 따릅니다."
)

# ---------------------------------------------------------------------------
# 특별약관 3: 상해 후유장해 부보장 특별약관 (페이지 37)
# ---------------------------------------------------------------------------

CLAUSE_INJURY_DISABILITY_EXCL_1_1_TEXT = (
    "회사는 보통약관 제3조(보험금의 지급사유) 및 제4조(보험금 지급에 관한 세부규정)에 정"
    "한 규정에도 불구하고 이 특별약관에 따라 상해 후유장해 보험금을 드리지 않습니다."
)

CLAUSE_INJURY_DISABILITY_EXCL_1_2_TEXT = (
    "이 특별약관에 정하지 않은 사항은 보통약관을 따릅니다."
)

# ---------------------------------------------------------------------------
# 특별약관 4: 해외여행중 상해50%이상고도후유장해 특별약관 (페이지 38)
# ---------------------------------------------------------------------------

CLAUSE_INJURY_DISABILITY_50_1_1_TEXT = (
    "회사는 피보험자가 해외여행 중에 상해를 입고 그 상해로 장해분류표(【별표1】참조. 이하"
    "같습니다.)에서 정한 장해지급률이 50%이상 고도의 장해상태가 되었을 경우에는 이 특별"
    "약관의 보험가입금액 전액을 피보험자에게 지급합니다."
)

CLAUSE_INJURY_DISABILITY_50_1_2_TEXT = (
    "이 특별약관에 정하지 않은 사항은 보통약관을 따릅니다."
)

# ---------------------------------------------------------------------------
# 특별약관 5: 해외여행중 상해80%이상고도후유장해 특별약관 (페이지 39)
# ---------------------------------------------------------------------------

CLAUSE_INJURY_DISABILITY_80_1_1_TEXT = (
    "회사는 피보험자가 해외여행 중에 상해를 입고 그 상해로 장해분류표(【별표1】참조. 이하"
    "같습니다.)에서 정한 장해지급률이 80%이상 고도의 장해상태가 되었을 경우에는 이 특별"
    "약관의 보험가입금액 전액을 피보험자에게 지급합니다."
)

CLAUSE_INJURY_DISABILITY_80_1_2_TEXT = (
    "이 특별약관에 정하지 않은 사항은 보통약관을 따릅니다."
)

# ---------------------------------------------------------------------------
# 특별약관 6: 해외여행중 상해100%고도후유장해 특별약관 (페이지 40)
# ---------------------------------------------------------------------------

CLAUSE_INJURY_DISABILITY_100_1_1_TEXT = (
    "회사는 피보험자가 해외여행 중에 상해를 입고 그 상해로 장해분류표(【별표1】참조. 이하"
    "같습니다.)에서 정한 장해지급률이 100%이상 고도의 장해상태가 되었을 경우에는 이 특별"
    "약관의 보험가입금액 전액을 피보험자에게 지급합니다."
)

CLAUSE_INJURY_DISABILITY_100_1_2_TEXT = (
    "이 특별약관에 정하지 않은 사항은 보통약관을 따릅니다."
)

# ---------------------------------------------------------------------------
# 특별약관 7: 질병사망 및 질병80%이상후유장해 특별약관 (페이지 41-42)
# ---------------------------------------------------------------------------

CLAUSE_ILLNESS_DEATH_1_1_TEXT = (
    "회사는 해외여행 도중에 다음 사항 중 어느 한 가지의 경우에 해당되는 사유가 발생한"
    "때에는 보험수익자에게 이 특별약관의 약정한 보험금을 지급합니다."
)

CLAUSE_ILLNESS_DEATH_1_1_1_TEXT = (
    "1. 보험기간 중 질병으로 인하여 사망한 경우 : 사망보험금"
)

CLAUSE_ILLNESS_DEATH_1_1_2_TEXT = (
    "2. 보험기간 중에 진단확정된 질병으로 장해분류표(【별표1】참조. 이하 같습니다)에서"
    "정한 장해지급률이 80%이상에 해당하는 장해상태가 되었을 때 : 고도후유장해보험금"
    "(보험증권에 기재된 이 특약의 보험가입금액)"
)

CLAUSE_ILLNESS_DEATH_1_2_TEXT = (
    "제1항에도 불구하고 해외여행 도중에 발생한 질병을 직접원인으로 하여 보험기간 마지"
    "막날로부터 30일 이내에 사망하거나 또는 80%이상에 해당하는 장해상태가 되었을 때에"
    "도 제1항에서 정하는 보험금을 지급합니다."
)

CLAUSE_ILLNESS_DEATH_2_1_TEXT = (
    "「호스피스·완화의료 및 임종과정에 있는 환자의 연명의료 결정에 관한 법률」에 따른"
    "연명의료중단등결정 및 그 이행으로 피보험자가 사망하는 경우 연명의료중단등결정 및"
    "그 이행은 제1조(보험금의 지급사유) 제1호 '사망'의 원인 및 '사망보험금' 지급에 영향"
    "을 미치지 않습니다."
)

CLAUSE_ILLNESS_DEATH_2_2_TEXT = (
    "제1조(보험금의 지급사유) 제1항에서 장해지급률이 질병의 진단 확정일부터 180일 이"
    "내에 확정되지 않은 경우에는 질병의 진단확정일부터 180일이 되는 날의 의사진단에"
    "기초하여 고정될 것으로 인정되는 상태를 장해지급률로 결정합니다. 다만, 장해분류표"
    "(【별표1】참조)에 장해판정시기를 별도로 정한 경우에는 그에 따릅니다."
)

CLAUSE_ILLNESS_DEATH_2_3_TEXT = (
    "제2항에 따라 장해지급률이 결정되었으나 그 이후 보장을 받을 수 있는 기간(계약의 효"
    "력이 없어진 경우에는 보험기간이 10년 이상인 계약은 질병의 진단확정일부터 2년 이"
    "내로 하고, 보험기간이 10년 미만인 계약은 질병의 진단확정일부터 1년 이내)에 장해상"
    "태가 더 악화된 때에는 그 악화된 장해상태를 기준으로 장해지급률을 결정합니다."
)

CLAUSE_ILLNESS_DEATH_2_4_TEXT = (
    "장해분류표에 해당되지 않는 후유장해는 피보험자의 직업, 연령, 신분 또는 성별 등에"
    "관계없이 신체의 장해정도에 따라 장해분류표의 구분에 준하여 지급액을 결정합니다."
    "다만, 장해분류표의 각 장해분류별 최저 지급률 장해정도에 이르지 않는 후유장해에 대"
    "하여는 후유장해보험금을 지급하지 않습니다."
)

CLAUSE_ILLNESS_DEATH_2_5_TEXT = (
    "보험수익자와 회사가 제1조(보험금의 지급사유)의 보험금 지급사유에 대해 합의하지 못"
    "할 때는 보험수익자와 회사가 함께 제3자를 정하고 그 제3자의 의견에 따를 수 있습니"
    "다. 제3자는 의료법 제3조(의료기관)에 규정한 의한 종합병원 소속 전문의 중에 정하"
    "며, 보험금 지급사유 판정에 드는 의료비용은 회사가 전액 부담합니다."
)

CLAUSE_ILLNESS_DEATH_2_6_TEXT = (
    "같은 질병으로 두 가지 이상의 후유장해가 생긴 경우에는 후유장해 지급률을 합산하여"
    "지급합니다. 다만, 장해분류표의 각 신체부위별 판정기준에 별도로 정한 경우에는 그"
    "기준에 따릅니다."
)

CLAUSE_ILLNESS_DEATH_2_7_TEXT = (
    "다른 질병으로 인하여 후유장해가 2회 이상 발생하였을 경우에는 그 때마다 이에 해당"
    "하는 후유장해지급률을 결정합니다. 그러나 그 후유장해가 이미 후유장해보험금을 지급"
    "받은 동일한 부위에 가중된 때에는 최종 장해상태에 해당하는 후유장해보험금에서 이"
    "미 지급받은 후유장해보험금을 차감하여 지급합니다. 다만, 장해분류표의 각 신체부위"
    "별 판정기준에서 별도로 정한 경우에는 그 기준에 따릅니다."
)

CLAUSE_ILLNESS_DEATH_2_8_TEXT = (
    "이미 이 계약에서 후유장해보험금 지급사유에 해당되지 않았거나(보장개시 이전의 원인"
    "에 의하거나 또는 그 이전에 발생한 후유장해를 포함합니다), 후유장해보험금이 지급되"
    "지 않았던 피보험자에게 그 신체의 동일 부위에 또다시 제7항에 규정하는 후유장해상"
    "태가 발생하였을 경우에는 직전까지의 후유장해에 대한 후유장해보험금이 지급된 것으"
    "로 보고 최종 후유장해 상태에 해당되는 후유장해보험금에서 이를 차감하여 지급합니"
    "다."
)

CLAUSE_ILLNESS_DEATH_2_9_TEXT = (
    "회사가 지급하여야 할 하나의 진단확정된 질병으로 인한 후유장해보험금은 보험가입금"
    "액을 한도로 합니다."
)

CLAUSE_ILLNESS_DEATH_3_TEXT = (
    "이 특별약관에 정하지 않은 사항은 보통약관을 따릅니다."
)


def run():
    """
    메리츠 2026년판 청크 1 시드 함수. Product/PolicyVersion을 최초 생성하고,
    페이지 35-42의 7개 특별약관을 Coverage/Clause로 시드한다.

    멱등성: 같은 policy_version_id + clause.text 조합이 이미 있으면 건너뜀.
    """
    db = SessionLocal()
    try:
        # ===== Product/PolicyVersion 생성 =====
        insurer = db.query(Insurer).filter_by(code="MERITZ").first()
        if not insurer:
            insurer = Insurer(
                name="메리츠화재해상보험",
                code="MERITZ",
                is_underwriter=True,
                official_url="https://www.meritzfire.com"
            )
            db.add(insurer)
            db.flush()

        product = db.query(Product).filter_by(insurer_id=insurer.insurer_id, product_code=PRODUCT_CODE).first()
        if not product:
            product = Product(
                insurer_id=insurer.insurer_id,
                name="다이렉트 해외여행보험",
                product_code=PRODUCT_CODE,
                channel="다이렉트",
                sale_start=None,
                sale_end=None,
                collected_at=COLLECTED_AT,
                review_status="raw",
            )
            db.add(product)
            db.flush()

        policy_version = db.query(PolicyVersion).filter_by(product_id=product.product_id, version_label=VERSION_LABEL).first()
        if not policy_version:
            policy_version = PolicyVersion(
                product_id=product.product_id,
                version_label=VERSION_LABEL,
                effective_date=None,
                approval_no=None,
                source_url=None,
                file_hash=FILE_HASH,
            )
            db.add(policy_version)
            db.flush()

        pv_id = policy_version.policy_version_id

        # 이 청크가 이미 시드됐으면(Coverage 생성이 idempotent하지 않으므로) 통째로 건너뛴다.
        if db.query(Coverage).filter_by(policy_version_id=pv_id, raw_name="상해 사망·후유장해 부보장 특별약관").first():
            print("메리츠 2026년판 청크 1: 이미 시드됨, 건너뜀.")
            db.commit()
            return

        # ===== 특별약관 1: 상해 사망·후유장해 부보장 =====
        cov_std_death = get_or_create_coverage_std(
            db, "DEATH_INJURY", "상해사망·후유장해", "상해", is_base=True
        )

        cov1 = Coverage(
            policy_version_id=pv_id,
            coverage_std_id=cov_std_death.coverage_std_id,
            raw_name="상해 사망·후유장해 부보장 특별약관",
            definition=None,
            limit_amount=None,
            deductible=None,
            waiting_condition=None,
        )
        db.add(cov1)
        db.flush()

        # 제1조 조항 (면책)
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov1.coverage_id,
            clause_type="면책",
            article_no="[상해 사망·후유장해 부보장 특별약관] 제1조",
            text=CLAUSE_INJURY_DEATH_EXCL_1_1_TEXT,
            page_ref="p.35",
            default_color="빨강",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # 제2조 조항 (준용규정)
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov1.coverage_id,
            clause_type="공통",
            article_no="[상해 사망·후유장해 부보장 특별약관] 제2조",
            text=CLAUSE_INJURY_DEATH_EXCL_1_2_TEXT,
            page_ref="p.36",
            default_color="회색",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # ===== 특별약관 2: 상해 사망 부보장 =====
        cov2 = Coverage(
            policy_version_id=pv_id,
            coverage_std_id=cov_std_death.coverage_std_id,
            raw_name="상해 사망 부보장 특별약관",
            definition=None,
            limit_amount=None,
            deductible=None,
            waiting_condition=None,
        )
        db.add(cov2)
        db.flush()

        # 제1조 조항
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov2.coverage_id,
            clause_type="면책",
            article_no="[상해 사망 부보장 특별약관] 제1조",
            text=CLAUSE_INJURY_DEATH_ONLY_EXCL_1_1_TEXT,
            page_ref="p.36",
            default_color="빨강",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # 제2조 조항
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov2.coverage_id,
            clause_type="공통",
            article_no="[상해 사망 부보장 특별약관] 제2조",
            text=CLAUSE_INJURY_DEATH_ONLY_EXCL_1_2_TEXT,
            page_ref="p.36",
            default_color="회색",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # ===== 특별약관 3: 상해 후유장해 부보장 =====
        cov3 = Coverage(
            policy_version_id=pv_id,
            coverage_std_id=cov_std_death.coverage_std_id,
            raw_name="상해 후유장해 부보장 특별약관",
            definition=None,
            limit_amount=None,
            deductible=None,
            waiting_condition=None,
        )
        db.add(cov3)
        db.flush()

        # 제1조 조항
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov3.coverage_id,
            clause_type="면책",
            article_no="[상해 후유장해 부보장 특별약관] 제1조",
            text=CLAUSE_INJURY_DISABILITY_EXCL_1_1_TEXT,
            page_ref="p.37",
            default_color="빨강",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # 제2조 조항
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov3.coverage_id,
            clause_type="공통",
            article_no="[상해 후유장해 부보장 특별약관] 제2조",
            text=CLAUSE_INJURY_DISABILITY_EXCL_1_2_TEXT,
            page_ref="p.37",
            default_color="회색",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # ===== 특별약관 4: 해외여행중 상해50%이상고도후유장해 =====
        cov4 = Coverage(
            policy_version_id=pv_id,
            coverage_std_id=cov_std_death.coverage_std_id,
            raw_name="해외여행중 상해50%이상고도후유장해 특별약관",
            definition=None,
            limit_amount=None,
            deductible=None,
            waiting_condition="50%이상 고도의 장해상태",
        )
        db.add(cov4)
        db.flush()

        # 제1조 조항 (보장정의)
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov4.coverage_id,
            clause_type="보장정의",
            article_no="[해외여행중 상해50%이상고도후유장해 특별약관] 제1조",
            text=CLAUSE_INJURY_DISABILITY_50_1_1_TEXT,
            page_ref="p.38",
            default_color="파랑",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # 제2조 조항
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov4.coverage_id,
            clause_type="공통",
            article_no="[해외여행중 상해50%이상고도후유장해 특별약관] 제2조",
            text=CLAUSE_INJURY_DISABILITY_50_1_2_TEXT,
            page_ref="p.38",
            default_color="회색",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # ===== 특별약관 5: 해외여행중 상해80%이상고도후유장해 =====
        cov5 = Coverage(
            policy_version_id=pv_id,
            coverage_std_id=cov_std_death.coverage_std_id,
            raw_name="해외여행중 상해80%이상고도후유장해 특별약관",
            definition=None,
            limit_amount=None,
            deductible=None,
            waiting_condition="80%이상 고도의 장해상태",
        )
        db.add(cov5)
        db.flush()

        # 제1조 조항
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov5.coverage_id,
            clause_type="보장정의",
            article_no="[해외여행중 상해80%이상고도후유장해 특별약관] 제1조",
            text=CLAUSE_INJURY_DISABILITY_80_1_1_TEXT,
            page_ref="p.39",
            default_color="파랑",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # 제2조 조항
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov5.coverage_id,
            clause_type="공통",
            article_no="[해외여행중 상해80%이상고도후유장해 특별약관] 제2조",
            text=CLAUSE_INJURY_DISABILITY_80_1_2_TEXT,
            page_ref="p.39",
            default_color="회색",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # ===== 특별약관 6: 해외여행중 상해100%고도후유장해 =====
        cov6 = Coverage(
            policy_version_id=pv_id,
            coverage_std_id=cov_std_death.coverage_std_id,
            raw_name="해외여행중 상해100%고도후유장해 특별약관",
            definition=None,
            limit_amount=None,
            deductible=None,
            waiting_condition="100% 고도의 장해상태",
        )
        db.add(cov6)
        db.flush()

        # 제1조 조항
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov6.coverage_id,
            clause_type="보장정의",
            article_no="[해외여행중 상해100%고도후유장해 특별약관] 제1조",
            text=CLAUSE_INJURY_DISABILITY_100_1_1_TEXT,
            page_ref="p.40",
            default_color="파랑",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # 제2조 조항
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov6.coverage_id,
            clause_type="공통",
            article_no="[해외여행중 상해100%고도후유장해 특별약관] 제2조",
            text=CLAUSE_INJURY_DISABILITY_100_1_2_TEXT,
            page_ref="p.40",
            default_color="회색",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # ===== 특별약관 7: 질병사망 및 질병80%이상후유장해 =====
        cov_std_ill = get_or_create_coverage_std(
            db, "ILL_DEATH", "질병사망·고도후유장해", "질병", is_base=True
        )

        cov7 = Coverage(
            policy_version_id=pv_id,
            coverage_std_id=cov_std_ill.coverage_std_id,
            raw_name="질병사망 및 질병80%이상후유장해 특별약관",
            definition=None,
            limit_amount=None,
            deductible=None,
            waiting_condition=None,
        )
        db.add(cov7)
        db.flush()

        # 제1조 1항 도입부 (보장정의)
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov7.coverage_id,
            clause_type="보장정의",
            article_no="[질병사망 및 질병80%이상후유장해 특별약관] 제1조 ①",
            text=CLAUSE_ILLNESS_DEATH_1_1_TEXT,
            page_ref="p.41",
            default_color="파랑",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # 제1조 1항 1호
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov7.coverage_id,
            clause_type="보장정의",
            article_no="[질병사망 및 질병80%이상후유장해 특별약관] 제1조 ①-1호",
            text=CLAUSE_ILLNESS_DEATH_1_1_1_TEXT,
            page_ref="p.41",
            default_color="파랑",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # 제1조 1항 2호
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov7.coverage_id,
            clause_type="보장정의",
            article_no="[질병사망 및 질병80%이상후유장해 특별약관] 제1조 ①-2호",
            text=CLAUSE_ILLNESS_DEATH_1_1_2_TEXT,
            page_ref="p.41",
            default_color="파랑",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # 제1조 2항
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov7.coverage_id,
            clause_type="보장정의",
            article_no="[질병사망 및 질병80%이상후유장해 특별약관] 제1조 ②",
            text=CLAUSE_ILLNESS_DEATH_1_2_TEXT,
            page_ref="p.41",
            default_color="파랑",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # 제2조 1항 (연명의료)
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov7.coverage_id,
            clause_type="조건",
            article_no="[질병사망 및 질병80%이상후유장해 특별약관] 제2조 ①",
            text=CLAUSE_ILLNESS_DEATH_2_1_TEXT,
            page_ref="p.41",
            default_color="노랑",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # 제2조 2항 (180일 판정)
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov7.coverage_id,
            clause_type="조건",
            article_no="[질병사망 및 질병80%이상후유장해 특별약관] 제2조 ②",
            text=CLAUSE_ILLNESS_DEATH_2_2_TEXT,
            page_ref="p.42",
            default_color="노랑",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # 제2조 3항 (악화된 장해)
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov7.coverage_id,
            clause_type="조건",
            article_no="[질병사망 및 질병80%이상후유장해 특별약관] 제2조 ③",
            text=CLAUSE_ILLNESS_DEATH_2_3_TEXT,
            page_ref="p.42",
            default_color="노랑",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # 제2조 4항 (장해분류표 미해당)
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov7.coverage_id,
            clause_type="조건",
            article_no="[질병사망 및 질병80%이상후유장해 특별약관] 제2조 ④",
            text=CLAUSE_ILLNESS_DEATH_2_4_TEXT,
            page_ref="p.42",
            default_color="노랑",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # 제2조 5항 (분쟁 조정)
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov7.coverage_id,
            clause_type="조건",
            article_no="[질병사망 및 질병80%이상후유장해 특별약관] 제2조 ⑤",
            text=CLAUSE_ILLNESS_DEATH_2_5_TEXT,
            page_ref="p.42",
            default_color="노랑",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # 제2조 6항 (다중 장해)
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov7.coverage_id,
            clause_type="조건",
            article_no="[질병사망 및 질병80%이상후유장해 특별약관] 제2조 ⑥",
            text=CLAUSE_ILLNESS_DEATH_2_6_TEXT,
            page_ref="p.42",
            default_color="노랑",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # 제2조 7항 (반복 장해)
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov7.coverage_id,
            clause_type="조건",
            article_no="[질병사망 및 질병80%이상후유장해 특별약관] 제2조 ⑦",
            text=CLAUSE_ILLNESS_DEATH_2_7_TEXT,
            page_ref="p.42",
            default_color="노랑",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # 제2조 8항 (이미 지급된 장해)
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov7.coverage_id,
            clause_type="조건",
            article_no="[질병사망 및 질병80%이상후유장해 특별약관] 제2조 ⑧",
            text=CLAUSE_ILLNESS_DEATH_2_8_TEXT,
            page_ref="p.42",
            default_color="노랑",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # 제2조 9항 (지급 한도)
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov7.coverage_id,
            clause_type="조건",
            article_no="[질병사망 및 질병80%이상후유장해 특별약관] 제2조 ⑨",
            text=CLAUSE_ILLNESS_DEATH_2_9_TEXT,
            page_ref="p.42",
            default_color="노랑",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        # 제3조 (준용규정)
        clause = Clause(
            policy_version_id=pv_id,
            coverage_id=cov7.coverage_id,
            clause_type="공통",
            article_no="[질병사망 및 질병80%이상후유장해 특별약관] 제3조",
            text=CLAUSE_ILLNESS_DEATH_3_TEXT,
            page_ref="p.42",
            default_color="회색",
        )
        existing = db.query(Clause).filter_by(
            policy_version_id=pv_id, text=clause.text
        ).first()
        if not existing:
            db.add(clause)

        db.commit()
        print("메리츠 2026년판 청크 1 시드 완료.")
        print(f"- Product: {PRODUCT_CODE}")
        print(f"- PolicyVersion: {VERSION_LABEL}")
        print(f"- Coverage: 7개 (상해 사망·후유장해 부보장, 상해 사망 부보장, 상해 후유장해 부보장, 50%/80%/100% 고도후유장해, 질병사망·고도후유장해)")
        print(f"- Clause: 약 25개")

    finally:
        db.close()


if __name__ == "__main__":
    run()
