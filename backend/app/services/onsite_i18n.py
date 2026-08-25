"""현지어 문구 조회 — 시드 우선, 없으면 Gemini, 그것도 없으면 한국어만.

**조항 원문은 이 파일을 통과하지 않는다.** 조항은 근거 그 자체라 번역하지 않고 한국어
원문 그대로 인용한다. 여기서 다루는 것은 서류명·요건 표시문구·창구 안내문 세 가지뿐이고,
`OnsitePhraseI18n.ALLOWED_KINDS`가 그것을 강제한다.

번역이 없을 때 기능을 막지 않는 이유: 서류 목록·약관 요건·근거 조항은 번역 없이도
그대로 유효하다. 번역은 전달 수단이지 결과의 근거가 아니다. (서류 사진 확인처럼 LLM이
없으면 결과 자체가 존재할 수 없는 기능과는 다르게 다룬다.)
"""
from __future__ import annotations

import json
import logging

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import config
from app.models.kb import CountryLanguage, OnsitePhraseI18n

logger = logging.getLogger(__name__)

DEFAULT_LANG = "en"
DEFAULT_LANG_NAME = "영어"

# 한 번에 번역을 요청할 최대 문구 수. 현지 대응 팩 하나가 다루는 문구는 서류 14종 +
# 요건 몇 개 + 안내문 1개 수준이라 이 한도에 걸릴 일이 사실상 없다. 한도를 두는 것은
# 데이터가 늘었을 때 프롬프트가 통째로 커지는 것을 막기 위해서다.
_BATCH_LIMIT = 40

_PROMPT = """다음은 해외에서 보험금 청구용 서류를 요청할 때 병원·경찰서·항공사 창구에
그대로 보여줄 문구입니다. 각 항목을 {lang_name}(으)로 번역하세요.

번역 규칙:
1. 각 항목은 그 나라 의료·행정 문서 창구에서 실제로 쓰이는 용어로 옮기세요.
   직역보다 그 나라에서 통용되는 서류 이름을 우선하세요.
2. 원문에 없는 내용을 덧붙이거나, 있는 항목을 빼지 마세요.
3. 입력과 같은 개수의 항목을, 같은 순서로 반환하세요.
4. 설명이나 주석 없이 번역문만 반환하세요.

번역할 문구:
{items}
"""


class _Translated(BaseModel):
    items: list[str]


def resolve_language(db: Session, country: str | None) -> tuple[str, str]:
    """목적지 → (언어코드, 한국어 언어이름). 매핑이 없으면 추측하지 않고 영어로 둔다."""
    if country and country.strip():
        row = (
            db.query(CountryLanguage)
            .filter(CountryLanguage.country_name == country.strip())
            .order_by(CountryLanguage.is_primary.desc(), CountryLanguage.id)
            .first()
        )
        if row:
            return row.lang_code, row.lang_name_ko
    return DEFAULT_LANG, DEFAULT_LANG_NAME


def _cached(db: Session, lang: str, keys: list[tuple[str, int]]) -> dict[tuple[str, int], str]:
    if not keys:
        return {}
    kinds = {k for k, _ in keys}
    ref_ids = {r for _, r in keys}
    rows = (
        db.query(OnsitePhraseI18n)
        .filter(
            OnsitePhraseI18n.lang_code == lang,
            OnsitePhraseI18n.kind.in_(kinds),
            OnsitePhraseI18n.ref_id.in_(ref_ids),
        )
        .all()
    )
    wanted = set(keys)
    return {(r.kind, r.ref_id): r.text for r in rows if (r.kind, r.ref_id) in wanted}


def _translate_with_gemini(texts: list[str], lang_name: str) -> list[str] | None:
    """실패하면 None. 개수가 어긋나도 None — 항목이 밀려서 엉뚱한 서류에 붙는 것을 막는다."""
    if not config.GEMINI_ENABLED or not texts:
        return None
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=config.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=_PROMPT.format(lang_name=lang_name, items=numbered),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_Translated,
                temperature=0.1,
            ),
        )
        parsed: _Translated = response.parsed or _Translated.model_validate(json.loads(response.text))
        if len(parsed.items) != len(texts):
            logger.warning("현지어 번역 개수 불일치(%d != %d), 번역 없이 진행",
                           len(parsed.items), len(texts))
            return None
        if any(not t.strip() for t in parsed.items):
            return None
        return [t.strip() for t in parsed.items]
    except Exception:
        logger.exception("현지어 번역 실패, 한국어만 표시")
        return None


def translate(
    db: Session, lang: str, lang_name: str, items: list[tuple[str, int, str]],
) -> dict[tuple[str, int], str]:
    """[(kind, ref_id, 한국어원문)] → {(kind, ref_id): 현지어}.

    번역을 못 구한 항목은 결과에서 빠진다 — 호출부는 그 자리에 한국어만 보여준다.
    빈 문자열이나 원문 그대로를 채워 넣지 않는다(번역된 척하지 않는다).
    """
    for kind, _, _ in items:
        if kind not in OnsitePhraseI18n.ALLOWED_KINDS:
            raise ValueError(f"번역할 수 없는 종류입니다: {kind}")

    # 한국어 화면이면 번역 자체가 필요 없다.
    if lang == "ko":
        return {}

    keys = [(kind, ref_id) for kind, ref_id, _ in items]
    result = _cached(db, lang, keys)

    missing = [(kind, ref_id, ko) for kind, ref_id, ko in items if (kind, ref_id) not in result]
    if not missing:
        return result
    missing = missing[:_BATCH_LIMIT]

    translated = _translate_with_gemini([ko for _, _, ko in missing], lang_name)
    if translated is None:
        return result

    for (kind, ref_id, _), text in zip(missing, translated):
        result[(kind, ref_id)] = text
        db.add(OnsitePhraseI18n(
            kind=kind, ref_id=ref_id, lang_code=lang, text=text, source="gemini",
        ))
    try:
        db.commit()
    except Exception:
        # 캐시 저장에 실패해도 이번 응답은 그대로 내보낸다 — 다음 요청에서 다시 만든다.
        db.rollback()
        logger.exception("현지어 번역 캐시 저장 실패")
    return result
