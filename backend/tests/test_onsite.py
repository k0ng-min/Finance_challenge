"""현지 대응 팩(「현지에서」) 검증.

핵심은 두 가지다.

1. **근거 인용은 언제나 조항 원문의 부분 문자열이다** — 다른 화면(중복보장 진단,
   표준약관 대조)에 걸어둔 규칙을 이 화면에도 똑같이 건다.
2. **한국어가 사라지지 않는다** — 현지어 카드는 창구에 보여주는 물건이라 번역이 붙지만,
   한국어 원문과 조항 인용이 함께 있어야 사용자가 자기가 뭘 보여주는지 알 수 있다.
   번역만 남고 한국어가 빈 행은 하나도 없어야 한다.
"""
import pytest

from app.models.kb import Clause, CountryLanguage, OnsitePhraseI18n
from app.services.onsite import LOCAL_ONLY, build_onsite_pack
from app.services.onsite_i18n import DEFAULT_LANG, resolve_language, translate


@pytest.fixture
def seeded(kb_session):
    """약관 KB 사본에 이번 기능의 시드를 얹은 세션."""
    from app.seed_country_language import seed as seed_lang
    from app.seed_onsite_phrases import seed as seed_phrases

    if kb_session.query(CountryLanguage).first() is None:
        seed_lang(kb_session)
    if kb_session.query(OnsitePhraseI18n).first() is None:
        seed_phrases(kb_session)
    kb_session.commit()
    return kb_session


def _all_docs(pack):
    for items in pack.docs_by_type.values():
        yield from items


def _all_requirements(pack):
    for doc in _all_docs(pack):
        yield from doc.requirements


def test_quotes_are_substrings_of_clause_text(seeded):
    """인용문에 원문에 없는 글자가 섞이면 "근거 있는 척"이 된다."""
    pack = build_onsite_pack(seeded, country="태국")
    checked = 0
    for req in _all_requirements(pack):
        assert req.clause_id is not None
        clause = seeded.get(Clause, req.clause_id)
        assert clause is not None
        assert req.clause_quote
        assert req.clause_quote in clause.text, (
            f"인용문이 조항 {req.clause_id} 원문의 부분 문자열이 아닙니다: {req.clause_quote[:40]}"
        )
        checked += 1
    if checked == 0:
        pytest.skip(
            "doc_requirement가 아직 비어 있다 — 2026-08-18 약관 재구축 1차분은 "
            "coverage_doc_map까지만 다시 만들었고 doc_requirement(서류 세부요건 "
            "앵커)는 다음 단계로 미뤘다(dataset_manifest.json의 known_gap 참조)."
        )


def test_korean_is_never_dropped(seeded):
    """현지어만 남고 한국어가 비는 행이 있으면 안 된다."""
    pack = build_onsite_pack(seeded, country="일본")
    docs = list(_all_docs(pack))
    assert docs
    for doc in docs:
        assert doc.doc_name_ko and doc.doc_name_ko.strip()
    for req in _all_requirements(pack):
        assert req.label_ko and req.label_ko.strip()
    assert pack.intro_ko and pack.intro_ko.strip()


def test_local_language_is_attached_for_seeded_country(seeded):
    """시드된 언어(태국어)는 Gemini 없이도 붙는다."""
    pack = build_onsite_pack(seeded, country="태국")
    assert pack.lang_code == "th"
    assert pack.intro_local
    assert any(doc.doc_name_local for doc in _all_docs(pack))


def test_unknown_country_falls_back_to_english(seeded):
    """매핑에 없는 나라는 추측하지 않고 영어로 둔다."""
    lang, _ = resolve_language(seeded, "존재하지않는나라")
    assert lang == DEFAULT_LANG


def test_clause_text_is_never_translated(seeded):
    """조항 원문은 근거 그 자체라 번역 대상이 아니다 — 종류 자체를 거절한다."""
    with pytest.raises(ValueError):
        translate(seeded, "en", "영어", [("clause", 1, "조항 원문")])

    kinds = {row.kind for row in seeded.query(OnsitePhraseI18n).all()}
    assert kinds <= set(OnsitePhraseI18n.ALLOWED_KINDS)


def test_local_only_documents_come_first(seeded):
    """귀국하면 못 받는 서류가 목록 위로 온다 — 이 화면이 막으려는 실패가 그것이다."""
    pack = build_onsite_pack(seeded, country="태국")
    for items in pack.docs_by_type.values():
        seen_other = False
        for doc in items:
            if doc.acquire_location != LOCAL_ONLY:
                seen_other = True
            else:
                assert not seen_other, "현지only 서류가 나머지 뒤에 있습니다."


def test_progress_is_none_without_linked_incident(seeded):
    """연결된 사고가 없으면 진행률을 0/N으로 지어내지 않는다."""
    pack = build_onsite_pack(seeded, country="태국")
    assert pack.progress_total is None
    assert pack.progress_secured is None
    assert all(doc.status is None for doc in _all_docs(pack))


def test_all_six_insurers_are_named_without_a_policy(seeded):
    """보험 미등록이면 6개사 합집합을 보여주고, 요건마다 출처 보험사를 밝힌다."""
    pack = build_onsite_pack(seeded, country="태국")
    assert len(pack.insurer_names) == 6
    for req in _all_requirements(pack):
        assert req.insurer_name
