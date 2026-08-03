"""실손의료보험 세대 판정.

실손은 2009년 표준화 이후 보험사별 보장내용이 동일하다. 그래서 "언제 가입했는지"만 알면
보장구조가 결정된다 — 사용자가 자기 가입금액을 몰라도 담보를 채울 수 있는 근거가 이것이다.
(보험다모아: "4세대 실손의료보험은 보험회사별 보장내용은 모두 표준화되어있지만,
보험료는 사업비 구조, 적용위험률 등에 따라 다를 수 있습니다")

세대별 자기부담률·한도 수치는 여기서 다루지 않는다. 금융감독원 표준약관 원문과 대조하기
전에는 숫자를 넣지 않는다.
"""
from __future__ import annotations

import re

_YM_RE = re.compile(r"^(\d{4})-(\d{2})$")

# (경계 년월, 그 년월까지의 세대). 위에서부터 순서대로 비교한다.
_BOUNDARIES = [
    ("2009-09", 1),
    ("2017-03", 2),
    ("2021-06", 3),
]
_LATEST_GENERATION = 4


def resolve_indemnity_generation(enrolled_ym: str | None) -> int | None:
    """가입 년월("YYYY-MM")로 실손 세대(1~4)를 정한다. 판정할 수 없으면 None.

    None을 돌려주는 경우 호출부는 담보 자동채움을 건너뛰고 보험 종류만 저장해야 한다.
    모르는 값을 그럴듯한 세대로 추측하면 근거 없는 진단이 나간다.
    """
    if not enrolled_ym:
        return None
    m = _YM_RE.match(enrolled_ym.strip())
    if not m:
        return None
    month = int(m.group(2))
    if not 1 <= month <= 12:
        return None

    for boundary, generation in _BOUNDARIES:
        if enrolled_ym <= boundary:  # "YYYY-MM"은 사전순 비교가 곧 시간순 비교다
            return generation
    return _LATEST_GENERATION
