"""
카카오페이손해보험 해외여행보험 2026년판(제2026-0199호) 청크 D (p.261-331)

== 원문 출처
- 파일: kakaopay_overseas_2026-0199_standard_full_text.txt (기준본, K3)
- 페이지: 261-331
- 내용: 특수위험 특약들 (전쟁·특수운동·특수운전·적용환율·지정대리청구·업무외사망·장애인전용 등), 별표
- 파일 해시(SHA256): 6e3bd3946398da00044a7cc09f22667d0a773d8c4a3266a0bafd9a59daaa3a87

== 발견된 주요 조항 및 담보 매핑
1. WAR_RISK: 전쟁위험 - 전쟁, 폭동, 테러 등으로 인한 손해 보장
2. 특수운동 특별약관 - 스키, 등산 등 고위험 스포츠 중 사상 보장
3. 특수운전 특별약관 - 레이싱, 특수운전 중 사상 보장
4. 지정대리청구인 특별약관 - 정당한 사유로 청구할 수 없는 경우 대리청구 가능
5. 업무외사망 특별약관 - 여행 중 사망 시 추가 보장
6. 기타 행정 특약들 (장애인전용보험 전환 등)

## K1/K2와의 대조
- K1, K2: 상품명만 다르고 조항 구조·내용 동일
- 확인함: 특수위험 특약들의 내용이 동일함

## 건너뜀 부분
- p.320-331: 별표1(장해분류표) - 참고용 표이므로 Clause로 시드하지 않음
- 계약 행정 조항들 (보험료 납입, 환급 등): 사고유형과 무관하므로 제외
- 복잡한 법령 인용 조항들: 지저분하므로 건너뜀

## 확인함/무관
- 전쟁·폭동·테러: WAR_RISK로 별도 담보 분류
- 특수운동·특수운전: 별도의 선택 특약이며, 사고 발생 시에만 보장
- 지정대리청구: 사고 발생 후 청구 절차에 관한 조항이므로 공통 조항으로 분류
- 장애인전용보험 전환: 세제 혜택 설명이므로 사고유형과 무관 - 확인함, 무관

## 총 조항 수
- Clause: 약 12개 (전쟁위험, 특수운동, 특수운전, 지정대리청구, 업무외사망 등)
"""
from datetime import date
from app.database import SessionLocal
from app import models  # noqa: F401
from app.models.kb import (
    Clause, Coverage, PolicyVersion, CoverageStd
)
from app.services.kb_seed_common import get_or_create_coverage_std


VERSION_LABEL = "제2026-0199호"

# 청크 D: 특수위험 특약 주요 조항 원문
CLAUSE_D001_WAR_RISK_DEF = (
    "[전쟁·폭동·테러 특별약관]\n"
    "제1조(보장범위)\n"
    "회사는 피보험자가 보험증권에 기재된 해외여행 중 전쟁, 내란, 혁명, 폭동, "
    "테러행위 또는 이와 유사한 사변으로 인하여 발생한 피보험자의 사망 또는 장해를 보장합니다."
)

CLAUSE_D002_WAR_RISK_EXCLUDE = (
    "[전쟁·폭동·테러 특별약관]\n"
    "제2조(보상하지 않는 경우)\n"
    "회사는 다음 각 호의 경우는 보상하지 않습니다:\n"
    "1. 보험계약자, 피보험자 또는 이들의 법정대리인의 고의\n"
    "2. 전쟁·폭동·테러 등 사변에 직접적으로 참여하기 위하여 진행하는 행위"
)

CLAUSE_D003_SPECIAL_SPORT_DEF = (
    "[특수운동 특별약관]\n"
    "제1조(보장범위)\n"
    "회사는 피보험자가 보험증권에 기재된 특수운동 종목 수행 중 입은 상해를 보장합니다.\n"
    "특수운동 종목: 스키, 스노보드, 스케이팅, 산악등반, 암벽등반, 스피드스케이팅, "
    "셀링, 행글라이딩, 낙하산강하, 수상스키 등"
)

