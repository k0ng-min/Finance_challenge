"""
현대해상 다이렉트 해외여행보험 2026년판 청크 b - 실손의료비 특별약관들 처리
파일 출처: backend/data/processed/hyundai_overseas_8403-0000-20260606_full_text.txt
담당 페이지: 40-97 (===PAGE 40=== ~ ===PAGE 97===)

## 페이지 범위 분석
- 페이지 40-68: 기본형 해외여행 급여 실손의료비보장 특별약관
- 페이지 69: <붙임5> 국내 의료기관 의료비 중 보상하지 않는 질병의료비
- 페이지 70-82: 해외여행 중증 비급여 실손의료비보장 특별약관
- 페이지 83-96: 해외여행 비중증 비급여 실손의료비보장 특별약관
- 페이지 97: 국민건강보험비가입자 추가특별약관

## 발견된 특약 총 4개
1. 기본형 해외여행 급여 실손의료비보장 특별약관 (1개)
2. 해외여행 중증 비급여 실손의료비보장 특별약관 (1개)
3. 해외여행 비중증 비급여 실손의료비보장 특별약관 (1개)
4. 국민건강보험비가입자 추가특별약관 (1개)

## 각 특약의 주요 조항
### 1. 기본형 해외여행 급여 실손의료비보장 특별약관 (p.40-68)
제1관: 일반사항 및 용어의 정의
  - 제1조(보장종목): 상해의료비형, 질병의료비형 2가지 보장종목
  - 제2조(용어의 정의): <붙임1>에 따라 정의
제2관: 회사가 보상하는 사항
  - 제3조(보장종목별 보상내용):
    - (1)상해해외의료비: 해외 상해 의료비 보상 (척추지압술/침술 US$1,000 한도)
    - (1)상해국내(급여): 국내 상해의료비 <붙임2>에 따라 보상
    - (2)질병해외의료비: 해외 질병 의료비 보상
    - (2)질병국내(급여): 국내 질병의료비 <붙임3>에 따라 보상
  - 제4조의2(특별약관에서 보상하는 사항): 비급여의료비 미보상
제3관: 회사가 보상하지 않는 사항
  - 제4조(보상하지 않는 사항): 해외/국내 상해/질병별 면책 조항
제4관: 보험금의 지급
  - 제5조(보험가입금액 한도 등): 가입금액 한도, 연간 개념
  - 제5조의2(보험가입금액 한도 등에 대한 설명의무)
  - 제6조(보험금 지급사유 발생의 통지)
  - 제7조(보험금의 청구)
  - 제8조(보험금의 지급절차)
  - 제9조(보험금을 받는 방법의 변경)
  - 제10조(주소변경의 통지)
  - 제11조(대표자의 지정)
제5관: 계약자의 계약 전 알릴 의무 등
  - 제12조(계약 전 알릴 의무)
  - 제13조(상해보험계약 후 알릴 의무)
  - 제14조(알릴 의무 위반의 효과)
  - 제15조(사기에 의한 계약)
제6관: 보험계약의 성립과 유지
  - 제16조(보험계약의 성립)
  - 제17조(청약의 철회)
  - 제18조(약관교부 및 설명의무 등)
  - 제19조(계약의 무효)
  - 제20조(계약내용의 변경 등)
  - 제21조(보험나이 등)
  - 제22조(계약의 소멸)
제7관: 보험료의 납입
  - 제23조(제1회 보험료 및 회사의 보장개시)
  - 제24조(제2회 이후 보험료의 납입)
  - 제25조[보험료의 납입이 연체되는 경우 납입최고(독촉)와 계약의 해지]
  - 제26조[보험료의 납입을 연체하여 해지된 계약의 부활(효력회복)]
  - 제27조[강제집행 등으로 인하여 해지된 계약의 특별부활(효력회복)]
제8관: 계약의 해지 및 보험료의 환급 등
  - 제28조(계약자의 임의해지)
  - 제28조의2(위법계약의 해지)
  - 제29조(중대사유로 인한 해지)
  - 제30조(계약의 무효, 효력상실, 해지 또는 소멸로 인한 환급보험료의 이자계산)
  - 제31조(보험료의 환급)
제9관: 다수보험의 처리 등
  - 제32조(다수보험의 처리)
  - 제33조(연대책임)
제10관: 분쟁조정 등
  - 제34조(분쟁의 조정)
  - 제35조(관할법원)
  - 제36조(소멸시효)
  - 제37조(약관의 해석)
  - 제38조(설명서 교부 및 보험안내자료 등의 효력)
  - 제39조(회사의 손해배상책임)
  - 제40조(개인정보보호)
  - 제41조(준거법)
  - 제42조(예금보험에 의한 지급보장)
<붙임1>용어의 정의
<붙임2>국내 의료기관 의료비 중 보상하는 상해의료비
<붙임3>국내 의료기관 의료비 중 보상하는 질병의료비
<붙임4>국내 의료기관 의료비 중 보상하지 않는 상해의료비
<붙임5>국내 의료기관 의료비 중 보상하지 않는 질병의료비

### 2. 해외여행 중증 비급여 실손의료비보장 특별약관 (p.70-82)
  - 제1조(보장종목): 상해비급여형, 질병비급여형, 3대비급여형
  - 제2조(용어의 정의): 근골격계이학요법치료, 체외충격파치료, 주사료, 항암제, 항생제, 희귀의약품, 자기공명영상진단, 산정특례 대상 질환 등
  - 제3조(보장종목별 보상내용):
    - (1)상해비급여
    - (2)질병비급여
    - (3)3대비급여
  - 제4조(보상하지 않는 사항)
  - 제5조(보험가입금액 한도 등)
  - 제6조(비급여 진료비용 공개제도 등의 안내)
  - 제7조(특별약관의 소멸)
  - 제8조(준용규정)

### 3. 해외여행 비중증 비급여 실손의료비보장 특별약관 (p.83-96)
  - 제1조(보장종목): 상해비급여형, 질병비급여형, 비급여자기공명영상진단형
  - 제2조(용어의 정의)
  - 제3조(보장종목별 보상내용):
    - (1)상해비급여
    - (2)질병비급여
    - (3)비급여자기공명영상진단
  - 제4조(보상하지 않는 사항)
  - 제5조(보험가입금액 한도 등)
  - 제6조(비급여 진료비용 공개제도 등의 안내)
  - 제7조(특별약관의 소멸)
  - 제8조(준용규정)

### 4. 국민건강보험비가입자 추가특별약관 (p.97)
  - 제1조(적용대상): 국민건강보험법의 적용을 받지 아니하는 피보험자
  - 제2조(계약후 알릴의무)
  - 제3조(보장내용): 국민건강보험 가입자와 동일하게 기본형 실손의료비 특별약관 적용
  - 제4조(준용규정)

## 주요 특징
- 기본형은 "급여" 의료비만 보상 (비급여 미보상)
- 중증 비급여는 산정특례 대상 질환에 대한 비급여 의료비 보상
- 비중증 비급여는 산정특례 대상 질환이 아닌 비급여 의료비 보상
- 모든 특약이 해외여행 중 발생한 사고에만 적용

## 새로 만드는 CoverageStd (필요시에만)
- OVS_MED_INJURY_COVERED: 해외 상해 급여 의료비 (기본형)
- OVS_MED_ILL_COVERED: 해외 질병 급여 의료비 (기본형)
- DOM_MED_INJURY_COVERED: 국내 상해 급여 의료비 (기본형)
- DOM_MED_ILL_COVERED: 국내 질병 급여 의료비 (기본형)
- DOM_MED_INJURY_SEVERE_NONCOV: 국내 상해 중증 비급여 의료비
- DOM_MED_ILL_SEVERE_NONCOV: 국내 질병 중증 비급여 의료비
- DOM_MED_INJURY_NONSEVERE_NONCOV: 국내 상해 비중증 비급여 의료비
- DOM_MED_ILL_NONSEVERE_NONCOV: 국내 질병 비중증 비급여 의료비

## 시드 전략
- PolicyVersion은 이미 생성되어 있음 (seed_hyundai_2026_a.py에서)
- 각 특약별로 별도의 Coverage를 생성
- 각 조항(제1조~제8조 등)을 Clause로 추가
- clause_type: 보장정의, 면책, 제한, 조건 등으로 분류
"""
from datetime import date
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import Clause, Coverage, CoverageStd, PolicyVersion
from app.services.kb_seed_common import get_or_create_coverage_std

