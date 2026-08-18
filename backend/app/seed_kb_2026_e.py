"""
KB해외여행보험 2026년판 청크 E (p.287-326)

원문 출처: backend/data/processed/kb_overseas_26-15505-1_full_text.txt (페이지 287-326)

## 내용 (건너뜸)
- p.287+: 나머지 계약형태 특약
  - 부부가입·가족가입·가족확장 특약 (c.py 참조)
  - 적용환율 특약 (c.py 참조)
- 별표(参考)
  - 【별표1】장해분류표 (상해 후유장해 기준)
  - 【별표9】기후성질환(온열질환) 분류표 (b.py 참조)
  - 【별표10】기후성질환(한랭질환) 분류표 (b.py 참조)
- 인용법규
  - 본 약관에서 인용된 법·규정 목록

## 건너뜀 이유
페이지 287-326은 다음으로 구성:
1. 계약형태 특약: 단순 피보험자 확장 정의 (계약행정)
2. 별표(분류표): 참고 자료
   - 장해분류표: 개별 조항에서 이미 참조됨 (예: 제4조 제2호)
   - 감염병/기후성질환 분류표: b.py에서 이미 포함됨
3. 인용법규: 법령 목록 (참고용 메타데이터)

이 부분은 보장 정의나 면책/제한 조항이 없고, 대부분 참고 자료 또는
이미 처리된 내용의 중복입니다.

멱등성: Product/PolicyVersion은 조회만 한다 (a.py에서 이미 생성됨).
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

        print("Seed completed for KB 2026 chunk E (p.287-326)")
        print(f"Note: Pages 287-326 contain reference materials and appendices.")
        print(f"  - Contract form variations (already covered in chunk C)")
        print(f"  - Classification tables (used as references in individual clauses)")
        print(f"  - Applicable laws and regulations (metadata)")
        print(f"  No new benefit clauses to extract.")

    finally:
        db.close()


if __name__ == "__main__":
    run()