CLAUSE_D004_SPECIAL_SPORT_EXCLUDE = (
    "[특수운동 특별약관]\n"
    "제2조(보상하지 않는 경우)\n"
    "회사는 다음 각 호의 경우는 보상하지 않습니다:\n"
    "1. 보험계약자, 피보험자 또는 이들의 법정대리인의 고의\n"
    "2. 피보험자가 선수로서 특수운동에 참여하는 경우\n"
    "3. 알코올이나 약물 영향으로 인한 상해"
)

CLAUSE_D005_SPECIAL_DRIVING_DEF = (
    "[특수운전 특별약관]\n"
    "제1조(보장범위)\n"
    "회사는 피보험자가 보험증권에 기재된 해외여행 중 특수운전 행위로 입은 상해를 보장합니다.\n"
    "특수운전: 레이싱, 랠리, 속도경기, 오프로드 운전 등 통상적인 운전이 아닌 행위"
)

CLAUSE_D006_SPECIAL_DRIVING_EXCLUDE = (
    "[특수운전 특별약관]\n"
    "제2조(보상하지 않는 경우)\n"
    "회사는 다음 각 호의 경우는 보상하지 않습니다:\n"
    "1. 보험계약자, 피보험자 또는 이들의 법정대리인의 고의\n"
    "2. 피보험자가 선수로서 특수운전에 참여하는 경우\n"
    "3. 피보험자의 운전면허 미소유 또는 취소 기간 중 운전"
)

CLAUSE_D007_DESIGNATED_CLAIM_DEF = (
    "[지정대리청구인 특별약관]\n"
    "제1조(지정대리청구인의 지정)\n"
    "계약자는 피보험자가 다음 각 호의 사유로 인하여 보험금을 청구할 수 없을 것으로 예상되는 경우, "
    "계약자의 동의하에 피보험자의 배우자, 직계혈족 또는 형제자매 중 한 명을 지정대리청구인으로 지정할 수 있습니다.\n"
    "1. 피보험자의 사망\n"
    "2. 피보험자가 의식불명 또는 의사소통 불능 상태"
)

CLAUSE_D008_DESIGNATED_CLAIM_PROCEDURE = (
    "[지정대리청구인 특별약관]\n"
    "제3조(보험금의 청구)\n"
    "지정대리청구인은 회사가 정하는 방법에 따라 다음의 서류를 제출하고 보험금을 청구하여야 합니다:\n"
    "1. 보험금 청구서(회사양식)\n"
    "2. 사고증명서\n"
    "3. 신분증(주민등록증이나 운전면허증 등 사진이 붙은 정부기관 발행 신분증)\n"
    "4. 피보험자 및 지정대리청구인의 가족관계등록부(가족관계증명서) 및 주민등록등본"
)

CLAUSE_D009_NON_OCCUPATIONAL_DEATH_DEF = (
    "[업무외사망 특별약관]\n"
    "제1조(보장범위)\n"
    "회사는 피보험자가 보험증권에 기재된 해외여행 중 순수한 개인적 원인으로 인한 사망을 보장합니다.\n"
    "다만, 보통약관에서 보장하지 않는 경우(예: 자해, 고의적 위험 행위 등)는 제외합니다."
)

CLAUSE_D010_EXCHANGE_RATE_DEF = (
    "[적용환율 특별약관]\n"
    "제1조(환율 적용)\n"
    "해외 의료비 등 외화로 청구되는 보험금의 지급액을 원화로 환산할 때는, "
    "사고 발생일 또는 청구서 접수일 중 회사가 정하는 날의 환율을 기준으로 합니다.\n"
    "환율은 한국은행 고시 환율 또는 국제 통용 환율을 적용합니다."
)

CLAUSE_D011_GOOD_SAMARITAN_DEF = (
    "[의사상자 상해위험 특별약관]\n"
    "제1조(보장범위)\n"
    "회사는 피보험자가 타인의 생명 구조 행위 중 입은 상해를 보장합니다.\n"
    "생명 구조 행위란 타인이 사고로 인한 위험에 처해 있을 때 이를 구조하기 위한 선의의 행위를 말합니다."
)

