"""
KB해외여행보험 2026년판 청크 A (p.1-88)

원문 출처: backend/data/processed/kb_overseas_26-15505-1_full_text.txt (페이지 1-88)
- 페이지 1-2: 표지 및 상품정보
- 페이지 3-9: 안내사항 및 고객정보 취급방침 (순수 계약행정, 무관)
- 페이지 10-13: 목차 및 가입자 유의사항
- 페이지 14-88: 보통약관 제1관~제7관 (제3조, 제5조 등 기본 사망/후유장해 조항)

## 보통약관에서 DEATH_INJURY로 매핑되는 조항
- 제3조(보험금의 지급사유) — 상해 사망/후유장해 보장정의
- 제4조(보험금 지급에 관한 세부규정) — 상해 판정 기준 및 지급 방법
- 제5조(보험금을 지급하지 않는 사유) — 상해 관련 면책사유 (고의·질병·임신·전쟁·운동위험 등)

## 확인함/무관으로 건너뜀 (순수 계약행정)
- 페이지 3-9: 개인신용정보 안내, 고객정보취급방침 (행정)
- 제1관 제1조(목적), 제2조(용어의 정의) — 정의만 있고 보장과 무관
- 제2관 나머지: 제6조(통지), 제7조(청구절차), 제8조(지급절차), 제9조(지급방법 변경),
  제10조(주소변경), 제11조(보험수익자 지정), 제12조(대표자 지정) — 모두 청구행정
- 제3관 제13조~제16조 — 계약 전후 알릴 의무, 사기, 무효 (계약행정)
- 제4관 제17조~제23조 — 계약 성립, 청약철회, 계약변경, 나이, 소멸 (계약관리)
- 제5관 제24조~제28조 — 보험료 납입, 연체, 부활 (계약행정)
- 제6관 제29조~제32조 — 계약 해지, 환급 (계약행정)
- 제7관 제33조~제41조 — 분쟁조정, 관할법원, 소멸시효, 약관해석 (소송/행정)

## Product/PolicyVersion 생성
PRODUCT_CODE = "KB-OVERSEAS-2026"
VERSION_LABEL = "일반26-15505-1"
Product: insurer.code="KB", name="KB해외여행보험(다이렉트)", channel="다이렉트", review_status="raw"
PolicyVersion: version_label=VERSION_LABEL, effective_date=None, approval_no="일반26-15505-1",
  source_url=None, file_hash="49a5ccecdb5cffe5bcf730efedf13322e0719cff8261aebcf47b724cc064e573"

멱등성: Insurer/Product/PolicyVersion은 code/product_code로 조회해서 이미 있으면 건너뛴다.
Coverage는 policy_version_id+raw_name, Clause는 (policy_version_id+coverage_id+article_no+text) 조합으로
이미 있으면 건너뛴다.
"""
from datetime import date
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Clause, Coverage, Insurer, PolicyVersion, Product, CoverageStd,
)
from app.services.kb_seed_common import get_or_create_coverage_std

PRODUCT_CODE = "KB-OVERSEAS-2026"
VERSION_LABEL = "일반26-15505-1"
FILE_HASH = "49a5ccecdb5cffe5bcf730efedf13322e0719cff8261aebcf47b724cc064e573"


