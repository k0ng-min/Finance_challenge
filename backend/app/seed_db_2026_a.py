"""
DB손해보험(insurer.code="DB") 프로미 해외여행보험Ⅰ 2026년판 - 청크 a (p.1-34)

## 원문 파일
backend/data/processed/db_overseas_promi1_2026_full_text.txt (p.1-34, 2026년판)

## 작업 내용
이 청크에서는 Product/PolicyVersion을 생성한다. 나머지 청크(b, c, d)는 이를 조회해서 재사용한다.

### 생성 대상
- Insurer: code="DB", name="DB손해보험"
- Product: code="DB-OVERSEAS-2026", name="프로미 해외여행보험Ⅰ"
- PolicyVersion: version_label="프로미Ⅰ_2026수집본", file_hash="151c57ec603cad5b5d5dcc4128468e2ac9102d45d842554f1d98fbbecbf3e008"

## 페이지 분석

### p.1-6 (목차)
확인함, 무관. 목차와 색인만 포함. 보상 판정과 무관.

### p.7-10 (안내사항, 주요내용 요약서, 보험용어 해설)
확인함, 무관. 순수 안내/정보성 문서. 보상 판정과 무관.

### p.11-34 (보통약관 제1-7관)
확인함, 무관.

- 제1관 제1-2조: 목적, 용어정의 (계약 구조)
- 제2관 제3-11조: 보험금 지급사유, 세부규정, 면책사유, 청구절차 (계약 구조 및 절차)
  * 제3조(보험금의 지급사유): 상해사망·후유장해 — 이미 기존 약관(보통약관)에서 DEATH_INJURY로 처리됨
  * 제5조(보험금을 지급하지 않는 사유): 고의, 전쟁·혁명, 임신·출산 등 면책사유 — 기존 약관의 일부
  * 나머지는 보험금 청구·지급 절차, 보험수익자 지정, 주소변경 등 계약행정
- 제3관 제13-16조: 계약 전·후 알릴의무, 사기에 의한 계약 (계약행정)
- 제4관 제17-23조: 계약 성립, 청약철회, 약관교부, 계약무효, 계약변경, 보험나이, 계약소멸 (계약행정)
- 제5관 제24-28조: 보험료 납입, 연체, 부활, 강제집행 (계약행정)
- 제6관 제29-32조: 계약해지, 보험료환급 (계약행정)
- 제7관 제33-41조: 분쟁조정, 관할법원, 소멸시효, 약관해석, 개인정보보호, 준거법, 예금보험 (계약행정)

**결론**: 보통약관은 계약 유지·관리·절차에 관한 순수 행정 조항들이다. 보상 판정에 직접 쓸 Clause 내용이 없다.
새로 만드는 특별약관 조항들(b, c, d 청크)에서 각 담보별 보장정의·면책·제한·조건이 이미 정의되므로,
보통약관의 일반 면책사항을 중복으로 넣을 필요 없다.

## 결론
Product/PolicyVersion 생성 + 보통약관 확인함/무관 기록. Clause 0개.

## 동작
run() 함수는:
1. Insurer 생성 (없으면 스킵)
2. Product 생성
3. PolicyVersion 생성 (정확한 file_hash 사용)
4. db.commit() 및 db.close()
"""

from datetime import date
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import Insurer, Product, PolicyVersion

PRODUCT_CODE = "DB-OVERSEAS-2026"
VERSION_LABEL = "프로미Ⅰ_2026수집본"
FILE_HASH = "151c57ec603cad5b5d5dcc4128468e2ac9102d45d842554f1d98fbbecbf3e008"


def run():
    db = SessionLocal()
    try:
        # Insurer 조회 또는 생성
        insurer = db.query(Insurer).filter_by(code="DB").first()
        if not insurer:
            insurer = Insurer(
                name="DB손해보험",
                code="DB",
                is_underwriter=True,
                official_url="https://www.dbinsurance.co.kr",
            )
            db.add(insurer)
            db.flush()
            print("Insurer DB손해보험 생성")
        else:
            print("Insurer DB손해보험 이미 존재")

        # Product 생성 (중복 체크)
        product = db.query(Product).filter_by(product_code=PRODUCT_CODE).first()
        if not product:
            product = Product(
                insurer_id=insurer.insurer_id,
                name="프로미 해외여행보험Ⅰ",
                product_code=PRODUCT_CODE,
                channel="다이렉트",
                sale_start=None,
                sale_end=None,
                collected_at=date(2026, 8, 18),
                review_status="raw",
            )
            db.add(product)
            db.flush()
            print(f"Product {PRODUCT_CODE} 생성")
        else:
            print(f"Product {PRODUCT_CODE} 이미 존재")

        # PolicyVersion 생성 (중복 체크)
        pv = db.query(PolicyVersion).filter_by(
            product_id=product.product_id,
            version_label=VERSION_LABEL,
        ).first()
        if not pv:
            pv = PolicyVersion(
                product_id=product.product_id,
                version_label=VERSION_LABEL,
                effective_date=None,
                approval_no=None,
                source_url=None,
                file_hash=FILE_HASH,
            )
            db.add(pv)
            db.flush()
            print(f"PolicyVersion {VERSION_LABEL} 생성 (file_hash: {FILE_HASH})")
        else:
            print(f"PolicyVersion {VERSION_LABEL} 이미 존재")

        db.commit()
        print("\nSeed DB 2026 청크 a (p.1-34) 완료")
        print("- Insurer, Product, PolicyVersion 생성 완료")
        print("- 보통약관 (p.11-34): 확인함, 무관 (계약행정 조항만 포함)")
        print("- Clause: 0개")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
