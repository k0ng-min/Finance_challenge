"""
삼성화재(insurer.code="SAMSUNG") 2026년판 약관 청크 A.
backend/data/processed/samsung_overseas_2026_full_text.txt 페이지 1-55.

## 담당 범위

### 페이지 1-20 (표지·안내사항·주요내용 요약서·보험용어 해설)
보험계약 관련 가입 전 주의사항과 보험금 지급 절차, 계약 전후 알릴 의무 등을 요약한 내용.
사고 판단·분류와 무관한 순수 계약 행정 문서이므로 Clause로 넣지 않음.

### 페이지 21-52 (보통약관 제1관~제7관, 제1조~제38조)
보통약관의 전체 조항. 검토 결과 모두 계약 행정 관련 조항이어서 사고 판단에 직접 쓸
조항이 없다. 확인한 항목:
- 제1조-제2조: 목적, 용어정의 (사고 분류 사전 아님 - 기본 개념만)
- 제3조-제8조: 보험금 지급(사유, 절차, 청구, 지급절차) - 지급사유는 "상해사망·후유장해"
  단 하나뿐이고, 특별약관으로 질병사망·질병고도후유장해를 추가하는 구조. 제3조는
  지급사유 목록 자체(고정)이고, 제4조의 세부규정(실종선고, 연명의료중단)도 지급사유
  판단 근거가 되지만, 이미 후술 질병사망 특별약관에서 같은 내용을 쓰므로 중복 피함.
- 제5조: 보험금을 지급하지 않는 사유(면책) - 상해 한정, 질병사망/고도후유장해는
  별도 특별약관에서 다룸
- 제6조-제8조: 보험금 지급사유 통지, 청구, 지급절차 - 순수 행정절차
- 제9조-제12조: 보험금 받는 방법 변경, 주소변경, 보험수익자 지정, 대표자 지정 -
  순수 계약 행정
- 제13조-제16조: 알릴 의무, 사기에 의한 계약 - 계약 유효성 판단(사고 판단과 분리)
- 제17조-제23조: 계약성립, 청약철회, 약관교부, 계약무효, 계약변경, 보험나이, 계약소멸 -
  순수 계약 성립·변경·해지 절차
- 제24조-제25조: 제1회 보험료 및 보장개시, 특별부활 - 보장 시작 시점(사고 판단 분리)
  다만 제24조⑤-⑦의 주거지 출발 전/도착 후 사고 면책 및 교통편 지연시 보험기간 연장
  조항은 "언제부터 보장이 시작되는가"라는 시간 기준이지 "무슨 사고인가" 판단 기준이
  아님.
- 제26조-제29조: 계약해지, 보험료환급 - 순수 계약행정
- 제30조-제38조: 분쟁조정, 소멸시효, 약관해석, 개인정보보호, 준거법 등 -
  순수 계약 행정·법률절차

결론: 보통약관은 지급사유 판정 자체에는 "상해사망" 1가지뿐이고, 상해의 정의·장해 분류는
별표 1에서 다루며, 특별약관으로 확장되는 구조이므로 보통약관 조항은 Clause로 넣지 않음.
확인함, 무관: 모든 조항(제1조~제38조)

### 페이지 53-55 (여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관)

새로운 담보 CoverageStd(ILL_DEATH). 지급사유 및 세부규정:
- 제1조: 보험금의 종류 및 지급사유
  - 질병사망보험금
  - 고도후유장해보험금(질병으로 진단된 후 80% 이상 장해지급률)
  - 보험기간 만료 후 30일 이내 발생 사례도 보장(제2항)
- 제2조: 보험금 지급에 관한 세부규정
  - 연명의료중단 결정으로 사망해도 보장(①)
  - 한시적 장해는 5년 이상이면 20% 적용(②)
  - 180일 내 확정 안 되는 경우 규정(③)
  - 악화시 재판정(④)
  - 심신장애 미충족 시 미지급(⑤)
  - 제5항 예외: 동일 신체부위 2가지 이상 장해는 더하지 않고 높은 것만 적용(⑥)
  - 다른 질병 후유장해 2회 이상시 차감 지급(⑦)
  - 기존 후유장해 있을 시 합산 처리(⑧)
  - 분쟁시 제3자 판정(⑨)
- 제3조: 준용규정 - 미정한 사항은 보통약관 따름

Clause 매핑:
- 제1조 전체: 지급사유 정의 (clause_type=보장정의, 파랑)
- 제2조 ①: 연명의료중단 조항 (clause_type=지급사유, 파랑)
- 제2조 ②: 한시적 장해 규정 (clause_type=제한, 초록)
- 제2조 ③-④: 180일 이내 미확정/악화시 재판정 (clause_type=조건, 노랑)
- 제2조 ⑤: 심신장애 미충족시 미지급 (clause_type=면책, 빨강)
- 제2조 ⑥: 동일부위 2가지 이상 높은 것만 적용 (clause_type=제한, 초록)
- 제2조 ⑦: 다른 질병 후유장해 2회 이상 차감 (clause_type=제한, 초록)
- 제2조 ⑧: 기존 후유장해 차감 (clause_type=제한, 초록)
- 제2조 ⑨: 분쟁시 제3자 판정 (clause_type=조건, 노랑)
"""