def run():
    db = SessionLocal()
    try:
        # Insurer 조회 또는 생성
        insurer = db.query(Insurer).filter_by(code="KB").first()
        if not insurer:
            insurer = Insurer(
                name="KB손해보험",
                code="KB",
                is_underwriter=True,
                official_url="http://www.kbinsure.co.kr"
            )
            db.add(insurer)
            db.flush()

        # Product 조회 또는 생성
        product = db.query(Product).filter(
            Product.insurer_id == insurer.insurer_id,
            Product.product_code == PRODUCT_CODE
        ).first()
        if not product:
            product = Product(
                insurer_id=insurer.insurer_id,
                name="KB해외여행보험(다이렉트)",
                product_code=PRODUCT_CODE,
                channel="다이렉트",
                sale_start=None,
                sale_end=None,
                collected_at=date(2026, 6, 1),
                review_status="raw",
            )
            db.add(product)
            db.flush()

        # PolicyVersion 조회 또는 생성
        pv = db.query(PolicyVersion).filter(
            PolicyVersion.product_id == product.product_id,
            PolicyVersion.version_label == VERSION_LABEL
        ).first()
        if not pv:
            pv = PolicyVersion(
                product_id=product.product_id,
                version_label=VERSION_LABEL,
                effective_date=None,
                approval_no="일반26-15505-1",
                source_url=None,
                file_hash=FILE_HASH,
            )
            db.add(pv)
            db.flush()

        # CoverageStd: DEATH_INJURY 재사용
        coverage_std = get_or_create_coverage_std(
            db, "DEATH_INJURY", "상해사망·후유장해", "상해", True
        )

        # ===== 보통약관 제3조(보험금의 지급사유) =====
        clause3_text = (
            "회사는 피보험자가 보험증권에 기재된 해외여행을 목적으로 주거지를 출발하여 "
            "여행을 마치고 주거지에 도착할 때까지의 여행 도중에 다음 중 어느 하나의 사유가 "
            "발생한 경우에는 보험수익자에게 약정한 보험금을 지급합니다.\n"
            "1. 보험기간 중에 상해의 직접결과로써 사망한 경우(질병으로 인한 사망은 제외합니다): 사망보험금\n"
            "2. 보험기간 중 상해로 장해분류표(<별표1> 참조)에서 정한 각 장해지급률에 해당하는 장해상태가 "
            "되었을 때: 후유장해보험금(장해분류표에서 정한 지급률을 보험가입금액에 곱하여 산출한 금액)"
        )
        existing = db.query(Clause).filter(
            Clause.policy_version_id == pv.policy_version_id,
            Clause.coverage_id == None,  # 보통약관은 coverage 없음 (base)
            Clause.article_no == "제3조(보험금의 지급사유)",
            Clause.text == clause3_text
        ).first()
        if not existing:
            db.add(Clause(
                policy_version_id=pv.policy_version_id,
                coverage_id=None,  # 보통약관 기본
                clause_type="보장정의",
                article_no="제3조(보험금의 지급사유)",
                text=clause3_text,
                page_ref="p.26",
                default_color="파랑",
            ))

        # ===== 보통약관 제4조(보험금 지급에 관한 세부규정) =====
        clause4_text = (
            "① 제3조(보험금의 지급사유) 제1호 '사망'에는 보험기간에 다음 어느 하나의 사유가 발생한 경우를 포함합니다.\n"
            "1. 실종선고를 받은 경우: 법원에서 인정한 실종기간이 끝나는 때에 사망한 것으로 봅니다.\n"
            "2. 관공서에서 수해, 화재나 그 밖의 재난을 조사하고 사망한 것으로 통보하는 경우: 가족관계등록부에 기재된 사망연월일을 기준으로 합니다.\n"
            "② 「호스피스·완화의료 및 임종과정에 있는 환자의 연명의료 결정에 관한 법률」에 따른 연명의료중단등결정 및 그 이행으로 "
            "피보험자가 사망하는 경우 연명의료중단등결정 및 그 이행은 제3조(보험금의 지급사유) 제1호 '사망'의 원인 및 '사망보험금' 지급에 "
            "영향을 미치지 않습니다.\n"
            "③ 제3조(보험금의 지급사유) 제2호에서 장해지급률이 상해 발생일부터 180일 이내에 확정되지 않는 경우에는 상해 발생일부터 "
            "180일이 되는 날의 의사 진단에 기초하여 고정될 것으로 인정되는 상태를 장해지급률로 결정합니다. 다만, 장해분류표(<별표1> 참조)에 "
            "장해판정시기를 별도로 정한 경우에는 그에 따릅니다.\n"
            "④ 제3항에 따라 장해지급률이 결정되었으나 그 이후 보장받을 수 있는 기간(계약의 효력이 없어진 경우에는 상해 발생일부터 1년 이내)에 "
            "장해상태가 더 악화된 때에는 그 악화된 장해상태를 기준으로 장해지급률을 결정합니다.\n"
            "⑤ 장해분류표에 해당되지 않는 후유장해는 피보험자의 직업, 연령, 신분 또는 성별 등에 관계없이 신체의 장해정도에 따라 "
            "장해분류표의 구분에 준하여 지급액을 결정합니다. 다만, 장해분류표의 각 장해분류별 최저 지급률 장해정도에 이르지 않는 "
            "후유장해에 대하여는 후유장해보험금을 지급하지 않습니다.\n"
            "⑥ 보험수익자와 회사가 제3조(보험금의 지급사유)의 보험금 지급사유에 대해 합의하지 못할 때는 보험수익자와 회사가 함께 "
            "제3자를 정하고 그 제3자의 의견에 따를 수 있습니다. 제3자는 의료법 제3조(의료기관)에 규정한 종합병원 소속 전문의 중에 정하며, "
            "보험금 지급사유 판정에 드는 의료비용은 회사가 전액 부담합니다.\n"
            "⑦ 같은 상해로 두 가지 이상의 후유장해가 생긴 경우에는 후유장해 지급률을 더하여 지급합니다. 다만, 장해분류표의 각 신체부위별 "
            "판정기준에 별도로 정한 경우에는 그 기준에 따릅니다.\n"
            "⑧ 다른 상해로 인하여 후유장해가 2회 이상 발생하였을 경우에는 그 때마다 이에 해당하는 후유장해지급률을 결정합니다. "
            "그러나 그 후유장해가 이미 후유장해보험금을 지급받은 동일한 부위에 가중된 때에는 최종 장해상태에 해당하는 후유장해보험금에서 "
            "이미 지급받은 후유장해보험금을 차감하여 지급합니다. 다만, 장해분류표의 각 신체부위별 판정기준에서 별도로 정한 경우에는 "
            "그 기준에 따릅니다.\n"
            "⑨ 이미 이 계약에서 후유장해보험금 지급사유에 해당되지 않았거나(보장개시 이전의 원인에 의하거나 또는 그 이전에 발생한 "
            "후유장해를 포함합니다), 후유장해보험금이 지급되지 않았던 피보험자에게 그 신체의 동일 부위에 또다시 제8항에 규정하는 "
            "후유장해상태가 발생하였을 경우에는 직전까지의 후유장해에 대한 후유장해보험금이 지급된 것으로 보고 최종 후유장해 상태에 "
            "해당되는 후유장해보험금에서 이를 차감하여 지급합니다.\n"
            "⑩ 회사가 지급하여야 할 하나의 상해로 인한 후유장해보험금은 보험가입금액을 한도로 합니다."
        )
        existing = db.query(Clause).filter(
            Clause.policy_version_id == pv.policy_version_id,
            Clause.coverage_id == None,
            Clause.article_no == "제4조(보험금 지급에 관한 세부규정)",
            Clause.text == clause4_text
        ).first()
        if not existing:
            db.add(Clause(
                policy_version_id=pv.policy_version_id,
                coverage_id=None,
                clause_type="공통",
                article_no="제4조(보험금 지급에 관한 세부규정)",
                text=clause4_text,
                page_ref="p.26-27",
                default_color="회색",
            ))

        # ===== 보통약관 제5조(보험금을 지급하지 않는 사유) =====
        clause5_text = (
            "① 회사는 다음 중 어느 한가지로 보험금 지급사유가 발생한 때에는 보험금을 지급하지 않습니다.\n"
            "1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 의사결정을 할 수 없는 상태에서 자신을 "
            "해친 경우에는 보험금을 지급합니다.\n"
            "2. 보험수익자가 고의로 피보험자를 해친 경우. 다만, 그 보험수익자가 보험금의 일부 보험수익자인 경우에는 다른 보험수익자에 "
            "대한 보험금은 지급합니다.\n"
            "3. 계약자가 고의로 피보험자를 해친 경우\n"
            "4. 피보험자의 임신, 출산(제왕절개를 포함합니다), 산후기. 그러나, 회사가 보장하는 보험금 지급사유와 보장개시일부터 2년이 지난 "
            "후에 발생한 습관성 유산, 불임 및 인공수정 관련 합병증으로 인한 경우에는 보험금을 지급합니다.\n"
            "5. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동\n"
            "② 회사는 다른 약정이 없으면 피보험자가 직업, 직무 또는 동호회 활동목적으로 아래에 열거된 행위로 인하여 제3조(보험금의 지급사유)의 "
            "상해 관련 보험금 지급사유가 발생한 때에는 해당 보험금을 지급하지 않습니다.\n"
            "1. 전문등반(전문적인 등산용구를 사용하여 암벽 또는 빙벽을 오르내리거나 특수한 기술, 경험, 사전훈련을 필요로 하는 등반을 말합니다), "
            "글라이더 조종, 스카이다이빙, 스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩\n"
            "2. 모터보트, 자동차 또는 오토바이에 의한 경기, 시범, 흥행(이를 위한 연습을 포함합니다) 또는 시운전(다만, 공용도로상에서 시운전을 "
            "하는 동안 보험금 지급사유가 발생한 경우에는 보장합니다)\n"
            "3. 선박에 탑승하는 것을 직무로 하는 사람이 직무상 선박에 탑승하고 있는 동안"
        )
        existing = db.query(Clause).filter(
            Clause.policy_version_id == pv.policy_version_id,
            Clause.coverage_id == None,
            Clause.article_no == "제5조(보험금을 지급하지 않는 사유)",
            Clause.text == clause5_text
        ).first()
        if not existing:
            db.add(Clause(
                policy_version_id=pv.policy_version_id,
                coverage_id=None,
                clause_type="면책",
                article_no="제5조(보험금을 지급하지 않는 사유)",
                text=clause5_text,
                page_ref="p.28",
                default_color="빨강",
            ))

        db.commit()
        print("Seed completed successfully for KB 2026 chunk A (p.1-88)")
        print(f"Insurer: {insurer.name} (code={insurer.code})")
        print(f"Product: {product.name} (code={product.product_code})")
        print(f"PolicyVersion: {pv.version_label} (approval_no={pv.approval_no})")
        print(f"CoverageStd: {coverage_std.std_name}")

    finally:
        db.close()


if __name__ == "__main__":
    run()
