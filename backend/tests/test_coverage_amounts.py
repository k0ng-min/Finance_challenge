"""청구 검토 결과에 붙는 "이 사고에 해당하는 담보의 가입금액" 조회 테스트.

약관(Coverage.limit_amount)에 한도가 적혀 있는 담보는 170개 중 27개뿐이라, 사고를 접수하고
청구 검토 결과를 봐도 정작 "얼마나 받을 수 있나"가 대부분 비어 있었다. 보험사 공시에서
받아온 등급별 가입금액표(InsurerComparisonMetric)에는 그 값이 전 보험사·전 등급에 다 있으니,
표준담보코드(coverage_std.std_code)로 그 표를 찾아 채운다.

여기서 제일 깨지기 쉬운 건 매핑의 문자열이다 — 담보 코드나 항목 이름을 하나라도 잘못 적으면
조용히 "금액 없음"이 되고 아무도 모른다. 그래서 매핑에 적힌 모든 이름이 실제 KB에 있는지부터
확인한다.
"""
import pytest

from app.models.kb import CoverageStd, InsurerComparisonMetric
from app.services.coverage_amounts import (
    STD_CODE_TO_METRIC_LABELS,
    amount_for_std_code,
)


def test_mapped_metric_labels_all_exist_in_kb(kb_session):
    """매핑이 가리키는 항목 이름이 전부 실제 비교표에 있어야 한다(오타 방지)."""
    real = {row.metric_label for row in kb_session.query(InsurerComparisonMetric).all()}
    assert real, "비교표가 비어 있어 검증할 수 없습니다"
    mapped = {label for labels in STD_CODE_TO_METRIC_LABELS.values() for label in labels}
    assert mapped - real == set()


def test_mapped_std_codes_all_exist_in_kb(kb_session):
    """매핑이 가리키는 표준담보 코드도 전부 실제로 있어야 한다."""
    real = {row.std_code for row in kb_session.query(CoverageStd).all()}
    assert real, "표준담보가 비어 있어 검증할 수 없습니다"
    assert set(STD_CODE_TO_METRIC_LABELS) - real == set()


@pytest.mark.parametrize(
    "insurer_code,plan_name,std_code,expected",
    [
        # 비교표 원문 값 그대로: DB손보 실속형 해외 상해의료비 5,000만원
        ("DB", "실속형", "OVS_INJ_MED", "5,000만원"),
        ("HYUNDAI", "실속형", "OVS_INJ_MED", "2,000만원"),
        ("KAKAOPAY", "플러스", "OVS_INJ_MED", "10,000만원"),
    ],
)
def test_amount_for_std_code(kb_session, insurer_code, plan_name, std_code, expected):
    got = amount_for_std_code(
        kb_session, insurer_code=insurer_code, plan_name=plan_name, std_code=std_code
    )
    assert got is not None
    assert got.startswith(expected)


def test_death_injury_shows_both_death_and_disability(kb_session):
    """상해사망·후유장해는 비교표에서 두 줄로 갈려 있다 — 한 줄만 보여주면 절반이 사라진다."""
    got = amount_for_std_code(
        kb_session, insurer_code="DB", plan_name="표준형", std_code="DEATH_INJURY"
    )
    assert got is not None
    assert "상해사망보험금" in got and "상해후유장해보험금" in got


def test_amount_names_the_plan_it_came_from(kb_session):
    """이 금액은 '그 보험사 그 등급' 기준이라, 어느 등급인지 빼면 근거 없는 숫자가 된다."""
    got = amount_for_std_code(
        kb_session, insurer_code="DB", plan_name="실속형", std_code="OVS_INJ_MED"
    )
    assert "실속형" in got


def test_unknown_inputs_return_none(kb_session):
    """등급을 모르거나(등록 시 안 고름) 매핑에 없는 담보면 지어내지 않고 비운다."""
    assert amount_for_std_code(
        kb_session, insurer_code="DB", plan_name=None, std_code="OVS_INJ_MED"
    ) is None
    assert amount_for_std_code(
        kb_session, insurer_code="DB", plan_name="실속형", std_code="NO_SUCH_CODE"
    ) is None
    assert amount_for_std_code(
        kb_session, insurer_code="NOPE", plan_name="실속형", std_code="OVS_INJ_MED"
    ) is None


def test_non_numeric_values_are_not_shown(kb_session):
    """'-'(미가입)이나 '가입'처럼 숫자가 아닌 표기는 금액으로 내보내지 않는다.

    비교표 원문에는 미가입·가입·미제공 같은 표기가 섞여 있다. 그걸 그대로 '가입금액'
    자리에 넣으면 금액인 척 읽힌다.
    """
    for row in kb_session.query(InsurerComparisonMetric).all():
        if row.value_text.strip().isdigit():
            continue
        # 숫자가 아닌 값을 가진 항목은, 그 항목을 가리키는 코드로 조회해도 그 값이
        # 그대로 나오면 안 된다.
        for code, labels in STD_CODE_TO_METRIC_LABELS.items():
            if row.metric_label not in labels:
                continue
            got = amount_for_std_code(
                kb_session,
                insurer_code=row.insurer.code,
                plan_name=row.plan_name,
                std_code=code,
            )
            if got is not None:
                assert row.value_text not in got
