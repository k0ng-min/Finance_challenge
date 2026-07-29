"""
NLU/LLM 추상화 레이어 (ne.md 11.3 "LLM의 역할" 대응).

설계 원칙
---------
1. 외부 AI API(OpenAI/Anthropic/Gemini 등)를 호출하지 않는다.
   팀 계획상 이 자리에는 나중에 자체 제작한 초경량 로컬 모델이 들어간다.
2. 그래서 라우터/규칙엔진은 절대 이 모듈의 "구현"에 의존하지 않고, 아래 NLUEngine
   인터페이스에만 의존한다. 나중에 LightLocalNLU 같은 클래스 하나만 추가하고
   get_nlu_engine()의 분기만 바꾸면, 호출부(routers, rules.py) 코드는 안 건드려도 된다.
3. 지금 기본 구현(RuleBasedNLU)은 정규식/키워드/문자열유사도 기반 스텁이다.
   정확도가 낮을 수 있으므로, 이 결과는 항상 "초안(draft)"으로만 쓰고
   question_bank 능동질문 엔진이 빈 필드·저신뢰 필드를 다시 사용자에게 확인하게 한다.
   → 즉 "가벼운 모델의 부정확함"을 능동 질문으로 보완하는 것이 이 프로젝트 아키텍처의 핵심 전제다.
4. 이 인터페이스가 반환하는 값에는 confidence를 반드시 포함한다. 규칙 엔진과
   근거검증(finding_evidence_link) 쪽에서 confidence가 낮은 필드는 그대로 추천에
   쓰지 않고 "확인 필요"로 돌리기 위함이다(ne.md 절대규칙 6, 7).
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ExtractedField:
    value: str | bool | None
    confidence: float  # 0.0~1.0. 규칙기반 스텁은 매칭 성공 시에도 1.0을 주지 않는다.
    source_span: str | None = None  # 원문 중 근거가 된 부분 (사용자에게 "이렇게 이해했어요" 보여주기용)


@dataclass
class IncidentDraft:
    """사고내용 자유서술 → 구조화 초안. incident 테이블 필드에 대응."""
    country: ExtractedField = field(default_factory=lambda: ExtractedField(None, 0.0))
    cause: ExtractedField = field(default_factory=lambda: ExtractedField(None, 0.0))
    injury_part: ExtractedField = field(default_factory=lambda: ExtractedField(None, 0.0))
    diagnosis: ExtractedField = field(default_factory=lambda: ExtractedField(None, 0.0))
    hospitalized: ExtractedField = field(default_factory=lambda: ExtractedField(None, 0.0))
    surgery: ExtractedField = field(default_factory=lambda: ExtractedField(None, 0.0))
    local_treatment: ExtractedField = field(default_factory=lambda: ExtractedField(None, 0.0))
    returned_home: ExtractedField = field(default_factory=lambda: ExtractedField(None, 0.0))

    def missing_or_low_confidence(self, threshold: float = 0.6) -> list[str]:
        out = []
        for name in self.__dataclass_fields__:
            f: ExtractedField = getattr(self, name)
            if f.value is None or f.confidence < threshold:
                out.append(name)
        return out


class NLUEngine(Protocol):
    """자유서술 구조화·담보명 표준화·쉬운말 설명을 위한 공통 인터페이스."""

    def structure_incident(self, free_text: str) -> IncidentDraft: ...

    def normalize_coverage_name(self, raw_name: str, std_candidates: list[tuple[str, str]]) -> tuple[str | None, float]:
        """raw_name(보험사별 원문 담보명)을 std_candidates([(std_code, std_name), ...]) 중
        가장 가까운 std_code로 매핑한다. (std_code, confidence) 반환. 매칭 실패 시 (None, 0.0)."""
        ...

    def explain_clause_plain(self, clause_text: str) -> str:
        """약관 원문을 쉬운 말로 바꾼다. 원문 자체를 대체하지 않고 병기용으로만 쓴다."""
        ...


# --- 규칙 기반 기본 구현 (외부 API 미사용) ---------------------------------

_CAUSE_KEYWORDS = ["낙상", "충돌", "미끄러짐", "교통사고", "추락", "화상", "골절", "타박상", "염좌"]
_INJURY_PART_KEYWORDS = ["머리", "두부", "허리", "다리", "발목", "손목", "무릎", "어깨", "팔", "손가락"]
_HOSPITALIZED_HINTS = ["입원"]
_SURGERY_HINTS = ["수술"]
_LOCAL_TREATMENT_HINTS = ["현지 병원", "현지병원", "현지에서 치료", "응급실"]
_RETURNED_HOME_HINTS = ["귀국", "한국 도착", "귀국 후"]
_COUNTRY_HINTS = [  # MVP 데모용 최소 목록. 실제로는 국가 사전 테이블로 분리 예정.
    "일본", "스위스", "태국", "베트남", "필리핀", "미국", "프랑스", "이탈리아", "괌", "사이판",
]


class RuleBasedNLU:
    """
    현재 기본으로 주입되는 구현체. 정규식/키워드 매칭만 사용하며 모델 추론이 없다.
    자체 초경량 모델이 준비되면 이 클래스와 동일한 인터페이스로 LightLocalNLU를 추가하고
    get_nlu_engine()에서 교체하면 된다 (routers/rules.py 수정 불필요).
    """

    def _find_keyword(self, text: str, keywords: list[str]) -> ExtractedField:
        for kw in keywords:
            if kw in text:
                return ExtractedField(value=kw, confidence=0.7, source_span=kw)
        return ExtractedField(value=None, confidence=0.0)

    _NEGATION_MARKERS = ["아직", "안 ", "않", "못", "전이", "전입니다", "전임"]

    def _is_negated(self, clause: str, keyword: str) -> bool:
        idx = clause.find(keyword)
        before = clause[max(0, idx - 8):idx]
        after = clause[idx + len(keyword):idx + len(keyword) + 6]
        return any(m in before for m in self._NEGATION_MARKERS) or any(m in after for m in self._NEGATION_MARKERS)

    def _find_bool(self, text: str, hints: list[str]) -> ExtractedField:
        # 절 단위로 끊어서 부정어("아직 ~ 전")가 같은 절에 있으면 뒤집는다.
        # 그래도 규칙기반 부정 탐지는 허술하므로 confidence를 낮게 준다 — 능동질문으로 재확인 유도.
        clauses = re.split(r"[.!?\n]", text)
        for clause in clauses:
            for h in hints:
                if h in clause:
                    if self._is_negated(clause, h):
                        return ExtractedField(value=False, confidence=0.4, source_span=clause.strip())
                    return ExtractedField(value=True, confidence=0.7, source_span=h)
        return ExtractedField(value=False, confidence=0.3)  # 명시적 부정 근거는 없으므로 저신뢰

    def structure_incident(self, free_text: str) -> IncidentDraft:
        text = free_text or ""
        return IncidentDraft(
            country=self._find_keyword(text, _COUNTRY_HINTS),
            cause=self._find_keyword(text, _CAUSE_KEYWORDS),
            injury_part=self._find_keyword(text, _INJURY_PART_KEYWORDS),
            diagnosis=ExtractedField(value=None, confidence=0.0),  # 진단명은 규칙기반으로 추출 불가 → 항상 질문 필요
            hospitalized=self._find_bool(text, _HOSPITALIZED_HINTS),
            surgery=self._find_bool(text, _SURGERY_HINTS),
            local_treatment=self._find_bool(text, _LOCAL_TREATMENT_HINTS),
            returned_home=self._find_bool(text, _RETURNED_HOME_HINTS),
        )

    def normalize_coverage_name(self, raw_name: str, std_candidates: list[tuple[str, str]]) -> tuple[str | None, float]:
        if not raw_name or not std_candidates:
            return None, 0.0
        best_code, best_score = None, 0.0
        for std_code, std_name in std_candidates:
            score = difflib.SequenceMatcher(None, raw_name, std_name).ratio()
            if score > best_score:
                best_code, best_score = std_code, score
        if best_score < 0.35:
            return None, 0.0
        return best_code, round(best_score, 2)

    def explain_clause_plain(self, clause_text: str) -> str:
        # 진짜 쉬운말 변환(패러프레이즈)은 모델이 필요한 영역이라 지금은 수행하지 않는다.
        # 원문을 그대로 반환해 "쉬운말 설명 미지원(원문 표시)"임을 명확히 한다.
        return clause_text


_engine_singleton: NLUEngine | None = None


def get_nlu_engine() -> NLUEngine:
    """
    의존성 주입 지점. 지금은 RuleBasedNLU 고정.
    자체 경량 모델이 준비되면 여기 분기만 추가한다. 예:
        backend = os.getenv("NLU_BACKEND", "rule_based")
        if backend == "light_local_llm":
            return LightLocalNLU(model_path=...)
    """
    global _engine_singleton
    if _engine_singleton is None:
        _engine_singleton = RuleBasedNLU()
    return _engine_singleton
