"""
KB해외여행보험 2026년판 청크 C (p.146-169)

원문 출처: backend/data/processed/kb_overseas_26-15505-1_full_text.txt (페이지 146-169)

## 발견한 특약
- p.146-148: 단체계약 특별약관
- p.149: 보험료정산 추가특별약관
- p.150-151: 단체취급 특별약관(I)
- p.152: 단체취급(I) 보험료정산 추가특별약관
- p.153: 단체취급(I) 보험기간설정 추가특별약관
- p.154-155: 단체취급 특별약관(II)
- p.156: 단체취급(II) 보험료정산 추가특별약관
- p.157: 단체취급(II) 보험기간설정 추가특별약관
- p.158: 상품다수구매자 보험계약 특별약관
- p.159: 상품다수구매자 보험료정산 추가특별약관
- p.160: 상품다수구매자 보험기간 설정에 관한 추가특별약관
- p.161: 부부가입 특별약관
- p.162: 가족가입 특별약관
- p.163-164: 가족확장 특별약관
- p.164-165: 적용환율 특별약관
- p.165: ()보험금만의 지급 특별약관
- p.166-167: 지정대리청구서비스 특별약관
- p.168-169: 업무외사망보험수익자지정 특별약관

## 확인함/무관으로 건너뜀 (모두 순수 계약행정용)
이 페이지의 모든 특약은 단체 관리, 계약 형태, 피보험자 확장, 환율 적용, 청구 절차, 상속자 지정 등
순수 계약행정을 다루고 있습니다. 사고 지급사유나 보장 내용이 없으므로 Clause 작성 불필요.

- 단체계약·단체취급: 단체 계약 조건, 요율, 피보험자 관리 (계약행정)
- 보험료정산: 예치금, 정산 방법 (계약행정)
- 보험기간설정: 보험기간 정의 (계약행정)
- 부부/가족가입/가족확장: 피보험자 확장 (계약행정)
- 적용환율: 환율 기준 (계약행정)
- 지정대리청구: 청구권자 지정 (계약행정)
- 업무외사망보험수익자지정: 수익자 지정 (계약행정)

멱등성: Product/PolicyVersion은 조회만 한다 (이미 a.py에서 생성됨).
"""
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import Product, PolicyVersion

PRODUCT_CODE = "KB-OVERSEAS-2026"
VERSION_LABEL = "일반26-15505-1"


def run():
    db = SessionLocal()
    try:
        # Product/PolicyVersion 조회 (a.py에서 이미 생성됨)
        product = db.query(Product).filter(
            Product.product_code == PRODUCT_CODE
        ).first()
        if not product:
            print(f"Product {PRODUCT_CODE} not found. Run seed_kb_2026_a.py first.")
            return

        pv = db.query(PolicyVersion).filter(
            PolicyVersion.product_id == product.product_id,
            PolicyVersion.version_label == VERSION_LABEL
        ).first()
        if not pv:
            print(f"PolicyVersion {VERSION_LABEL} not found.")
            return

        print("Seed completed for KB 2026 chunk C (p.146-169)")
        print(f"Note: Pages 146-169 contain only contract administration features")
        print(f"  (group contracts, settlement, family coverage, beneficiary designation, etc.).")
        print(f"  No benefit clauses to extract.")

    finally:
        db.close()


if __name__ == "__main__":
    run()
