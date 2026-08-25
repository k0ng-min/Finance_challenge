"""조항 원문을 화면 인용용으로 자르는 한 가지 방법.

자르기만 하고 말줄임표를 붙이지 않으므로 결과는 **항상 원문의 연속 부분 문자열**이다 —
"인용문은 원문의 부분 문자열"이라는 검증(tests)이 이 함수를 쓰는 모든 화면에 그대로
적용된다.

중복보장 진단(coverage_overlap)에서 쓰던 규칙을 현지 대응 팩(onsite)에서도 그대로
쓰기 위해 공용 모듈로 옮겼다. 인용 규칙이 화면마다 갈라지면 어느 화면의 인용이 원문을
보존하는지 일일이 따져야 한다.
"""
from __future__ import annotations

from app.models.kb import Clause

#: 인용문 최대 길이. 화면에 넣기 좋은 만큼만 자른다.
QUOTE_LIMIT = 200


def quote_clause(clause: Clause | None, anchor_phrase: str | None = None) -> str | None:
    """조항 원문을 인용용으로 자른다.

    근거로 삼는 문구(anchor_phrase)가 조항 뒷부분에 있으면, 앞에서부터 무조건 자르는
    방식은 그 문구를 통째로 잘라버려 "인용은 있는데 근거는 없는" 상태가 된다.
    anchor_phrase가 주어지면 그 문구를 포함하는 창(window)을 대신 잘라낸다.
    """
    if clause is None or not clause.text:
        return None
    text = clause.text.strip()
    if len(text) <= QUOTE_LIMIT:
        return text

    if anchor_phrase:
        idx = text.find(anchor_phrase)
        if idx != -1:
            anchor_len = len(anchor_phrase)
            # anchor가 창 안에서 가운데쯤 오도록 시작점을 잡되, 텍스트 경계를 넘지 않게 보정한다.
            start = max(0, idx - (QUOTE_LIMIT - anchor_len) // 2)
            end = min(len(text), start + QUOTE_LIMIT)
            start = max(0, end - QUOTE_LIMIT)
            return text[start:end]

    return text[:QUOTE_LIMIT]
