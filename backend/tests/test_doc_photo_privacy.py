"""서류 사진 고지문이 실제 서버 동작과 맞는지 지킨다.

화면은 파일을 고르기 전에 이렇게 알린다.

  · 사진·PDF는 Google Gemini API로 전송된다
  · 보험펜 서버에는 사진 원본도 번역문도 저장하지 않는다
  · 다만 체크리스트에는 서류 상태와 "약관 요건 N개 중 M개 확인" 개수 요약이 남는다

말은 쉽게 낡는다. 코드가 조용히 바뀌어 번역문을 DB에 한 줄 남기기 시작해도 화면 문구는
그대로일 것이고, 그러면 우리는 사용자에게 사실과 다른 말을 하게 된다. 그 세 줄이
계속 사실이도록 여기서 붙잡아 둔다.
"""
import inspect

import pytest

from app.models.user import Evidence
from app.routers import incidents as incidents_router
from app.services import doc_verify, doc_verify_gemini
from app.services.doc_verify import DocCheck, VerifiedDoc, decide_status


def _verified(**kw) -> VerifiedDoc:
    base = dict(
        readable=True, unreadable_reason=None, detected_doc_type="영수증",
        language="영어", translation="치료비 120달러를 결제한 영수증입니다.",
        grounded=[DocCheck(code="ISSUER_MEDICAL", label="의료기관 발행", found=True, quote="ABC Clinic")],
        practical=[DocCheck(code="AMOUNT", label="결제 금액", found=True, quote="USD 120.00")],
    )
    base.update(kw)
    return VerifiedDoc(**base)


def test_체크리스트에_남는_것은_상태와_개수뿐이다():
    """번역문도, 서류에서 뽑은 인용문도 memo에 들어가지 않는다."""
    decision = decide_status(_verified())

    assert decision.summary == "약관 요건 1개 중 1개 확인"
    for leaked in ("치료비", "120", "ABC Clinic", "USD", "영수증"):
        assert leaked not in decision.summary, f"요약에 서류 내용이 새어 들어갔습니다: {leaked}"


def test_Evidence에_저장되는_칸은_상태와_요약뿐이다(db_session):
    """모델이 바뀌어 이미지나 번역문을 담을 칸이 생기면 고지문도 같이 바뀌어야 한다."""
    columns = {c.name for c in Evidence.__table__.columns}
    금지 = {"image", "image_bytes", "photo", "file_path", "translation", "translated_text", "raw_text"}
    assert not (columns & 금지), f"Evidence에 서류 내용을 담는 칸이 생겼습니다: {columns & 금지}"


def test_업로드_경로가_이미지_바이트를_저장하지_않는다():
    """엔드포인트 본문에 파일을 디스크나 DB로 넘기는 코드가 없어야 한다.

    구현을 문자열로 들여다보는 건 거친 방법이지만, 여기서 막으려는 사고("사진을 어딘가에
    남기는 코드가 슬쩍 들어옴")는 결과값만 봐서는 잡히지 않는다."""
    source = inspect.getsource(incidents_router.verify_document_photo)

    for 금지 in ("open(", "write(", "shutil", "save(", "aiofiles", "os.path.join"):
        assert 금지 not in source, f"업로드 경로에 파일을 남기는 코드가 있습니다: {금지}"
    # 바이트 참조를 끊는 줄이 남아 있는지 — 이 줄은 약속을 코드로 적어 둔 것이다.
    assert "del image_bytes" in source


def test_이미지_바이트는_Gemini_모듈_밖으로_나가지_않는다():
    """이미지를 만지는 곳을 한 군데로 묶어 둔다. 여러 곳이 만지기 시작하면 '어디에도
    저장하지 않는다'를 사람이 눈으로 확인할 수 없게 된다."""
    source = inspect.getsource(doc_verify_gemini)
    assert "image_bytes" in source
    # 판정 로직(doc_verify)은 이미지 근처에도 가지 않는다.
    assert "image_bytes" not in inspect.getsource(doc_verify)


def test_판독_실패면_체크리스트에_아무것도_남기지_않는다():
    """흐린 사진 한 장으로 '서류 없음'을 단정하지 않는다. 상태가 None이면 라우터가
    Evidence를 아예 건드리지 않는다(고지문의 '남는 것' 목록이 그만큼 더 짧아진다)."""
    decision = decide_status(_verified(readable=False, unreadable_reason="사진이 흐려요."))
    assert decision.status is None


@pytest.mark.parametrize("금지어", ["완전히 익명", "외부로 전송되지 않", "전송하지 않습니다"])
def test_안내_문구에_사실과_다른_표현을_쓰지_않는다(금지어):
    """서버 코드가 사용자에게 돌려주는 문장에 '외부 전송 없음'이나 '완전히 익명' 같은
    검증되지 않은 표현이 섞이면, 화면의 고지와 정면으로 어긋난다."""
    for module in (doc_verify, doc_verify_gemini, incidents_router):
        assert 금지어 not in inspect.getsource(module), (
            f"{module.__name__}에 사실과 다른 표현이 있습니다: {금지어}"
        )
