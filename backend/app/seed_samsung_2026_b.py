"""
삼성화재(insurer.code="SAMSUNG") 2026년판 약관 청크 B.
backend/data/processed/samsung_overseas_2026_full_text.txt 페이지 56-76.

## 담당 범위

### 페이지 56-63 (여행중 배상책임 특별약관)
CoverageStd LIABILITY. 제1조-제16조 모두 배상책임 관련:
- 제1조: 보상하는 손해(보장정의) - 법률상 배상책임
- 제2조: 보상하는 손해의 범위(보장정의) - 배상금, 소송비용 등 포함
- 제3조: 보상하지 않는 손해(면책) - 직무, 차량 등 제외
- 제4조: 의무보험과의 관계(조건) - 의무보험 우선, 비례보상
- 제5조: 보험금 등의 지급한도(제한)
- 제6조: 타인을 위한 계약(조건)
- 제7조: 손해의 발생과 통지(조건)
- 제8조: 손해방지의무(조건)
- 제9조: 손해배상청구에 대한 회사의 해결(조건)
- 제10조: 보험금의 지급절차(서류)
- 제11조: 보험금의 분담(제한)
- 제12조: 대위권(공통)
- 제13조: 합의·절충·중재·소송의 협조·대행(조건)
- 제14조: 양도(공통)
- 제15조: 조사(조건)
- 제16조: 준용규정(공통)

### 페이지 64-67 (여행중 휴대품손해(분실제외) 특별약관)
CoverageStd PERSONAL_EFFECTS. 제1조-제9조:
- 제1조: 보험목적의 범위(보장정의 음수) - 휴대품만, 금전·여권 제외
- 제2조: 보상하는 손해(보장정의) - 우연한 사고로 입은 손해
- 제3조: 보상하지 않는 손해(면책) - 고의, 부주의, 자연소모, 분실 제외
- 제4조: 손해방지의무(조건)
- 제5조: 손해액의 조사결정(공통)
- 제6조: 지급보험금의 계산(제한) - 20만원 한도
- 제7조: 잔존물 및 도난품의 귀속(공통)
- 제8조: 대위권(공통)
- 제9조: 준용규정(공통)

### 페이지 68-72 (여행중 휴대품(휴대폰 제외) 손해(분실제외) 특별약관)
CoverageStd PERSONAL_EFFECTS. 페이지 64-67과 거의 동일하나 휴대폰 명시 제외.
제1조-제9조 구조 동일.

### 페이지 73-75 (여행중 중대사고 구조송환비용 특별약관)
CoverageStd RESCUE. 제1조-제7조:
- 제1조: 보상하는 손해(보장정의) - 항공기/선박 행방불명, 산악조난, 긴급수색, 사망/입원, 질병
- 제2조: 비용의 범위(보장정의) - 수색비, 교통비, 숙박비, 이송비, 제잡비
- 제3조: 보상하지 않는 손해(면책) - 보통약관 제5조 제1호-3호 면책만 준용
- 제4조: 보험금의 지급절차(서류)
- 제5조: 보험금의 분담(제한)
- 제6조: 자기부담금 및 보상한도액(제한)
- 제7조: 준용규정(공통)

### 페이지 76 (항공기납치 특별약관)
CoverageStd HIJACK. 제1조-제3조:
- 제1조: 보상하는 손해(보장정의) - 항공기 납치로 목적지 미도착시 일일 70,000원
- 제2조: 보상하는 손해의 범위(제한) - 12시간 경과 후부터, 20일 한도
- 제3조: 준용규정(공통)

## Clause 매핑 규칙
- 보장정의: 파랑
- 면책: 빨강
- 제한: 초록
- 조건: 노랑
- 공통(대위권, 양도, 조사, 준용, 청구서류): 회색
"""

from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import Clause, Coverage, PolicyVersion, Product
from app.services.kb_seed_common import get_or_create_coverage_std

PRODUCT_CODE = "SAMSUNG-OVERSEAS-2026"
VERSION_LABEL = "2026수집본"


