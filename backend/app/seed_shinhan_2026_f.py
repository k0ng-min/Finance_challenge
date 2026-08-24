"""
신한EZ손해보험 - 청크 f: 등급별 보장금액 (InsurerPlanCoverage + InsurerComparisonMetric)

## 자료 출처가 다른 6개사와 다르다 - 반드시 읽을 것
6개사분은 사용자가 정리해 준 엑셀
(`backend/data/source_files/insurer_plan_coverage_2026-08.xlsx`)에서
`app.seed_plan_coverage` / `app.seed_comparison_metrics`가 읽어 적재한다. 그 엑셀에는
신한 열이 없다. 신한 값의 근거는 **다이렉트 「보장 비교하기」 화면 캡처 2장**이다:

    backend/data/source_files/shinhan_plan_screenshots/direct_compare_1.jpg
    backend/data/source_files/shinhan_plan_screenshots/direct_compare_2.jpg

그래서 엑셀 경로에 신한을 끼워 넣지 않고 이 스크립트로 따로 적재하며,
source/collected_at에 "화면 캡처"라고 그대로 남긴다. 나중에 사용자가 신한 열을 엑셀에
추가하면 이 스크립트를 지우고 원래 경로로 합치는 게 맞다.

## 신한은 2등급이다
신한이 파는 등급은 **실속케어 / 안심케어** 둘뿐이다(6개사는 3등급). 화면의 3단계
"실속/표준/고급" 중 고급 자리는 비운다 - `insurer_tiers.TIER_PLAN_NAMES["SHINHAN"]`가
`["실속케어", "안심케어", None]`이고, 고급 등급 비교에서는 `_drop_insurers_without_plan`이
신한을 빼고 그 사유를 화면에 한 줄로 밝힌다.

실속케어를 실속에, 안심케어를 표준에 둔 근거는 금액 수준이다. 해외 실손의료비가
3,000만원 / 5,000만원인데, 다른 6개사의 실속 등급이 2,000~3,000만원, 표준이
3,000~5,000만원, 고급이 5,000만원~1억원 구간이다. 안심케어(5,000만원)를 고급에 두면
같은 금액의 다른 회사 표준 등급과 다른 칸에서 비교된다.

## 화면 캡처에 없어서 추론한 값 (source_note에도 남긴다)
1. **상해후유장해보험금** - 캡처에는 "상해 사망"만 있고 후유장해 금액이 따로 없다.
   보통약관 제3조 제2호가 후유장해보험금을 "장해분류표에서 정한 지급률을 보험가입금액에
   곱하여 산출한 금액"으로 정하므로 최대액은 상해사망과 같은 보험가입금액이다.
   현대해상·KB·삼성화재·DB손해보험도 이 둘이 통합 담보로 같은 금액이다.
2. **자택도난손해 / 상해입원일당** - 신한 약관 236쪽 전체에 해당 특별약관이 없다.
   "미제공"(상품 자체에 그 담보가 없음)으로 표기한다.
3. **출국항공기지연(지수형)** - 약관에는 [출국 항공기 지연 손해 특별약관]이 있지만
   캡처의 실속케어·안심케어 구성표에는 이 담보가 올라와 있지 않다. 등급 기본구성이
   아니라는 뜻이라 "미가입"으로 둔다(담보가 없는 "미제공"과 구분).

## 비교표 21항목에 자리가 없는 캡처 행
캡처에는 국내 비급여를 중증/비중증 × 상해/질병으로 네 줄(3,000·1,000·3,000·1,000만원)로
나눠 놨는데, 6개사 공통 비교표(21항목)에는 그 네 줄에 해당하는 칸이 없다(3대비급여와
MRI/MRA 두 줄만 있다). 비교표에서는 빠지지만 **InsurerPlanCoverage에는 캡처 원문 그대로
전부 넣는다** - 원문 대조가 필요하면 그쪽을 본다.

Run from ``backend``::

    python -m app.seed_shinhan_2026_f
"""
from __future__ import annotations