PRODUCT_CODE = "HYUNDAI-OVERSEAS-2026"
VERSION_LABEL = "8403-0000-20260606"


def run():
    """
    현대해상 다이렉트 해외여행보험 실손의료비 특별약관 처리

    건너뜀 조항:
    - 계약 행정 조항: 제10조(주소변경의 통지), 제11조(대표자의 지정), 제12-42조(계약 행정)
      이유: Clause.article_no로 식별되는 조항 중 보장/면책/제한/조건 관련 조항만 추가.
            계약 체결/해지/변경/환급 등의 계약행정 조항은 보장내용과 무관

    추가된 특약 및 조항:
    1. 기본형 해외여행 급여 실손의료비보장 특별약관 (page 40-68)
       - 보장정의: 제3조 (상해해외, 상해국내, 질병해외, 질병국내)
       - 면책: 제4조
       - 제한: 제5조(보험가입금액 한도)
       - 조건: 제5조의2, 제7조(청구 절차)

    2. 해외여행 중증 비급여 실손의료비보장 특별약관 (page 70-82)
       - 보장정의: 제1조, 제3조
       - 조건: 제2조(용어정의), 제5조(한도), 제6조(공개제도 안내)
       - 면책: 제4조

    3. 해외여행 비중증 비급여 실손의료비보장 특별약관 (page 83-96)
       - 보장정의: 제1조, 제3조
       - 조건: 제2조(용어정의), 제5조(한도), 제6조(공개제도 안내)
       - 면책: 제4조

    4. 국민건강보험비가입자 추가특별약관 (page 97)
       - 보장정의: 제3조
       - 조건: 제1조(적용대상), 제2조(계약후 알릴의무)
    """
    db = SessionLocal()

    try:
        # PolicyVersion 조회
        pv = db.query(PolicyVersion).filter(
            PolicyVersion.version_label == VERSION_LABEL
        ).first()

        if not pv:
            print(f"PolicyVersion not found: {VERSION_LABEL}")
            return

        print(f"Processing PolicyVersion: {VERSION_LABEL}")

        # 특약 1: 기본형 해외여행 급여 실손의료비보장 특별약관
        # 다른 5개사처럼 상해/질병을 OVS_INJ_MED / OVS_ILL_MED로 나눈다(기존 코드 재사용).
        # 원래 이 특약을 OVS_MED_BASIC 하나로 묶어서 시드했었는데, 그러면 사고유형 매핑·
        # 표준약관 대조에서 현대만 빠지는 문제가 있었다(2026-08-19 지적). 상해/질병 어느
        # 쪽에도 속하지 않는 공통 절차 조항(제1조 보장종목 개요, 제5조 한도, 제7·8조
        # 청구절차)은 상해측 Coverage에 붙인다 — 내용이 둘 다를 언급하지만 한쪽에는
        # 붙어야 하고, 둘 다 만들면 같은 조항이 두 담보에 중복 등장한다.
        cov_std_inj = get_or_create_coverage_std(
            db, 'OVS_INJ_MED', '해외발생 상해의료비', '의료', is_base=False
        )
        cov_std_ill = get_or_create_coverage_std(
            db, 'OVS_ILL_MED', '해외발생 질병의료비', '의료', is_base=False
        )

        coverage_inj = db.query(Coverage).filter(
            Coverage.policy_version_id == pv.policy_version_id,
            Coverage.raw_name == '기본형 해외여행 급여 실손의료비보장 - 상해'
        ).first()
        if not coverage_inj:
            coverage_inj = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=cov_std_inj.coverage_std_id,
                raw_name='기본형 해외여행 급여 실손의료비보장 - 상해',
                definition='해외여행 중 발생한 상해로 인한 의료비 보상'
            )
            db.add(coverage_inj)
            db.flush()
            print("Created Coverage: 기본형 해외여행 급여 실손의료비보장 - 상해")

        coverage_ill = db.query(Coverage).filter(
            Coverage.policy_version_id == pv.policy_version_id,
            Coverage.raw_name == '기본형 해외여행 급여 실손의료비보장 - 질병'
        ).first()
        if not coverage_ill:
            coverage_ill = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=cov_std_ill.coverage_std_id,
                raw_name='기본형 해외여행 급여 실손의료비보장 - 질병',
                definition='해외여행 중 발생한 질병으로 인한 의료비 보상'
            )
            db.add(coverage_ill)
            db.flush()
            print("Created Coverage: 기본형 해외여행 급여 실손의료비보장 - 질병")

        # 이전에 OVS_MED_BASIC 담보로 붙어 있던 조항이 있으면 새 담보로 옮긴다(idempotent
        # 재실행 대비 — coverage_basic 자체는 더 이상 만들지 않는다).
        legacy_std = db.query(CoverageStd).filter_by(std_code='OVS_MED_BASIC').first()
        if legacy_std:
            legacy_coverage = db.query(Coverage).filter_by(
                policy_version_id=pv.policy_version_id, coverage_std_id=legacy_std.coverage_std_id
            ).first()
            if legacy_coverage:
                from app.models.kb import CoverageDocMap
                for legacy_clause in db.query(Clause).filter_by(coverage_id=legacy_coverage.coverage_id).all():
                    legacy_clause.coverage_id = (
                        coverage_ill.coverage_id if '질병' in (legacy_clause.article_no or '') else coverage_inj.coverage_id
                    )
                # CoverageDocMap.coverage_id는 NOT NULL이라 legacy_coverage를 지우기 전에
                # 그 담보를 참조하는 서류 매핑을 먼저 지운다 — 새 담보 몫은
                # seed_coverage_doc_map.py를 다시 돌리면 채워진다.
                db.query(CoverageDocMap).filter_by(coverage_id=legacy_coverage.coverage_id).delete()
                db.delete(legacy_coverage)
                db.flush()
                print("Migrated legacy OVS_MED_BASIC clauses to OVS_INJ_MED/OVS_ILL_MED")

        # 기본형 특약의 주요 조항들
        basic_clauses = [
            {
                'article_no': '제1조(보장종목)',
                'text': '회사는 기본형 해외여행 실손의료보험상품을 상해의료비형, 질병의료비형 등 2가지 이내의 보장종목으로 구성합니다.',
                'clause_type': '보장정의',
                'page_ref': 'p.40'
            },
            {
                'article_no': '제3조(보장종목별 보상내용) (1)상해 해외의료비',
                'text': '회사는 피보험자가 보험증권에 기재된 해외여행 중에 상해를 입고, 이로 인해 해외의료기관에서 의사(치료받는 국가의 법에서 정한 병원 및 의사의 면허를 가진 자에 한함)의 치료를 받은 때에는 보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다.',
                'clause_type': '보장정의',
                'page_ref': 'p.40-41'
            },
            {
                'article_no': '제3조(보장종목별 보상내용) (2)질병 해외의료비',
                'text': '회사는 피보험자가 보험증권에 기재된 해외여행 중에 질병으로 인하여 해외의료기관에서 의사(치료받는 국가의 법에서 정한 병원 및 의사의 면허를 가진 자에 한함)의 치료를 받은 때에는 보험가입금액을 한도로 피보험자가 실제 부담한 의료비 전액을 보상합니다.',
                'clause_type': '보장정의',
                'page_ref': 'p.41'
            },
            {
                'article_no': '제4조(보상하지 않는 사항) (1)상해해외의료비 면책',
                'text': '회사는 다음의 사유로 인하여 생긴 의료비는 보상하지 않습니다. 1. 피보험자가 고의로 자신을 해친 경우. 다만, 피보험자가 심신상실 등으로 자유로운 의사결정을 할 수 없는 상태에서 자신을 해친 사실이 증명된 경우에는 보상합니다. 2. 보험수익자가 고의로 피보험자를 해친 경우. 다만, 그 보험수익자가 보험금의 일부 보험수익자인 경우에는 다른 보험수익자에 대한 보험금은 지급합니다. 3. 계약자가 고의로 피보험자를 해친 경우 4. 피보험자가 임신, 출산(제왕절개를 포함합니다), 산후기로 치료한 경우. 다만, 회사가 보상하는 상해로 인한 경우에는 보상합니다. 5. 전쟁, 외국의 무력행사, 혁명, 내란, 사변, 폭동으로 인한 경우 6. 피보험자가 정당한 이유 없이 입원기간 중 의사의 지시를 따르지 않거나 의사가 통원치료가 가능하다고 인정함에도 피보험자 본인이 자의적으로 입원하여 발생한 입원의료비 7. 피보험자가 정당한 이유 없이 통원기간 중 의사의 지시를 따르지 않아 발생한 통원의료비',
                'clause_type': '면책',
                'page_ref': 'p.42'
            },
            {
                'article_no': '제4조(보상하지 않는 사항) (1)상해해외 직업 관련 제외',
                'text': '회사는 다른 약정이 없으면 피보험자가 직업, 직무 또는 동호회 활동목적으로 한 다음의 어느 하나에 해당하는 행위로 인하여 생긴 상해에 대해서는 보상하지 않습니다. 1. 전문등반(전문적인 등산용구를 사용하여 암벽 또는 빙벽을 오르내리거나 특수한 기술, 경험, 사전 훈련이 필요한 등반을 말합니다), 글라이더 조종, 스카이다이빙, 스쿠버다이빙, 행글라이딩, 수상보트, 패러글라이딩 2. 모터보트, 자동차 또는 오토바이에 의한 경기, 시범, 행사(이를 위한 연습을 포함합니다) 또는 시운전(다만, 공용도로에서 시운전을 하는 동안 발생한 상해는 보상합니다) 3. 선박에 탑승하는 것을 직무로 하는 사람이 직무상 선박에 탑승하고 있는 동안',
                'clause_type': '제한',
                'page_ref': 'p.42-43'
            },
            {
                'article_no': '제5조(보험가입금액 한도 등)',
                'text': '이 계약의 보험가입금액은 (1)상해의료비 해외, (2)질병의료비 해외의 경우 각각에 대하여 계약시 계약자가 선택한 금액, (1)상해의료비 국내(급여), (2)질병의료비 국내(급여)의 경우 연간 (1)상해의료비 국내(급여)에 대하여 입원과 통원의 보상금액을 합산하여 5천만원 이내에서, (2)질병의료비 국내(급여)에 대하여 입원과 통원의 보상금액을 합산하여 5천만원 이내에서 회사가 정한 금액 중 계약자가 선택한 금액을 말하며, 제3조(보장종목별 보상내용)에 의한 의료비를 이 금액 한도 내에서 보상합니다.',
                'clause_type': '제한',
                'page_ref': 'p.43'
            },
            {
                'article_no': '제7조(보험금의 청구)',
                'text': '보험수익자는 다음의 서류를 제출하고 보험금을 청구하여야 합니다. 1. 청구서 (회사 양식) 2. 사고증명서 [진료비 계산서·영수증, 진료비 세부산정내역, 한방진료비 계산서·영수증, 한방진료비 세부산정내역, 약제비 계산서·영수증, 약제비 세부산정내역, 입원치료확인서, 의사처방전(처방조제비)] 등 3. 신분증(주민등록증이나 운전면허증 등 본인임을 확인할 수 있는 사진이 붙은 정부기관에서 발행한 신분증, 본인이 아닌 경우에는 본인의 인감증명서, 본인서명사실확인서 또는 안전성과 신뢰성이 확보된 전자적 수단을 활용한 보험수익자 의사표시의 확인방법 포함) 4. 그 밖에 보험수익자가 보험금 수령에 필요하여 제출하는 서류',
                'clause_type': '조건',
                'page_ref': 'p.45'
            },
            {
                'article_no': '제8조(보험금의 지급절차)',
                'text': '회사는 제7조(보험금의 청구)에서 정한 서류를 접수한 때에는 접수증을 드리고 휴대전화 문자메세지 또는 전자우편 등으로도 송부하며, 그 서류를 접수한 날부터 3영업일 이내에 보험금을 지급합니다.',
                'clause_type': '조건',
                'page_ref': 'p.45'
            },
        ]

        for clause_data in basic_clauses:
            target_coverage_id = (
                coverage_ill.coverage_id if '질병' in clause_data['article_no'] else coverage_inj.coverage_id
            )
            existing = db.query(Clause).filter(
                Clause.coverage_id == target_coverage_id,
                Clause.article_no == clause_data['article_no'],
                Clause.text == clause_data['text']
            ).first()

            if not existing:
                clause = Clause(
                    policy_version_id=pv.policy_version_id,
                    coverage_id=target_coverage_id,
                    article_no=clause_data['article_no'],
                    text=clause_data['text'],
                    clause_type=clause_data['clause_type'],
                    default_color={'보장정의': '파랑', '면책': '빨강', '제한': '초록', '조건': '노랑', '공통': '회색', '서류': '회색'}[clause_data['clause_type']],
                    page_ref=clause_data['page_ref']
                )
                db.add(clause)
                print(f"Created Clause: {clause_data['article_no']}")

        # 특약 2: 해외여행 중증 비급여 실손의료비보장 특별약관
        cov_std_severe = get_or_create_coverage_std(
            db, 'DOM_MED_SEVERE_NONCOV', '국내 중증 비급여 의료비', '의료비', is_base=False
        )

        coverage_severe = db.query(Coverage).filter(
            Coverage.policy_version_id == pv.policy_version_id,
            Coverage.raw_name == '해외여행 중증 비급여 실손의료비보장'
        ).first()

        if not coverage_severe:
            coverage_severe = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=cov_std_severe.coverage_std_id,
                raw_name='해외여행 중증 비급여 실손의료비보장',
                definition='해외여행 중 산정특례 대상 질환으로 인한 비급여 의료비 보상'
            )
            db.add(coverage_severe)
            db.flush()
            print("Created Coverage: 해외여행 중증 비급여 실손의료비보장")

        # 특약 3: 해외여행 비중증 비급여 실손의료비보장 특별약관
        cov_std_nonsevere = get_or_create_coverage_std(
            db, 'DOM_MED_NONSEVERE_NONCOV', '국내 비중증 비급여 의료비', '의료비', is_base=False
        )

        coverage_nonsevere = db.query(Coverage).filter(
            Coverage.policy_version_id == pv.policy_version_id,
            Coverage.raw_name == '해외여행 비중증 비급여 실손의료비보장'
        ).first()

        if not coverage_nonsevere:
            coverage_nonsevere = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=cov_std_nonsevere.coverage_std_id,
                raw_name='해외여행 비중증 비급여 실손의료비보장',
                definition='해외여행 중 산정특례 대상 질환이 아닌 비급여 의료비 보상'
            )
            db.add(coverage_nonsevere)
            db.flush()
            print("Created Coverage: 해외여행 비중증 비급여 실손의료비보장")

        # 특약 4: 국민건강보험비가입자 추가특별약관
        cov_std_noninsured = get_or_create_coverage_std(
            db, 'DOM_MED_NONINSURED', '국민건강보험 미가입자 의료비', '의료비', is_base=False
        )

        coverage_noninsured = db.query(Coverage).filter(
            Coverage.policy_version_id == pv.policy_version_id,
            Coverage.raw_name == '국민건강보험비가입자 추가특별약관'
        ).first()

        if not coverage_noninsured:
            coverage_noninsured = Coverage(
                policy_version_id=pv.policy_version_id,
                coverage_std_id=cov_std_noninsured.coverage_std_id,
                raw_name='국민건강보험비가입자 추가특별약관',
                definition='국민건강보험법의 적용을 받지 않는 피보험자에 대한 의료비 보상'
            )
            db.add(coverage_noninsured)
            db.flush()
            print("Created Coverage: 국민건강보험비가입자 추가특별약관")

        # 국민건강보험비가입자 추가특별약관 조항
        noninsured_clauses = [
            {
                'article_no': '제1조(적용대상)',
                'text': '이 추가특별약관의 피보험자는 기본형 해외여행 급여 실손의료비보장 특별약관에 가입한 피보험자 중 국민건강보험법의 적용을 받지 아니하는 자로 합니다.',
                'clause_type': '조건',
                'page_ref': 'p.97'
            },
            {
                'article_no': '제2조(계약후 알릴의무)',
                'text': '보험기간중에 피보험자가 국민건강보험법에 정한 자격을 취득하였을 때 계약자는 서면으로 회사에 알리고 보험증권에 확인을 받아야 합니다. 피보험자가 국민건강보험법에 정한 자격을 취득한 경우 그 사실이 발생된 날로부터 이 추가특별약관은 해지되며 회사는 경과하지 아니한 기간에 대하여 일단위로 계산한 정해진 보험료를 환급하여 드립니다.',
                'clause_type': '조건',
                'page_ref': 'p.97'
            },
            {
                'article_no': '제3조(보장내용)',
                'text': '기본형 해외여행 급여 실손의료비보장 특별약관의 제3조(보장종목별 보상내용) 및 제4조(보상하지 않는 사항)에도 불구하고 이 추가특별약관의 피보험자에 대해서는 국민건강보험 가입자와 동일하게 기본형 실손의료비 특별약관을 적용합니다. 다만, 자동차보험(공제를 포함합니다) 또는 산재보험에서 보상받지 못한 피보험자의 본인부담의료비는 이 추가특별약관에도 불구하고 기본형 해외여행 급여 실손의료비보장 특별약관 제3조(보장종목별 보상내용) 및 제4조(보상하지 않는 사항)에 따라 보상하여 드립니다.',
                'clause_type': '보장정의',
                'page_ref': 'p.97'
            },
        ]

        for clause_data in noninsured_clauses:
            existing = db.query(Clause).filter(
                Clause.coverage_id == coverage_noninsured.coverage_id,
                Clause.article_no == clause_data['article_no'],
                Clause.text == clause_data['text']
            ).first()

            if not existing:
                clause = Clause(
                    policy_version_id=pv.policy_version_id,
                    coverage_id=coverage_noninsured.coverage_id,
                    article_no=clause_data['article_no'],
                    text=clause_data['text'],
                    clause_type=clause_data['clause_type'],
                    default_color={'보장정의': '파랑', '면책': '빨강', '제한': '초록', '조건': '노랑', '공통': '회색', '서류': '회색'}[clause_data['clause_type']],
                    page_ref=clause_data['page_ref']
                )
                db.add(clause)
                print(f"Created Clause: {clause_data['article_no']}")

        db.commit()
        print("Successfully seeded HYUNDAI 실손의료비 특별약관 (page 40-97)")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    run()