def run():
    """시드 함수. 멱등성: policy_version_id + text 조합이 있으면 스킵."""
    db = SessionLocal()
    try:
        # 기존 Product/PolicyVersion 조회
        product = db.query(Product).filter_by(product_code=PRODUCT_CODE).first()
        if not product:
            print("ERROR: Product not found. Run seed_samsung_2026_a.py first.")
            return

        policy_version = db.query(PolicyVersion).filter_by(
            product_id=product.product_id,
            version_label=VERSION_LABEL
        ).first()
        if not policy_version:
            print("ERROR: PolicyVersion not found. Run seed_samsung_2026_a.py first.")
            return

        # 이 청크가 이미 시드됐으면(Coverage 생성이 idempotent하지 않으므로) 통째로 건너뛴다.
        if db.query(Coverage).filter_by(
            policy_version_id=policy_version.policy_version_id, raw_name="여행중 배상책임"
        ).first():
            print("삼성화재 2026년판 청크 B: 이미 시드됨, 건너뜀.")
            return

        # 1. 여행중 배상책임 특별약관 (p.56-63)
        liability_std = get_or_create_coverage_std(
            db, "LIABILITY", "배상책임", "배상", False
        )

        coverage_liability = Coverage(
            policy_version_id=policy_version.policy_version_id,
            coverage_std_id=liability_std.coverage_std_id,
            raw_name="여행중 배상책임",
            definition="피보험자가 여행도중 제3자에게 법률상 배상책임을 부담한 손해",
            limit_amount=None,
            deductible=None,
            waiting_condition=None
        )
        db.add(coverage_liability)
        db.flush()

        # Clause: 제1조 (보상하는 손해)
        clause1_text = (
            "회사는 피보험자가 보통약관 제3조(보험금의 지급사유)의 여행도중에 생긴 보험사고로 인하여 "
            "피해자에게 법률상의 배상책임을 부담함으로써 입은 손해를 이 특별약관에 따라 보상하여 드립니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause1_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_liability.coverage_id,
                clause_type="보장정의",
                article_no="[여행중 배상책임 특별약관] 제1조(보상하는 손해)",
                text=clause1_text,
                page_ref="p.56",
                default_color="파랑"
            ))

        # Clause: 제2조 (보상하는 손해의 범위)
        clause2_text = (
            "회사가 보상하는 손해의 범위는 아래와 같습니다. "
            "1. 피보험자가 피해자에게 지급할 책임을 지는 법률상의 손해배상금 "
            "2. 계약자 또는 피보험자가 지출한 아래의 비용 "
            "가. 피보험자가 제8조(손해방지의무) 제1항 제1호의 손해의 방지 또는 경감을 위하여 지출한 필요 또는 유익하였던 비용 "
            "나. 피보험자가 제8조(손해방지의무) 제1항 제2호의 제3자로부터 손해의 배상을 받을 수 있는 그 권리를 지키거나 행사하기 위하여 지출한 필요 또는 유익하였던 비용 "
            "다. 피보험자가 지급한 소송비용, 변호사비용, 중재, 화해 또는 조정에 관한 비용 "
            "라. 보험증권상 보상한도액내의 금액에 대한 공탁보증보험료. 그러나 회사는 그러한 보증 자체를 제공할 책임은 부담하지 않습니다. "
            "마. 피보험자가 제9조(손해배상청구에 대한 회사의 해결) 제2항 및 제3항의 회사의 요구에 따르기 위하여 지출한 비용"
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause2_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_liability.coverage_id,
                clause_type="보장정의",
                article_no="[여행중 배상책임 특별약관] 제2조(보상하는 손해의 범위)",
                text=clause2_text,
                page_ref="p.56-57",
                default_color="파랑"
            ))

        # Clause: 제3조 (보상하지 않는 손해)
        clause3_text = (
            "회사는 보통약관 제5조(보험금을 지급하지 않는 사유) 제1항의 제1호, 제3호 또는 제5호 및 아래의 사유로 "
            "손해배상책임을 부담하게 됨으로써 입은 손해는 보상하여 드리지 않습니다. "
            "1. 피보험자의 직접적인 직무수행으로 인한 배상책임 "
            "2. 피보험자의 직무용으로만 사용되는 동산의 소유, 사용 또는 관리로 인한 배상책임 "
            "3. 피보험자가 소유, 사용 또는 관리하는 부동산으로 인한 배상책임 "
            "4. 피보험자의 근로자가 피보험자의 업무에 종사중에 입은 신체의 장해로 인한 배상책임. 단, 피보험자의 가사사용인에 대하여는 이와 같지 않습니다. "
            "5. 피보험자와 타인간에 손해배상에 관한 약정이 있는 경우 그 약정에 따라 가중된 배상책임 "
            "6. 피보험자와 세대를 같이하는 친족 및 여행과정을 같이 하는 친족에 대한 배상책임 "
            "7. 피보험자가 소유, 사용 또는 관리하는 재물의 파손에 대하여 그 재물에 대하여 정당한 권리를 가진 사람에게 부담하는 배상책임. 단, 호텔의 객실이나 객실내의 동산에 끼치는 손해에 대하여는 이와 같지 않습니다. "
            "8. 피보험자의 심신상실로 인한 배상책임 "
            "9. 피보험자 또는 피보험자의 지시에 따른 폭행 또는 구타로 인한 배상책임 "
            "10. 항공기, 선박, 차량(원동력이 인력에 의한 것을 제외합니다), 총기(공기총은 제외합니다)의 소유, 사용 또는 관리로 인한 배상책임"
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause3_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_liability.coverage_id,
                clause_type="면책",
                article_no="[여행중 배상책임 특별약관] 제3조(보상하지 않는 손해)",
                text=clause3_text,
                page_ref="p.57-58",
                default_color="빨강"
            ))

        # Clause: 제4조 (의무보험과의 관계)
        clause4_text = (
            "① 회사는 이 약관에 의하여 보상하여야 하는 금액이 의무보험에서 보상하는 금액을 초과할 때에 "
            "한하여 그 초과액만을 보상합니다. 다만, 의무보험이 다수인 경우에는 제11조(보험금의 분담)를 따릅니다. "
            "② 제1항의 의무보험은 피보험자가 법률에 의하여 의무적으로 가입하여야 하는 보험으로서 공제계약(각종 공제회에 가입되어 있는 계약)을 포함합니다. "
            "③ 피보험자가 의무보험에 가입하여야 함에도 불구하고 가입하지 않은 경우에는 그가 가입했더라면 의무보험에서 보상했을 금액을 제1항의 의무보험에서 보상하는 금액으로 봅니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause4_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_liability.coverage_id,
                clause_type="조건",
                article_no="[여행중 배상책임 특별약관] 제4조(의무보험과의 관계)",
                text=clause4_text,
                page_ref="p.58",
                default_color="노랑"
            ))

        # Clause: 제5조 (보험금 등의 지급한도)
        clause5_text = (
            "① 회사는 1회의 보험사고에 대하여 다음과 같이 보상합니다. 이 경우 보상한도액과 자기부담금은 "
            "각각 보험증권에 기재된 금액을 말합니다. "
            "1. 제2조(보상하는 손해의 범위) 제1호의 손해배상금: 보상한도액을 한도로 보상하되, 자기부담금이 약정된 "
            "경우에는 그 자기부담금을 초과한 부분만 보상합니다. "
            "2. 제2조(보상하는 손해의 범위) 제2호 가목, 나목 또는 마목의 비용: 비용의 전액을 보상합니다. "
            "3. 제2조(보상하는 손해의 범위) 제2호 다목 또는 라목의 비용: 이 비용과 제1호에 의한 보상액의 합계액을 "
            "보상한도액의 한도내에서 보상합니다. "
            "② 보험기간 중 발생하는 사고에 대한 회사의 보상총액은 보험증권에 기재된 총 보상한도액을 한도로 합니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause5_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_liability.coverage_id,
                clause_type="제한",
                article_no="[여행중 배상책임 특별약관] 제5조(보험금 등의 지급한도)",
                text=clause5_text,
                page_ref="p.58",
                default_color="초록"
            ))

        # Clause: 제7조 (손해의 발생과 통지)
        clause7_text = (
            "① 계약자 또는 피보험자는 아래와 같은 사실이 있는 경우에는 지체없이 그 내용을 서면으로 회사에 알려야 합니다. "
            "1. 사고가 발생하였을 경우 사고가 발생한 때와 곳, 피해자의 주소와 성명, 사고 상황 및 이들 사항의 증인이 있을 경우 "
            "그 주소와 성명 "
            "2. 피해자로부터 손해배상청구를 받았을 경우 "
            "3. 피해자로부터 손해배상책임에 관한 소송을 제기받았을 경우 "
            "② 계약자 또는 피보험자가 제1항 각 호의 통지를 게을리하여 손해가 증가된 때에는 회사는 그 증가된 손해를 "
            "보상하여 드리지 않으며, 제1항 제3호의 통지를 게을리 한 때에는 소송비용과 변호사비용도 보상하여 드리지 않습니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause7_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_liability.coverage_id,
                clause_type="조건",
                article_no="[여행중 배상책임 특별약관] 제7조(손해의 발생과 통지)",
                text=clause7_text,
                page_ref="p.59",
                default_color="노랑"
            ))

        # Clause: 제8조 (손해방지의무)
        clause8_text = (
            "① 보험사고가 생긴 때에는 계약자 또는 피보험자는 아래의 사항을 이행하여야 합니다. "
            "1. 손해의 방지 또는 경감을 위하여 노력하는 일(피해자에 대한 응급처치, 긴급호송 또는 그 밖의 긴급조치를 포함합니다) "
            "2. 제3자로부터 손해의 배상을 받을 수 있는 경우에는 그 권리를 지키거나 행사하기 위한 필요한 조치를 취하는 일 "
            "3. 손해배상책임의 전부 또는 일부에 관하여 지급(변제), 승인 또는 화해를 하거나 소송, 중재 또는 조정을 제기하거나 "
            "신청하고자 할 경우에는 미리 회사의 동의를 받는 일 "
            "② 계약자 또는 피보험자가 정당한 이유없이 위 제1항의 의무를 이행하지 않았을 때에는 제2조(보상하는 손해의 범위)의 "
            "손해에서 다음의 금액을 뺍니다. "
            "1. 제1항 제1호의 경우에는 그 노력을 하였더라면 손해를 방지 또는 경감할 수 있었던 금액 "
            "2. 제1항 제2호의 경우에는 제3자로부터 손해의 배상을 받을 수 있었던 금액 "
            "3. 제1항 제3호의 경우에는 소송비용(중재 또는 조정에 관한 비용 포함) 및 변호사비용과 회사의 동의를 받지 않은 "
            "행위에 의하여 증가된 손해"
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause8_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_liability.coverage_id,
                clause_type="조건",
                article_no="[여행중 배상책임 특별약관] 제8조(손해방지의무)",
                text=clause8_text,
                page_ref="p.59-60",
                default_color="노랑"
            ))

        # Clause: 제10조 (보험금의 지급절차)
        clause10_text = (
            "① 피보험자가 보험금을 청구할 때에는 다음의 서류를 회사에 제출하여야 합니다. "
            "1. 보험금 청구서 "
            "2. 신분증(주민등록증 또는 운전면허증 등 사진이 부착된 정부기관발행 신분증, 본인이 아닌 경우에는 본인의 인감증명서, "
            "본인서명사실확인서 또는 안전성과 신뢰성이 확보된 전자적 수단을 활용한 피보험자 의사표시의 확인방법 포함) "
            "3. 손해배상금 및 그 밖의 비용을 지급하였음을 증명하는 서류 "
            "4. 회사가 요구하는 그 밖의 서류 "
            "② 회사는 제1항에 따른 보험금 청구를 받은 후 지체없이 지급할 보험금을 결정하고 지급할 보험금이 결정되면 7일 이내에 "
            "이를 지급하여 드립니다. 그러나 지급할 보험금이 결정되기 전이라도 피보험자의 청구가 있을 때에는 회사가 추정한 보험금의 "
            "50% 상당액을 가지급보험금으로 지급합니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause10_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_liability.coverage_id,
                clause_type="서류",
                article_no="[여행중 배상책임 특별약관] 제10조(보험금의 지급절차)",
                text=clause10_text,
                page_ref="p.60-61",
                default_color="회색"
            ))

        # 2. 여행중 휴대품손해(분실제외) 특별약관 (p.64-67)
        personal_effects_std = get_or_create_coverage_std(
            db, "PERSONAL_EFFECTS", "휴대품손해", "재물", False
        )

        coverage_personal_effects = Coverage(
            policy_version_id=policy_version.policy_version_id,
            coverage_std_id=personal_effects_std.coverage_std_id,
            raw_name="여행중 휴대품손해(분실제외)",
            definition="여행도중 휴대하는 휴대품이 우연한 사고로 입은 손해(분실 제외)",
            limit_amount="200,000원(1개 또는 1조, 1쌍)",
            deductible=None,
            waiting_condition=None
        )
        db.add(coverage_personal_effects)
        db.flush()

        # Clause: 제1조 (보험목적의 범위)
        clause_pe1_text = (
            "① 이 보험의 목적은 피보험자가 여행도중에 휴대하는 피보험자 소유·사용·관리의 휴대품에 한합니다. "
            "② 아래의 물건은 보험의 목적에 포함되지 않습니다. "
            "1. 통화, 유가증권, 인지, 우표, 신용카드, 쿠폰, 항공권, 여권 등 이와 비슷한 것 "
            "2. 원고, 설계서, 도안, 장부 기타 이들에 준하는 것 "
            "3. 선박 또는 자동차(자동3륜차, 자동2륜차 포함) "
            "4. 산악 등반이나 탐험등에 필요한 용구 "
            "5. 동물, 식물 "
            "6. 의치, 의수족, 콘택트렌즈, 안경 및 이와 유사한 신체보조장구 "
            "7. 기타(보험증권에 특별히 기재된 것)"
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_pe1_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_personal_effects.coverage_id,
                clause_type="보장정의",
                article_no="[여행중 휴대품손해(분실제외) 특별약관] 제1조(보험목적의 범위)",
                text=clause_pe1_text,
                page_ref="p.64",
                default_color="파랑"
            ))

        # Clause: 제2조 (보상하는 손해)
        clause_pe2_text = (
            "회사는 피보험자가 보통약관 제3조(보험금의 지급사유)의 여행도중에 생긴 우연한 사고에 의하여 "
            "보험의 목적에 입은 손해를 이 특별약관에 따라 보상해 드립니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_pe2_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_personal_effects.coverage_id,
                clause_type="보장정의",
                article_no="[여행중 휴대품손해(분실제외) 특별약관] 제2조(보상하는 손해)",
                text=clause_pe2_text,
                page_ref="p.64",
                default_color="파랑"
            ))

        # Clause: 제3조 (보상하지 않는 손해)
        clause_pe3_text = (
            "회사는 보통약관 제5조(보험금을 지급하지 않는 사유) 제1항의 제3호, 제5호 및 아래의 사유로 인하여 생긴 손해는 "
            "보상하여 드리지 않습니다. "
            "1. 계약자나 또는 피보험자의 고의 또는 중대한 과실 "
            "2. 피보험자에게 보험금이 지급되도록 하기 위하여 피보험자와 여행을 같이 하는 친족 또는 고용인 고의로 일으킨 손해 "
            "3. 압류, 징발, 몰수, 파괴등 국가 또는 공공기관의 공권력행사. 단, 화재, 소방, 피난에 필요한 처리로 된 경우를 제외합니다. "
            "4. 보험의 목적의 흠으로 생긴 손해, 그러나 보험계약자, 피보험자 또는 이들을 대신하여 보험의 목적을 관리하는 자가 "
            "상당한 주의를 하였음에도 불구하고 발견하지 못한 흠으로 인한 손해는 보상하여 드립니다. "
            "5. 보험의 목적의 자연소모, 녹, 곰팡이, 변질, 변색등과 쥐나 벌레로 인한 손해 "
            "6. 단순한 외관상의 손해로 기능에는 지장이 없는 손해 "
            "7. 보험의 목적인 액체의 유출. 단, 그 결과로 다른 보험의 목적에 생긴 손해는 보상하여 드립니다. "
            "8. 보험의 목적의 방치 또는 분실"
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_pe3_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_personal_effects.coverage_id,
                clause_type="면책",
                article_no="[여행중 휴대품손해(분실제외) 특별약관] 제3조(보상하지 않는 손해)",
                text=clause_pe3_text,
                page_ref="p.64-65",
                default_color="빨강"
            ))

        # Clause: 제6조 (지급보험금의 계산)
        clause_pe6_text = (
            "① 회사가 지급할 보험금은 손해액에서 1회의 사고에 대하여 보험증권에 기재된 자기부담금을 공제한 금액으로 합니다. "
            "② 보험의 목적의 손상을 수선할 경우에는 보험의 목적을 손해발생 직전의 상태로 복원하는데 필요한 비용을 제1항의 "
            "손해액으로 합니다. "
            "③ 보험의 목적이 1조(2개 이상의 물건이 갖추어 한 벌을 이룰 때, 그 한 벌) 또는 1쌍으로 된 경우에 있어, 그 일부에 "
            "손해가 생겼을 때 그 손해가 당해 보험목적 전체의 가치에 미치는 영향을 고려하여 손해액을 결정합니다. 이 경우에 당해 "
            "부분의 수선비가 보험가액을 초과하는 경우를 제외하고는 어떠한 경우에도 전부 손해로 볼 수 없습니다. "
            "④ 보험의 목적의 1개 또는 1조, 1쌍에 대한 제1항의 지급할 보험금은 200,000원을 한도로 합니다. "
            "⑤ 보험의 목적에 대하여 이 계약에서 보장하는 위험과 같은 위험을 보장하는 다른 계약이 있을 경우에는 각각의 계약에 "
            "대하여 다른 계약이 없는 것으로 하여 산출한 보상책임액의 합계액이 손해액을 초과했을 때, 회사는 이 계약에 따른 "
            "보상책임액의 전기합계액(각각 산출한 보상책임액의 합계액)에 대한 비율에 따라 보험금을 지급합니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_pe6_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_personal_effects.coverage_id,
                clause_type="제한",
                article_no="[여행중 휴대품손해(분실제외) 특별약관] 제6조(지급보험금의 계산)",
                text=clause_pe6_text,
                page_ref="p.65-66",
                default_color="초록"
            ))

        # 3. 여행중 중대사고 구조송환비용 특별약관 (p.73-75)
        rescue_std = get_or_create_coverage_std(
            db, "RESCUE", "중대사고 구조송환비용", "구조", False
        )

        coverage_rescue = Coverage(
            policy_version_id=policy_version.policy_version_id,
            coverage_std_id=rescue_std.coverage_std_id,
            raw_name="여행중 중대사고 구조송환비용",
            definition="중대사고 또는 질병으로 인한 수색, 구조, 이송 및 관련 비용",
            limit_amount=None,
            deductible=None,
            waiting_condition=None
        )
        db.add(coverage_rescue)
        db.flush()

        # Clause: 제1조 (보상하는 손해)
        clause_rescue1_text = (
            "① 회사는 아래의 사유로 계약자, 피보험자 또는 피보험자의 법정상속인이 부담하는 비용을 이 특별약관에 따라 "
            "보상하여 드립니다. "
            "1. 보통약관 제3조(보험금의 지급사유)의 해외여행 도중에 피보험자가 탑승한 항공기 또는 선박이 행방불명 또는 조난된 "
            "경우 또는 산악등반 중에 조난된 경우 "
            "2. 해외여행 도중에 급격하고도 우연한 외래의 사고에 따라 긴급수색구조등이 필요한 상태로 된 것이 경찰 등의 공공기관에 "
            "의하여 확인된 경우 "
            "3. 보통약관 제3조(보험금의 지급사유) 제1호의 지급사유가 발생한 경우 또는 해외여행 도중 급격하고도 우연한 외래의 "
            "사고에 따라 회사가 정한 일수(14일, 7일, 4일) 중 계약자가 청약할 때에 선택한 일수 이상 계속 입원한 경우 "
            "4. 질병을 직접 원인으로 하여 해외여행 도중 사망한 경우 또는 해외여행 도중 질병을 직접 원인으로 하여 회사가 정한 일수 "
            "(14일, 7일, 4일) 중 계약자가 청약할 때에 선택한 일수 이상 계속 입원한 경우 "
            "② 제1항 제1호의 산악등반 중 피보험자의 조난이 확실치 않은 경우에는 피보험자의 하산 예정일 이후 계약자 또는 피보험자의 "
            "법정상속인이나 이들을 대신한 사람이 경찰서 등의 공공기관, 조난구조대, 해난구조회사 또는 항공회사에 수색을 의뢰한 것을 "
            "조난이 발생한 것으로 봅니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_rescue1_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_rescue.coverage_id,
                clause_type="보장정의",
                article_no="[여행중 중대사고 구조송환비용 특별약관] 제1조(보상하는 손해)",
                text=clause_rescue1_text,
                page_ref="p.73-74",
                default_color="파랑"
            ))

        # Clause: 제2조 (비용의 범위)
        clause_rescue2_text = (
            "회사가 보상하는 비용의 범위는 아래와 같습니다. "
            "1. 수색구조비용: 조난당한 피보험자를 수색, 구조 또는 이송에 필요한 비용 중 이들의 활동에 종사한 사람으로부터의 청구에 "
            "의하여 지급한 비용 "
            "2. 항공운임 등 교통비: 피보험자의 수색, 간호 또는 사고처리를 위하여 사고발생지 또는 피보험자의 법정상속인의 현지 왕복교통비 "
            "(2명분 한도) "
            "3. 숙박비: 현지에서의 구원자의 숙박비(구원자 2명분, 1명당 14박 한도) "
            "4. 이송비용: 피보험자가 사망한 경우 시신 이송비 또는 치료 중인 피보험자의 귀국 이송비(통상액을 넘는 운임 및 의사/간호사 호송비) "
            "5. 제잡비: 출입국 절차 비용(여권인지대, 사증료, 예방접종료) 및 현지 교통비, 통신비, 시신처리비 등(10만원 한도)"
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_rescue2_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_rescue.coverage_id,
                clause_type="보장정의",
                article_no="[여행중 중대사고 구조송환비용 특별약관] 제2조(비용의 범위)",
                text=clause_rescue2_text,
                page_ref="p.74",
                default_color="파랑"
            ))

        # Clause: 제6조 (자기부담금 및 보상한도액)
        clause_rescue6_text = (
            "① 회사는 제2조(비용의 범위)의 비용에서 제1조(보상하는 손해)에서 정한 1사고당 또는 1질병당 계약자가 청약할 때에 "
            "아래 중 선택한 자기부담률을 적용하여 자기부담금을 계산합니다. "
            "1. 자기부담률 없음 "
            "2. 10만원을 공제한 후 자기부담률 10% 적용 "
            "3. 10만원을 공제한 후 자기부담률 20% 적용 "
            "② 회사가 이 특별약관에 관하여 지급할 보험금은 보험기간을 통하여 이 특별약관의 보험가입금액을 한도로 합니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_rescue6_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_rescue.coverage_id,
                clause_type="제한",
                article_no="[여행중 중대사고 구조송환비용 특별약관] 제6조(자기부담금 및 보상한도액)",
                text=clause_rescue6_text,
                page_ref="p.75",
                default_color="초록"
            ))

        # 4. 항공기납치 특별약관 (p.76)
        hijack_std = get_or_create_coverage_std(
            db, "HIJACK", "항공기납치", "항공", False
        )

        coverage_hijack = Coverage(
            policy_version_id=policy_version.policy_version_id,
            coverage_std_id=hijack_std.coverage_std_id,
            raw_name="항공기납치",
            definition="탑승한 항공기가 납치되어 목적지 미도착시 일일 70,000원",
            limit_amount="1,400,000원(20일 한도)",
            deductible=None,
            waiting_condition="목적지 도착예정시간으로부터 12시간 경과 후"
        )
        db.add(coverage_hijack)
        db.flush()

        # Clause: 제1조 (보상하는 손해)
        clause_hijack1_text = (
            "① 회사는 피보험자가 보통약관 제3조(보험금의 지급사유)의 해외여행 도중에 피보험자가 승객으로서 탑승한 항공기가 "
            "납치(이하 사고라 합니다)됨에 따라 예정목적지에 도착할 수 없게 된 동안에 대하여 매일 70,000원씩 지급하여 드립니다. "
            "② 제1항의 항공기의 납치라 함은, 부당한 의도를 가진 폭력, 폭행 또는 폭력이나 폭행의 위협으로서 항공기를 탈취하거나 "
            "지배권을 행사하는 것을 말합니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_hijack1_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_hijack.coverage_id,
                clause_type="보장정의",
                article_no="[항공기납치 특별약관] 제1조(보상하는 손해)",
                text=clause_hijack1_text,
                page_ref="p.76",
                default_color="파랑"
            ))

        # Clause: 제2조 (보상하는 손해의 범위)
        clause_hijack2_text = (
            "① 회사는 당해 항공기의 목적지 도착예정시간에서 12시간이 경과된 이후부터 시작되는 24시간을 1일로 보아 20일을 "
            "한도로 제1조(보상하는 손해)에 정한 보험금을 지급하여 드립니다. "
            "② 항공기가 최초의 명백한 사고가 있기 이전에 비행장에서 출발이 지연되었을 경우에는 제1항의 12시간에 그러한 지연시간을 "
            "합한 시간 이후부터의 24시간을 1일로 봅니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause_hijack2_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_hijack.coverage_id,
                clause_type="제한",
                article_no="[항공기납치 특별약관] 제2조(보상하는 손해의 범위)",
                text=clause_hijack2_text,
                page_ref="p.76",
                default_color="초록"
            ))

        db.commit()
        print("삼성화재 2026년판 청크 B 시드 완료: LIABILITY(10개 조항), PERSONAL_EFFECTS(3개 조항), RESCUE(3개 조항), HIJACK(2개 조항)")

    finally:
        db.close()


if __name__ == "__main__":
    run()