from datetime import date

from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401
from app.models.kb import Insurer, InsurerComparisonMetric, InsurerPlanCoverage

INSURER_CODE = "SHINHAN"
PLANS = ("실속케어", "안심케어")

_SOURCE = "신한EZ손해보험 다이렉트 「보장 비교하기」 화면 캡처(사용자 제공)"
_COLLECTED_AT = date(2026, 8, 24)
_SOURCE_NOTE = (
    "신한EZ손해보험 값의 출처는 6개사와 다릅니다. 6개사는 사용자가 정리한 엑셀"
    "(insurer_plan_coverage_2026-08.xlsx)에서, 신한은 다이렉트 「보장 비교하기」 화면 캡처"
    "(backend/data/source_files/shinhan_plan_screenshots/)에서 옮겼습니다. "
    "신한은 실속케어·안심케어 2등급만 판매하므로 고급 등급 비교에서는 제외됩니다. "
    "상해후유장해보험금은 캡처에 별도 금액이 없어 상해사망과 같은 금액으로 두었습니다 — "
    "보통약관 제3조 제2호가 후유장해보험금을 보험가입금액에 장해지급률을 곱한 금액으로 정하고 있어 "
    "최대액이 상해사망과 같고, 현대해상·KB손해보험·삼성화재·DB손해보험도 두 담보가 통합되어 있습니다. "
    "자택도난손해·상해입원일당은 약관 236쪽에 해당 특별약관이 없어 '미제공'입니다. "
    "출국항공기지연(지수형)은 약관에는 특별약관이 있으나 캡처의 등급 구성표에 올라와 있지 않아 '미가입'입니다. "
    "보험료는 아직 확보하지 못해 순위에서 가격 축을 빼고 나머지 축으로 재정규화합니다."
)

#: 화면 캡처의 담보명·금액 그대로. (담보명, 실속케어, 안심케어)
#: unit은 전부 '만원'이며, 캡처의 순서를 sort_order로 그대로 재현한다.
PLAN_COVERAGE_ROWS: list[tuple[str, str, str]] = [
    ("해외병원 실손의료비 (상해)", "3000", "5000"),
    ("해외병원 실손의료비 (질병)", "3000", "5000"),
    ("휴대물품손해(분실제외)", "50", "100"),
    ("분실여권 재발급 비용", "6.7", "6.7"),
    ("항공기 수하물 지연비용", "30", "50"),
    ("여행 중 배상책임", "3000", "5000"),
    ("항공기 납치", "140", "140"),
    ("중대사고 구조 송환비용", "5000", "10000"),
    ("상해 사망", "10000", "20000"),
    ("질병사망/고도 후유장해", "3000", "5000"),
    ("국내(급여) 실손의료비(상해)", "3000", "5000"),
    ("국내(급여) 실손의료비(질병)", "3000", "5000"),
    ("국내(중증 비급여) 실손의료비(상해)", "3000", "5000"),
    ("국내(비중증 비급여) 실손의료비(상해)", "1000", "1000"),
    ("국내(중증 비급여) 실손의료비(질병)", "3000", "5000"),
    ("국내(비중증 비급여) 실손의료비(질병)", "1000", "1000"),
    ("국내(중증 비급여) 실손의료비(3대비급여)", "350", "350"),
    ("국내(비중증 비급여) 실손의료비(자기공명영상진단)", "200", "200"),
    ("해외여행중중단사고발생추가비용", "미가입", "30"),
    ("식중독 보상금", "미가입", "30"),
    ("특정전염병 보상금", "미가입", "30"),
]

