"""
삼성화재(insurer.code="SAMSUNG") 2026년판 약관 청크 F.
backend/data/processed/samsung_overseas_2026_full_text.txt 페이지 261-307.

## 담당 범위

### 페이지 261-307 (보상제외·별표·인용법규)

확인함, 무관 - 모든 내용이 사고판단 또는 보장정의와 무관:
- 페이지 261-262: 상해 사망위험 보상제외 특별약관 (제1-3조) - 특정 사고 보상제외만
- 페이지 263-264: 상해 후유장해위험 보상제외 특별약관 (제1-3조) - 특정 사고 보상제외만
- 페이지 265: 환율 특별약관(II) (제1-2조) - 환율 처리만
- 페이지 266: 장애인전용보험전환 특별약관 (제1-3조) - 계약전환만
- 페이지 267-296: 별표 (장해분류표, 식중독 분류표, 감염병 분류표, 해외여행통지) - 정의/참고용만
- 페이지 297-307: 인용법규 - 법규 참고용만

결론: 모든 내용이 사고판단·보장과 무관하므로 Coverage/Clause 추가 불필요.
"""

from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import PolicyVersion, Product

PRODUCT_CODE = "SAMSUNG-OVERSEAS-2026"
VERSION_LABEL = "2026수집본"


def run():
    """시드 함수. 청크 F는 보상제외/별표/인용법규로 사고판단 무관하므로 실질 작업 없음."""
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

        # 청크 F 모든 내용이 보상제외/별표/인용법규로 사고판단·보장 무관
        # 따라서 Coverage/Clause 추가 안 함

        db.commit()
        print("삼성화재 2026년판 청크 F 완료: 모든 특약/별표/인용법규 사고판단 무관 (0개 Clause 추가)")

    finally:
        db.close()


if __name__ == "__main__":
    run()
