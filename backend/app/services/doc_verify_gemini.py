"""서류 사진 한 장을 Gemini로 읽어 번역하고 요건을 대조한다.

이 모듈만 이미지 바이트를 만진다. 바이트는 함수 밖으로 나가지 않고, 호출이 끝나면
참조가 끊긴다 — 디스크에 쓰지 않는다(진단서는 민감정보라 보관 자체를 하지 않기로 했다).

Gemini가 꺼져 있으면 규칙기반으로 흉내내지 않고 None을 돌려준다. 사진을 읽는 일은
폴백이 존재할 수 없는 기능이라, 못 하는데 하는 척하는 게 더 나쁘다.
"""
from __future__ import annotations

import json as _json

from pydantic import BaseModel, Field

from app import config
from app.services.doc_verify import DocCheck, VerifiedDoc

# 약관에 근거가 없는, 실무에서 흔히 반려되는 항목. 화면에서 약관 요건과 칸을 나눠 보여주고
# 이 결과만으로는 체크리스트 상태를 바꾸지 않는다(doc_verify.decide_status 참고).
PRACTICAL_CHECKS: dict[str, list[tuple[str, str]]] = {
    "MEDICAL_EXPENSE_CERT": [
        ("PATIENT", "환자 이름"),
        ("AMOUNT", "결제 금액"),
        ("DATE", "진료 날짜"),
        ("FACILITY", "병원 이름"),
    ],
    "MEDICAL_DETAIL_CERT": [("PATIENT", "환자 이름"), ("ITEMS", "항목별 진료 내역"), ("DATE", "진료 날짜")],
    "TREATMENT_CERT": [("PATIENT", "환자 이름"), ("PERIOD", "입원·통원 기간"), ("FACILITY", "병원 이름")],
    "PRESCRIPTION": [("PATIENT", "환자 이름"), ("DRUGS", "처방된 약 이름"), ("DATE", "처방 날짜")],
    "DISABILITY_CERT": [("PATIENT", "환자 이름"), ("DIAGNOSIS", "진단 내용"), ("DATE", "진단 날짜")],
    "DEATH_CERT": [("NAME", "사망자 이름"), ("DATE", "사망 일시"), ("FACILITY", "발급 기관")],
    "POLICE_REPORT": [("DATE", "신고 날짜"), ("PLACE", "발생 장소"), ("SUMMARY", "사고 내용")],
    "FLIGHT_DELAY_CERT": [("FLIGHT", "항공편 번호"), ("DELAY", "지연·결항 사실"), ("DATE", "해당 날짜")],
    "BAGGAGE_IRREGULARITY": [("REFERENCE", "접수 번호"), ("FLIGHT", "항공편 번호"), ("DATE", "접수 날짜")],
    "PASSPORT_REISSUE_RECEIPT": [("NAME", "신청인 이름"), ("AMOUNT", "결제 금액"), ("DATE", "발급 날짜")],
}


class _CheckOut(BaseModel):
    code: str
    found: bool
    quote: str | None = Field(default=None, description="서류에서 근거가 된 부분(원문 그대로)")


class _VerifyOut(BaseModel):
    readable: bool = Field(description="글자를 읽을 수 있으면 true")
    unreadable_reason: str | None = None
    detected_doc_type: str | None = None
    language: str | None = None
    translation: str | None = Field(default=None, description="한국어 요약 번역, 3문장 이내")
    checks: list[_CheckOut] = Field(default_factory=list)


_PROMPT = """당신은 해외 여행자보험 청구서류를 검토합니다.

사용자가 올린 사진은 '{doc_name}'로 제출하려는 서류입니다.

할 일:
1. 사진에서 글자를 읽을 수 있는지 판단하세요. 흐리거나, 잘렸거나, 문서가 아니면
   readable=false로 두고 unreadable_reason에 한국어로 이유를 한 문장 적으세요.
2. 어떤 서류로 보이는지(detected_doc_type)와 무슨 언어인지(language)를 적으세요.
3. 내용을 한국어로 3문장 이내로 요약해 translation에 적으세요.
4. 아래 각 항목이 서류에 실제로 있는지 확인해 checks에 담으세요. 코드는 그대로 쓰세요.
   추측하지 말고, 사진에서 보이는 것만 found=true로 두세요.
   found=true면 quote에 근거가 된 서류 속 문구를 원문 그대로 옮기세요.

확인할 항목:
{check_list}
"""


def _get_client():
    from google import genai
    return genai.Client(api_key=config.GEMINI_API_KEY)


def verify_document(
    image_bytes: bytes,
    mime_type: str,
    doc_code: str,
    doc_name: str,
    grounded_requirements: list[tuple[str, str]],
) -> VerifiedDoc | None:
    """사진을 읽어 요건별 확인 결과를 만든다. Gemini가 꺼져 있거나 실패하면 None.

    grounded_requirements: [(코드, 라벨)] — 약관 조항에 근거가 있는 요건.
    """
    if not config.GEMINI_ENABLED or not image_bytes:
        return None

    practical = PRACTICAL_CHECKS.get(doc_code, [])
    all_checks = [(code, label) for code, label in grounded_requirements] + practical
    if not all_checks:
        all_checks = [("EXISTS", "이 서류로 볼 수 있는 내용")]

    check_list = "\n".join(f"- {code}: {label}" for code, label in all_checks)
    prompt = _PROMPT.format(doc_name=doc_name, check_list=check_list)

    try:
        from google.genai import types

        client = _get_client()
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt,
            ],
            config={
                "response_mime_type": "application/json",
                "response_schema": _VerifyOut,
            },
        )
        parsed = _VerifyOut.model_validate(_json.loads(response.text))
    except Exception:
        # 쿼터 초과·네트워크 오류 등. 라우터가 "지금은 확인할 수 없다"로 안내한다.
        return None

    labels = dict(all_checks)
    grounded_codes = {code for code, _ in grounded_requirements}
    by_code = {c.code: c for c in parsed.checks}

    def build(codes) -> list[DocCheck]:
        out = []
        for code, label in all_checks:
            if code not in codes:
                continue
            got = by_code.get(code)
            out.append(DocCheck(
                code=code,
                label=labels.get(code, code),
                found=bool(got and got.found),
                quote=(got.quote if got else None),
            ))
        return out

    return VerifiedDoc(
        readable=parsed.readable,
        unreadable_reason=parsed.unreadable_reason,
        detected_doc_type=parsed.detected_doc_type,
        language=parsed.language,
        translation=parsed.translation,
        grounded=build(grounded_codes),
        practical=build({code for code, _ in practical}),
    )
