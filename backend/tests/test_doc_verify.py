"""서류 사진 판독 결과를 체크리스트 상태로 옮기는 규칙.

이 파일은 Gemini를 부르지 않는다. "모델이 이렇게 답했을 때 상태를 뭘로 둘 것인가"만
결정적으로 검증한다 — 판독 실패를 서류 미비로 잘못 단정하지 않는 게 핵심이다.
"""
import pytest

from app.services.doc_verify import DocCheck, VerifiedDoc, decide_status


def _doc(*, readable=True, grounded=(), practical=()):
    return VerifiedDoc(
        readable=readable,
        unreadable_reason=None if readable else "글자가 흐려서 읽을 수 없습니다",
        detected_doc_type="진료비계산서",
        language="일본어",
        translation="병원 영수증입니다",
        grounded=[DocCheck(code=c, label=c, found=f, quote=None) for c, f in grounded],
        practical=[DocCheck(code=c, label=c, found=f, quote=None) for c, f in practical],
    )


def test_약관_요건이_모두_확인되면_보유로_바뀐다():
    result = decide_status(_doc(grounded=[("ISSUER_MEDICAL", True)], practical=[("AMOUNT", True)]))

    assert result.status == "보유"


def test_약관_요건이_하나라도_안_보이면_미보유로_바뀐다():
    result = decide_status(_doc(grounded=[("ISSUER_MEDICAL", False)], practical=[("AMOUNT", True)]))

    assert result.status == "미보유"


def test_판독_불가면_상태를_바꾸지_않는다():
    """사진이 흐리거나 잘린 것과 서류에 항목이 없는 것은 다르다. 사진 문제일 때 '미보유'로
    단정하면 실제로는 갖고 있는 서류를 없다고 표시하게 된다."""
    result = decide_status(_doc(readable=False, grounded=[("ISSUER_MEDICAL", False)]))

    assert result.status is None
    assert "다시" in result.message


def test_약관_요건이_없는_서류는_실무항목만으로_상태를_바꾸지_않는다():
    """경찰 신고확인서처럼 약관에 세부 요건이 없는 서류가 있다. 근거 없는 실무 항목만으로
    '미보유'라고 단정하지 않는다 — 사용자가 직접 고르도록 남겨둔다."""
    result = decide_status(_doc(grounded=[], practical=[("DATE", False)]))

    assert result.status is None


def test_요약은_약관_요건_충족_개수만_남긴다():
    """진단명·금액 같은 내용은 저장하지 않는다(민감정보). 건조한 집계만 남긴다."""
    result = decide_status(_doc(
        grounded=[("ISSUER_MEDICAL", True), ("PHOTO_ID", False)],
        practical=[("AMOUNT", True)],
    ))

    assert result.summary == "약관 요건 2개 중 1개 확인"
    assert "진료비계산서" not in result.summary
    assert "병원" not in result.summary


@pytest.mark.parametrize("reason", ["", None])
def test_판독_불가인데_이유가_비어도_안내문이_나온다(reason):
    doc = _doc(readable=False)
    doc.unreadable_reason = reason

    result = decide_status(doc)

    assert result.status is None
    assert result.message