from datetime import date
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import Clause, Coverage, Insurer, PolicyVersion, Product
from app.services.kb_seed_common import get_or_create_coverage_std

PRODUCT_CODE = "SAMSUNG-OVERSEAS-2026"
VERSION_LABEL = "2026수집본"
FILE_HASH = "95fc1ac011933d8b329eeee3698cfd8adffa0540bf353b0e90dca446156406b7"


def run():
    """시드 함수. 멱등성: policy_version_id + text 조합이 있으면 스킵."""
    db = SessionLocal()
    try:
        # 1. Insurer/Product/PolicyVersion 생성 (첫 청크에서만)
        insurer = db.query(Insurer).filter_by(code="SAMSUNG").first()
        if not insurer:
            insurer = Insurer(
                name="삼성화재",
                code="SAMSUNG",
                is_underwriter=True,
                official_url="https://www.samsungfire.com"
            )
            db.add(insurer)
            db.flush()

        product = db.query(Product).filter_by(product_code=PRODUCT_CODE).first()
        if not product:
            product = Product(
                insurer_id=insurer.insurer_id,
                name="해외여행보험",
                product_code=PRODUCT_CODE,
                channel="다이렉트",
                sale_start=None,
                sale_end=None,
                collected_at=date(2026, 1, 1),
                review_status="raw"
            )
            db.add(product)
            db.flush()

        policy_version = db.query(PolicyVersion).filter_by(
            product_id=product.product_id,
            version_label=VERSION_LABEL
        ).first()
        if not policy_version:
            policy_version = PolicyVersion(
                product_id=product.product_id,
                version_label=VERSION_LABEL,
                effective_date=None,
                approval_no=None,
                source_url=None,
                file_hash=FILE_HASH
            )
            db.add(policy_version)
            db.flush()

        # 이 청크가 이미 시드됐으면(Coverage 생성이 idempotent하지 않으므로) 통째로 건너뛴다.
        if db.query(Coverage).filter_by(
            policy_version_id=policy_version.policy_version_id,
            raw_name="여행중 질병사망 및 질병 80%이상 고도후유장해"
        ).first():
            print("삼성화재 2026년판 청크 A: 이미 시드됨, 건너뜀.")
            db.commit()
            return

        # 2. 여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관 (p.53-55)
        ill_death_std = get_or_create_coverage_std(
            db, "ILL_DEATH", "질병사망·고도후유장해", "질병", False
        )

        # Coverage 생성
        coverage_ill_death = Coverage(
            policy_version_id=policy_version.policy_version_id,
            coverage_std_id=ill_death_std.coverage_std_id,
            raw_name="여행중 질병사망 및 질병 80%이상 고도후유장해",
            definition="보험기간 중 해외여행 도중에 발생한 질병으로 인한 사망 또는 80% 이상 고도후유장해",
            limit_amount=None,
            deductible=None,
            waiting_condition=None
        )
        db.add(coverage_ill_death)
        db.flush()

        # Clause 생성: 제1조 (보장정의)
        clause1_text = (
            "① 회사는 피보험자가 보통약관 제3조(보험금의 지급사유)의 해외여행 도중에 "
            "다음 사항 중 어느 한 가지의 경우에 해당되는 사유가 발생한 때에는 보험수익자에게 "
            "약정한 보험금을 지급합니다. "
            "1. 보험기간 중 질병으로 인하여 사망한 경우 : 사망보험금 "
            "2. 보험기간 중 진단확정된 질병으로 장해분류표([별표1] 참조. 이하 같습니다)에서 "
            "정한 장해지급률이 80% 이상에 해당하는 장해상태가 되었을 때 : 고도후유장해보험금 "
            "② 제1항에도 불구하고 해외여행 도중에 발생한 질병을 직접원인으로 하여 보험기간 "
            "마지막날로부터 30일 이내에 사망하거나 또는 80% 이상 후유장해가 남았을 경우에도 "
            "동일하게 보상하여 드립니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause1_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_ill_death.coverage_id,
                clause_type="보장정의",
                article_no="[여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관] 제1조(보험금의 종류 및 지급사유)",
                text=clause1_text,
                page_ref="p.53-54",
                default_color="파랑"
            ))

        # Clause: 제2조 ① (연명의료중단)
        clause2_1_text = (
            "「호스피스·완화의료 및 임종과정에 있는 환자의 연명의료 결정에 관한 법률」에 따른 "
            "연명의료중단 등 결정 및 그 이행으로 피보험자가 사망하는 경우 연명의료중단 등 "
            "결정 및 그 이행은 제1조(보험금의 종류 및 지급사유) 제1항 제1호 '사망'의 원인 및 "
            "'사망보험금' 지급에 영향을 미치지 않습니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause2_1_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_ill_death.coverage_id,
                clause_type="지급사유",
                article_no="[여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관] 제2조(보험금 지급에 관한 세부규정) ①",
                text=clause2_1_text,
                page_ref="p.54",
                default_color="파랑"
            ))

        # Clause: 제2조 ② (한시적 장해 5년 이상 20% 적용)
        clause2_2_text = (
            "제1조(보험금의 종류 및 지급사유) 제1항 제2호에도 불구하고 영구히 고정된 증상은 "
            "아니지만 치료종결 후 한시적으로 나타나는 장해에 대하여는 그 기간이 5년 이상인 때에는 "
            "해당 장해 지급률의 20%를 후유장해지급률로 하여 제5항을 적용합니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause2_2_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_ill_death.coverage_id,
                clause_type="제한",
                article_no="[여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관] 제2조(보험금 지급에 관한 세부규정) ②",
                text=clause2_2_text,
                page_ref="p.54",
                default_color="초록"
            ))

        # Clause: 제2조 ③ (180일 이내 미확정시 규정)
        clause2_3_text = (
            "제1조(보험금의 종류 및 지급사유) 제1항 제2호에서 장해지급률이 질병의 진단확정일부터 "
            "180일 이내에 확정되지 않는 경우에는 질병의 진단확정일부터 180일이 되는 날의 의사진단에 "
            "기초하여 고정될 것으로 인정되는 상태를 장해지급률로 결정합니다. 다만, 장해지급률이 "
            "결정된 이후 보장을 받을 수 있는 기간(계약의 효력이 없어진 경우에는 보험기간이 10년 이상인 "
            "계약은 질병의 진단확정일부터 2년 이내로 하고, 보험기간이 10년 미만인 계약은 질병의 "
            "진단확정일부터 1년)중에 장해상태가 더 악화되는 경우에는 그 악화된 장해상태를 기준으로 "
            "장해지급률을 결정하되 장해분류표에 장해판정 시기가 별도로 정해진 경우에는 그에 따릅니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause2_3_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_ill_death.coverage_id,
                clause_type="조건",
                article_no="[여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관] 제2조(보험금 지급에 관한 세부규정) ③",
                text=clause2_3_text,
                page_ref="p.54",
                default_color="노랑"
            ))

        # Clause: 제2조 ④ (장해분류표 미충족시 미지급)
        clause2_4_text = (
            "장해분류표에 해당되지 않는 후유장해는 피보험자의 직업, 연령, 신분 또는 성별 등에 관계없이 "
            "신체의 장해정도에 따라 장해분류표의 구분에 준하여 지급액을 결정합니다. 다만, 장해분류표의 "
            "각 장해분류별 최저 지급률 장해정도에 이르지 않는 후유장해에 대하여는 고도후유장해보험금을 "
            "지급하지 않습니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause2_4_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_ill_death.coverage_id,
                clause_type="제한",
                article_no="[여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관] 제2조(보험금 지급에 관한 세부규정) ④",
                text=clause2_4_text,
                page_ref="p.54",
                default_color="초록"
            ))

        # Clause: 제2조 ⑤ (동일 신체부위 2가지 이상 높은 것만 적용)
        clause2_5_text = (
            "같은 질병으로 두 가지 이상의 후유장해가 생긴 경우에는 후유장해 지급률을 더하여 지급합니다. "
            "다만, 장해분류표의 각 신체부위별 판정기준에 별도로 정한 경우에는 그 기준에 따릅니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause2_5_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_ill_death.coverage_id,
                clause_type="지급사유",
                article_no="[여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관] 제2조(보험금 지급에 관한 세부규정) ⑤",
                text=clause2_5_text,
                page_ref="p.54",
                default_color="파랑"
            ))

        # Clause: 제2조 ⑥ (동일 신체부위 2가지 이상 높은 것만)
        clause2_6_text = (
            "제5항에도 불구하고 동일한 신체부위에 장해분류표상의 2가지 이상의 장해가 발생한 경우에는 "
            "더하지 않고 그 중 높은 지급률을 적용합니다. 다만, 장해분류표의 각 신체부위별 판정기준에서 "
            "별도로 정한 경우에는 그 기준에 따릅니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause2_6_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_ill_death.coverage_id,
                clause_type="제한",
                article_no="[여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관] 제2조(보험금 지급에 관한 세부규정) ⑥",
                text=clause2_6_text,
                page_ref="p.54",
                default_color="초록"
            ))

        # Clause: 제2조 ⑦ (다른 질병 후유장해 2회 이상 차감)
        clause2_7_text = (
            "다른 질병으로 인하여 후유장해가 2회 이상 발생하였을 경우에는 그 때마다 이에 해당하는 "
            "후유장해지급률을 결정합니다. 그러나 그 후유장해가 이미 고도후유장해보험금을 지급받은 동일한 "
            "부위에 가중된 때에는 최종 장해상태에 해당하는 고도후유장해보험금에서 이미 지급받은 "
            "고도후유장해보험금을 차감하여 지급합니다. 다만, 장해분류표의 각 신체부위별 판정기준에서 "
            "별도로 정한 경우에는 그 기준에 따릅니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause2_7_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_ill_death.coverage_id,
                clause_type="제한",
                article_no="[여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관] 제2조(보험금 지급에 관한 세부규정) ⑦",
                text=clause2_7_text,
                page_ref="p.54-55",
                default_color="초록"
            ))

        # Clause: 제2조 ⑧ (기존 후유장해 차감)
        clause2_8_text = (
            "이미 다음 중 한가지의 경우에 해당하는 후유장해가 있었던 피보험자에게 그 신체의 동일 부위에 "
            "또다시 제7항에 규정하는 후유장해상태가 발생하였을 경우에는 다음 중 한가지의 경우에 해당되는 "
            "후유장해에 대한 고도후유장해보험금이 지급된 것으로 보고 최종 후유장해상태에 해당되는 "
            "고도후유장해보험금에서 이미 지급받은 것으로 간주한 고도후유장해보험금을 차감하여 지급합니다. "
            "1. 이 계약의 보장개시 전의 원인에 의하거나 또는 그 이전에 발생한 후유장해로 고도후유장해보험금의 "
            "지급사유가 되지 않았던 후유장해 "
            "2. 제1호 이외에 이 계약의 규정에 의하여 고도후유장해보험금의 지급사유가 되지 않았던 후유장해 "
            "또는 고도후유장해보험금이 지급되지 않았던 후유장해"
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause2_8_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_ill_death.coverage_id,
                clause_type="제한",
                article_no="[여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관] 제2조(보험금 지급에 관한 세부규정) ⑧",
                text=clause2_8_text,
                page_ref="p.55",
                default_color="초록"
            ))

        # Clause: 제2조 ⑨ (분쟁시 제3자 판정)
        clause2_9_text = (
            "피보험자와 회사가 피보험자의 장해지급률에 대해 합의에 도달하지 못하는 때에는 피보험자와 회사가 "
            "동의하는 제3자를 정하고 그 제3자의 의견에 따를 수 있습니다. 제3자는 「의료법 제3조(의료기관)」의 "
            "규정에 의한 종합병원 소속 전문의 중에 정하며, 장해판정에 소요되는 의료비용은 회사가 전액 부담합니다."
        )
        if not db.query(Clause).filter_by(
            policy_version_id=policy_version.policy_version_id,
            text=clause2_9_text
        ).first():
            db.add(Clause(
                policy_version_id=policy_version.policy_version_id,
                coverage_id=coverage_ill_death.coverage_id,
                clause_type="조건",
                article_no="[여행중 질병사망 및 질병 80%이상 고도후유장해 특별약관] 제2조(보험금 지급에 관한 세부규정) ⑨",
                text=clause2_9_text,
                page_ref="p.55",
                default_color="노랑"
            ))

        db.commit()
        print("삼성화재 2026년판 청크 A 시드 완료: Product/PolicyVersion 생성, ILL_DEATH 담보 9개 조항")

    finally:
        db.close()


if __name__ == "__main__":
    run()
