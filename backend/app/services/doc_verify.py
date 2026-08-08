"""서류 사진 판독 결과를 다루는 순수 로직(LLM 호출 없음).

읽어들인 결과를 체크리스트 상태로 옮길 때 지키는 규칙은 두 가지다.

1. 사진을 못 읽은 것과 서류에 항목이 없는 것은 다르다. 흐리거나 잘린 사진 때문에
   "미보유"로 단정하면, 실제로 갖고 있는 서류를 없다고 표시하게 된다. 판독 실패는
   상태를 건드리지 않고 다시 찍어달라고만 한다.
2. 상태를 바꾸는 근거는 약관에 적힌 요건(DocRequirement)뿐이다. 금액·진료일자 같은
   실무 점검 항목은 약관 근거가 없으므로 보여주기만 하고 상태를 바꾸지 않는다.

여기서 만드는 요약(summary)에는 진단명·금액·병원명 같은 내용을 절대 넣지 않는다.
사진과 번역문을 저장하지 않기로 했는데 요약에 내용이 남으면 같은 정보를 남기는 셈이다.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DocCheck:
    """요건 하나의 확인 결과."""
    code: str
    label: str
    found: bool
    # 모델이 근거로 든 서류 속 문구(화면에 한 번 보여줄 뿐 저장하지 않는다).
    quote: str | None = None


@dataclass
class VerifiedDoc:
    """사진 한 장을 읽어낸 결과."""
    readable: bool
    unreadable_reason: str | None
    detected_doc_type: str | None
    language: str | None
    translation: str | None
    grounded: list[DocCheck] = field(default_factory=list)
    practical: list[DocCheck] = field(default_factory=list)


@dataclass
class StatusDecision:
    """체크리스트에 반영할 내용. status가 None이면 기존 상태를 그대로 둔다."""
    status: str | None
    message: str
    summary: str


_RETRY_ACTION = "밝은 곳에서 문서 전체가 나오게 다시 찍어주세요."
_RETRY_MESSAGE = f"사진에서 글자를 읽지 못했어요. {_RETRY_ACTION}"


def decide_status(doc: VerifiedDoc) -> StatusDecision:
    total = len(doc.grounded)
    met = sum(1 for check in doc.grounded if check.found)
    summary = f"약관 요건 {total}개 중 {met}개 확인" if total else "약관에 정해진 서류 요건 없음"

    if not doc.readable:
        # 원인만 알려주면 사용자는 뭘 해야 할지 모른다. 원인 뒤에 다음 행동을 붙인다.
        reason = (doc.unreadable_reason or "").strip()
        message = f"{reason} {_RETRY_ACTION}" if reason else _RETRY_MESSAGE
        return StatusDecision(status=None, message=message, summary=summary)

    if not doc.grounded:
        # 약관에 세부 요건이 없는 서류(경찰 신고확인서 등). 실무 항목만 보여주고 판단은
        # 사용자에게 맡긴다 — 근거 없이 미보유로 내리지 않는다.
        return StatusDecision(
            status=None,
            message="이 서류는 약관에 정해진 형식 요건이 없어요. 내용을 보고 직접 골라주세요.",
            summary=summary,
        )

    if met == total:
        return StatusDecision(status="보유", message="약관이 요구하는 내용이 모두 확인됐어요.", summary=summary)

    missing = [check.label for check in doc.grounded if not check.found]
    return StatusDecision(
        status="미보유",
        message="약관이 요구하는 내용 중 " + ", ".join(missing) + "을(를) 찾지 못했어요.",
        summary=summary,
    )
