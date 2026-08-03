import pytest

from app.services.external_policy.indemnity import resolve_indemnity_generation


@pytest.mark.parametrize("ym,expected", [
    ("2005-01", 1),
    ("2009-09", 1),   # 1세대 마지막 달
    ("2009-10", 2),   # 2세대 첫 달
    ("2017-03", 2),   # 2세대 마지막 달
    ("2017-04", 3),   # 3세대 첫 달
    ("2021-06", 3),   # 3세대 마지막 달
    ("2021-07", 4),   # 4세대 첫 달
    ("2026-08", 4),
])
def test_가입시기로_세대를_판정한다(ym, expected):
    assert resolve_indemnity_generation(ym) == expected


@pytest.mark.parametrize("ym", [None, "", "몰라요", "2021", "2021-13", "202107"])
def test_알수없는_가입시기는_None을_돌려준다(ym):
    """세대를 모르면 추측하지 않는다 — 담보 자동채움을 건너뛰고 종류만 저장한다."""
    assert resolve_indemnity_generation(ym) is None
