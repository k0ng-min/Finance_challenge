"""서류 사진 업로드가 받아들이는 것을 좁게 유지한다.

Content-Type은 클라이언트가 자기 마음대로 붙이는 값이다. 그것만 믿으면 확장자와 헤더만
이미지로 위장한 임의 파일이 그대로 통과해 외부 API(Gemini)로 넘어간다. 실제 내용의
앞부분 바이트를 대조해 한 겹 더 거른다.
"""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.kb import RequiredDocStd
from app.models.user import AppUser, Incident
from app.services.auth import hash_session_token

AUTH = {"Authorization": "Bearer up-token"}
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
JPEG = b"\xff\xd8\xff" + b"0" * 64
PDF = b"%PDF-1.4\n" + b"0" * 64


@pytest.fixture
def client(db_session):
    user = AppUser(
        nickname="업로더", auth_provider="guest",
        session_token=hash_session_token("up-token"),
        session_expires_at=datetime.utcnow() + timedelta(days=1),
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(Incident(incident_id=1, user_id=user.user_id))
    db_session.add(RequiredDocStd(required_doc_std_id=1, doc_code="CLAIM_FORM",
                                  doc_name="보험금 청구서", acquire_location="공통"))
    db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def upload(client, data: bytes, content_type: str = "image/png"):
    return client.post(
        "/incidents/1/documents/1/verify",
        headers=AUTH,
        files={"file": ("doc.png", data, content_type)},
    )


def test_이미지인_척하는_실행파일은_거부한다(client):
    """확장자와 Content-Type만 이미지로 맞춘 파일. 내용은 Windows 실행파일이다."""
    res = upload(client, b"MZ\x90\x00" + b"\x00" * 128)

    assert res.status_code == 400, f"위장 파일이 {res.status_code}로 통과했습니다"
    # 어떤 검사에 걸렸는지 알려주면 우회 방법을 알려주는 셈이다.
    assert "매직" not in res.text and "시그니처" not in res.text


def test_스크립트_내용도_거부한다(client):
    res = upload(client, b"<?php system($_GET['c']); ?>")

    assert res.status_code == 400


def test_빈_파일은_거부한다(client):
    res = upload(client, b"")

    assert res.status_code == 400


@pytest.mark.parametrize("data,ctype", [(PNG, "image/png"), (JPEG, "image/jpeg"), (PDF, "application/pdf")])
def test_실제_이미지_PDF는_형식_검사를_통과한다(client, data, ctype):
    """형식 검사는 넘어가야 한다. 그 뒤 Gemini가 꺼져 있으면 503으로 막히는데(키 없음),
    400이 아니라는 것이 곧 '형식 때문에 막힌 게 아니다'라는 뜻이다."""
    res = upload(client, data, ctype)

    assert res.status_code != 400, f"정상 파일이 형식 검사에서 막혔습니다: {res.text[:100]}"


def test_허용하지_않는_Content_Type은_거부한다(client):
    res = upload(client, PNG, "text/html")

    assert res.status_code == 400


def test_토큰_없이는_업로드할_수_없다(client):
    res = client.post("/incidents/1/documents/1/verify",
                      files={"file": ("doc.png", PNG, "image/png")})

    assert res.status_code == 401