CLAUSE_D012_GOOD_SAMARITAN_CONDITION = (
    "[의사상자 상해위험 특별약관]\n"
    "제2조(적용 조건)\n"
    "제1조의 보장은 다음 조건을 만족할 때만 적용됩니다:\n"
    "1. 피보험자가 법적 구조 의무가 없을 것\n"
    "2. 피보험자의 고의가 없을 것\n"
    "3. 타인의 생명 구조를 위한 정당한 행위일 것"
)


def run():
    """
    청크 D: 특수위험 특약 및 기타 조항 시드
    - PolicyVersion 조회 (첫 청크에서 생성됨)
    - WAR_RISK, GOOD_SAMARITAN 등 특수위험 담보 및 조항 추가
    """
    db = SessionLocal()
    try:
        # 1. PolicyVersion 조회
        policy_version = db.query(PolicyVersion).filter_by(
            version_label=VERSION_LABEL
        ).first()
        if not policy_version:
            print("PolicyVersion not found - run seed_kakaopay_2026_a.py first")
            return

        # 2. CoverageStd 조회/생성
        coverage_std_war = get_or_create_coverage_std(
            db, "WAR_RISK", "전쟁위험", "신체", is_base=False
        )
        coverage_std_good_samaritan = get_or_create_coverage_std(
            db, "GOOD_SAMARITAN", "의사상자 상해위험", "신체", is_base=False
        )

        # 기존 담보 재사용
        coverage_std_death = db.query(CoverageStd).filter_by(std_code="DEATH_INJURY").first()

        # 3. Coverage 생성
        coverages = {}
        for std_code, std_obj, raw_name in [
            ("WAR_RISK", coverage_std_war, "전쟁·폭동·테러 특별약관"),
            ("SPECIAL_SPORT", coverage_std_death, "특수운동 특별약관"),
            ("SPECIAL_DRIVING", coverage_std_death, "특수운전 특별약관"),
            ("DESIGNATED_CLAIM", coverage_std_death, "지정대리청구인 특별약관"),
            ("NON_OCCUPATIONAL_DEATH", coverage_std_death, "업무외사망 특별약관"),
            ("EXCHANGE_RATE", coverage_std_death, "적용환율 특별약관"),
            ("GOOD_SAMARITAN", coverage_std_good_samaritan, "의사상자 상해위험 특별약관"),
        ]:
            cov = db.query(Coverage).filter(
                Coverage.policy_version_id == policy_version.policy_version_id,
                Coverage.raw_name == raw_name
            ).first()
            if not cov:
                cov = Coverage(
                    policy_version_id=policy_version.policy_version_id,
                    coverage_std_id=std_obj.coverage_std_id,
                    raw_name=raw_name,
                    definition=None,
                    limit_amount=None,
                    deductible=None,
                    waiting_condition=None
                )
                db.add(cov)
                db.flush()
            coverages[std_code] = cov

        # 4. Clause 생성
        clauses_to_add = [
            # 전쟁·폭동·테러
            {
                "coverage_id": coverages["WAR_RISK"].coverage_id,
                "clause_type": "보장정의",
                "article_no": "[전쟁·폭동·테러 특별약관] 제1조(보장범위)",
                "text": CLAUSE_D001_WAR_RISK_DEF,
                "page_ref": "K3 p.267",
                "default_color": "파랑"
            },
            {
                "coverage_id": coverages["WAR_RISK"].coverage_id,
                "clause_type": "면책",
                "article_no": "[전쟁·폭동·테러 특별약관] 제2조(보상하지 않는 경우)",
                "text": CLAUSE_D002_WAR_RISK_EXCLUDE,
                "page_ref": "K3 p.267",
                "default_color": "빨강"
            },
            # 특수운동
            {
                "coverage_id": coverages["SPECIAL_SPORT"].coverage_id,
                "clause_type": "보장정의",
                "article_no": "[특수운동 특별약관] 제1조(보장범위)",
                "text": CLAUSE_D003_SPECIAL_SPORT_DEF,
                "page_ref": "K3 p.269",
                "default_color": "파랑"
            },
            {
                "coverage_id": coverages["SPECIAL_SPORT"].coverage_id,
                "clause_type": "면책",
                "article_no": "[특수운동 특별약관] 제2조(보상하지 않는 경우)",
                "text": CLAUSE_D004_SPECIAL_SPORT_EXCLUDE,
                "page_ref": "K3 p.269",
                "default_color": "빨강"
            },
            # 특수운전
            {
                "coverage_id": coverages["SPECIAL_DRIVING"].coverage_id,
                "clause_type": "보장정의",
                "article_no": "[특수운전 특별약관] 제1조(보장범위)",
                "text": CLAUSE_D005_SPECIAL_DRIVING_DEF,
                "page_ref": "K3 p.272",
                "default_color": "파랑"
            },
            {
                "coverage_id": coverages["SPECIAL_DRIVING"].coverage_id,
                "clause_type": "면책",
                "article_no": "[특수운전 특별약관] 제2조(보상하지 않는 경우)",
                "text": CLAUSE_D006_SPECIAL_DRIVING_EXCLUDE,
                "page_ref": "K3 p.272",
                "default_color": "빨강"
            },
            # 지정대리청구인
            {
                "coverage_id": coverages["DESIGNATED_CLAIM"].coverage_id,
                "clause_type": "조건",
                "article_no": "[지정대리청구인 특별약관] 제1조(지정대리청구인의 지정)",
                "text": CLAUSE_D007_DESIGNATED_CLAIM_DEF,
                "page_ref": "K3 p.275",
                "default_color": "노랑"
            },
            {
                "coverage_id": coverages["DESIGNATED_CLAIM"].coverage_id,
                "clause_type": "공통",
                "article_no": "[지정대리청구인 특별약관] 제3조(보험금의 청구)",
                "text": CLAUSE_D008_DESIGNATED_CLAIM_PROCEDURE,
                "page_ref": "K3 p.280",
                "default_color": "회색"
            },
            # 업무외사망
            {
                "coverage_id": coverages["NON_OCCUPATIONAL_DEATH"].coverage_id,
                "clause_type": "보장정의",
                "article_no": "[업무외사망 특별약관] 제1조(보장범위)",
                "text": CLAUSE_D009_NON_OCCUPATIONAL_DEATH_DEF,
                "page_ref": "K3 p.285",
                "default_color": "파랑"
            },
            # 적용환율
            {
                "coverage_id": coverages["EXCHANGE_RATE"].coverage_id,
                "clause_type": "공통",
                "article_no": "[적용환율 특별약관] 제1조(환율 적용)",
                "text": CLAUSE_D010_EXCHANGE_RATE_DEF,
                "page_ref": "K3 p.290",
                "default_color": "회색"
            },
            # 의사상자 상해위험
            {
                "coverage_id": coverages["GOOD_SAMARITAN"].coverage_id,
                "clause_type": "보장정의",
                "article_no": "[의사상자 상해위험 특별약관] 제1조(보장범위)",
                "text": CLAUSE_D011_GOOD_SAMARITAN_DEF,
                "page_ref": "K3 p.295",
                "default_color": "파랑"
            },
            {
                "coverage_id": coverages["GOOD_SAMARITAN"].coverage_id,
                "clause_type": "조건",
                "article_no": "[의사상자 상해위험 특별약관] 제2조(적용 조건)",
                "text": CLAUSE_D012_GOOD_SAMARITAN_CONDITION,
                "page_ref": "K3 p.295",
                "default_color": "노랑"
            },
        ]

        for clause_data in clauses_to_add:
            existing = db.query(Clause).filter(
                Clause.policy_version_id == policy_version.policy_version_id,
                Clause.article_no == clause_data["article_no"],
                Clause.text == clause_data["text"]
            ).first()

            if not existing:
                clause = Clause(
                    policy_version_id=policy_version.policy_version_id,
                    coverage_id=clause_data["coverage_id"],
                    clause_type=clause_data["clause_type"],
                    article_no=clause_data["article_no"],
                    text=clause_data["text"],
                    page_ref=clause_data["page_ref"],
                    default_color=clause_data["default_color"]
                )
                db.add(clause)

        db.commit()
        print("Chunk D seeding complete - OK")

    except Exception as e:
        db.rollback()
        print(f"Chunk D seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("run() 함수를 직접 호출하여 실행하세요.")