#: 6개사 공통 비교표(21항목)에 맞춘 값.
#: (category_order, category, sort_order, metric_label, 실속케어, 안심케어)
COMPARISON_ROWS: list[tuple[int, str, int, str, str, str]] = [
    (0, "사망 · 후유장해", 0, "상해사망보험금", "10000", "20000"),
    (0, "사망 · 후유장해", 1, "상해후유장해보험금", "10000", "20000"),
    (0, "사망 · 후유장해", 2, "질병사망/고도후유장해", "3000", "5000"),

    (1, "의료비", 0, "해외 상해의료비", "3000", "5000"),
    (1, "의료비", 1, "해외 질병의료비", "3000", "5000"),
    (1, "의료비", 2, "국내 상해의료비(급여)", "3000", "5000"),
    (1, "의료비", 3, "국내 질병의료비(급여)", "3000", "5000"),
    (1, "의료비", 4, "국내 3대 비급여의료비", "350", "350"),
    (1, "의료비", 5, "국내 비급여 MRI/MRA", "200", "200"),

    (2, "휴대품 · 도난 · 배상책임", 0, "휴대품손해(분실제외)", "50", "100"),
    (2, "휴대품 · 도난 · 배상책임", 1, "자택도난손해", "미제공", "미제공"),
    (2, "휴대품 · 도난 · 배상책임", 2, "배상책임", "3000", "5000"),

    (3, "항공기 · 수하물 지연", 0, "수하물/항공편 지연", "30", "50"),
    (3, "항공기 · 수하물 지연", 1, "출국항공기지연(지수형)", "미가입", "미가입"),

    (4, "기타 특수담보", 0, "여권분실 재발급비용", "6.7", "6.7"),
    (4, "기타 특수담보", 1, "중대사고 구조송환비용", "5000", "10000"),
    (4, "기타 특수담보", 2, "항공기납치위로금", "140", "140"),
    (4, "기타 특수담보", 3, "여행중단 추가비용", "미가입", "30"),
    (4, "기타 특수담보", 4, "식중독 보상", "미가입", "30"),
    (4, "기타 특수담보", 5, "특정전염병 보상금", "미가입", "30"),
    (4, "기타 특수담보", 6, "상해입원일당", "미제공", "미제공"),
]


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        insurer = db.query(Insurer).filter_by(code=INSURER_CODE).first()
        if insurer is None:
            raise SystemExit("신한 보험사가 없습니다. app.seed_shinhan_2026_a부터 실행하세요.")

        # 이 보험사분만 통째로 새로 채운다(등급이 늘거나 값이 바뀔 수 있어 부분 갱신보다 안전).
        db.query(InsurerPlanCoverage).filter_by(insurer_id=insurer.insurer_id).delete()
        db.query(InsurerComparisonMetric).filter_by(insurer_id=insurer.insurer_id).delete()

        made_cov = 0
        for order, (label, *amounts) in enumerate(PLAN_COVERAGE_ROWS):
            for plan_name, amount_text in zip(PLANS, amounts):
                db.add(InsurerPlanCoverage(
                    insurer_id=insurer.insurer_id, plan_name=plan_name,
                    coverage_label=label, amount_text=amount_text, unit="만원",
                    sort_order=order, source=_SOURCE, source_note=_SOURCE_NOTE,
                    collected_at=_COLLECTED_AT,
                ))
                made_cov += 1

        made_metric = 0
        for cat_order, category, sort_order, metric_label, *values in COMPARISON_ROWS:
            for plan_name, value_text in zip(PLANS, values):
                db.add(InsurerComparisonMetric(
                    category=category, category_order=cat_order,
                    metric_label=metric_label, sort_order=sort_order,
                    insurer_id=insurer.insurer_id, plan_name=plan_name,
                    value_text=value_text, unit="만원",
                    source=_SOURCE, source_note=_SOURCE_NOTE, collected_at=_COLLECTED_AT,
                ))
                made_metric += 1

        db.commit()
        print(f"InsurerPlanCoverage {made_cov}건 적재 ({len(PLAN_COVERAGE_ROWS)}담보 x {len(PLANS)}등급)")
        print(f"InsurerComparisonMetric {made_metric}건 적재 ({len(COMPARISON_ROWS)}항목 x {len(PLANS)}등급)")
    finally:
        db.close()


if __name__ == "__main__":
    run()
