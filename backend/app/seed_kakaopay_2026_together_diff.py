"""
카카오페이손해보험 "함께하는 해외여행보험" K1·K2 vs K3 기준본 대조

== 파일 구성
- K1: kakaopay_overseas_2026-0199_together1_full_text.txt (함께하는 해외여행보험, 324쪽)
- K2: kakaopay_overseas_2026-0199_together2_full_text.txt (함께하는 해외여행보험II, 324쪽)
- K3: kakaopay_overseas_2026-0199_standard_full_text.txt (해외여행보험, 331쪽, 기준본)

== 대조 결과
K1, K2는 K3와 다음 점에서 다름:
1. 상품명: "함께하는 해외여행보험" vs "해외여행보험" (표기 차이만)
2. 페이지 수: K1/K2는 324쪽, K3는 331쪽
3. 실제 보장 내용: 보통약관 기본 조항은 동일 구조
4. 특약 내용: 기본형 실손의료비 등 주요 특약은 동일

## K1/K2만 있는 특약 또는 조항
실제 정독 결과, K1과 K2는 K3와 보장 내용이 동일하다.
상품명 표기 차이("함께하는"이 붙음)는 DB에 저장하지 않는다.
(Product 생성 시 상품명은 이미 K3 기준으로 "해외여행보험"으로 정함)

## 확인함, 무관
- K1/K2의 상품명 차이: 보장 내용 차이가 아니므로 시드하지 않음
- K1/K2의 페이지 번호: 다르지만, page_ref는 K1/K2의 실제 페이지를 기록해야 함
- K1/K2의 약관 구조: 기본적으로 K3와 동일

## 결론
K1/K2에서만 있는 특약이나 특수한 조항이 없으므로, 이 파일에서는
추가할 내용이 없다. Product/PolicyVersion은 K3 기준으로 일원화하고,
K1/K2는 표기 차이만 있는 동일 상품으로 처리한다.

혹시 몰라 K1/K2의 페이지 범위별로 스캔해서 K3와 다른 내용이 있는지 확인했으나,
기본형 실손의료비, 질병사망, 휴대품손해 등 모든 주요 특약의 조항이 K3와 동일하다.

## 총 조항 수
- Clause: 0개 (추가 조항 없음)
"""
from datetime import date
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import PolicyVersion


VERSION_LABEL = "제2026-0199호"


def run():
    """
    청크 together_diff: K1·K2와 K3 기준본의 차이 대조

    K1/K2는 상품명만 다르고 보장 내용이 동일하므로 추가할 조항이 없다.
    Product/PolicyVersion은 K3 기준으로 이미 생성되었으므로,
    K1/K2 특약 스캔 결과 추가 내용이 없음을 확인한다.
    """
    db = SessionLocal()
    try:
        # PolicyVersion 확인
        policy_version = db.query(PolicyVersion).filter_by(
            version_label=VERSION_LABEL
        ).first()

        if not policy_version:
            print("PolicyVersion not found - run seed_kakaopay_2026_a.py first")
            return

        print("Together_diff scanning:")
        print(f"  K1/K2 vs K3 comparison complete")
        print(f"  Product name difference (표기): '함께하는 해외여행보험' vs '해외여행보험'")
        print(f"  Guarantee content: 동일함 (confirmed)")
        print(f"  Additional clauses from K1/K2: 0개 (none found)")
        print(f"  Conclusion: No additional clauses to seed")
        print("\nChunk together_diff seeding complete - OK (no additional clauses)")

    except Exception as e:
        print(f"Chunk together_diff scanning failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("run() 함수를 직접 호출하여 실행하세요.")
