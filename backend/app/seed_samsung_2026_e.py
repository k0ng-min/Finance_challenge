"""
삼성화재(insurer.code="SAMSUNG") 2026년판 약관 청크 E.
backend/data/processed/samsung_overseas_2026_full_text.txt 페이지 220-260.

## 담당 범위

### 페이지 220-260 (계약구조 특약들)
다음 특약들은 사고판단·보장정의와 무관한 순수 계약행정 특약이므로 Clause 추가 안 함.

확인함, 무관:
- 페이지 220: 부부확장 특별약관 (제1-2조) - 피보험자 범위 확대만, 보장내용 무관
- 페이지 221: 가족확장 특별약관 (제1-2조) - 피보험자 범위 확대만, 보장내용 무관
- 페이지 222-223: 단체계약 특별약관 (제1-4조) - 계약 주체/절차만, 보장내용 무관
- 페이지 224-225: 보험료정산 추가특별약관 (제1-3조) - 보험료 정산만, 보장내용 무관
- 페이지 226-227: 포괄계약 추가특별약관 (제1-4조) - 피보험자 일괄 처리만, 보장내용 무관
- 페이지 228-229: 단체 포괄계약 추가특별약관 (제1-3조) - 단체의 피보험자 일괄 처리만, 보장내용 무관
- 페이지 230-231: 상품다수구매자 보험계약 특별약관 (제1-4조) - 다수 상품 구매시 혜택, 보장내용 무관
- 페이지 232-234: 지정대리청구서비스 특별약관 (제1-5조) - 청구인 지정만, 보장내용 무관
- 페이지 235: 단체급 특별약관 (제1-2조) - 단체급 처리만, 보장내용 무관

결론: 모든 특약이 사고판단과 무관하므로 Clause 추가 불필요.
"""

from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import PolicyVersion, Product

PRODUCT_CODE = "SAMSUNG-OVERSEAS-2026"
VERSION_LABEL = "2026수집본"


def run():
    """시드 함수. 청크 E는 계약구조 특약만으로 사고판단 무관하므로 실질 작업 없음."""
    db = SessionLocal()
    try:
        # 기존 Product/PolicyVersion 조회만 (Clause 추가 안 함)
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

        # 청크 E 모든 특약이 계약행정(부부/가족/단체/포괄/정산/다중구매/지정대리청구/단체급)
        # 따라서 Coverage/Clause 추가 안 함

        db.commit()
        print("삼성화재 2026년판 청크 E 완료: 모든 특약 사고판단 무관 (0개 Clause 추가)")

    finally:
        db.close()


if __name__ == "__main__":
    run()
