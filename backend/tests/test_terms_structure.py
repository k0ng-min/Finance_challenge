"""약관 제목 헤딩 추출 테스트."""
from scripts.map_terms_structure import headings

SAMPLE = """

===PAGE 43===
배상책임 특별약관
제1조(보상하는 손해)
회사는 피보험자가 여행도중에 생긴 보험사고로 인하여 피해자에게 법률상의

===PAGE 44===
가적으로 부담한 비용 손해를 이 특별약관
에 따라 보상합니다.

===PAGE 58===
해외여행중 중대사고 구조송환비용 특별약관
"""


def test_headings_are_page_and_title_pairs():
    assert (43, "배상책임 특별약관") in headings(SAMPLE)
    assert (58, "해외여행중 중대사고 구조송환비용 특별약관") in headings(SAMPLE)


def test_mid_sentence_reference_is_not_a_heading():
    """'... 이 특별약관' 처럼 문장이 끊긴 줄은 제목이 아니다."""
    titles = [title for _, title in headings(SAMPLE)]
    assert not any(title.startswith("가적으로") for title in titles)
    assert all("이 특별약관" != title for title in titles)
